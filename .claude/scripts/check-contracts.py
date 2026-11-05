#!/usr/bin/env python3
"""契約(OpenAPI)を検査し、設計 ⇄ 実装 ⇄ コードの三者を突き合わせる。

規範: .claude/directions/02-design.md / 03-impl.md の contracts 節

REST API の契約を OpenAPI で書く理由は「機械的に検査できるから」であって、
検査しなければ表を YAML に書き換えただけになる。このスクリプトがその検査である。

  CT1 OpenAPI として妥当か(パース可能・paths がある)
  CT2 エラー応答があるか(2xx だけの operation は未完成)
  CT3 02(設計)⇄ 03(実装)のパス・メソッドが一致するか
  CT4 コールグラフのエントリポイント ⇄ 03 の契約が一致するか  ★実装と契約の乖離
      **コード側の経路は2か所から読む** — 言語側の REST と、インフラ定義の API Gateway の
      経路(`routing`)。**どちらも 0 件なら「未検査」と出し、黙って飛ばさない**。
      **突き合わせ先は OpenAPI だけではない** — 契約が正しく非 REST の側に在る経路
      (WebSocket の升格点など)は、その契約の frontmatter に `endpoints:` を書けば
      覆っていると見なす。書く口が無かったころ、そういう経路は直しようの無い
      重大度「高」として出続けた(実測 2026-09-01: `GET /ws`)。
  CT5 片側にしか無い CTR-*
  CT6 `x-impl` のシンボルが callgraph に実在するか(抽出器が無い言語のシンボルは「未検査」として件数だけ出す)

**どちらが正かは決めない。** 事実の不一致として出す(CLAUDE.md 原則2)。

使い方:
    python3 .claude/scripts/check-contracts.py
    python3 .claude/scripts/check-contracts.py --list           # 実装している検査IDの一覧(正はここ)
    python3 .claude/scripts/check-contracts.py --format json
    python3 .claude/scripts/check-contracts.py --warn-only
    python3 .claude/scripts/check-contracts.py --no-callgraph   # CT4/CT6 を省く(高速)
    python3 .claude/scripts/check-contracts.py --selftest

終了コード: 0=重大度「高」なし(または --warn-only) 1=重大度「高」あり 2=使い方・解析エラー
(callgraph-check.py と同じ約束。「中」「低」だけでは 1 を返さない)
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import posixpath
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from cgx import base  # noqa: E402

DESIGN_DIR = "docs/02-design/contracts"
IMPL_DIR = "docs/03-impl/contracts"
OPENAPI_FENCE = re.compile(r"^```ya?ml\s+openapi\s*$(.*?)^```\s*$", re.M | re.S)
HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


def _load_yaml():
    try:
        import yaml
        return yaml
    except ImportError as exc:
        raise SystemExit(
            f"エラー: PyYAML が無い({exc})。"
            "`python3 .claude/scripts/setup-tools.py` でキット専用 venv に導入すること")


def _load_builder():
    spec = importlib.util.spec_from_file_location("build_callgraphs", _HERE / "build-callgraphs.py")
    mod = importlib.util.module_from_spec(spec)          # type: ignore[arg-type]
    spec.loader.exec_module(mod)                          # type: ignore[union-attr]
    return mod


def read_frontmatter(path: Path) -> dict[str, str]:
    """1行スカラーの辞書。**解析できないときは空を返すので、呼び出し元が黙って通さないこと**
    (KIT-changeset-ignores-broken-frontmatter と同型の穴。空 = 「REST ではない」と
    解釈されると、その契約は CT 検査を1つも受けずに合格に見える)。"""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    fm: dict[str, str] = {}
    for line in text.splitlines()[1:]:
        if line.rstrip() == "---":
            break
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip()
    return fm


# `endpoints:` を信用してよい kind(= 語彙内で、かつ REST でないもの)
NONREST_KINDS = ("data-schema", "event", "storage", "other")

ENDPOINT_ITEM = re.compile(r"^(?:(?P<m>[A-Za-z]+)\s+)?(?P<p>/\S*)$")


def parse_endpoints(raw: str) -> list[tuple[str, str]]:
    """非 REST 契約の frontmatter `endpoints:` を (METHOD, path) の一覧にする。

    **なぜ要るか**: CT4 はコードの経路を **OpenAPI としか**突き合わせない。だが経路の中には
    契約が正しく非 REST の側に在るものがある(WebSocket の升格点、Server-Sent Events)。
    宣言する口が無いと、**その経路は永久に「契約が無い」と重大度「高」で出続ける** —
    直しようが無い所見は、やがて一覧ごと読まれなくなる(実測 2026-09-01: `GET /ws`)。

    書き方は1行スカラー(frontmatter の解析器が1行しか読まないため)。
    角括弧は在っても無くてもよく、区切りはコンマ `,` である(全角の読点 `、` も受ける):

        endpoints: [GET /ws, /healthz]

    メソッドを省いた項目は `ANY` として、そのパスのどのメソッドにも当たる。
    """
    out: list[tuple[str, str]] = []
    for item in re.split(r"[,、]", raw.strip().strip("[]")):
        m = ENDPOINT_ITEM.match(item.strip().strip("\"'"))
        if m:
            out.append(((m.group("m") or "ANY").upper(), m.group("p")))
    return out


def covers(key: tuple[str, str], declared: list[tuple[str, str]]) -> bool:
    """コードの経路 key を、宣言 declared のどれかが覆っているか。`ANY` は総当たり。"""
    meth, path = key
    return any(p == path and (m == "ANY" or meth == "ANY" or m == meth)
               for m, p in declared)


# --------------------------------------------------------------------------- 収集

def load_contracts(root: Path, rel_dir: str, yaml) -> tuple[dict[str, dict], list[dict]]:
    """CTR-ID → {kind, spec, source, path}。spec は OpenAPI の dict(REST 以外は None)。"""
    out: dict[str, dict] = {}
    findings: list[dict] = []
    base_dir = root / rel_dir
    if not base_dir.is_dir():
        return out, findings

    for md in sorted(base_dir.rglob("*.md")):
        if md.name == "index.md":
            continue
        fm = read_frontmatter(md)
        cid = f"CTR-{fm.get('id', md.stem)}"
        rel = md.relative_to(root).as_posix()
        entry = {"kind": fm.get("kind", ""), "spec": None, "doc": rel,
                 "openapi": fm.get("openapi", ""), "spec_source": "",
                 "endpoints": parse_endpoints(fm.get("endpoints", ""))}
        out[cid] = entry
        if not entry["kind"]:
            # **黙って飛ばさない。** kind が空(frontmatter が壊れている / 雛形のまま)だと
            # 「REST ではない」と解釈され、この契約は CT 検査を1つも受けない。
            # 「検査した結果あわなかった」と「検査していない」は区別できなければならない。
            findings.append({"check": "CT1", "severity": "中", "subject": cid,
                             "detail": "kind が空(frontmatter が壊れているか雛形のまま)。"
                                       "この契約は CT 検査を1件も受けていない",
                             "evidence": rel})
            continue
        if entry["kind"] not in ("rest-api", "data-schema", "event", "storage", "other"):
            findings.append({"check": "CT1", "severity": "中", "subject": cid,
                             "detail": f"kind の値が語彙外: {entry['kind']}",
                             "evidence": rel})
            continue
        if entry["kind"] != "rest-api":
            continue        # 非 REST の突き合わせは endpoints(上で拾った)だけで行う

        ref = entry["openapi"]
        if not ref:
            findings.append({"check": "CT1", "severity": "高", "subject": cid,
                             "detail": "kind: rest-api なのに `openapi:` が無い",
                             "evidence": rel})
            continue
        if ref == "inline":
            m = OPENAPI_FENCE.search(md.read_text(encoding="utf-8"))
            if not m:
                findings.append({"check": "CT1", "severity": "高", "subject": cid,
                                 "detail": "`openapi: inline` だが ```yaml openapi ブロックが無い",
                                 "evidence": rel})
                continue
            raw, entry["spec_source"] = m.group(1), rel
        else:
            target = root / ref
            if not target.is_file():
                findings.append({"check": "CT1", "severity": "高", "subject": cid,
                                 "detail": f"`openapi: {ref}` のファイルが存在しない",
                                 "evidence": rel})
                continue
            raw, entry["spec_source"] = target.read_text(encoding="utf-8"), ref

        try:
            spec = yaml.safe_load(raw)
        except Exception as exc:
            findings.append({"check": "CT1", "severity": "高", "subject": cid,
                             "detail": f"OpenAPI が YAML として読めない: {exc}"[:150],
                             "evidence": entry["spec_source"]})
            continue
        if not isinstance(spec, dict) or "paths" not in spec:
            findings.append({"check": "CT1", "severity": "高", "subject": cid,
                             "detail": "OpenAPI に `paths` が無い",
                             "evidence": entry["spec_source"]})
            continue
        entry["spec"] = spec
    return out, findings


def server_prefix(spec: dict) -> str:
    for s in spec.get("servers") or []:
        url = str(s.get("url", ""))
        m = re.match(r"^(?:[a-z]+://[^/]+)?(/.*)$", url)
        if m and m.group(1) != "/":
            return m.group(1).rstrip("/")
    return ""


def operations(spec: dict) -> dict[tuple[str, str], dict]:
    """(METHOD, 正規化パス) → operation。"""
    out: dict[tuple[str, str], dict] = {}
    pre = server_prefix(spec)
    for raw_path, item in (spec.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        full = base.path_key(base.join_paths(pre, str(raw_path)))
        for meth, op in item.items():
            if meth.lower() in HTTP_METHODS and isinstance(op, dict):
                out[(meth.upper(), full)] = op
    return out


# --------------------------------------------------------------------------- 検査

def run_checks(root: Path, use_callgraph: bool) -> tuple[list[dict], dict]:
    yaml = _load_yaml()
    design, f1 = load_contracts(root, DESIGN_DIR, yaml)
    impl, f2 = load_contracts(root, IMPL_DIR, yaml)
    findings = f1 + f2

    def add(check, sev, subject, detail, evidence=""):
        findings.append({"check": check, "severity": sev, "subject": subject,
                         "detail": detail, "evidence": evidence})

    # CT2 エラー応答
    for side, table in (("02", design), ("03", impl)):
        for cid, e in sorted(table.items()):
            if not e["spec"]:
                continue
            for (meth, path), op in sorted(operations(e["spec"]).items()):
                codes = {str(c) for c in (op.get("responses") or {})}
                if not codes:
                    add("CT2", "高", cid, f"{meth} {path}: `responses` が無い", e["spec_source"])
                elif not any(c.startswith(("4", "5")) or c == "default" for c in codes):
                    add("CT2", "高", cid,
                        f"{meth} {path}: エラー応答が無い(定義は {', '.join(sorted(codes))} のみ)",
                        f"{side}: {e['spec_source']}")

    # CT5 片側にしか無い契約
    for cid in sorted(set(design) - set(impl)):
        add("CT5", "中", cid, "02 にあるが 03 に無い(未実装、または実装側の記載漏れ)",
            design[cid]["doc"])
    for cid in sorted(set(impl) - set(design)):
        add("CT5", "中", cid, "03 にあるが 02 に無い(設計漏れ、または設計外の実装)",
            impl[cid]["doc"])

    # CT3 02 ⇄ 03 の差分
    for cid in sorted(set(design) & set(impl)):
        d, i = design[cid], impl[cid]
        if not (d["spec"] and i["spec"]):
            continue
        if d["spec_source"] == i["spec_source"]:
            continue                     # 同じファイルを指している = 定義上一致
        dops, iops = set(operations(d["spec"])), set(operations(i["spec"]))
        for meth, path in sorted(dops - iops):
            add("CT3", "高", cid, f"設計にあるが実装に無い: {meth} {path}", d["doc"])
        for meth, path in sorted(iops - dops):
            add("CT3", "高", cid, f"実装にあるが設計に無い: {meth} {path}", i["doc"])

    stats = {"design": len(design), "impl": len(impl),
             "rest_design": sum(1 for e in design.values() if e["spec"]),
             "rest_impl": sum(1 for e in impl.values() if e["spec"]),
             "callgraph": False}

    if not use_callgraph:
        return findings, stats

    # CT4 / CT6 コールグラフとの突き合わせ
    cfg = base.load_config(root)
    builder = _load_builder()
    langs = [l for l, s in cfg["languages"].items() if s.get("enabled")]
    cg, _notes = builder.run_extractors(root, cfg, langs, None)
    stats["callgraph"] = True

    symbols: set[str] = set()
    for _lang, d in cg["languages"].items():
        symbols |= {s["id"] for s in d["symbols"]}
    spec_sources = {e["spec_source"] for e in impl.values() if e["spec_source"]}
    cg_eps, ep_stats = code_endpoints(cg, spec_sources, symbols)
    stats.update(ep_stats)

    contract_ops: dict[tuple[str, str], str] = {}
    exts = base.symbol_extensions(cfg)
    stats["ct6_unchecked"] = 0
    stats["ct6_unchecked_ids"] = []
    for cid, e in sorted(impl.items()):
        if not e["spec"]:
            continue
        for key, op in operations(e["spec"]).items():
            contract_ops[key] = cid
            verdict = ct6_verdict(op.get("x-impl"), symbols, exts, cfg, root)
            if verdict == "unchecked":
                stats["ct6_unchecked"] += 1
                stats["ct6_unchecked_ids"].append(f"{cid}: {op['x-impl']}")
            elif verdict == "missing":
                add("CT6", "中", cid,
                    f"{key[0]} {key[1]}: `x-impl` のシンボルが callgraph に無い: `{op['x-impl']}`",
                    e["spec_source"])

    # ★ 非 REST の契約が `endpoints:` で覆うと宣言した経路。**OpenAPI だけを見ると、
    # 契約が正しく非 REST の側に在る経路が永久に「高」で出続ける**(WebSocket の升格点)
    # **`kind` が語彙内のものだけを信用する。** 空・語彙外の契約は CT1「中」になるだけで
    # 落とされないので、そのままだと**壊れた frontmatter が CT4 の「高」を消せる** —
    # 「中」だけなら終了コードは 0 なので、重大な契約の欠落が黙って green になる
    nonrest: dict[tuple[str, str], str] = {}
    for cid, e in sorted(impl.items()):
        if e["kind"] not in NONREST_KINDS:
            continue
        for pair in e["endpoints"]:
            nonrest[pair] = cid

    ct4_findings, ct4_stats = ct4(cg_eps, contract_ops, nonrest)
    findings += ct4_findings
    stats.update(ct4_stats)
    return findings, stats


# HTTP の経路として照合してよいメソッド
ROUTE_METHODS = {m.upper() for m in HTTP_METHODS} | {"ANY"}
# WebSocket API だけが持つ予約ルートキー。HTTP の経路ではないと確定できる。
# **`$default` は入れない** — HTTP API にも在る catch-all なので、HTTP か WebSocket か確定できない
RESERVED_ROUTE_KEYS = {"$CONNECT", "$DISCONNECT"}


def _norm_rel(path: str) -> str:
    """リポジトリ相対パスの表記ゆれ(`./`・`a/../b`)を畳む。"""
    return posixpath.normpath(path.strip()) if path.strip() else ""


def code_endpoints(cg: dict, spec_sources: set[str],
                   symbols: set[str] | None = None) -> tuple[dict[tuple[str, str], str], dict]:
    """コールグラフの中間表現から、コード側の HTTP の経路 (METHOD, path_key) → handler を組む。

    **読む場所は2つある。** 言語側の抽出器が出す `languages[*].endpoints` の
    `protocol == "rest"`(Flask / FastAPI・Express・Go net/http のようにコードが経路を持つ構成)と、
    infra 抽出器が出す最上位の `routing` の `kind == "apigw"`(SAM の `Events: {Type: Api}`・
    ApiGatewayV2::Route・Terraform・API Gateway 統合つき OpenAPI のように、**経路がコードではなく
    インフラ定義に在る**構成)である。前者しか読まなかったころ、サーバレスの構成では経路が
    何十件抽出されていても CT4 の対象が常に 0 件になり、黙って飛ばされていた
    (実測 2026-09-21: `routing` の apigw 44 件に対し `protocol == "rest"` 0 件)。

    **取り込まない経路**(件数は stats に出す — 取り込まなかったことを黙らない):
      ・`kind == "alb"` — ALB のリスナールールは `/api/*` のような前方一致で**転送先の
        サービスへ振り分ける**ものであって、エンドポイントそのものではない。個々の経路は
        転送先のコードが持ち、言語側の抽出器が `rest` として出す。取り込むと、どの契約にも
        書きようの無い `ANY /api/{}` が CT4「高」で出続ける
      ・パスを論理IDから推定した経路(ApiGateway::Method。`cgx/infra.py` が出典に
        「推定」と書く)— 推定のパスと契約を照合すると、両向きに偽の所見を出す
      ・03 の契約自身が指す OpenAPI から読んだ経路 — 契約を契約自身と照合することになり、
        CT4 が中身を見ずに一致してしまう(`./api/x.yaml` と `api/x.yaml` を同じものと見る)
      ・`METHOD /path` の形でない経路 — ApiGatewayV2::Route は WebSocket API の `$connect` /
        `$disconnect` / 任意のルートキーと HTTP API の `$default` も同じ資源で受けるので、
        `cgx/infra.py` はそれも apigw として出す。**中間表現は HTTP と WebSocket の別を持たず、
        キーの文字種からも判別できない**(WebSocket のキーは `chat/join` のような任意の値でよく、
        Terraform の `${var.method}` のような未解決の式と見分けが付かない)。そこで**経路の形で**分ける:
          - WebSocket の予約キー(`$connect` / `$disconnect`)→ HTTP ではない。落とす
            (`$default` は HTTP API にも在るので、下の「区別できない」に入る)
          - メソッドが HTTP でなく、パスが `/` 以外 → 元が「<メソッド> <パス>」の形 = HTTP の経路で
            メソッドだけが未解決。`ANY` として取り込み、パスだけで照合する(件数は NOTE)
          - メソッドが HTTP でなく、パスが `/` → WebSocket のキー(空白が無いのでパスが `/` に補われる)か、
            キー全体が未解決の式か、区別できない。**照合に使わず、未検査として件数を見出しと合格文に出す**
        **残る限界**: 空白を含む WebSocket のキーは、抽出器が最初の空白で分けてパスの先頭に `/` を補うので、
        HTTP の経路と見分けられない。`[item1, item2]` は `ANY /item2]` という架空の経路になって偽の CT4「高」を
        出し、キーがたまたま `GET /foo` の形なら、同じ経路の REST 契約が在ると**黙って一致してしまう**。
        中間表現に元のキーも API の種別も残らないので、ここでは直せない。根本の直しは、
        抽出器(`cgx/infra.py`)が経路ごとに HTTP / WebSocket の別を持つことである

    同じ鍵が両方に在るときは言語側のハンドラを採る(シンボルIDとして正確なため)。
    経路どうしで鍵が重なるとき(同じテンプレートの展開前と展開後など)は、ハンドラが
    `symbols` に実在するほうを採る — 所見の根拠に、辿れないパスを出さないため。
    """
    cg_eps: dict[tuple[str, str], str] = {}
    for _lang, d in cg.get("languages", {}).items():
        for ep in d.get("endpoints", []):
            if ep.get("protocol") == "rest" and ep.get("path_key"):
                cg_eps[((ep.get("method") or "ANY").upper(), ep["path_key"])] = ep.get("handler", "")
    rest_count = len(cg_eps)
    routed = alb = guessed = self_ref = nonhttp = dynamic = unknown = 0
    own_specs = {_norm_rel(p) for p in spec_sources}
    routed_keys: set[tuple[str, str]] = set()
    for r in cg.get("routing", []):
        m, t = r.get("match") or {}, r.get("target") or {}
        src = str(r.get("source", ""))
        if r.get("kind") == "alb":
            alb += 1
            continue
        if r.get("kind") != "apigw" or not m.get("path_key"):
            continue
        meth = (m.get("method") or "ANY").upper()
        if meth not in ROUTE_METHODS:
            if meth in RESERVED_ROUTE_KEYS:
                nonhttp += 1            # WebSocket の予約ルート。HTTP の経路ではないと確定している
                continue
            if m["path_key"] == "/":
                unknown += 1            # WebSocket のキーか、鍵全体が未解決の式か、区別できない
                continue
            meth = "ANY"                # 「<式> /path」= HTTP の経路でメソッドだけが未解決
            dynamic += 1
        if not str(m["path_key"]).startswith("/"):
            nonhttp += 1
            continue
        if "推定" in src:
            guessed += 1
            continue
        if _norm_rel(src.split("::", 1)[0]) in own_specs:
            self_ref += 1
            continue
        key = (meth, m["path_key"])
        ref = t.get("ref") or ""
        handler = t.get("handler_hint") or (f"{t.get('type', '')}:{ref}" if ref else "")
        if key not in cg_eps:
            routed += 1
            cg_eps[key] = handler
            routed_keys.add(key)
        elif key in routed_keys and symbols and handler in symbols \
                and cg_eps[key] not in symbols:
            cg_eps[key] = handler
    stats = {"cg_endpoints": len(cg_eps), "cg_rest_endpoints": rest_count,
             "cg_apigw_routes": routed}
    for name, n in (("cg_skipped_alb", alb), ("cg_skipped_guessed", guessed),
                    ("cg_skipped_self", self_ref), ("cg_skipped_nonhttp", nonhttp),
                    ("cg_dynamic_method", dynamic), ("cg_unknown_routes", unknown)):
        if n:
            stats[name] = n
    return cg_eps, stats


def ct4(cg_eps: dict[tuple[str, str], str], contract_ops: dict[tuple[str, str], str],
        nonrest: dict[tuple[str, str], str]) -> tuple[list[dict], dict]:
    """CT4 コードの経路 ⇄ 03 の契約。(所見, stats) を返す。"""
    findings: list[dict] = []
    stats: dict = {}

    def add(sev, subject, detail, evidence):
        findings.append({"check": "CT4", "severity": sev, "subject": subject,
                         "detail": detail, "evidence": evidence})

    if not cg_eps:
        # **0 件と突き合わせたことを「突き合わせた」と言わない。** 入力が空になったことを
        # 合格と区別せずに返すと、抽出の取り違えが別の構成で再発しても黙って通る
        # (実測 2026-09-21: サーバレスの構成で CT4 がこうして飛ばされていた)。
        # 見出しには必ず「未検査」と出し、照合すべき契約の経路が在るのに照合できなかった
        # ときは所見にも立てる(json だけを読む側にも届くように)
        stats["ct4_unchecked"] = True
        declared = len(contract_ops) + len(nonrest)
        if declared:
            add("中", "(CT4 全体)",
                f"コードから HTTP の経路を1件も取れなかったので、契約の経路 {declared} 件を"
                "1件も突き合わせていない(CT4 は未検査。未検査は合格ではない)",
                "言語側の REST も API Gateway の経路も 0 件。抽出器が未対応の構成かもしれない")
        return findings, stats

    # 片側が "ANY"(メソッドを原理的に知れない抽出 — Go net/http の Handle/HandleFunc、
    # Express の all/use、ALB / API GW の ANY)のときは**パスだけで照合する**
    # (`cgx/boundaries.py` の同種の規則に揃える)。メソッドの照合は失われるので、
    # 黙って合格にせず件数を stats と NOTE に出す(「未検査は合格ではない」)。
    contract_paths = {p for _m, p in contract_ops}
    cg_any_paths = {p for m, p in cg_eps if m == "ANY"}
    any_matched = 0
    nonrest_matched = 0
    for key in sorted(set(cg_eps) - set(contract_ops)):
        meth, path = key
        if meth == "ANY" and path in contract_paths:
            any_matched += 1
            continue
        if covers(key, list(nonrest)):
            nonrest_matched += 1
            continue
        add("高", f"{meth} {path}",
            "コードにこのエンドポイントがあるが、03 のどの契約も覆っていない"
            "(OpenAPI の `paths` にも、非 REST 契約の `endpoints:` にも無い)",
            f"handler: {cg_eps[key] or '(未特定)'}")
    for key in sorted(set(contract_ops) - set(cg_eps)):
        meth, path = key
        if path in cg_any_paths:
            any_matched += 1
            continue
        add("中", contract_ops[key],
            f"契約にあるが、コードにエンドポイントが見つからない: {meth} {path}",
            "抽出器が未対応の言語かもしれない。Tier を確認すること")
    # ★ 非 REST の `endpoints:` も**両向きに**見る。コード→契約だけだと、
    # 消した経路や打ち間違えた経路の宣言が残っても誰も気づかない
    cg_keys = list(cg_eps)
    for pair, cid in sorted(nonrest.items()):
        if covers(pair, cg_keys):
            continue
        add("中", cid,
            f"契約の `endpoints:` にあるが、コードにエンドポイントが見つからない: "
            f"{pair[0]} {pair[1]}",
            "経路を消したか綴りを誤ったか、抽出器が未対応の言語である")
    if any_matched:
        stats["ct4_any_path_matched"] = any_matched
    if nonrest_matched:
        stats["ct4_nonrest_matched"] = nonrest_matched
    return findings, stats


# --------------------------------------------------------------------------- 本体

# 実装している検査の一覧(--list で出す。IDの正はここ)
CHECKS = {
    "CT1": "OpenAPI として妥当か(パース可能・paths がある・kind と openapi: の整合)",
    "CT2": "エラー応答があるか(2xx だけの operation は未完成)",
    "CT3": "02(設計)⇄ 03(実装)のパス・メソッドが一致するか",
    "CT4": "コールグラフのエントリポイント ⇄ 03 の契約が一致するか",
    "CT5": "片側にしか無い CTR-*",
    "CT6": "x-impl のシンボルが callgraph に実在するか(抽出器が無い言語のものは未検査として件数を出す)",
}


def ct6_verdict(ximpl, symbols: set[str], exts: set[str], cfg: dict,
                root: Path | None) -> str:
    """CT6 の1件の判定: "ok" / "missing"(CT6 中)/ "unchecked"(抽出器が無い言語)。

    抽出器が無い言語の `x-impl` は callgraph に無くて当然 — CT6 にせず未検査として数える
    (KIT-callgraph-ft1-unsupported-lang。機能表の入口の FT1 と同じ判定 `base.unextracted_symbol`)。
    """
    if not ximpl or not symbols or ximpl in symbols:
        return "ok"
    return "unchecked" if base.unextracted_symbol(ximpl, exts, cfg, root) else "missing"


def selftest() -> int:
    ok = True
    # ★ 抽出器が無い言語の x-impl は CT6 にせず未検査に数える(KIT-callgraph-ft1-unsupported-lang)。
    # 「抽出器が無い」は設定で決まる(go は有効なのにシンボル 0 件でも .go は照合する)。
    # 判定できないもの・消えたファイル・テストは従来どおり CT6 に回す
    import tempfile
    ccfg = {"languages": {"python": {"enabled": True, "extensions": [".py"]},
                          "go": {"enabled": True, "extensions": [".go"]},
                          "kotlin": {"enabled": True, "extensions": [".kt"]},   # 抽出器が未実装
                          "infra": {"enabled": True, "extensions": [".tf"]}},
            "test_markers": ["/tests/"]}
    exts = base.symbol_extensions(ccfg)
    if exts != {".py", ".go"}:
        print(f"NG シンボルを出す抽出器の拡張子 → {exts}"); ok = False
    syms = {"svc/app.py::h"}
    with tempfile.TemporaryDirectory() as tmp:
        troot = Path(tmp)
        for rel in ("app/src/App.kt", "infra/main.tf", "tests/x.kt"):
            (troot / rel).parent.mkdir(parents=True, exist_ok=True)
            (troot / rel).write_text("", encoding="utf-8")
        for sid, want in (("svc/app.py::h", "ok"), (None, "ok"),
                          ("app/src/App.kt::handle", "unchecked"),
                          ("infra/main.tf::aws_s3_bucket.b", "unchecked"),
                          ("svc/app.py::gone", "missing"), ("svc/main.go::main", "missing"),
                          ("app/src/Gone.kt::x", "missing"), ("tests/x.kt::t", "missing"),
                          ("POST /x", "missing"), ("Makefile::x", "missing")):
            got = ct6_verdict(sid, syms, exts, ccfg, troot)
            if got != want:
                print(f"NG CT6 の判定: {sid} → {got} != {want}"); ok = False
        if ct6_verdict("app/src/App.kt::handle", syms, exts, ccfg, None) != "missing":
            print("NG root を省いたのに CT6 を未検査に回している"); ok = False
    cases = [
        ("[GET /ws, /healthz]", [("GET", "/ws"), ("ANY", "/healthz")]),
        ("GET /ws", [("GET", "/ws")]),
        ("/ws", [("ANY", "/ws")]),
        ("", []),
        ("ws-session", []),                      # パスに見えないものは拾わない
    ]
    cases.append(("[GET /ws、POST /events]",                 # 全角の読点も受ける
                  [("GET", "/ws"), ("POST", "/events")]))
    for raw, want in cases:
        got = parse_endpoints(raw)
        if got != want:
            print(f"NG endpoints の解析: {raw!r} → {got} != {want}"); ok = False
    # ★ `endpoints:` を信用してよい kind は語彙内のものだけ(壊れた frontmatter で
    # CT4 の「高」が消せてしまうと、「中」しか出ないぶん終了コードが 0 になる)
    for bad in ("", "rest-api", "REST", "しらない種別"):
        if bad in NONREST_KINDS:
            print(f"NG 語彙外/REST の kind を信用している: {bad!r}"); ok = False
    for good in ("event", "data-schema", "storage", "other"):
        if good not in NONREST_KINDS:
            print(f"NG 語彙内の kind を落としている: {good!r}"); ok = False
    # 覆っているかの判定。`ANY` はどちらの側でも総当たりになる
    for key, decl, want in (
        (("GET", "/ws"), [("GET", "/ws")], True),
        (("GET", "/ws"), [("ANY", "/ws")], True),
        (("ANY", "/ws"), [("GET", "/ws")], True),
        (("POST", "/ws"), [("GET", "/ws")], False),
        (("GET", "/wsx"), [("GET", "/ws")], False),   # 前方一致にしない
        (("GET", "/ws"), [], False),
    ):
        if covers(key, decl) is not want:
            print(f"NG 覆いの判定: {key} vs {decl} → {covers(key, decl)} != {want}"); ok = False
    # ★ 言語側の REST が 0 件でも、API Gateway の経路(routing)があれば CT4 は走る。
    # 以前は前者しか読まず、サーバレスの構成で CT4 が常に 0 件のまま黙って飛ばされていた
    def route(kind, meth, pk, src, hint=""):
        return {"kind": kind, "match": {"method": meth, "path_key": pk},
                "target": {"type": "lambda", "ref": "Fn", "handler_hint": hint}, "source": src}
    cg = {"languages": {"python": {"symbols": [], "endpoints": [
              {"protocol": "event", "path_key": "", "handler": "h"}]}},
          "routing": [route("apigw", "POST", "/pay", "infra/t.yaml::Fn.Events.Pay", "svc/app.py::h"),
                      route("alb", "ANY", "/api/{}", "infra/t.yaml::Rule"),
                      route("apigw", "GET", "/PayRes", "infra/t.yaml::M(パスは論理IDから推定)"),
                      route("apigw", "GET", "/self", "api/openapi.yaml::/self")]}
    eps, st = code_endpoints(cg, {"api/openapi.yaml"})
    if eps != {("POST", "/pay"): "svc/app.py::h"}:
        print(f"NG REST 0件・経路あり: apigw の経路を取り込めていない / 除外が効いていない → {eps}")
        ok = False
    if (st.get("cg_rest_endpoints"), st.get("cg_apigw_routes"), st.get("cg_skipped_alb"),
            st.get("cg_skipped_guessed"), st.get("cg_skipped_self")) != (0, 1, 1, 1, 1):
        print(f"NG REST 0件・経路あり: 件数の stats が違う → {st}"); ok = False
    f4, s4 = ct4(eps, {("POST", "/pay"): "CTR-pay", ("GET", "/gone"): "CTR-pay"}, {})
    if s4.get("ct4_unchecked") or [(f["severity"], f["subject"]) for f in f4] != [("中", "CTR-pay")]:
        print(f"NG REST 0件・経路あり: 経路で CT4 が両向きに走っていない → {s4} {f4}"); ok = False
    # 同じ鍵なら言語側のハンドラを採る
    cg2 = {"languages": {"python": {"symbols": [], "endpoints": [
               {"protocol": "rest", "method": "post", "path_key": "/pay", "handler": "a.py::real"}]}},
           "routing": [route("apigw", "POST", "/pay", "t.yaml::Fn.Events.Pay", "a.py::hint")]}
    eps2, _ = code_endpoints(cg2, set())
    if eps2 != {("POST", "/pay"): "a.py::real"}:
        print(f"NG 同じ鍵で言語側のハンドラを採っていない → {eps2}"); ok = False
    # 経路どうしで鍵が重なるなら、ハンドラが実在シンボルのほうを採る(順序に依らない)
    cg3 = {"languages": {}, "routing": [
        route("apigw", "POST", "/r", "packaged.yaml::Fn.Events.R", "s3://b/k/app.py::h"),
        route("apigw", "POST", "/r", "template.yaml::Fn.Events.R", "svc/app.py::h")]}
    eps3, st3 = code_endpoints(cg3, set(), {"svc/app.py::h"})
    if eps3 != {("POST", "/r"): "svc/app.py::h"} or st3.get("cg_apigw_routes") != 1:
        print(f"NG 重なった経路で実在シンボルのハンドラを採っていない → {eps3} {st3}"); ok = False
    # ★ `METHOD /path` の形でない経路(WebSocket の `$connect`・HTTP API の `$default`)は
    # HTTP の経路として取り込まない。取り込むと、正しい WebSocket 構成に偽の CT4「高」が出る
    cg4 = {"languages": {}, "routing": [
        route("apigw", "$CONNECT", "/", "t.yaml::ConnectRoute"),
        route("apigw", "$DEFAULT", "/", "t.yaml::DefaultRoute"),
        route("apigw", "SENDMESSAGE", "/", "t.yaml::MsgRoute"),
        route("apigw", "GET", "/ok", "t.yaml::OkRoute")]}
    eps4, st4 = code_endpoints(cg4, set())
    if eps4 != {("GET", "/ok"): "lambda:Fn"} or st4.get("cg_skipped_nonhttp") != 1 \
            or st4.get("cg_unknown_routes") != 2:       # $DEFAULT は HTTP API にも在る = 判別できない
        print(f"NG HTTP でない経路を取り込んでいる → {eps4} {st4}"); ok = False
    # ★ ただしメソッドが未解決の式なら HTTP の経路でありうる — 落とさず ANY として照合する。
    # 落とすと、他にリテラルの経路が1件でも在れば CT4 は「検査済み」になり、契約の欠落を見逃す
    cg6 = {"languages": {}, "routing": [
        route("apigw", "GET", "/ok", "main.tf::aws_apigatewayv2_route.ok"),
        route("apigw", "${VAR.METHOD}", "/orders", "main.tf::aws_apigatewayv2_route.orders"),
        route("apigw", "{'REF': 'M'}", "/cfn", "t.yaml::Fn.Events.Dyn"),
        route("apigw", "CHAT.SEND", "/", "t.yaml::ChatRoute"),
        route("apigw", "CHAT/JOIN", "/", "t.yaml::JoinRoute"),     # WebSocket のキーは任意の値
        route("apigw", "CHAT:JOIN", "/", "t.yaml::Join2Route"),
        route("apigw", "${VAR.ROUTE_KEY}", "/", "main.tf::aws_apigatewayv2_route.k")]}
    eps6, st6 = code_endpoints(cg6, set())
    if set(eps6) != {("GET", "/ok"), ("ANY", "/orders"), ("ANY", "/cfn")} \
            or st6.get("cg_dynamic_method") != 2 or st6.get("cg_unknown_routes") != 4 \
            or st6.get("cg_skipped_nonhttp"):
        print(f"NG メソッドが未解決の経路の扱いが違う → {eps6} {st6}"); ok = False
    f6, _ = ct4(eps6, {("GET", "/ok"): "CTR-ok"}, {})
    if sorted(f["subject"] for f in f6 if f["severity"] == "高") != ["ANY /cfn", "ANY /orders"]:
        print(f"NG メソッドが未解決の経路の契約欠落を CT4「高」で出していない → {f6}"); ok = False
    # ★ 契約自身の OpenAPI の除外は、表記ゆれ(`./`・`..`)を畳んで比べる
    for own in ("./api/openapi.yaml", "api/../api/openapi.yaml", "api/openapi.yaml"):
        eps5, st5 = code_endpoints({"languages": {}, "routing": [
            route("apigw", "GET", "/x", "api/openapi.yaml::/x")]}, {own})
        if eps5 or st5.get("cg_skipped_self") != 1:
            print(f"NG 契約自身の OpenAPI を {own!r} の表記で除外できていない → {eps5}"); ok = False
    # ★ どちらも 0 件なら「未検査」を明示し、照合すべき契約の経路があれば所見にも立てる
    eps0, st0 = code_endpoints({"languages": {}, "routing": []}, set())
    f0, s0 = ct4(eps0, {("GET", "/x"): "CTR-x"}, {("GET", "/ws"): "CTR-ws"})
    if eps0 or st0.get("cg_endpoints") != 0 or not s0.get("ct4_unchecked") \
            or [(f["check"], f["severity"]) for f in f0] != [("CT4", "中")] \
            or "2 件" not in f0[0]["detail"]:
        print(f"NG どちらも0件: 未検査を明示していない → {st0} {s0} {f0}"); ok = False
    f00, s00 = ct4({}, {}, {})
    if f00 or not s00.get("ct4_unchecked"):
        print(f"NG どちらも0件・契約も0件: 未検査の印か所見の有無が違う → {s00} {f00}"); ok = False
    # ★ 人が読む見出し・json・終了コードまで「未検査」が届くこと(内部の印だけでは足りない)
    base_stats = {"design": 1, "impl": 1, "rest_design": 1, "rest_impl": 1, "callgraph": True}

    def run_report(fs, st, flags):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = report([dict(f) for f in fs], st, flags)
        return code, buf.getvalue()
    unchecked = {**base_stats, **st0, **s0}
    code, out = run_report(f0, unchecked, set())
    if code != 0 or "CT4 未検査" not in out or "件と突き合わせた" in out \
            or "\n合格" in out:
        print(f"NG 未検査の見出し・終了コードが違う → {code}\n{out}"); ok = False
    code, out = run_report([], {**base_stats, **st0, **s00}, set())
    if code != 0 or "合格(CT4 を除く)" not in out or "合格: 契約に不整合なし" in out:
        print(f"NG 所見0件・CT4 未検査を「合格」と言っている → {code}\n{out}"); ok = False
    code, out = run_report(f0, unchecked, {"--format=json"})
    got = json.loads(out)
    if code != 0 or not got["stats"].get("ct4_unchecked") \
            or [f["subject"] for f in got["findings"]] != ["(CT4 全体)"]:
        print(f"NG json に未検査が届いていない → {code} {got}"); ok = False
    checked = {**base_stats, **st, **s4}
    code, out = run_report(f4, checked, set())
    if code != 0 or "1 件と突き合わせた(言語側の REST 0 / API Gateway の経路 1)" not in out \
            or "ALB の前方一致 1 件" not in out:
        print(f"NG 突き合わせた件数・除外の NOTE が見出しに出ていない → {code}\n{out}"); ok = False
    code, out = run_report([], {**checked, "cg_unknown_routes": 2}, set())
    if code != 0 or "未検査 2 件" not in out or "合格(判別できない経路 2 件は未検査)" not in out \
            or "合格: 契約に不整合なし" in out:
        print(f"NG 判別できない経路を未検査と言わずに合格にしている → {code}\n{out}"); ok = False
    # ★ CT6 の未検査が見出しと、どの合格行にも届くこと(KIT-callgraph-ft1-unsupported-lang)
    for extra in ({}, {"ct4_unchecked": True}, {"cg_unknown_routes": 1}):
        code, out = run_report([], {**checked, **extra, "ct6_unchecked": 3}, set())
        if code != 0 or "CT6 未検査 3 件" not in out or "x-impl 3 件は未検査" not in out \
                or "合格: 契約に不整合なし" in out:
            print(f"NG CT6 の未検査が見出し・合格行に出ていない({extra})→ {code}\n{out}"); ok = False
    high = [{"check": "CT4", "severity": "高", "subject": "GET /y", "detail": "d", "evidence": "e"}]
    if run_report(high, checked, set())[0] != 1 or run_report(high, checked, {"--warn-only"})[0] != 0 \
            or run_report(high, checked, {"--format=json"})[0] != 1:
        print("NG 重大度「高」の終了コードの約束(1 / --warn-only で 0 / json でも 1)が崩れている")
        ok = False
    print("OK check-contracts: 非 REST 契約の endpoints の解析(コンマ・全角読点)/ "
          "経路の覆いの判定(ANY の総当たり・前方一致にしない)/ "
          "endpoints を信用する kind は語彙内のものだけ / "
          "REST 0件でも API Gateway の経路で CT4 が走る(ALB・推定パス・契約自身は除く)/ "
          "HTTP でない経路は取り込まない(メソッドだけ未解決なら ANY、判別できないものは未検査と明示)/ "
          "どちらも0件なら CT4 未検査を明示する(見出し・json・終了コード)/ "
          "抽出器が無い言語の x-impl は CT6 にせず未検査と明示する" if ok else "NG check-contracts")
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    if "--selftest" in argv[1:]:
        return selftest()
    if any(a in ("-h", "--help") for a in argv[1:]):
        print(__doc__)   # 明示要求は 0。使い方エラーの 2 と区別する(tools-readme §2)
        return 0
    flags = set(argv[1:])
    if "--list" in flags:
        for cid, desc in CHECKS.items():
            print(f"{cid}  {desc}")
        return 0
    if flags - {"--warn-only", "--format=json", "--format", "json",
                "--no-callgraph", "--selftest"}:
        print(__doc__)
        return 2

    root = base.find_root()
    base.ensure_kit_venv(root)
    findings, stats = run_checks(root, "--no-callgraph" not in flags)
    return report(findings, stats, flags)


def report(findings: list[dict], stats: dict, flags: set[str]) -> int:
    """所見と stats を印字し、終了コードを返す(selftest が見出し・json・終了コードを縛れるように分けた)。"""
    as_json = "--format=json" in flags or ("--format" in flags and "json" in flags)
    order = {"高": 0, "中": 1, "低": 2}
    findings.sort(key=lambda f: (order.get(f["severity"], 9), f["check"], f["subject"]))

    if as_json:
        print(json.dumps({"findings": findings, "stats": stats},
                         ensure_ascii=False, indent=2, sort_keys=True))
        # テキスト経路と同じ約束: --warn-only は json でも効く(callgraph-check.py と同じ)
        return 0 if "--warn-only" in flags or not [f for f in findings if f["severity"] == "高"] else 1

    print("## 契約(OpenAPI)の検査")
    print(f"  02-design: {stats['design']} 件(うち REST {stats['rest_design']})"
          f" / 03-impl: {stats['impl']} 件(うち REST {stats['rest_impl']})")
    if stats["callgraph"]:
        skipped = [f"{label} {stats[k]} 件" for k, label in (
            ("cg_skipped_alb", "ALB の前方一致"), ("cg_skipped_guessed", "パスが推定の経路"),
            ("cg_skipped_self", "契約自身の OpenAPI から読んだ経路"),
            ("cg_skipped_nonhttp", "WebSocket の予約ルート($connect・$disconnect)")) if stats.get(k)]
        if stats.get("cg_unknown_routes"):
            print(f"  NOTE  未検査 {stats['cg_unknown_routes']} 件: HTTP の経路か WebSocket のキーか"
                  "判別できない API Gateway の経路(メソッドが HTTP でなくパスが `/`)は照合していない")
        if stats.get("cg_dynamic_method"):
            print(f"  NOTE  メソッドが未解決の経路 {stats['cg_dynamic_method']} 件"
                  "(ANY としてパスだけで照合 — メソッドは未検査)")
        if stats.get("ct4_unchecked"):
            print("  CT4 未検査: コールグラフから HTTP の経路が1件も取れなかった"
                  "(言語側の REST も API Gateway の経路も 0 件。突き合わせていない — "
                  "未検査は合格ではない)")
        else:
            print(f"  コールグラフのエントリポイント: {stats['cg_endpoints']} 件と突き合わせた"
                  f"(言語側の REST {stats['cg_rest_endpoints']} / "
                  f"API Gateway の経路 {stats['cg_apigw_routes']})")
        if skipped:
            print(f"  NOTE  照合に使わなかった経路: {' / '.join(skipped)}")
        if stats.get("ct6_unchecked"):
            print(f"  CT6 未検査 {stats['ct6_unchecked']} 件: `x-impl` が抽出器の無い言語のシンボルを"
                  "指している(callgraph に現れないので実在を確かめていない — 未検査は合格ではない)")
            for u in stats.get("ct6_unchecked_ids", []):
                print(f"    - {u}")
        if stats.get("ct4_any_path_matched"):
            print(f"  NOTE  ANY のため method 未照合 {stats['ct4_any_path_matched']} 件"
                  "(パス一致のみ — 抽出器がメソッドを知れないエンドポイント。未検査は合格ではない)")
    else:
        print("  --no-callgraph: CT4/CT6(コードとの突き合わせ)は実施していない")

    if not findings:
        if stats["design"] + stats["impl"] == 0:
            # 検査対象ゼロと「検査して不整合なし」を同じ「合格」にしない(未検査は合格ではない)
            print("\n対象なし: 契約が1件も無い(CT1〜CT6 は1つも走っていない。"
                  "**未検査は合格ではない** — REST API を持つなら "
                  ".claude/directions/02-design.md の contracts 節に従って書く)。")
            return 0
        # CT6 の未検査はどの合格行にも付ける(先に返る行で落とさない)
        ct6 = (f"(抽出器が無い言語の x-impl {stats['ct6_unchecked']} 件は未検査)"
               if stats.get("ct6_unchecked") else "")
        if stats.get("ct4_unchecked"):
            print("\n合格(CT4 を除く): CT4 は未検査なので、コードと契約の一致は確かめていない。" + ct6)
            return 0
        if stats.get("cg_unknown_routes"):
            print(f"\n合格(判別できない経路 {stats['cg_unknown_routes']} 件は未検査): "
                  "それ以外の契約に不整合なし。" + ct6)
            return 0
        if ct6:
            print(f"\n合格{ct6}: それ以外の契約に不整合なし。")
            return 0
        print("\n合格: 契約に不整合なし。")
        return 0

    print(f"\n### 所見 {len(findings)} 件")
    print("| 重大度 | 検査 | 対象 | 内容 | 根拠 |")
    print("|---|---|---|---|---|")
    for f in findings:
        print(f"| {f['severity']} | {f['check']} | `{f['subject']}` | "
              f"{base.escape_cell(f['detail'])} | {base.escape_cell(f['evidence'])} |")
    print("\n→ **どちらが正かはこのツールが決めない。** CT4 はコードと契約の乖離、")
    print("  CT3 は設計と実装の乖離である。判断できないものは人間に問うこと。")

    high = [f for f in findings if f["severity"] == "高"]
    return 0 if "--warn-only" in flags or not high else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))

#!/usr/bin/env python3
"""契約(OpenAPI)を検査し、設計 ⇄ 実装 ⇄ コードの三者を突き合わせる。

規範: .claude/directions/02-design.md / 03-impl.md の contracts 節

REST API の契約を OpenAPI で書く理由は「機械的に検査できるから」であって、
検査しなければ表を YAML に書き換えただけになる。このスクリプトがその検査である。

  CT1 OpenAPI として妥当か(パース可能・paths がある)
  CT2 エラー応答があるか(2xx だけの operation は未完成)
  CT3 02(設計)⇄ 03(実装)のパス・メソッドが一致するか
  CT4 コールグラフのエントリポイント ⇄ 03 の契約が一致するか  ★実装と契約の乖離
      **突き合わせ先は OpenAPI だけではない** — 契約が正しく非 REST の側に在る経路
      (WebSocket の升格点など)は、その契約の frontmatter に `endpoints:` を書けば
      覆っていると見なす。書く口が無かったころ、そういう経路は直しようの無い
      重大度「高」として出続けた(実測 2026-09-01: `GET /ws`)。
  CT5 片側にしか無い CTR-*
  CT6 `x-impl` のシンボルが callgraph に実在するか

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

import importlib.util
import json
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

    cg_eps: dict[tuple[str, str], str] = {}
    symbols: set[str] = set()
    for _lang, d in cg["languages"].items():
        symbols |= {s["id"] for s in d["symbols"]}
        for ep in d["endpoints"]:
            if ep["protocol"] == "rest" and ep["path_key"]:
                cg_eps[((ep.get("method") or "ANY").upper(), ep["path_key"])] = ep["handler"]
    stats["cg_endpoints"] = len(cg_eps)

    contract_ops: dict[tuple[str, str], str] = {}
    for cid, e in sorted(impl.items()):
        if not e["spec"]:
            continue
        for key, op in operations(e["spec"]).items():
            contract_ops[key] = cid
            ximpl = op.get("x-impl")
            if ximpl and symbols and ximpl not in symbols:
                add("CT6", "中", cid,
                    f"{key[0]} {key[1]}: `x-impl` のシンボルが callgraph に無い: `{ximpl}`",
                    e["spec_source"])

    if cg_eps:
        # 片側が "ANY"(メソッドを原理的に知れない抽出 — Go net/http の Handle/HandleFunc、
        # Express の all/use、ALB / API GW の ANY)のときは**パスだけで照合する**
        # (`cgx/boundaries.py` の同種の規則に揃える)。メソッドの照合は失われるので、
        # 黙って合格にせず件数を stats と NOTE に出す(「未検査は合格ではない」)。
        contract_paths = {p for _m, p in contract_ops}
        cg_any_paths = {p for m, p in cg_eps if m == "ANY"}
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
            add("CT4", "高", f"{meth} {path}",
                "コードにこのエンドポイントがあるが、03 のどの契約も覆っていない"
                "(OpenAPI の `paths` にも、非 REST 契約の `endpoints:` にも無い)",
                f"handler: {cg_eps[key] or '(未特定)'}")
        for key in sorted(set(contract_ops) - set(cg_eps)):
            meth, path = key
            if path in cg_any_paths:
                any_matched += 1
                continue
            add("CT4", "中", contract_ops[key],
                f"契約にあるが、コードにエンドポイントが見つからない: {meth} {path}",
                "抽出器が未対応の言語かもしれない。Tier を確認すること")
        # ★ 非 REST の `endpoints:` も**両向きに**見る。コード→契約だけだと、
        # 消した経路や打ち間違えた経路の宣言が残っても誰も気づかない
        cg_keys = list(cg_eps)
        for pair, cid in sorted(nonrest.items()):
            if covers(pair, cg_keys):
                continue
            add("CT4", "中", cid,
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
    "CT6": "x-impl のシンボルが callgraph に実在するか",
}


def selftest() -> int:
    ok = True
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
    print("OK check-contracts: 非 REST 契約の endpoints の解析(コンマ・全角読点)/ "
          "経路の覆いの判定(ANY の総当たり・前方一致にしない)/ "
          "endpoints を信用する kind は語彙内のものだけ" if ok else "NG check-contracts")
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
    as_json = "--format=json" in flags or ("--format" in flags and "json" in flags)

    root = base.find_root()
    base.ensure_kit_venv(root)
    findings, stats = run_checks(root, "--no-callgraph" not in flags)

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
        print(f"  コールグラフのエントリポイント: {stats.get('cg_endpoints', 0)} 件と突き合わせた")
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

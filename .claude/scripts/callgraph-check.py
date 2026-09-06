#!/usr/bin/env python3
"""機能表・コールグラフ・機能間連携仕様書の整合を検査する。

規範: .claude/directions/features.md・callgraphs.md §6 / 設計: callgraph-design.md §4・§8.5

この検査が、機能間連携仕様書を「実装と仕様ドキュメントの接点」として機能させる。
**機能間の関係は `cluster-features.py` と同じ実装で導出する**(二重実装しない)。
機械が出した辺(③)と、AI が宣言した `callees:` の差が指摘になる。

**実装している検査IDの正はこのファイルの CHECKS だけである。**
一覧は `--list` で出る。**規範側に「CG1〜CGn」のような範囲を書かないこと** —
CG5 は FT2 に吸収されて欠番なので、範囲表記は必ず実数と食い違う(実際 `CG1〜CG7` と
`CG1〜CG6` が18箇所で割れていた)。

CG5(エントリポイント ⇄ 機能)は **FT2 に吸収した** — 機能表が唯一の入口一覧だから。

**機能表が無い場合は relations の `impl:` を入口とみなして動く**(ブラウンフィールドの
途中段階で止まらないため)。その場合はそう報告し、FT2〜FT5 は検査しない。

**どちらが正かは決めない。** 事実の不一致として出すだけである(CLAUDE.md 原則2)。

使い方:
    python3 .claude/scripts/callgraph-check.py                    # SSOT の relations と突き合わせ
    python3 .claude/scripts/callgraph-check.py --list             # 実装している検査IDの一覧
    python3 .claude/scripts/callgraph-check.py --from cg.json      # 抽出をやり直さない
    python3 .claude/scripts/callgraph-check.py --format json
    python3 .claude/scripts/callgraph-check.py --warn-only

終了コード: 0=重大度「高」なし(中・低のみ、または --warn-only を含む) 1=重大度「高」あり
            2=使い方・解析エラー
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from cgx import base       # noqa: E402
from cgx import features as ft  # noqa: E402


def _load_builder():
    spec = importlib.util.spec_from_file_location("build_callgraphs", _HERE / "build-callgraphs.py")
    mod = importlib.util.module_from_spec(spec)          # type: ignore[arg-type]
    spec.loader.exec_module(mod)                          # type: ignore[union-attr]
    return mod


# **実装している検査IDの唯一の正。** `--list` もレポートの見出しもここから作る。
# 規範側(directions / SKILL.md / templates)に範囲表記を書き写さないこと — CG5 が欠番なので
# 「CG1〜CG7」は7件あるように読め、「CG1〜CG6」は CG7 を落とす。どちらも嘘になる。
# 意味・重大度・既定の対処は `.claude/directions/callgraphs.md` §6 が正(ここには書かない)。
CHECKS: dict[str, str] = {
    "FT1": "機能表の入口が callgraph に実在するか(**これが落ちたら以降は検査しない**)",
    "FT2": "callgraph のエントリポイントが、いずれかの機能の入口になっているか ★機能の取りこぼし",
    "FT3": "機能表の機能ID と relations/MODULE-*.md が 1:1 か",
    "FT4": "機能表の 所属 が 02 のモジュール分割定義に実在するか",
    "FT5": "入口を網羅宣言したファイルに、機能表が知らないシンボルが増えていないか ★入口の取りこぼし",
    "CG1": "impl のシンボルが callgraph に実在するか",
    "CG2": "どの入口からも到達しないシンボル(到達不能コード候補)",
    "CG3": "宣言された callees に対応する辺が在るか(relations の過剰主張)",
    "CG4": "機械が出した辺が callees に宣言されているか  ★取りこぼし",
    "CG6": "kind と実際のエントリポイントの整合",
    "CG7": "同じ資源を触る機能が、その資源を機能間連携仕様書に書いているか  ★呼び出し辺の無い連携",
}
# 見出しは列挙から作る(範囲に畳まない)。欠番があっても嘘にならない唯一の書き方である。
CHECK_LINE = " / ".join(
    "・".join(k for k in CHECKS if k.startswith(p)) for p in ("FT", "CG"))

RELATIONS_DIR = "docs/03-impl/relations"
DESIGN_SYSTEM = "docs/02-design/system.md"
NONE_WORDS = {"なし", "none", "-", ""}
EXTERNAL_PREFIXES = ("USER-", "EVENT-", "SCHEDULER-", "EXTERNAL-")
ENTRY_KINDS = {"rest-api": {"rest", "graphql", "grpc"}, "event": {"event", "schedule"},
               "tool": {"cli", "tool"}}

# 種別を主張しない protocol(callgraph-schema.json の endpoints.protocol の説明)。
# `main` は「これは実行ファイルの入口である」ことしか言わず、その実行ファイルが対話的な道具なのか
# 定時処理なのか HTTP サーバなのかは抽出位置から決まらない。CG6 の突き合わせから外す。
KIND_AGNOSTIC_PROTOCOLS = {"main"}


# --------------------------------------------------------------------------- 読み込み

def read_frontmatter(path: Path) -> dict[str, str]:
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


def items(value: str) -> list[str]:
    v = (value or "").strip()
    if v.lower() in NONE_WORDS or v.startswith("なし"):
        return []
    return [p.strip() for p in v.split(",") if p.strip()]


def load_relations(root: Path) -> dict[str, dict]:
    """SSOT の relations を読む。

    **重ねる層は無い。** 以前はタスクの変更指示(`docs/tasks/<slug>/new-features/`)を
    合成する `--to-be` を持っていたが、変更指示はワークフロー再設計(2026-08-19)で
    全廃された。実装前の姿は検査せず、デプロイ点で全検証が green かどうかだけを見る。
    """
    docs: dict[str, dict] = {}

    def absorb(path: Path) -> None:
        fm = read_frontmatter(path)
        mid = fm.get("id") or path.stem
        docs[mid] = {
            "id": mid,
            "module": fm.get("module", ""),
            "kind": fm.get("kind", ""),
            "impl": items(fm.get("impl", "")),
            "callees": items(fm.get("callees", "")),
            "callers": items(fm.get("callers", "")),
            # CG7 は「資源の名前が本文に出ているか」を見るので本文が要る。
            # 資源結合は callees では表現できない(呼び出しではない)ため、
            # 検査できるのは**書いてあるかどうか**だけである。
            "body": path.read_text(encoding="utf-8").lower(),
        }

    rel_dir = root / RELATIONS_DIR
    if rel_dir.is_dir():
        for path in sorted(rel_dir.glob("MODULE-*.md")):
            absorb(path)
    return docs


# --------------------------------------------------------------------------- グラフ

def build_index(cg: dict):
    """(シンボル表, エントリポイント, 未解決を持つシンボル)。

    未解決を分けて持つ理由: **解決できなかった呼び出しがある symbol については
    「経路が無い」と断定できない**。断定すると CG3 が偽陽性だらけになる
    (.claude/directions/callgraphs.md §5.5 の「空欄と未解決は別」の帰結)。
    """
    symbols: dict[str, dict] = {}
    endpoints: list[dict] = []
    has_unresolved: dict[str, set[str]] = {}
    for lang, d in cg["languages"].items():
        for sym in d["symbols"]:
            symbols[sym["id"]] = {**sym, "language": lang}
        for ep in d["endpoints"]:
            endpoints.append({**ep, "language": lang})
        for u in d["unresolved"]:
            has_unresolved.setdefault(u["from"], set()).add(u["reason"])
    return symbols, endpoints, has_unresolved


def module_ids(root: Path) -> set[str]:
    path = root / DESIGN_SYSTEM
    if not path.is_file():
        return set()
    return set(re.findall(r"MOD-[a-z0-9][a-z0-9-]*", path.read_text(encoding="utf-8")))


# --------------------------------------------------------------------------- 検査

def run_checks(root: Path, cfg: dict, cg: dict,
               docs: dict[str, dict]) -> tuple[list[dict], dict]:
    symbols, endpoints, has_unresolved = build_index(cg)
    findings: list[dict] = []

    covered_exts = {
        "." + s["file"].rsplit(".", 1)[-1] for s in symbols.values() if "." in s["file"]}
    tiers = {lang: d["tier"] for lang, d in cg["languages"].items()}
    tier3 = [l for l, t in tiers.items() if t == 3]

    def add(check: str, severity: str, subject: str, detail: str,
            evidence: str = "") -> None:
        findings.append({"check": check, "severity": severity, "subject": subject,
                         "detail": detail, "evidence": evidence})

    def ext_covered(sid: str) -> bool:
        head = sid.split("::", 1)[0]
        return ("." + head.rsplit(".", 1)[-1]) in covered_exts if "." in head else False

    # --- CG1 impl の実在。ここで所有できたシンボルだけを後段に渡す
    owner: dict[str, str] = {}
    skipped_impl = 0
    for mid, d in sorted(docs.items()):
        for sid in d["impl"]:
            if "::" not in sid:
                add("CG1", "高", mid, f"impl の区切りが `::` でない: `{sid}`",
                    "callgraphs のシンボルIDと同一表記にする")
                continue
            if sid in owner and owner[sid] != mid:
                add("CG1", "高", mid,
                    f"シンボル `{sid}` を {owner[sid]} と重複して所有している",
                    "所有が一意でないと畳み込みが定義できない")
                continue
            if sid not in symbols:
                if not ext_covered(sid):
                    skipped_impl += 1
                    continue                      # 抽出器が無い言語。誤検出を出さない
                add("CG1", "高", mid,
                    f"impl のシンボルが callgraph に無い: `{sid}`",
                    "実装が消えた/改名された、または表記の誤り")
                continue
            owner[sid] = mid

    # --- 入口の決定。機能表があればそれが唯一の定義(directions/features.md §1)
    notes: list[str] = []
    feats, ferrors = ft.load_features(root, cfg)
    from_table = bool(feats) and not ferrors
    if not from_table:
        if ferrors and (root / ft.feature_cfg(cfg)["path"]).is_file():
            notes.append("機能表が読めなかったので relations の `impl:` を入口とみなした: "
                         + " / ".join(ferrors))
        else:
            notes.append(f"機能表({ft.feature_cfg(cfg)['path']})が無いので relations の "
                         "`impl:` を入口とみなした。**FT2〜FT5 は未検査**。"
                         "`propose-features.py` で候補を出せる")
        grouped: dict[str, list[str]] = {}
        for sid, mid in sorted(owner.items()):
            grouped.setdefault(mid, []).append(sid)
        feats = [{"id": mid, "kind": docs[mid]["kind"], "entries": ents,
                  "module": docs[mid]["module"], "summary": ""}
                 for mid, ents in sorted(grouped.items())]

    def entry_kind(fid: str) -> str:
        """その機能の入口がテスト/開発ツールを指しているか(features.md §0.1)。

        機能ではないものは収集段階で callgraph から落ちているので、FT1 に「実在しない」として
        現れる。**新しい検査IDは足さず、FT1 が行き先を教える**。

        **限界**: 判定できるのは入口が**パスを含む**場合(シンボルID `path::symbol`、
        あるいはパスを含むエンドポイントID)だけである。`POST /internal/health` のような
        パスを持たないエンドポイントIDは、定義元ファイルが分からないので判定できず、
        通常の FT1(入口が callgraph に無い)として出る。**マーカーで機械が守れる範囲は
        ここまで**で、残りは人間の判断である(features.md §0.1)。
        """
        for f in feats:
            if f["id"] != fid:
                continue
            for e in f.get("entries", []):
                # シンボルIDならパス部、そうでなければ入口文字列全体を照合する
                for cand in {e.split("::", 1)[0], e}:
                    if base.is_test(cand, cfg.get("test_markers", [])):
                        return "test"
                    if base.is_test(cand, cfg.get("tooling_markers", [])):
                        return "tooling"
        return ""

    NOT_A_FEATURE = {
        "test": ("**テストは機能ではない**(features.md §0.1)。"
                 "行き先は `docs/03-impl/tests/`(relations には `tests:` の参照だけ)"),
        "tooling": ("**開発ツールは機能ではない**(features.md §0.1)。行き先は "
                    "`docs/02-design/environments.md`(コマンド)と `docs/03-impl/environments/`(仕組み)"),
    }

    # --- FT1。**落ちたら以降は検査しない**(誤ったクラスタで指摘を出す方が有害)
    result = ft.cluster(cg, feats, cfg)

    if result.get("errors"):
        for e in result["errors"]:
            err_fid = e.split(":", 1)[0].strip()
            kind = entry_kind(err_fid)
            if kind:
                # 収集段階で落とした = 機能ではない。未実装扱い(「低」)にしてはならない
                add("FT1", "高", ft.feature_cfg(cfg)["path"], f"{e} — {NOT_A_FEATURE[kind]}",
                    "機能表からこの行を削り、内容を上の行き先へ移す。"
                    "**これが通るまで CG2〜CG4 は検査しない**")
                continue
            add("FT1", "高", ft.feature_cfg(cfg)["path"], e,
                "機能表の入口を直すか、コードを直す。**これが通るまで CG2〜CG4 は検査しない**")
        return findings, {"relations": len(docs), "symbols": len(symbols),
                          "owned_symbols": len(owner), "effective_edges": 0,
                          "declared_edges": 0, "endpoints": len(endpoints), "tiers": tiers,
                          "skipped_impl": skipped_impl, "folded_symbols": 0,
                          "unresolved_symbols": len(has_unresolved), "features": len(feats),
                          "from_table": from_table, "notes": notes, "aborted": True}

    # --- FT2〜FT5(機能表があるときだけ)
    if from_table:
        for miss in ft.missing_entrypoints(cg, result["roots"], cfg):
            add("FT2", "高", miss.split(" → ")[0],
                "callgraph にあるのに、どの機能の入口にもなっていない(**機能の取りこぼし**)",
                f"ハンドラ: `{miss.split(' → ')[-1]}`")
        # FT5。FT2 が見られるのは endpoints だけで、画面ハンドラのようにエンドポイントを
        # 持たない入口は落ちても黙って ④ に積まれる(cgx/features.py の docstring に実測)。
        for miss in ft.missing_consolidated_entrypoints(cg, feats, result):
            others = [f for f in miss["features"][1:]]
            add("FT5", "中" if miss["tier3"] else "高", miss["features"][0],
                f"入口を {miss['declared']} 件並べたファイルに、機能表が知らないシンボルが"
                f"ある(**入口の取りこぼし**): `{miss['symbol']}`"
                + ("(Tier 3 抽出のため「到達しない」の判定が不完全)" if miss["tier3"] else ""),
                f"`{miss['file']}` は未宣言のシンボルがどれも機能から到達しない = 入口を"
                "網羅宣言したファイル。機能表のこの行に入口を足す"
                + (f" / 同じファイルを宣言している他の機能: {', '.join(others)}" if others else ""))
        fids = {f["id"] for f in feats}
        for fid in sorted(fids - set(docs)):
            add("FT3", "高", fid, "機能表にあるが relations/MODULE-*.md が無い",
                "機能表と relations は 1:1(directions/features.md §0)")
        for mid in sorted(set(docs) - fids):
            add("FT3", "高", mid, "relations があるが機能表に行が無い",
                "機能表と relations は 1:1(directions/features.md §0)")
        known = module_ids(root)
        if known:
            for f in feats:
                if f["module"] and f["module"] not in known:
                    add("FT4", "中", f["id"],
                        f"所属 `{f['module']}` が 02-design のモジュール分割定義に無い", "")

    # --- CG2 到達不能(候補辺も算入した上で到達しない = 「無い」の主張は広く)
    for sid in result["unreached"]:
        add("CG2", "低", sid, "どの入口からも到達しない",
            "到達不能コード候補。**削ってよいかは決めない**(動的呼び出しの可能性)")

    # --- CG3 / CG4。機械が出した辺(③)と宣言の差
    declared: set[tuple[str, str]] = set()
    for mid, d in sorted(docs.items()):
        for callee in d["callees"]:
            if not callee.startswith(EXTERNAL_PREFIXES):
                declared.add((mid, callee))

    machine = {(e["from"], e["to"]): e for e in result["edges"]}
    boundary_pairs = {(b.get("from", ""), b.get("to", "")) for b in cg.get("boundaries", [])}

    for a, b in sorted(declared):
        if (a, b) in machine:
            continue                     # 候補辺で繋がっていても宣言の裏付けにはなる
        if b not in docs:
            add("CG3", "高", a, f"callees の `{b}` が存在しない機能を指している", "")
            continue
        both_covered = all(ext_covered(s) for s in docs[a]["impl"] + docs[b]["impl"]
                           if "::" in s)
        blocked = sorted({r for sid in result["closure"].get(a, ())
                          for r in has_unresolved.get(sid, set())})
        if not both_covered:
            add("CG3", "低", a, f"`{b}` への連携を検査できない(抽出器が無い言語を含む)", "")
        elif blocked:
            # 経路上に解決できなかった呼び出しがある = 「経路が無い」とは言えない
            add("CG3", "低", a,
                f"`{b}` への経路の有無を断定できない(経路上に未解決の呼び出しがある)",
                f"未解決の分類: {', '.join(blocked)}。callgraphs の未解決表を確認すること")
        else:
            add("CG3", "中", a,
                f"callees に `{b}` とあるが、機械が出した辺に対応するものが無い",
                "REST/キューなど境界を跨ぐ連携なら本文に根拠(どのコードが呼ぶか)が要る"
                if not boundary_pairs else "boundaries の候補にも無い")

    def edge_tier3(e: dict) -> bool:
        """この辺の根拠(call_sites)に Tier 3 の言語、または言語を特定できないシンボルが
        絡むか。**降格は辺単位** — リポジトリに Tier 3 言語(shell/make は常に Tier 3)が
        在るだけで全 CG4 を「参考」に落とすと、正確に解析できた言語の取りこぼし検出まで
        恒久的に検査から外れる(inspection-17 判断2)。根拠が1つも無い辺は保守的に True。"""
        if not e.get("call_sites"):
            return True
        for cs in e["call_sites"]:
            for sid in (cs.get("from", ""), cs.get("to", "")):
                s = symbols.get(sid)
                if s is None or tiers.get(s.get("language"), 3) == 3:
                    return True
        return False

    # 棄却済みの候補辺は再審しない(inspection-17 M-20)。抑止するのは確度「候補」だけ —
    # 機械が「確定」の根拠を得た辺は、過去の棄却があっても取りこぼしとして出し直す。
    rejected = ft.load_rejected_edges(root, cfg)
    suppressed = 0
    for (a, b), e in sorted(machine.items()):
        if (a, b) in declared or a not in docs or b not in docs:
            continue                     # 片側が未記述なら FT3 の担当
        if e["confidence"] == "候補" and (a, b) in rejected:
            suppressed += 1
            continue
        sites = ", ".join(f"`{cs['from']}` → `{cs['to']}`" for cs in e["call_sites"][:2])
        if len(e["call_sites"]) > 2:
            sites += f" ほか {len(e['call_sites']) - 2} 件"
        if tier3 and edge_tier3(e):
            sev = "参考"                 # Tier 3 の根拠しか無い辺だけを落とす(判断2)
        elif e["confidence"] == "確定":
            sev = "高"
        else:
            sev = "中"                   # 候補辺だけで繋がった辺。実在するとは限らない
        add("CG4", sev, a,
            f"コードでは `{b}` を呼んでいるが callees に宣言が無い(**取りこぼし**"
            f"{' / 確度は候補' if e['confidence'] == '候補' else ''})", sites)
    if suppressed:
        notes.append(f"棄却済みの候補辺 {suppressed} 本を CG4 から抑止した"
                     "(機能表の「棄却した候補辺・確認済みの境界辺」の記録による — "
                     "確定の根拠を得た辺は棄却があっても出し直す)")

    # --- CG7 共有データストア結合(P10)。**呼び出し辺として存在しない連携**
    # `callees` では表現できない(呼び出しではない)ので、検査できるのは
    # 「その資源の名前が機能間連携仕様書の本文に出ているか」だけである。それでも、
    # 書式を決めている機能の 副作用 に資源名が1度も出てこないなら記述漏れである。
    coupling = result.get("resource_coupling", {})
    for r in coupling.get("findings", []):
        token = r["name"].strip("$#").replace("{}", "").strip().lower()
        if len(token) < 3:
            continue                     # 短すぎる名前は本文照合の当たりが信用できない
        writers = [f for f in r["writers"]
                   if f in docs and token not in docs[f]["body"]]
        readers = [f for f in r["readers"]
                   if f in docs and f not in r["writers"] and token not in docs[f]["body"]]
        if not writers and not readers:
            continue
        sev = "中" if writers else "参考"
        miss = writers + readers
        add("CG7", sev, r["key"],
            f"同じ資源を触る機能が {len(r['features'])} 件あり、うち "
            f"{len(r['unlinked_pairs'])} 対は呼び出し辺で繋がっていないのに、"
            f"{len(miss)} 件の機能間連携仕様書が資源名に一度も触れていない",
            "記述が無い機能: " + ", ".join(miss[:6])
            + (f" ほか {len(miss) - 6} 件" if len(miss) > 6 else "")
            + f" / 書き込む機能: {', '.join(r['writers'][:4]) or 'なし'}"
            + "(書き込む側が書式を決め、読む側がそれに依存する。"
              "**戻り値・副作用** と **連携先と連携内容** に書く)")

    # --- CG6 kind と実際のエントリポイントの整合
    ep_by_handler: dict[str, list[dict]] = {}
    for e in endpoints:
        if e["handler"]:
            ep_by_handler.setdefault(e["handler"], []).append(e)
    for mid, d in sorted(docs.items()):
        want = ENTRY_KINDS.get(d["kind"])
        if not want:
            continue
        eps = [ep for sid in d["impl"] for ep in ep_by_handler.get(sid, [])]
        got = {ep["protocol"] for ep in eps} - KIND_AGNOSTIC_PROTOCOLS
        if not got:
            # 入口は在るが種別を主張しない protocol しか無い = 突き合わせる材料が無い。
            # 「食い違い」も「経路が無い」も、この位置からは言えない。
            if not eps and any(ext_covered(s) for s in d["impl"] if "::" in s):
                add("CG6", "中", mid,
                    f"kind: {d['kind']} だが、対応するエントリポイントが callgraph に無い",
                    "種別の誤りか、ルート定義が抽出パターンに載っていない")
        elif not (got & want):
            add("CG6", "中", mid,
                f"kind: {d['kind']} と実際の種別({', '.join(sorted(got))})が食い違う", "")

    counts = result["counts"]
    stats = {
        "relations": len(docs), "features": len(feats), "from_table": from_table,
        "owned_symbols": len(owner), "symbols": len(symbols),
        "effective_edges": len(machine), "declared_edges": len(declared),
        "candidate_edges": counts["candidate_edges"], "shared_symbols": counts["shared"],
        "endpoints": len(endpoints), "tiers": tiers, "skipped_impl": skipped_impl,
        "folded_symbols": sum(len(v) for v in result["members"].values()),
        "unresolved_symbols": len(has_unresolved), "notes": notes, "aborted": False,
        "coupled_resources": counts.get("coupled_resources", 0),
        "unlinked_pairs": counts.get("unlinked_pairs", 0),
        "ubiquitous_resources": counts.get("ubiquitous", 0),
    }
    return findings, stats


# --------------------------------------------------------------------------- 本体

def main(argv: list[str]) -> int:
    if any(a in ("-h", "--help") for a in argv[1:]):
        print(__doc__)   # 明示要求は 0。使い方エラーの 2 と区別する(tools-readme §2)
        return 0
    args = argv[1:]
    from_json = None
    fmt = "table"
    warn_only = False
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--from" and i + 1 < len(args):
            i += 1
            from_json = args[i]
        elif a.startswith("--from="):
            from_json = a.split("=", 1)[1]
        elif a.startswith("--format="):
            fmt = a.split("=", 1)[1]
        elif a == "--format" and i + 1 < len(args):
            i += 1
            fmt = args[i]
        elif a == "--warn-only":
            warn_only = True
        elif a == "--list":
            print("## 実装している検査")
            for cid, desc in CHECKS.items():
                print(f"  {cid}  {desc}")
            print("\nCG5 は FT2 に吸収した(欠番)。**規範側に範囲表記を書かないこと。**")
            print("意味・重大度・既定の対処は .claude/directions/callgraphs.md §6 が正。")
            return 0
        else:
            print(__doc__)
            return 2
        i += 1
    if fmt not in {"table", "json"}:
        print(__doc__)
        return 2

    root = base.find_root()
    base.ensure_kit_venv(root)   # キット専用 venv があればそちらで自己再実行
    cfg = base.load_config(root)
    notes: list[str] = []

    if from_json:
        cg = json.loads((root / from_json).read_text(encoding="utf-8"))
    else:
        builder = _load_builder()
        langs = [l for l, s in cfg["languages"].items() if s.get("enabled")]
        cg, build_notes = builder.run_extractors(root, cfg, langs, None)
        notes.extend(build_notes)

    if not cg.get("languages"):
        print("## コールグラフ整合検査")
        print("  コールグラフが空(抽出器が無い、または対象コードが無い)。**実装前のため未検査**。")
        print("  新規開発では relations を先に書き、実装後にこの検査を走らせる"
              "(.claude/directions/callgraphs.md §6)。")
        return 0

    docs = load_relations(root)
    if not docs:
        print("## コールグラフ整合検査")
        print("  機能間連携仕様書が1本も無い。ブラウンフィールド導入なら")
        print("  `/relations all --apply --bootstrap` が最初の一歩。")
        return 0

    findings, stats = run_checks(root, cfg, cg, docs)
    notes.extend(stats.pop("notes", []))

    if fmt == "json":
        print(json.dumps({"findings": findings, "stats": stats, "notes": notes},
                         ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if not [f for f in findings if f["severity"] == "高"] or warn_only else 1

    order = {"高": 0, "中": 1, "低": 2, "参考": 3}
    findings.sort(key=lambda f: (order.get(f["severity"], 9), f["check"], f["subject"]))

    print(f"## 整合検査({CHECK_LINE})")
    src = "機能表" if stats["from_table"] else "relations の impl(機能表なし)"
    print(f"  入口の定義: {src} / 機能 {stats['features']} / relations {stats['relations']} 本")
    print(f"  シンボル {stats['symbols']}(impl で所有 {stats['owned_symbols']})")
    print(f"  機械が出した辺 {stats['effective_edges']}"
          f"(うち候補 {stats.get('candidate_edges', 0)}) / 宣言エッジ {stats['declared_edges']}"
          f" / 共有関数 {stats.get('shared_symbols', 0)} / エントリポイント {stats['endpoints']}")
    if stats.get("coupled_resources"):
        print(f"  複数機能が触る資源 {stats['coupled_resources']}"
              f"(呼び出し辺の無い機能対 {stats.get('unlinked_pairs', 0)}"
              f" / 広域共有資源 {stats.get('ubiquitous_resources', 0)} は指摘から除外)")
    print(f"  Tier: {', '.join(f'{k}={v}' for k, v in sorted(stats['tiers'].items()))}")
    if stats["skipped_impl"]:
        print(f"  抽出器が無い言語のため検査を飛ばした impl: {stats['skipped_impl']} 件")
    if stats["unresolved_symbols"]:
        print(f"  未解決の呼び出しを持つシンボル: {stats['unresolved_symbols']} 件"
              " — この範囲では「経路が無い」と断定しない(CG3 を『低』に落とす)")
    if stats.get("aborted"):
        print("  **FT1 が落ちたので CG2〜CG4 は検査していない**(誤ったクラスタで指摘を出さない)")
    if any(f["check"] == "CG4" and f["severity"] == "参考" for f in findings):
        print("  **Tier 3 の根拠しか無い CG4(取りこぼし)は「参考」に落としている** — "
              "降格は辺単位で、正確に解析できた言語どうしの辺は落とさない(inspection-17 判断2)")

    if not findings:
        print("\n合格: 機能表・コールグラフ・機能間連携仕様書に不整合なし。")
        return 0

    print(f"\n### 所見 {len(findings)} 件")
    print("| 重大度 | 検査 | 対象 | 内容 | 根拠 |")
    print("|---|---|---|---|---|")
    for f in findings:
        print(f"| {f['severity']} | {f['check']} | `{f['subject']}` | "
              f"{base.escape_cell(f['detail'])} | {base.escape_cell(f['evidence'])} |")

    if notes:
        print("\n### 注記")
        for n in notes:
            print(f"- {n}")

    print("\n→ **どちらが正かはこのツールが決めない。** 実装が正のことが多いが、要件・設計が正の")
    print("  場合もある(CLAUDE.md 原則2)。CG4 と FT2 は取りこぼし、CG3 は過剰主張の疑いである。")
    print("  確度が『候補』の辺は同名衝突などの候補辺で繋がったもので、実在するとは限らない")
    print("  (.claude/directions/features.md §5)。判断できないものは人間に問うこと。")

    high = [f for f in findings if f["severity"] == "高"]
    return 0 if warn_only or not high else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))

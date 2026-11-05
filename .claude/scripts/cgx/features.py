"""機能表クラスタリングの中核。

規範: .claude/directions/features.md / 設計: .claude/scripts/callgraph-design.md §8

**出力は (callgraph 中間表現, 機能表) の純関数である**(design §8.3.1)。
探索順に依存する量を1つでも出力に混ぜると決定性が壊れるので、ここでは
到達も辺も**集合として**定義し、DFS/BFS はそれを求める手段としてだけ使う。

  ① 各機能に属する関数集合   → JSON のみ(docs には出さない)
  ② 複数機能から到達される共有関数(= 境界の実体)
  ③ 機能間の辺と呼び出し箇所
  ④ どの入口からも到達しない関数
"""

from __future__ import annotations

import re
from collections import defaultdict

from . import base
from . import resources as res

FEATURE_KINDS ={"user-action", "event", "function-call", "rest-api", "tool", "other"}
FEATURES_PATH = "docs/03-impl/features.md"
GRAPH_PATH = "docs/03-impl/feature-graph.md"
TABLE_HEADING = "## 機能一覧"

# 抽出器がモジュール直下の呼び出しを帰属させる擬似シンボル。関数ではないので
# 「どの入口からも到達しない関数」には数えない(import 時に走るコードであり、
# 機能から到達しないのが正常。数えると全モジュール分が系統的なノイズになる)。
# **黙っては落とさない** — 件数を出力に明記する。
MODULE_SCOPE_SUFFIX = "::<module>"

GRAPH_NOTE = base.wrap_note(
    "cluster-features.py",
    "<!-- 生成物。手書き禁止。`CG_OUT=$(python3 .claude/scripts/resolve-callgraph-out.py) "
    "&& python3 .claude/scripts/cluster-features.py --out \"$CG_OUT\"` で再生成する。\n"
    "     不変則: **実装と機能表が変わらなければ1バイトも変わらない**。\n"
    "     鮮度は保存せず `--check` で検査する。\n"
    "     **これは機能間連携仕様書ではない。** relations の代わりに使ってはならない\n"
    "     (.claude/directions/features.md §6)。 -->"
)


def feature_cfg(cfg: dict) -> dict:
    f = dict(cfg.get("features") or {})
    f.setdefault("fanin_threshold", 2)
    f.setdefault("merge_jaccard", 0.8)
    f.setdefault("call_sites_shown", 3)
    f.setdefault("path", FEATURES_PATH)
    f.setdefault("graph_output", GRAPH_PATH)
    return f


# --------------------------------------------------------------------------- 機能表

# 表のセル区切り。**`\|` はセルの中の `|`** であって区切りではない。
# 入口IDは `|` を含みうる — `if cmd in ["ALL","GROUP"]` の合成シンボルは
# `dispatch ALL|GROUP @ app.py::lambda_handler` になる(実データで踏んだ)。
_CELL_SPLIT = re.compile(r"(?<!\\)\|")


def _split_row(line: str) -> list[str]:
    parts = _CELL_SPLIT.split(line.strip())
    if parts and not parts[0].strip():
        parts = parts[1:]
    if parts and not parts[-1].strip():
        parts = parts[:-1]
    return [p.replace("\\|", "|").strip() for p in parts]


def parse_features(text: str) -> tuple[list[dict], list[str]]:
    """機能表の「## 機能一覧」表を読む。(機能, エラー) を返す。

    雛形のままの行(`<...>` を含む)は、まだ書かれていないので黙って飛ばす。
    """
    errors: list[str] = []
    rows: list[list[str]] = []
    in_table = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_table = line.strip().startswith(TABLE_HEADING)
            continue
        if not in_table:
            continue
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = _split_row(s)
        if not cells or set("".join(cells)) <= set("-: "):
            continue
        if cells[0] in {"機能ID"}:
            continue
        rows.append(cells)

    features: list[dict] = []
    seen: dict[str, str] = {}
    for cells in rows:
        if len(cells) < 4:
            errors.append(f"列が足りない行がある: {' | '.join(cells)}")
            continue
        fid, kind, entry, module = cells[0], cells[1], cells[2], cells[3]
        summary = cells[4] if len(cells) > 4 else ""
        if "<" in fid or not fid:
            continue                                   # 雛形のままの行
        if not fid.startswith("MODULE-"):
            errors.append(f"機能ID は MODULE- で始まること: {fid}")
        if fid in seen:
            errors.append(f"機能ID が重複している: {fid}")
            continue
        seen[fid] = entry
        if kind not in FEATURE_KINDS:
            errors.append(f"{fid}: 種別が語彙にない: {kind}"
                          f"(使えるのは {', '.join(sorted(FEATURE_KINDS))})")
        entries = [e.strip().strip("`") for e in entry.split(",") if e.strip()]
        if not entries:
            errors.append(f"{fid}: 入口が空。1つ以上必要")
        features.append({"id": fid, "kind": kind, "entries": entries,
                         "module": module, "summary": summary})
    return features, errors


REJECTED_HEADING = "## 棄却した候補辺・確認済みの境界辺"
_EDGE_RE = re.compile(r"`?(MODULE-[a-z0-9][a-z0-9-]*)`?\s*(?:→|->)\s*`?(MODULE-[a-z0-9][a-z0-9-]*)`?")


def parse_rejected_edges(text: str) -> set[tuple[str, str]]:
    """「棄却した候補辺・確認済みの境界辺」の表から、判断が「棄却」の辺集合を返す。

    この記録を読む機械が無いと、棄却済みの候補辺が検査のたびに未判断として
    再提示される(inspection-17 M-20 — 雛形自身が「ここに無い棄却は
    次回の検査で再提示される」と約束している側)。節スコープは parse_features と同じ規則。
    """
    out: set[tuple[str, str]] = set()
    in_table = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_table = line.strip().startswith(REJECTED_HEADING)
            continue
        if not in_table:
            continue
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = _split_row(s)
        if len(cells) < 3 or "<" in cells[0] or cells[0].startswith("辺"):
            continue                                   # 雛形行・見出し行
        if set("".join(cells)) <= set("-: "):
            continue                                   # 区切り行
        if cells[2].strip() != "棄却":
            continue                                   # 採用/確認済みは抑止の対象ではない
        m = _EDGE_RE.search(cells[0])
        if m:
            out.add((m.group(1), m.group(2)))
    return out


def load_rejected_edges(root, cfg: dict) -> set[tuple[str, str]]:
    path = root / feature_cfg(cfg)["path"]
    if not path.is_file():
        return set()
    return parse_rejected_edges(path.read_text(encoding="utf-8"))


def load_features(root, cfg: dict) -> tuple[list[dict], list[str]]:
    """SSOT の機能表を読む。

    **機能表は SSOT であり、重ねる層は無い。** 以前はタスクの変更指示
    (`docs/tasks/<slug>/new-features/`)を上書きマージする経路を持っていたが、
    変更指示はワークフロー再設計(2026-08-19)で全廃された — SSOT は `/build` が
    直接書き、実装前の姿は検査せず、デプロイ点で全検証が green かどうかだけを見る。
    """
    path = root / feature_cfg(cfg)["path"]
    if not path.is_file():
        return [], [f"機能表が無い: {feature_cfg(cfg)['path']}"
                    "(`.claude/templates/03-features.md` を写して作る。"
                    "候補は `propose-features.py` が出す)"]
    return parse_features(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- 辺集合

def _symbols(cg: dict) -> set[str]:
    out: set[str] = set()
    for data in cg.get("languages", {}).values():
        out |= {s["id"] for s in data.get("symbols", [])}
    return out


def _endpoint_handlers(cg: dict) -> dict[str, list[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    for data in cg.get("languages", {}).values():
        for ep in data.get("endpoints", []):
            if ep.get("handler"):
                out[ep["id"]].add(ep["handler"])
    return {k: sorted(v) for k, v in out.items()}


def edge_sets(cg: dict) -> tuple[set[tuple[str, str]], set[tuple[str, str]]]:
    """(確定辺 E1, 候補辺 E2) を返す。

    **from が空の boundary 辺は入れない**(外部→ハンドラの入口の証拠であって
    機能間の辺ではない。空文字を節点として扱うと結果が実装依存になる)。
    """
    e1: set[tuple[str, str]] = set()
    e2: set[tuple[str, str]] = set()
    for data in cg.get("languages", {}).values():
        for e in data.get("edges", []):
            e1.add((e["from"], e["to"]))
        for u in data.get("unresolved", []):
            if u.get("reason") != "ambiguous":
                continue                     # 他の分類は候補を持たない
            for cand in u.get("candidates", []):
                e2.add((u["from"], cand))
    for b in cg.get("boundaries", []):
        if not b.get("from") or not b.get("to"):
            continue
        if b.get("confidence") == "確実":
            e1.add((b["from"], b["to"]))
        elif b.get("confidence") == "候補":
            e2.add((b["from"], b["to"]))
    return e1, e2 - e1


def _adj(edges) -> dict[str, list[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    for u, v in edges:
        out[u].add(v)
    return {k: sorted(v) for k, v in out.items()}


# --------------------------------------------------------------------------- クラスタリング

def resolve_roots(features: list[dict], cg: dict, cfg: dict, root=None
                  ) -> tuple[dict[str, set[str]], list[str], list[str]]:
    """機能の入口をシンボルIDに解決する。FT1 の実体。(入口, エラー, 未検査の入口) を返す。

    **抽出器が無い言語の入口はエラーにしない** — callgraph に無くて当然だからである。
    `<機能ID>: <入口>` の形で3つ目に返し、呼び出し側が「未検査」として件数を出す。
    判定は `base.unextracted_symbol`(設定とファイルの実在で決まる。**`root` を省くと1件も
    飛ばさない** — 照合する側へ倒す)。
    **重複の検査は飛ばさない** — 未検査の入口でも、2つの機能が同じ文字列を宣言すれば FT1 である。
    """
    symbols = _symbols(cg)
    handlers = _endpoint_handlers(cg)
    exts = base.symbol_extensions(cfg)
    skipped_owner: dict[str, str] = {}
    roots: dict[str, set[str]] = {}
    errors: list[str] = []
    skipped: list[str] = []
    owner: dict[str, str] = {}

    for f in features:
        got: set[str] = set()
        for entry in f["entries"]:
            # **エンドポイントIDを先に照合する。** `::` の有無では判別できない —
            # cmd 分岐のエンドポイントIDは `dispatch ADDGROUP @ path::lambda_handler` の形で
            # `::` を含む(実データで踏んだ)。書式に頼らず、実在するものに当てる。
            if entry in handlers:
                got |= set(handlers[entry])
            elif entry in symbols:
                got.add(entry)
            elif base.unextracted_symbol(entry, exts, cfg, root):
                if entry in skipped_owner and skipped_owner[entry] != f["id"]:
                    errors.append(f"入口が重複している: {entry} を "
                                  f"{skipped_owner[entry]} と {f['id']} が宣言している"
                                  "(所有が一意でないとクラスタリングが定義できない)")
                skipped_owner.setdefault(entry, f["id"])
                skipped.append(f"{f['id']}: {entry}")
            else:
                errors.append(
                    f"{f['id']}: 入口が callgraph に無い: {entry}"
                    + ("(シンボルとしても未検出。ハンドラ未特定のエンドポイントかもしれない)"
                       if "::" in entry else "(エンドポイントIDとしても未検出)"))
        for sym in sorted(got):
            if sym in owner and owner[sym] != f["id"]:
                errors.append(f"入口が重複している: {sym} を "
                              f"{owner[sym]} と {f['id']} が宣言している"
                              "(所有が一意でないとクラスタリングが定義できない)")
            owner[sym] = f["id"]
        roots[f["id"]] = got
    return roots, errors, sorted(skipped)


def _reach(start: set[str], adj: dict[str, list[str]], all_roots: set[str]) -> set[str]:
    """start から、**中間ノードが1つも all_roots に属さない**経路で到達できる集合。

    ROOTS に属するノードには入るが展開しない(そこは機能間の辺になる)ので、
    戻り値に ROOTS のノードは含めない。集合として定義されており探索順に依存しない。
    """
    seen: set[str] = set()
    stack = sorted(start)
    while stack:
        for nxt in adj.get(stack.pop(), ()):
            if nxt in all_roots or nxt in seen:
                continue
            seen.add(nxt)
            stack.append(nxt)
    return seen


def cluster(cg: dict, features: list[dict], cfg: dict, root=None) -> dict:
    """①〜④ を返す。入力が同じなら出力も同じ(design §8.3.1)。

    `root` はリポジトリの根。抽出器が無い言語の入口を未検査に回すには、そのファイルの実在を
    ここで確かめる(無ければ FT1。**省くと全部を照合する** — `base.unextracted_symbol`)。
    """
    roots, errors, skipped = resolve_roots(features, cg, cfg, root)
    if errors:
        return {"errors": errors, "skipped_entries": skipped}

    e1, e2 = edge_sets(cg)
    adj_n, adj_w = _adj(e1), _adj(e1 | e2)
    all_roots = {s for rs in roots.values() for s in rs}
    root_owner = {s: fid for fid, rs in sorted(roots.items()) for s in rs}

    nodes_n = {f["id"]: roots[f["id"]] | _reach(roots[f["id"]], adj_n, all_roots)
               for f in features}
    nodes_w = {f["id"]: roots[f["id"]] | _reach(roots[f["id"]], adj_w, all_roots)
               for f in features}

    contains_w: dict[str, set[str]] = defaultdict(set)
    for fid, nodes in sorted(nodes_w.items()):
        for sym in nodes:
            contains_w[sym].add(fid)

    # ③ 機能間の辺 — 条件を満たす (u,v) を**全部**持つ(代表1本を選ぶと探索順に依存する)
    sites: dict[tuple[str, str], dict[tuple[str, str], str]] = defaultdict(dict)
    for u, v in sorted(e1 | e2):
        if v not in all_roots:
            continue
        to_fid = root_owner[v]
        for from_fid in sorted(contains_w.get(u, ())):
            if from_fid == to_fid:
                continue
            conf = "確定" if ((u, v) in e1 and u in nodes_n[from_fid]) else "候補"
            prev = sites[(from_fid, to_fid)].get((u, v))
            if prev != "確定":
                sites[(from_fid, to_fid)][(u, v)] = conf

    edges = []
    for (from_fid, to_fid) in sorted(sites):
        per = sites[(from_fid, to_fid)]
        edges.append({
            "from": from_fid, "to": to_fid,
            "confidence": "確定" if "確定" in per.values() else "候補",
            "call_sites": [{"from": u, "to": v, "confidence": c}
                           for (u, v), c in sorted(per.items())],
        })

    # 所有(ルートは定義により自機能に属する。これが無いと全ルートが ④ に落ちる)
    own: dict[str, set[str]] = {}
    for sym in sorted(_symbols(cg)):
        own[sym] = {root_owner[sym]} if sym in all_roots else set(contains_w.get(sym, ()))

    shared = [{"symbol": s, "fanin": len(fids), "features": sorted(fids)}
              for s, fids in sorted(own.items()) if len(fids) >= 2]
    shared.sort(key=lambda r: (-r["fanin"], r["symbol"]))
    unreached_all = sorted(s for s, fids in own.items() if not fids)
    unreached = [s for s in unreached_all if not s.endswith(MODULE_SCOPE_SUFFIX)]
    unreached_module_scope = [s for s in unreached_all if s.endswith(MODULE_SCOPE_SUFFIX)]

    # Tier 3(正規表現抽出)の言語は呼び出し関係が系統的に不完全なので、その言語由来の
    # 「未到達」は取りこぼしでありうる(features.md §5.1 の第2の例外)。絶不在の主張が
    # 最も濃縮される ④ にだけ警告が無い、が実測の欠陥だった — ここで言語別に印を付ける
    tier3_syms: set[str] = set()
    for data in cg.get("languages", {}).values():
        if int(data.get("tier", 0) or 0) >= 3:
            tier3_syms |= {s["id"] for s in data.get("symbols", [])}
    unreached_tier3 = [s for s in unreached if s in tier3_syms]
    members = {f["id"]: sorted(s for s in nodes_w[f["id"]]
                               if own.get(s) == {f["id"]} or s in roots[f["id"]])
               for f in features}

    out = {
        "features": [f["id"] for f in features],
        "roots": {fid: sorted(rs) for fid, rs in sorted(roots.items())},
        "members": members,          # ① JSON のみ。docs には出さない
        # 各機能から到達する全シンボル(共有関数を含む)。「経路が無い」と断定してよいかの
        # 判定に要る(経路上に未解決の呼び出しがあれば断定しない)。JSON のみ。
        "closure": {f["id"]: sorted(nodes_w[f["id"]]) for f in features},
        "shared": shared,            # ②
        "edges": edges,              # ③
        "unreached": unreached,      # ④
        "unreached_tier3": unreached_tier3,   # ④ のうち Tier 3 言語由来(偽陽性でありうる)
        "unreached_module_scope": unreached_module_scope,
        # 抽出器が無い言語の入口(未検査)。その機能の辺・共有関数・到達は数えていない
        "skipped_entries": skipped,
        "counts": {"features": len(features), "edges": len(edges),
                   "shared": len(shared), "unreached": len(unreached),
                   "unreached_module_scope": len(unreached_module_scope),
                   "confirmed_edges": sum(1 for e in edges if e["confidence"] == "確定"),
                   "candidate_edges": sum(1 for e in edges if e["confidence"] == "候補")},
        "errors": [],
    }
    # ⑤ 共有データストア結合(P10)。**呼び出し辺として存在しない連携**を資源の側から拾う。
    # ここに置くのは、③(機能間の辺)を引いた残りが指摘になるからである。
    out["resource_coupling"] = res.couplings(out, cg, cfg)
    out["counts"].update(out["resource_coupling"]["counts"])
    return out


def missing_entrypoints(cg: dict, roots: dict[str, set[str]],
                        cfg: dict | None = None) -> list[str]:
    """FT2: callgraph にあるのに、どの機能の入口にもなっていないエントリポイント。

    **母集団は `features.md` §0.1 が定めたものに限る。** テストと開発ツールは機能ではないので、
    ハンドラが `test_markers` / `tooling_markers` に当たるエントリポイントはここで外す。
    ふつうは収集の段階で落ちるのでここまで来ないが、**make 抽出器は自分の対象である
    Makefile を解析するために `include_tooling` を立てて集める**(`cgx/make_regex.py`)ので、
    Make のターゲットだけは endpoints に載ったままここへ届く。

    **濾さないと、規範が「機能表に載せない」と名指ししたものが、そのまま
    「機能の取りこぼし(高)」になる。**しかも `tooling_markers` へ足しても閉じない
    (make 抽出器が自分のために `include_tooling` を上書きするため)ので、
    **設定では回避できない**。実測 2026-08-22: 重大度「高」235 件の全件が
    `Makefile`(183)と `.mk`(52)のターゲットだった(`docs/issues/219`)。
    同じファイルの FT1 は `callgraph-check.py` の `entry_kind()` で既にこの濾しを通している —
    **FT2 だけが通っていなかった。**

    **判定できるのはハンドラがパスを含むときだけ**で、`POST /internal/health` のように
    定義元ファイルが分からないものは濾せない(`entry_kind()` と同じ限界。§0.1 の
    「機械が強制するものと、人間が強制するものを混同しない」)。

    `include_tests` / `include_tooling` を立てた run は「その母集団も見たい」という明示なので、
    そのときは濾さない。`cfg` を渡さない呼び出しは濾さない(従来どおり)。
    """
    covered = {s for rs in roots.values() for s in rs}
    cfg = cfg or {}
    skip: list[str] = []
    if not cfg.get("include_tests"):
        skip += cfg.get("test_markers", [])
    if not cfg.get("include_tooling"):
        skip += cfg.get("tooling_markers", [])
    out: set[str] = set()
    for data in cg.get("languages", {}).values():
        for ep in data.get("endpoints", []):
            handler = ep.get("handler")
            if not handler or handler in covered:
                continue
            if skip and base.is_test(handler.split("::", 1)[0], skip):
                continue
            out.add(f"{ep['id']} → {handler}")
    return sorted(out)


# **FT5 が対象にするのは「統合された機能」だけ**(§2)。入口が1件の普通のファイルまで広げると、
# ハンドラの隣に在る死にコードが全部「入口の取りこぼし」に化ける — 実測で15件の偽陽性が出た。
MIN_CONSOLIDATED_ENTRIES = 2


def missing_consolidated_entrypoints(cg: dict, features: list[dict],
                                     result: dict) -> list[dict]:
    """FT5: 入口を**網羅宣言した**ファイルに、機能表が知らないシンボルが増えていないか。

    FT2 が見られるのは endpoints(REST・キュー・スケジュール)だけである。**画面ハンドラの
    ように エンドポイントを持たない入口**は、機能表から落ちても FT2 の網にかからず、
    `feature-graph.md` の「どの入口からも到達しない関数」に静かに積まれるだけだった
    (実測: Vue 画面1枚の入口が 23 のまま実装が 37 になり、14 件が未到達に化けていた。
    見つけたのは人手の独立レビューで、機械は最後まで黙っていた)。

    **偽陽性を出す検査は「誤作動して作業を阻む検査」そのもの**なので、対象は
    次の2条件を満たすファイル(= 入口を網羅宣言したファイル)に限る:

      (a) 機能表がそのファイルのシンボルIDを `MIN_CONSOLIDATED_ENTRIES` 件以上、
          入口として並べている(= §2 の「統合」。入口1件の普通のファイルは対象外)
      (b) そのファイルの**未宣言シンボルが1つも機能から到達しない**
          (= 内部ヘルパを持たない。持つファイルは「全部並べる」規約ではない)

    この2条件の下で未宣言かつ未到達のシンボルは、死にコードではなく入口の取りこぼしである。
    実測(286機能・280入口ファイル・未到達 9,702)で、この絞り込みは HEAD で0件、
    23→37 の欠落では 14 件ちょうどを出した。
    """
    declared: dict[str, set[str]] = defaultdict(set)
    owners: dict[str, set[str]] = defaultdict(set)
    for f in features:
        for entry in f["entries"]:
            if "::" not in entry:
                continue                     # エンドポイントIDはファイルを特定できない
            declared[entry.split("::", 1)[0]].add(entry)
            owners[entry.split("::", 1)[0]].add(f["id"])
    if not declared:
        return []

    by_file: dict[str, set[str]] = defaultdict(set)
    for data in cg.get("languages", {}).values():
        for sym in data.get("symbols", []):
            sid = sym["id"]
            if sid.endswith(MODULE_SCOPE_SUFFIX):
                continue                     # 関数ではない擬似シンボル(④ でも数えない)
            by_file[sid.split("::", 1)[0]].add(sid)

    unreached = set(result.get("unreached", ()))
    tier3 = set(result.get("unreached_tier3", ()))
    out: list[dict] = []
    for path, decl in sorted(declared.items()):
        if len(decl) < MIN_CONSOLIDATED_ENTRIES:
            continue
        rest = by_file.get(path, set()) - decl
        if any(s not in unreached for s in rest):
            continue                         # 到達する未宣言シンボル = 内部ヘルパを持つ
        for sid in sorted(rest):
            out.append({"file": path, "symbol": sid, "declared": len(decl),
                        "features": sorted(owners[path]), "tier3": sid in tier3})
    return out


# --------------------------------------------------------------------------- 出力

def _table(headers: list[str], rows: list[list[str]]) -> list[str]:
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    if not rows:
        out.append("|" + "|".join(" (なし) " if i == 0 else " - "
                                  for i in range(len(headers))) + "|")
        return out
    out.extend("| " + " | ".join(base.escape_cell(c) for c in r) + " |" for r in rows)
    return out


def render_graph(result: dict, cfg: dict) -> str:
    shown = int(feature_cfg(cfg)["call_sites_shown"])
    c = result["counts"]
    out = [
        "---",
        "id: feature-graph",
        f"features: {c['features']}",
        f"edges: {c['edges']}",
        f"confirmed_edges: {c['confirmed_edges']}",
        f"candidate_edges: {c['candidate_edges']}",
        f"shared: {c['shared']}",
        f"unreached: {c['unreached']}",
        f"coupled_resources: {c.get('coupled_resources', 0)}",
        f"unlinked_pairs: {c.get('unlinked_pairs', 0)}",
        "---",
        "",
        GRAPH_NOTE,
        "",
        "# 機能間の関係(機能表クラスタリング)",
        "",
        "`docs/03-impl/features.md`(境界の定義)と `docs/03-impl/callgraphs/`(コード由来の事実)",
        "から機械的に導出したもの。**どちらが正かは決めない。**",
        "",
        "確度の意味(`.claude/directions/features.md` §5):",
        "",
        "- `確定` — 名前解決が成功した辺だけで経路が繋がる",
        "- `候補` — 同名衝突などの**候補辺**を算入して初めて繋がる。"
        "経路が実在するとは限らないが、**取りこぼすよりは出す**",
        "",
    ]
    skipped = result.get("skipped_entries", [])
    if skipped:
        out += [
            f"**未検査: 入口 {len(skipped)} 件は抽出器が無い言語のもので、callgraph に現れない** — "
            "その入口から先の辺・共有関数・到達はこの文書に出ていない(「無い」ではない)。",
            "",
        ] + [f"- `{s}`" for s in skipped] + [""]
    out += [
        "## 機能間の辺",
        "",
    ]
    rows = []
    for e in result["edges"]:
        sites = e["call_sites"]
        shown_sites = sites[:shown]
        cell = ", ".join(f"`{s['from']}` → `{s['to']}`"
                         + ("(候補)" if s["confidence"] == "候補" else "")
                         for s in shown_sites)
        if len(sites) > shown:
            cell += f" ほか {len(sites) - shown} 件"
        rows.append([e["from"], e["to"], e["confidence"], cell])
    out += _table(["呼び出し元", "呼び出し先", "確度", "呼び出し箇所"], rows)

    out += [
        "",
        "## 複数機能から到達される共有関数(境界の実体)",
        "",
        "ファンインが2以上の関数は機能の内部ヘルパではありえない"
        "(`.claude/directions/features.md` §4)。",
        "機能表に足すとルートに昇格し、呼んでいた側に `callees` の辺が1本立つ。",
        "**昇格させるかは人間の判断。**",
        "",
    ]
    out += _table(["シンボル", "ファンイン", "到達元の機能"],
                  [[f"`{r['symbol']}`", str(r["fanin"]), ", ".join(r["features"])]
                   for r in result["shared"]])

    out += [
        "",
        "## どの入口からも到達しない関数",
        "",
        "**候補辺も算入した上で**到達しない(`.claude/directions/features.md` §5:"
        "「無い」の主張は広く)。到達不能コードの候補だが、**削ってよいかは決めない** — "
        "動的呼び出し・外部からの参照・ツール未対応の可能性がある。",
        "",
    ]
    if result["unreached_module_scope"]:
        out += [
            f"モジュール直下の擬似シンボル `<module>` {c['unreached_module_scope']} 件は"
            "この表から除いてある(import 時に走るコードであり、機能から到達しないのが正常)。",
            "",
        ]
    tier3 = set(result.get("unreached_tier3", []))
    if tier3:
        out += [
            f"**注意: うち {len(tier3)} 件は Tier 3(正規表現抽出)言語のシンボル** — "
            "呼び出し関係が系統的に不完全で、**「到達しない」は取りこぼしでありうる**"
            "(features.md §5.1)。削除候補として扱う前に人間が確認すること。",
            "",
        ]
    out += _table(["シンボル", "備考"],
                  [[f"`{s}`", "Tier 3(取りこぼしの可能性)" if s in tier3 else ""]
                   for s in result["unreached"]])
    out += _render_coupling(result, cfg)
    return "\n".join(out) + "\n"


def _render_coupling(result: dict, cfg: dict) -> list[str]:
    """⑤ 共有データストア結合 — 呼び出し辺として存在しない連携。

    ★ **資源ごとに1行**にする。機能対を全部並べると資源1つで O(n²) 行になり、
      実データでは読めない大きさになる。対の総数は必ず出し、代表だけを表示する。
    """
    cp = result.get("resource_coupling")
    if cp is None:
        return []
    rcfg = res.cfg_of(cfg)
    shown = int(rcfg["pairs_shown"])
    c = cp["counts"]
    out = [
        "",
        "## 同じ資源を触るのに呼び出し辺が無い機能",
        "",
        "サーバレス/イベント駆動では、連携の相当部分が**呼び出し辺として原理的に存在しない**。",
        "A がテーブルに書き B が読む — 呼び出しは1本も無いが、B は A の書式に依存している。",
        "この結合は callgraph に出ないので、**CG4(取りこぼし検出)の網にかからない**。",
        # `resources.md` は資源が1件も無ければ build-callgraphs.py が書かない。無条件に
        # リンクすると、資源を持たないプロジェクトで CS11(参照実在)違反を生成物が作る。
        *(["資源そのものは `docs/03-impl/callgraphs/resources.md`。"] if result.get("resources") else []),
        "",
        f"- 2つ以上の機能が触る資源: {c['coupled_resources']}",
        f"- そのうち**呼び出し辺で繋がっていない機能対**を含むもの: {c['finding_resources']}"
        f"(対の総数 {c['unlinked_pairs']})",
        f"- 広域共有資源(機能の {int(float(rcfg['ubiquitous_ratio']) * 100)}% 以上が触る): "
        f"{c['ubiquitous']} — **指摘からは外している**"
        "(全機能が触る資源に対の一覧を出しても読めないため。行としては下表に残る)",
        f"- どの機能にも属さないシンボルからの参照: {c['orphan_refs']}"
        "(入口の登録漏れか、機能から到達しないコード)",
        "",
        "**書き込みが絡む結合は「片方の書式に他方が依存する」**ので重大度は中、",
        "読み取りだけなら共有された読み取りモデルなので参考に落としてある。",
        "",
    ]
    def fold(ids: list[str]) -> str:
        # ★ 機能対を並べてはならない。資源1つで O(n²) 行になり、実データでは
        #   どの資源も同じ「辞書順で先頭の対」が並ぶだけの壁になる(実測で確認した)。
        #   読み手が要るのは「誰が書式を決めていて、誰がそれに依存しているか」である。
        if not ids:
            return "(なし)"
        head = ", ".join(ids[:shown])
        return head + (f" ほか {len(ids) - shown} 件" if len(ids) > shown else "")

    rows = []
    for r in cp["resources"]:
        writers, readers = r["writers"], r["readers"]
        others = [f for f in r["features"] if f not in set(writers) | set(readers)]
        rows.append([
            f"`{r['key']}`",
            str(len(r["features"])),
            str(len(r["unlinked_pairs"])),
            "広域" if r["ubiquitous"] else r["severity"],
            fold(writers),
            # 読み書きが判別できなかった機能もここに出す。両方空の行を作らない
            # (資源の操作名が語彙に無いと access が unknown のままになる)。
            fold([f for f in readers if f not in set(writers)]
                 or [f"{f}(読み書き不明)" for f in others]),
        ])
    out += _table(["資源", "触る機能", "辺の無い対", "重大度",
                   "書き込む機能(書式の持ち主)", "読むだけの機能(依存側)"], rows)
    out += ["",
            "**書き込む機能が書式を決め、読む機能がそれに依存する。**"
            "呼び出し辺が無いので、書式を変えても機械的には誰も気付かない — "
            "そこを relations の本文(戻り値・副作用 / 連携先と連携内容)で埋める。",
            "個々の機能対は `--format json` の `resource_coupling.resources[].unlinked_pairs` に全部ある。",
            ""]
    return out

#!/usr/bin/env python3
"""機能表に足すべき行を提案する(**確定はしない**)。

規範: .claude/directions/features.md / 設計: .claude/scripts/callgraph-design.md §8.4

**境界は設計判断なので機械は決めない。** ここでやるのは材料を出すことだけ:

  ・機能候補     — エントリポイント1つ = 1機能(既定の粒度)
  ・共通基盤候補 — ファンイン(到達できる機能の数)が閾値以上の関数 = 境界の実体
  ・統合候補     — 関数集合の重なりが大きい機能対(束ねるかは人間が決める)
  ・FT2          — callgraph にあるのに機能表に無いエントリポイント(機能の取りこぼし)

機能表がまだ無ければ、エントリポイントから**暫定クラスタリング**して全部を提案する。
既にあれば、それを入力にして「次に足すべき行」を出す。
**入口を写す → ファンイン上位を昇格させる → 再実行** を繰り返すと収束する
(ルートへの昇格は経路を切るだけで新しい到達を生まないため)。

閾値は `callgraph-config.json` の `features` 節。**提案のためのパラメータであって規範ではない**
(`cluster-features.py` の結果は閾値に依存しない)。

使い方:
    python3 .claude/scripts/propose-features.py
    python3 .claude/scripts/propose-features.py --format json
    python3 .claude/scripts/propose-features.py --from cg.json

終了コード: 0=成功 2=使い方・解析エラー
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

# `main` だけは種別を主張しない protocol なので、ここでも種別に落とさず `other` に置く
# (`callgraph-check.py` の `KIND_AGNOSTIC_PROTOCOLS` と同じ理由)。`tool` に落とすと、
# 抽出器が持っていない知識を機能候補の側で主張し直すことになる。**種別は人間が決める。**
PROTOCOL_KIND = {"rest": "rest-api", "graphql": "rest-api", "grpc": "rest-api",
                 "event": "event", "schedule": "event", "cli": "tool", "tool": "tool",
                 "main": "other"}


def slug(text: str) -> str:
    out = re.sub(r"[^0-9a-zA-Z]+", "-", text).strip("-").lower()
    return re.sub(r"-{2,}", "-", out) or "x"


def module_slug_of(symbol_id: str) -> str:
    path = symbol_id.split("::", 1)[0]
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 2:
        return slug(parts[-2])
    return slug(Path(path).stem)


def feature_slug_of(ep: dict) -> str:
    if ep.get("protocol") in {"rest", "graphql", "grpc"} and ep.get("path_key"):
        segs = [("id" if s == "{}" else s) for s in ep["path_key"].split("/") if s]
        method = (ep.get("id", "").split(" ", 1)[0] or "any").lower()
        return slug("-".join([*segs, method]))
    qual = ep.get("handler", "").split("::", 1)[-1]
    return slug(qual)


def suggest_rows(cg: dict) -> tuple[list[dict], list[str]]:
    """(機能候補の行, 注記) を返す。エントリポイント1つ = 1機能。"""
    notes: list[str] = []
    cands: list[dict] = []
    for data in sorted(cg.get("languages", {}).items()):
        for ep in data[1].get("endpoints", []):
            if not ep.get("handler"):
                notes.append(f"ハンドラが特定できないエンドポイントを飛ばした: {ep['id']}"
                             "(**機能候補から漏れている**ので手で足すか抽出器を直す)")
                continue
            if ep.get("protocol") == "main":
                notes.append(f"種別が決まらない入口: {ep['id']}"
                             "(`protocol: main` は「実行ファイルの入口」しか言わない。"
                             "**`kind` は `other` で出すので、人間が決めること** — "
                             "`other` のままにするなら、対応する docs/03-impl/relations/MODULE-*.md "
                             "の本文に理由が要る(.claude/directions/relations.md §3))")
            cands.append({"entry": ep["id"], "handler": ep["handler"],
                          "kind": PROTOCOL_KIND.get(ep.get("protocol", ""), "other"),
                          "slug": feature_slug_of(ep)})

    if not cands:
        # エンドポイントが1つも無いライブラリ等。呼び出し元の無い public シンボルを候補にする。
        called = {e["to"] for d in cg.get("languages", {}).values()
                  for e in d.get("edges", [])}
        for data in sorted(cg.get("languages", {}).items()):
            for s in data[1].get("symbols", []):
                if s["id"] not in called and s.get("visibility") == "public":
                    cands.append({"entry": s["id"], "handler": s["id"],
                                  "kind": "function-call",
                                  "slug": slug(s["id"].split("::", 1)[-1])})
        if cands:
            notes.append("エンドポイントが0件だったので、**呼び出し元の無い public シンボル**を"
                         "入口候補にした。パターン未対応の可能性もあるので"
                         "「エントリポイントが無い」と結論しないこと")

    # ★ 同じハンドラを指すエントリポイントは**1機能に畳む**。
    #   Lambda ハンドラは「関数として入口」でもあり「定時起動の宛先」でもあるので、
    #   インフラ定義を読むようになった途端に同じハンドラが複数のエンドポイントで出てくる
    #   (実データで踏んだ)。畳まないと入口が重複して FT1 が即座に止まる。
    #   FT2 はハンドラで判定するので、代表を1つ載せれば取りこぼしにはならない。
    kind_rank = {"rest-api": 0, "event": 1, "tool": 2, "function-call": 3, "other": 4}

    # ★ 同じエンドポイントIDが**複数のハンドラ**に対応することがある。
    #   実データでは `GET /health` が Lambda ごとに1本ずつあり、5関数に解決された。
    #   機能表の入口はエンドポイントIDとして照合されると**その全部**がルートになるので、
    #   そのまま提案すると入口が重なって FT1 が即座に止まる。
    #   こういう入口は**ハンドラのシンボルIDで提案する**(機能表はどちらの表記も取れる)。
    by_entry: dict[str, set[str]] = {}
    for c in cands:
        by_entry.setdefault(c["entry"], set()).add(c["handler"])
    ambiguous_entries = {e for e, hs in by_entry.items() if len(hs) > 1}
    for c in cands:
        if c["entry"] in ambiguous_entries:
            c["entry"] = c["handler"]
    if ambiguous_entries:
        notes.append(
            "同じエンドポイントIDが複数のハンドラに解決される入口があったので、"
            "**シンボルIDで提案した**: "
            + ", ".join(f"`{e}`" for e in sorted(ambiguous_entries)[:5])
            + (f" ほか {len(ambiguous_entries) - 5} 件" if len(ambiguous_entries) > 5 else "")
            + "(エンドポイントIDのままだと全ハンドラが1機能のルートになり、入口が重なる)")

    by_handler: dict[str, list[dict]] = {}
    for c in cands:
        by_handler.setdefault(c["handler"], []).append(c)
    cands = []
    for handler, group in sorted(by_handler.items()):
        group.sort(key=lambda c: (kind_rank.get(c["kind"], 9), c["entry"]))
        head = dict(group[0])
        if len(group) > 1:
            head["also"] = [c["entry"] for c in group[1:]]
            notes.append(f"同じハンドラを指す入口を1機能に畳んだ: `{handler}` ← "
                         + ", ".join(f"`{c['entry']}`" for c in group)
                         + "(**別の機能にしたいなら機能表で分ける**)")
        cands.append(head)

    rows: list[dict] = []
    used: dict[str, int] = {}
    for c in sorted(cands, key=lambda c: (c["entry"], c["handler"])):
        mod = module_slug_of(c["handler"])
        fid = f"MODULE-{mod}-{c['slug']}"
        used[fid] = used.get(fid, 0) + 1
        if used[fid] > 1:
            fid = f"{fid}-{used[fid]}"
        rows.append({"id": fid, "kind": c["kind"], "entry": c["entry"],
                     "module": f"MOD-{mod}", "handler": c["handler"]})
    return rows, sorted(set(notes))


def jaccard(a: set, b: set) -> float:
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def main(argv: list[str]) -> int:
    if any(a in ("-h", "--help") for a in argv[1:]):
        print(__doc__)   # 明示要求は 0。使い方エラーの 2 と区別する(tools-readme §2)
        return 0
    args = argv[1:]
    fmt, from_json = "md", None
    i = 0
    while i < len(args):
        a = args[i]
        if a in {"--format", "--from"} and i + 1 < len(args):
            i += 1
            if a == "--format":
                fmt = args[i]
            else:
                from_json = args[i]
        elif a.startswith("--format="):
            fmt = a.split("=", 1)[1]
        elif a.startswith("--from="):
            from_json = a.split("=", 1)[1]
        else:
            print(__doc__)
            return 2
        i += 1
    if fmt not in {"md", "json"}:
        print(__doc__)
        return 2

    root = base.find_root()
    base.ensure_kit_venv(root)
    cfg = base.load_config(root)
    fcfg = ft.feature_cfg(cfg)

    cluster_mod = importlib.util.spec_from_file_location(
        "cluster_features", _HERE / "cluster-features.py")
    cm = importlib.util.module_from_spec(cluster_mod)        # type: ignore[arg-type]
    cluster_mod.loader.exec_module(cm)                        # type: ignore[union-attr]
    cg = cm.load_callgraph(root, cfg, from_json)

    feats, ferrors = ft.load_features(root, cfg)
    proposed_rows, notes = suggest_rows(cg)
    provisional = not feats

    if provisional:
        # 機能表がまだ無い。提案した入口で暫定クラスタリングして材料を出す。
        feats = [{"id": r["id"], "kind": r["kind"], "entries": [r["entry"]],
                  "module": r["module"], "summary": ""} for r in proposed_rows]
        ferrors = []
    if ferrors:
        print("## 機能表が読めない")
        for e in ferrors:
            print("  - " + e)
        return 2

    result = ft.cluster(cg, feats, cfg, root)
    if result.get("errors"):
        print("## 機能表とコールグラフが食い違っている(FT1)。先にこれを直す")
        for e in result["errors"]:
            print("  - " + e)
        return 2

    fanin_min = int(fcfg["fanin_threshold"])
    shared = [r for r in result["shared"] if r["fanin"] >= fanin_min]

    nodes = {fid: set(members) for fid, members in result["members"].items()}
    merges = []
    for a_id, b_id in ((a, b) for i2, a in enumerate(sorted(nodes))
                       for b in sorted(nodes)[i2 + 1:]):
        j = jaccard(nodes[a_id], nodes[b_id])
        if j >= float(fcfg["merge_jaccard"]):
            merges.append({"a": a_id, "b": b_id, "jaccard": round(j, 2)})
    merges.sort(key=lambda m: (-m["jaccard"], m["a"], m["b"]))

    missing = ft.missing_entrypoints(cg, result["roots"], cfg)

    if fmt == "json":
        print(json.dumps({"provisional": provisional, "rows": proposed_rows,
                          "shared_candidates": shared, "merge_candidates": merges,
                          "missing_entrypoints": missing, "notes": notes},
                         ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    print("# 機能表への提案(**これは候補であって確定ではない**)")
    print()
    print("境界は設計判断なので、機械は決めない。人間が"
          f"`{fcfg['path']}` に写した時点で確定する(.claude/directions/features.md §7)。")
    print()

    if provisional:
        print(f"## 機能候補 — 入口 {len(proposed_rows)} 件(1入口 = 1機能)")
        print()
        print(f"`{fcfg['path']}` の「## 機能一覧」にそのまま貼れる。"
              "**機能ID・所属・概要は案なので直すこと。**")
        print()
        print("| 機能ID | 種別 | 入口 | 所属 | 概要 |")
        print("|---|---|---|---|---|")
        for r in proposed_rows:
            # 入口IDは `|` を含みうる(`dispatch ALL|GROUP @ ...`)。表のセルとして必ず逃がす。
            cells = [base.escape_cell(r[k]) for k in ("id", "kind", "entry", "module")]
            print("| " + " | ".join(cells) + " |  |")
        print()
        print("以降の表は、この暫定の入口でクラスタリングした結果である。")
    else:
        print(f"## 機能表は既にある({len(feats)} 機能)。次に足すべき行を出す")
    print()

    print(f"## 共通基盤候補 — ファンイン {fanin_min} 以上の関数 {len(shared)} 件")
    print()
    print("2つ以上の機能から到達される関数は**機能の内部ヘルパではありえない**"
          "(= 境界の実体)。")
    print("機能表に `function-call` の行として足すとルートに昇格し、"
          "呼んでいた側に `callees` の辺が1本立つ。")
    print("**ファンインが高いだけで昇格させなければならないわけではない** — "
          "薄いユーティリティは畳み込んだままでよい。判断は人間。")
    print()
    print("| シンボル | ファンイン | 到達元の機能(先頭5件) |")
    print("|---|---|---|")
    for r in shared:
        heads = r["features"][:5]
        tail = f" ほか {len(r['features']) - 5} 件" if len(r["features"]) > 5 else ""
        print(f"| `{r['symbol']}` | {r['fanin']} | {', '.join(heads)}{tail} |")
    if not shared:
        print("| (なし) | - | - |")
    print()
    if shared:
        dist = " / ".join(f"≥{t}: {sum(1 for r in result['shared'] if r['fanin'] >= t)}"
                          for t in (2, 3, 5, 10, 20))
        print(f"ファンイン別の件数 — {dist}")
        print("多すぎて見切れないときは `callgraph-config.json` の "
              "`features.fanin_threshold` を上げて**上流から順に**片付ける。"
              "**閾値はこの提案の絞り込みにしか効かない** — "
              "`cluster-features.py` の結果は閾値に依存しない。")
        print()

    print(f"## 統合候補 — 関数集合の重なりが {fcfg['merge_jaccard']} 以上の機能対 "
          f"{len(merges)} 件")
    print()
    print("**機械は勝手に束ねない。** 束ねるなら機能表の1行に入口を複数書く"
          "(.claude/directions/features.md §2)。")
    print()
    print("| 機能A | 機能B | 重なり |")
    print("|---|---|---|")
    for m in merges:
        print(f"| {m['a']} | {m['b']} | {m['jaccard']} |")
    if not merges:
        print("| (なし) | - | - |")
    print()

    if not provisional:
        print(f"## FT2 — 機能表に無いエントリポイント {len(missing)} 件(**機能の取りこぼし**)")
        print()
        for m in missing:
            print(f"- {m}")
        if not missing:
            print("- (なし)")
        print()

    if notes:
        print("## 注記")
        print()
        for n in notes:
            print(f"- {n}")
        print()

    print("→ 次: 機能表を人間が確定させてから "
          "`python3 .claude/scripts/cluster-features.py`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

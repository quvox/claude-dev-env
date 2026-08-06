---
id: 075-modify-feature-graph-references-resources-md-that-is-not-always-generated
type: modify
severity: 低
found: 2026-08-07
found_in: /doc-check(task-clause-ids-and-split-policy の機械検査 CS11)
related: docs/03-impl/feature-graph.md, docs/03-impl/callgraphs/index.md
pattern: generated-file-references-conditionally-generated-sibling
pattern_survey: SSOT 全 154 ファイルの CS11(参照実在)違反 23 件を分類。22 件は削除済み issue のパス(`docs/issues/054` が追跡)で、生成物どうしの参照切れはこの1件のみ
summary: 生成物 feature-graph.md が callgraphs/resources.md を参照するが、資源が0件のプロジェクトではそのファイルが生成されない
---

# 075 `feature-graph.md` が生成されない `callgraphs/resources.md` を参照する

## 事象

`docs/03-impl/feature-graph.md:230`(生成物。手書き禁止)が
「資源そのものは `docs/03-impl/callgraphs/resources.md`。」と書いているが、
そのファイルは存在しない。`.claude/scripts/build-callgraphs.py:381-382` は

```python
if result.get("resources"):
    out["resources.md"] = render_resources(result)
```

と**資源が1件以上あるときだけ**書き出す。本プロジェクトの資源は 0 件なので生成されない。
一方 `cluster-features.py` はこの参照文を**無条件に**出力するため、参照切れが恒久的に残る。

再現手順:

1. `CG_OUT=$(python3 .claude/scripts/resolve-callgraph-out.py) && python3 .claude/scripts/cluster-features.py --out "$CG_OUT"` で再生成する。
2. `python3 .claude/scripts/check-changeset.py --ssot docs` の CS11 に
   「`03-impl/feature-graph.md`: 230行: 参照先が実在しない: `docs/03-impl/callgraphs/resources.md`」が出る。

## 影響

`check-changeset.py --ssot`(仕様ドキュメントの一括検査)の CS11 違反が1件残り続ける。
**プロジェクト側では直せない**(両方とも生成物で、手書きは禁止されている)。
読み手は存在しないファイルを探すことになる。振る舞いへの影響は無い。

## 原因の見当

キット側(`.claude/scripts/`)の欠陥である。`resources.md` を条件付きで書き出す側と、
それを無条件に参照する側が噛み合っていない。**修正は `/kit-improve` 案件**であり、
本プロジェクトのドキュメント修正では閉じられない。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| 参照の有無 | `feature-graph.md` は資源ファイルを無条件に名指す | `.claude/directions/callgraphs.md` §3 のファイル一覧は `resources.md` を常設として描いている | キット側の生成器が正しくない(参照するなら常に出力するか、参照を条件付きにする) |

## 対処案

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | `build-callgraphs.py` が資源0件でも `resources.md` を「(なし)」の表で常に出力する | キット。`callgraphs.md` §3 の一覧と一致し、参照が常に解決する |
| B | `cluster-features.py` が、資源が0件のときは参照文を出力しない | キット。生成物どうしの整合が取れる |

## 経緯

- 2026-08-07 起票。`task-clause-ids-and-split-policy` の `/doc-check` で、
  SSOT 一括検査の CS11 違反 23 件を分類した際に、22 件の削除済み issue パス
  (`docs/issues/054` が追跡)とは別の欠陥として分離した。
  **`docs/issues/054` の「本文で扱う 23 件」の内訳は 22 件に訂正が必要**である。

---
id: python
language: python
tier: 2
symbols: 5
edges: 0
endpoints: 0
unresolved: 0
---

<!-- BEGIN NOTE: build-callgraphs.py -->
<!-- 生成物。手書き禁止。`CG_OUT=$(python3 .claude/scripts/resolve-callgraph-out.py) && python3 .claude/scripts/build-callgraphs.py --out "$CG_OUT"` で再生成する。
     辞書順に固定されており、実装が変わらなければこのファイルも変わらない。
     **これは機能間連携仕様書ではない**(.claude/directions/callgraphs.md)。 -->
<!-- END NOTE: build-callgraphs.py -->

# python コールグラフ (Tier 2)

## エントリポイント

| 種別 | 識別子 | 正規化キー | ハンドラ | 検出根拠 |
|---|---|---|---|---|
| (なし) | - | - | - | - |

## 関数表

| シンボル | 種別 | 可視性 | 呼び出す先 | 呼び出し元 |
|---|---|---|---|---|
| `examples/orch-sample/src/mathkit/geometry.py::circle_area` | function | public | - | - |
| `examples/orch-sample/src/mathkit/geometry.py::rect_area` | function | public | - | - |
| `examples/orch-sample/src/mathkit/stats.py::mean` | function | public | - | - |
| `examples/orch-sample/src/mathkit/stats.py::median` | function | public | - | - |
| `examples/orch-sample/src/mathkit/strings.py::slugify` | function | public | - | - |

## 解決できなかった呼び出し

<!-- 空欄は「呼び出しが無い」を意味する。解決できなかったものは必ずここに出る。 -->

| 呼び出し元 | 呼び出し式 | 分類 | 候補 |
|---|---|---|---|
| (なし) | - | - | - |

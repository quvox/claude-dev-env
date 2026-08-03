---
id: 001-modify-orchestrator-test-only-symbols
type: modify
severity: 中
found: 2026-08-02
found_in: task-docs-restructure の機能表起案(cluster-features.py の未到達関数)
related: MODULE-orchestrator-controller, MODULE-orchestrator-dashboard
summary: orchestrator の7シンボルが製品コードから呼ばれず、テストからのみ参照されている
---

## 事象

`cluster-features.py` の「どの入口からも到達しない関数」に次の7件が出た。候補辺を算入しても
到達せず、`grep` でも製品コード側の呼び出し箇所が見つからない(参照はすべて `*_test.go`)。

| シンボル | 定義位置 | 製品コード側の参照 |
|---|---|---|
| `orchestrator/controller.go::Controller.resolveInterventions` | controller.go:833 | なし(`controller_test.go:407` のみ) |
| `orchestrator/controller.go::Controller.resolveOne` | controller.go:897 | なし(`controller_test.go:683,695` のみ) |
| `orchestrator/controller.go::Controller.openInterventionCount` | controller.go:798 | なし(`controller_test.go:301,345,389` のみ) |
| `orchestrator/dashboard.go::DashboardState.SelectableWorker` | dashboard.go:119 | なし(`term_test.go:102` 経由) |
| `orchestrator/dashboard.go::DashboardState.SelectableWorkerStatus` | dashboard.go:127 | なし(`mode_test.go:87` 経由) |
| `orchestrator/dashboard.go::selectableWorker` | dashboard.go | 上2件からのみ |
| `orchestrator/dashboard.go::selectableWorkerID` | dashboard.go | 上2件からのみ |

比較のため、同じく未到達に出た次の4件は**説明がつくので対象外**とした:
`term.go::resolveMenu`(「pure, unit-testable twin」とコメントに明示)、
`state.go::Store.SaveControl` / `Store.RemoveSidecar`(「used in tests / by tooling」と明示)、
`main.go::terminalConfirm` と `docker-proxy/main.go::cachedResolveProjectDir`(関数値経由で
静的解決できないだけ。実際には使われている)。

## 影響

- 死んだコードであれば、`resolveInterventions` が担っていたはずの**介入の一括解決経路が製品では
  動いていない**ことになる(テストは通るので気づけない)。振る舞いの欠落かどうかは未確認。
- 死んでいないなら、抽出器が辿れない動的な呼び出し経路があるということで、コールグラフの
  未到達判定の信頼性に関わる。

いずれにせよ機能間連携仕様書の記述内容が変わるため、severity は「中」。

## 原因の見当

**推測**: `resolveInterventions`(バッチ経路)と `resolveOne`(worker セッション内経路)は
`controller.go:868` のコメントで「Shared by the batch path (resolveInterventions) and the
per-worker session path (resolveOne / selector, Phase③ 3d)」と説明されている。
実装の途中でセッション内経路へ一本化され、バッチ経路の呼び出しだけが外れた可能性がある。
`DashboardState.SelectableWorker*` は TUI の選択操作から呼ばれる想定に見えるが、
`dashtui.go` は `dashModel.selectable` を自前で持っている。

## 正はどちらか

**要確認。** 設計意図(介入の一括解決を残すのか)が分からないため、実装が誤りとも仕様が誤りとも
判断できない。02-design の状態遷移を書き起こす際に、この経路が設計に存在するかを突き合わせること。

## 対処案

- 02-design の orchestrator 状態遷移に「介入の一括解決」が存在するかを確認する。
- 存在するなら呼び出し経路の欠落(bug へ格上げ)。存在しないなら死んだコードの削除(modify のまま)。
- `DashboardState.SelectableWorker*` は TUI の選択実装と重複していないかを併せて確認する。

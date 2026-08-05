---
target: docs/03-impl/features.md
change: replace
sections:
  - "## 到達しない関数についての判断"
deletes: []
reason: 変更相対・タスク相対の言い回し(「本変更」「本タスク」「現行も」)が残っており、参照先が SSOT に存在しない(docs/issues/056。CLAUDE.md §1「SSOT はいまの姿だけを記述する」)
reflected: 2026-08-05
---

<!-- 変更指示。反映後の最終形を書く。version / verified は持たない。
     変更点は言い回しだけで、意味は変えていない(「本変更より前に起動した」→「管理ラベルが
     付く前に起動された」など、時点を観測できる性質で言い直した)。 -->

## 到達しない関数についての判断

<!-- feature-graph.md の「どの入口からも到達しない関数」16件に対する仕分け。生成物ではなく人間の判断。 -->

| シンボル | 判断 |
|---|---|
| `claude-dev::main` / `claude-dev-mac::main` | ディスパッチャ本体。サブコマンドのハンドラを入口にしているので本体には辺が立たない(抽出の構造上そうなる) |
| `docker-proxy/main.go::cachedResolveProjectDir` / `lookupProjectDir` | `var resolveProjectDir = cachedResolveProjectDir`(`docker-proxy/main.go:47`)の関数値経由。Tier 2 の静的解決の限界 |
| `orchestrator/main.go::terminalConfirm` | `Confirm: terminalConfirm`(`orchestrator/main.go:166`)の関数値経由。同上 |
| `orchestrator/term.go::resolveMenu` | `selectMenu` の鍵操作を単体テスト可能にした純粋関数(`orchestrator/term.go:184` のコメント)。テスト専用であることが明示されている |
| `orchestrator/state.go::Store.SaveControl` / `Store.RemoveSidecar` | 「used in tests / by tooling」と明示(`orchestrator/state.go:472`)。外部ツール向けの公開 API |
| `orchestrator/controller.go::Controller.resolveInterventions` / `resolveOne` / `openInterventionCount`、`orchestrator/dashboard.go::DashboardState.SelectableWorker` / `SelectableWorkerStatus`(と私有ヘルパ2件) | **製品コードからの呼び出しが見つからない**(テストからのみ参照)。到達不能コードの疑い → `docs/issues/001-modify-orchestrator-test-only-symbols.md` で報告しており、機能表の側では扱わない |


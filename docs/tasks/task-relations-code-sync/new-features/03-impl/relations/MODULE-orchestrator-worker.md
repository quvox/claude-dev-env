---
target: docs/03-impl/relations/MODULE-orchestrator-worker.md
change: replace
sections:
  - "## 呼び出され方"
deletes: []
reason: 引数表が `task` と `ctx` の2項目だけで、実シグネチャの `p *Plan` と `feedback` が呼び出し契約から落ちている(docs/issues/038 #13)。callees に claude-exec が無い(同 #12 の対称)
id: MODULE-orchestrator-worker
module: MOD-orchestrator
kind: function-call
sync: sync
impl: orchestrator/worker.go::Worker.Dispatch, orchestrator/worker.go::Worker.BuildPrompt, orchestrator/worker.go::ParseWorkerResult, orchestrator/worker.go::extractFromClaudeEnvelope, orchestrator/worker.go::resultFromStream
callers: MODULE-orchestrator-controller, MODULE-orchestrator-review
callees: MODULE-orchestrator-claude-exec, MODULE-orchestrator-state, MODULE-orchestrator-state-intervention, MODULE-orchestrator-worktree
contracts: CTR-orchestrator-prompt
design: DSN-mod-01, DSN-orch-01
requirements: FR-orch-03
tests: orchestrator/worker_stream_test.go::TestParseWorkerResultStreamJSON, orchestrator/worker_stream_test.go::TestParseWorkerResultBare, orchestrator/worker_stream_test.go::TestParseWorkerResultRealSample, orchestrator/policy_test.go::TestBuildPrompt_IncludesPolicyWhenPresent
updated: 2026-08-05
summary: タスクを worker へ割り当てて並列実行し結果を解釈する
---

<!-- 変更指示。反映後の最終形を書く。version / verified は持たない。
     callees に MODULE-orchestrator-claude-exec を追加した(worker.go:231 が Claude.RunPrompt を呼ぶ)。 -->

## 呼び出され方

- 契機: `MODULE-orchestrator-controller` が ready タスクを起動するとき、および
  `MODULE-orchestrator-review` が revise(差し戻し)を走らせるとき。
- 前提条件: worktree が用意でき、`claude` が PATH 上にあること。
- 引数(実シグネチャは `Worker.Dispatch(ctx context.Context, p *Plan, t *Task, feedback string)`。
  `orchestrator/worker.go:221`):

| 引数 | 型 | 必須 | 制約 | 実装が行う検証 |
|---|---|---|---|---|
| `ctx` | `context.Context` | 必須 | 中断時にキャンセルされる。キャンセルは `RunOpts.GraceSeconds` の猶予つきで子プロセスへ伝わる | **検証しない**(プロセス内呼び出し) |
| `p` | `*Plan` | 必須 | **plan 全体を受け取る**。`Goal` と `Completion` をプロンプトの文脈に使い、`Tasks` は完了済み依存タスクの要約(`dependencySummaries`)を組むために走査する | 検証しない。`nil` は想定していない |
| `t` | `*Task` | 必須 | `ID` / `Description` / `Completion` / `Kind` / `SessionID` / `ResumeSession` / `Attempts` を参照する | 検証しない。`ID` はそのまま worktree 名とログのパス要素になる(`docs/issues/011`) |
| `feedback` | 文字列 | 任意(空文字可) | 直前の Attempt からの差し戻し内容。**呼び出し契約の一部**であり、レビュアの重大指摘がここを通って worker へ戻る | 空文字なら該当見出しを出さない(`BuildPrompt`) |

- **呼び出し元は plan のスナップショットを渡す**: `controller.go:596`(`snapshotPlan`)が `planMu` の下で
  深いコピーを作り、`Dispatch` はロックの外で走る。したがって `Dispatch` が受け取る `p` / `t` は
  **live な plan ではない**(並行 worker の書き込みと競合しない)。
- 認可: プロセス内呼び出し。worker には後戻り不可の操作(push / deploy / 削除)と
  `SLACK_BOT_TOKEN` を渡さない。

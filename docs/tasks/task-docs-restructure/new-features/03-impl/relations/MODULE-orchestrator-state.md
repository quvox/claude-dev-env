---
target: docs/03-impl/relations/MODULE-orchestrator-state.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
id: MODULE-orchestrator-state
module: MOD-orchestrator
kind: function-call
sync: sync
impl: orchestrator/state.go::NewStore, orchestrator/state.go::Store.path, orchestrator/state.go::Store.SaveState, orchestrator/state.go::Store.LoadState, orchestrator/state.go::Store.SavePlan, orchestrator/state.go::Store.LoadPlan, orchestrator/state.go::Store.ArchiveRun, orchestrator/state.go::Store.WriteSummary, orchestrator/state.go::Store.WorkerLogPath, orchestrator/state.go::Store.WorktreeAbs, orchestrator/state.go::Store.WorktreeRel, orchestrator/state.go::LoadProjectPolicy, orchestrator/state.go::VMModePreamble
callers: MODULE-orchestrator-controller, MODULE-orchestrator-dashboard, MODULE-orchestrator-main, MODULE-orchestrator-mode, MODULE-orchestrator-review, MODULE-orchestrator-state-intervention, MODULE-orchestrator-worker, MODULE-orchestrator-worktree
callees: MODULE-orchestrator-state-io
contracts: なし
design: DSN-mod-01, DSN-arch-02
requirements: FR-orch-05
tests: orchestrator/state_test.go::TestStateRoundTrip, orchestrator/state_test.go::TestPlanRoundTrip, orchestrator/state_test.go::TestWorktreePaths, orchestrator/archive_test.go::TestArchiveRun_MovesNotDeletes, orchestrator/archive_test.go::TestArchiveRun_NoState, orchestrator/archive_test.go::TestCountUndone, orchestrator/policy_test.go::TestLoadProjectPolicy_Present, orchestrator/policy_test.go::TestVMModePreamble_VMMode
updated: 2026-08-02
summary: 実行状態・計画・作業ツリーの配置を .orchestrator/ に永続化する
---

# MODULE-orchestrator-state 状態ストア

## 目的

中断・端末破壊から復旧できるようにするため、run のすべての運用状態を
`/workspace/.orchestrator/` に置く(FR-orch-05)。tmux セッションやクライアントは使い捨ての
ビューであり、失われて困るものはここにしか無い。

## 処理の流れ

1. `NewStore(workspace)` が `<workspace>/.orchestrator/` を基準ディレクトリとする `Store` を作る。
2. `Store.path(...)` が基準ディレクトリからの相対パスを解決する(すべてのファイル位置の起点)。
3. `LoadState` / `SaveState` が `state.json`(`Phase` / `RunID` / `CurrentTask` / `StartedAt` /
   `UpdatedAt`)を読み書きする。
4. `LoadPlan` / `SavePlan` が `plan.json`(`Goal` / `Completion` / `Ready` / `Tasks[]`)を読み書きする。
   書き込みは `MODULE-orchestrator-state-io` の原子的置換を通す。
5. `WriteSummary` が run の要約を書き出す。
6. `WorkerLogPath(taskID)` が `workers/<taskID>.log` を、`WorktreeAbs` / `WorktreeRel` が
   `worktrees/<taskID>/` の絶対 / 相対パスを返す。
7. `ArchiveRun(runID)` が片付けを行う。**削除ではなく `os.Rename` で `history/<run_id>/` へ退避**し、
   `plan.json` / `state.json` / `control.json` / `intervention/open.json` と summary のスナップショットを
   移す。追記型ログ(`audit.jsonl` 等)はその場に残す。
8. `LoadProjectPolicy` が `ORCHESTRATOR.md`(あれば)を読み、各プロンプトの先頭に前置する内容を返す。
9. `VMModePreamble` が `CLAUDE_DEV_VM=1` のとき VM モードの短い前置文を返す。

## 呼び出され方

- 契機: `MODULE-orchestrator-main` の起動時、および controller / worker / review / mode / dashboard が
  状態を読み書きするたび。
- 前提条件: `<workspace>` が書き込み可能であること。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| workspace | パス | 必須 | 絶対パス。`.orchestrator/` をこの直下に作る |
| taskID | 文字列 | 一部の関数で必須 | worktree / ログのパス生成に使う |

- 認可: プロセス内呼び出し。

## 連携先と連携内容

### MODULE-orchestrator-state-io

- 何のために呼ぶか: JSON の読み書きを一時ファイル経由の原子的置換で行うため。
- 何を渡すか: パスと対象の構造体。
- 何を受け取るか: エラー(成功時は nil)。
- **失敗したときどうなるか**: 書き込みに失敗すると元のファイルは書き換わらない(原子的置換の性質)。
  呼び出し元にエラーが返り、controller はログに残して次の tick で再試行する。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 各関数の対象(`State` / `Plan` / パス文字列)とエラー |
| 永続化 | `/workspace/.orchestrator/` 配下: `state.json`、`plan.json`、`history/<run_id>/`、`workers/<taskID>.log`(パスのみ提供)、`worktrees/<taskID>/`(パスのみ提供)、summary。**書式はこの機能が決め、読む側(dashboard の tail、CLI の運用)がそれに依存する** |
| 発火するイベント | なし |
| ログ | なし |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| `state.json` / `plan.json` が存在しない | 空の構造体とエラーを返す | 呼び出し元は新規 run として扱う |
| JSON が壊れている | デコードエラーを返す | main は新規開始に倒れる |
| 書き込み権限が無い | 一時ファイルの作成に失敗し、元ファイルは無傷のまま | 状態が保存されず、次回の再開が古い地点からになる |
| `ArchiveRun` の退避先が既存 | `os.Rename` が失敗する | 退避されないまま新規 run が始まりうる |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | **起動時の自動処理で plan / 状態 / 履歴を `os.Remove` しない**(片付けは必ず `history/` への退避)。これは不変条件である | D0-orch-03 |
| 2 | `.orchestrator/` は機械の所有物とし、人間が手編集しない前提にする(修正は対話へ誘導する) | D0-orch-03 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| `Store.SaveControl` / `Store.RemoveSidecar` は製品コードから呼ばれない(テストと外部ツール向けの公開 API と明示されている) | 静的解析では未到達に見える | なし |

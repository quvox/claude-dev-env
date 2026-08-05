---
target: docs/03-impl/relations/MODULE-orchestrator-state.md
change: replace
sections:
  - "## 呼び出され方"
  - "## 異常系"
deletes: []
reason: ArchiveRun の退避先が既存でも失敗しない(docs/issues/032 #10)。NewStore が絶対パス制約を保証すると読めるが filepath.Join するだけである(同 #20)
reflected: 2026-08-05
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
tests: orchestrator/state_test.go::TestStateRoundTrip, orchestrator/state_test.go::TestPlanRoundTrip, orchestrator/state_test.go::TestWorktreePaths, orchestrator/archive_test.go::TestArchiveRun_MovesNotDeletes, orchestrator/archive_test.go::TestArchiveRun_NoState, orchestrator/archive_test.go::TestCountUndone, orchestrator/policy_test.go::TestLoadProjectPolicy_Present, orchestrator/policy_test.go::TestVMModePreamble_PrependedInVMMode
updated: 2026-08-05
summary: 実行状態・計画・作業ツリーの配置を .orchestrator/ に永続化する
---

<!-- 変更指示。反映後の最終形を書く。version / verified は持たない。frontmatter は `updated` の日付以外変更なし。 -->

## 呼び出され方

- 契機: `MODULE-orchestrator-main` の起動時、および controller / worker / review / mode / dashboard が
  状態を読み書きするたび。
- 前提条件: `<workspace>` が書き込み可能であること。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| workspace | パス | 必須 | `.orchestrator/` をこの直下に作る。**`NewStore` は `filepath.Join` するだけで、絶対化も相対パスの拒否も行わない**(`orchestrator/state.go:232`〜`:239`)。絶対パスであることは**呼び出し元**(`MODULE-orchestrator-main` が `filepath.Abs` を通す)が保証している。相対パスのまま渡すと git の作業ディレクトリ解決と食い違って worktree パスが二重ネストする(`docs/issues/011` と同種の入力検証の欠落) |
| taskID | 文字列 | 一部の関数で必須 | worktree / ログのパス生成に使う |

- 認可: プロセス内呼び出し。

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| `state.json` / `plan.json` が存在しない | **`(nil, nil)` を返す**(エラーにしない。`LoadState` は `orchestrator/state.go:323`、`LoadPlan` は `:443`) | 呼び出し元は nil を新規 run の合図として扱う |
| JSON が壊れている | デコードエラーを返す | main は新規開始に倒れる |
| 書き込み権限が無い | 一時ファイルの作成に失敗し、元ファイルは無傷のまま | 状態が保存されず、次回の再開が古い地点からになる |
| `ArchiveRun` の退避先が既存 | **失敗しない。** `os.MkdirAll(history/<run_id>)` を先に行い(既存ならそのまま使う)、`state.json` / `plan.json` / `control.json` / `summary.md` を1件ずつ `os.Rename` で移し、`intervention/open.json` があれば `history/<run_id>/intervention/open.json` へ移す(退避先の中間ディレクトリも `MkdirAll` で作る)。**移動先に同名ファイルがあれば上書きになる**(`os.Rename` の意味論)。元ファイルが無いものは `os.Stat` で判定して**黙ってスキップ**する | 同じ `run_id` で2度退避すると、後の内容が前の退避を上書きする。`run_id` が空のときは UTC 時刻から生成するので通常は衝突しない |

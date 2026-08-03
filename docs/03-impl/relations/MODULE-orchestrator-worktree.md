---
id: MODULE-orchestrator-worktree
module: MOD-orchestrator
kind: function-call
sync: sync
impl: orchestrator/worker.go::Worker.PrepareWorktree, orchestrator/worker.go::CleanOrchWorktrees, orchestrator/worker.go::ExecGit.run, orchestrator/worker.go::ExecGit.WorktreeAdd, orchestrator/worker.go::ExecGit.WorktreeAddExisting, orchestrator/worker.go::ExecGit.WorktreeRemove, orchestrator/worker.go::ExecGit.BranchExists, orchestrator/worker.go::ExecGit.CurrentBranch, orchestrator/worker.go::ExecGit.HasCommits, orchestrator/worker.go::ExecGit.Merge
callers: MODULE-orchestrator-controller, MODULE-orchestrator-main, MODULE-orchestrator-worker
callees: MODULE-orchestrator-state
contracts: なし
design: DSN-mod-01, DSN-orch-01
requirements: FR-orch-03
tests: orchestrator/accept_test.go::TestReconcileAndAccept_MarksDoneAndMerges, orchestrator/state_test.go::TestWorktreePaths
updated: 2026-08-02
summary: worker ごとの git worktree を作成・撤去し、統合の git 操作を実行する
---

# MODULE-orchestrator-worktree worktree と git 操作

## 目的

worker を並列に走らせても互いのファイル変更が混ざらないようにする(FR-orch-03)。
分離の実体が git worktree であり、レビュー合格後の統合もこの機能の git 操作で行う。

## 処理の流れ

1. `PrepareWorktree(taskID)` が
   `git worktree add .orchestrator/worktrees/<taskID> -b orch/<taskID>` を実行する。
2. ディレクトリが既にあれば再利用する。ブランチ `orch/<taskID>` だけが残っている場合は
   `BranchExists` で検出し、`-b` を付けない `WorktreeAddExisting` で再接続する
   (そのまま `-b` を付けると `git worktree add` が exit 128 で失敗する)。
3. `CurrentBranch` / `HasCommits` が統合前の状態確認に使われる。
4. `Merge(taskID, strategy)` が worker のコミットを作業ブランチへ取り込む
   (`merge_strategy` は `merge` または `rebase`。既定は `merge`)。
5. `WorktreeRemove(taskID)` が使い終わった worktree を外す。
6. `CleanOrchWorktrees()` が起動時に前回 run の残骸をまとめて掃除する。
7. すべての git 呼び出しは `ExecGit.run` に集約する(`Git` インターフェース経由で注入され、
   テストでは差し替えられる)。

## 呼び出され方

- 契機: `MODULE-orchestrator-worker` がタスク実行の直前に、`MODULE-orchestrator-controller` が
  統合時に、`MODULE-orchestrator-main` が起動時の掃除で呼ぶ。
- 前提条件: workspace が git リポジトリであること。`--workspace` が絶対パスであること
  (相対だと worktree パスが二重ネストして exit 128 になる)。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `taskID` | 文字列 | 必須 | worktree ディレクトリ名とブランチ名 `orch/<taskID>` になる |
| `strategy` | 文字列 | `Merge` で必須 | `merge` / `rebase` |

- 認可: プロセス内呼び出し。

## 連携先と連携内容

### MODULE-orchestrator-state

- 何のために呼ぶか: worktree の絶対 / 相対パス(`WorktreeAbs` / `WorktreeRel`)を得るため。
- 何を渡すか: タスク ID。 / 何を受け取るか: パス。
- **失敗したときどうなるか**: 想定されない(文字列連結のみ)。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | worktree のパス、真偽値(`BranchExists` / `HasCommits`)、エラー |
| 永続化 | `.orchestrator/worktrees/<taskID>/` のディレクトリ、git ブランチ `orch/<taskID>`、作業ブランチへのマージコミット |
| 発火するイベント | なし |
| ログ | なし(git の stderr はエラーに含めて返す) |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| ブランチ `orch/<taskID>` だけが残っている | `-b` なしで再接続する(exit 128 を回避) | なし |
| worktree ディレクトリが既に存在する | 再利用する | 前回の作業内容が引き継がれる |
| マージが競合する | `Merge` がエラーを返す | controller は `accept` 経路で done にせずタスクを `pending` へ戻す |
| workspace が git リポジトリでない | `git worktree add` が失敗する | タスクが実行できない |
| `CleanOrchWorktrees` が消せない | エラーを握りつぶして起動を続ける | 残骸が残り、次の `PrepareWorktree` が再利用する |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | git 操作を `Git` インターフェース経由の動的束縛にする(テストで差し替えるため)。この結果、静的解析では `ExecGit.*` への呼び出し辺が見えない | D0-orch-02 |
| 2 | 統合は controller が直列に行い、worker からは呼ばない(並列マージの競合を避ける) | D0-orch-04 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| `Git` インターフェース経由のためコールグラフに `ExecGit.*` への辺が出ない | 静的な影響範囲解析ではこの機能への依存が見えない。機能表で明示して補っている | なし |

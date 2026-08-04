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
updated: 2026-08-04
summary: worker ごとの git worktree を作成・撤去し、統合の git 操作を実行する
---

# MODULE-orchestrator-worktree worktree と git 操作

## 目的

worker を並列に走らせても互いのファイル変更が混ざらないようにする(FR-orch-03)。
分離の実体が git worktree であり、レビュー合格後の統合もこの機能の git 操作で行う。

## 処理の流れ

1. `PrepareWorktree(ctx, t *Task)` が `CurrentBranch` で基点ブランチを求める(失敗したら `HEAD`)。
2. worktree ディレクトリが**既に存在すれば再利用**し、パスをタスクに記録して戻る(git は呼ばない)。
3. ディレクトリが無く、ブランチ `orch/<taskID>` だけが残っている場合は `BranchExists` で検出し、
   `-b` を付けない `WorktreeAddExisting(ctx, repoDir, path, branch)` で再接続する
   (そのまま `-b` を付けると `git worktree add` が exit 128 で失敗し、タスクが再試行ループに落ちる)。
4. どちらでもなければ `WorktreeAdd(ctx, repoDir, path, branch, base)` =
   `git worktree add <abs> -b orch/<taskID> <base>` を実行する。
5. `CurrentBranch(ctx, repoDir)` / `HasCommits(ctx, repoDir, branch, base)` が統合前の状態確認に使われる
   (`HasCommits` は `git rev-list --count <base>..<branch>` の出力が `""` でも `0` でもないことで判定する)。
6. `Merge(ctx, repoDir, branch, strategy)` が worker のコミットを作業ブランチへ取り込む。
   **`strategy` が `rebase` のときだけ `git rebase <branch>`、それ以外はすべて
   `git merge --no-edit <branch>`**(未知の値は `merge` として実行される)。
7. `WorktreeRemove(ctx, repoDir, path)` = `git worktree remove --force <path>` が使い終わった
   worktree を外す。
8. `CleanOrchWorktrees(ctx, repoDir, worktreesDir)` が **`--fresh` 指定の起動時にだけ**前回 run の
   残骸をまとめて掃除する(`orchestrator/main.go:84`。通常の起動と再開では呼ばれない)
   (各 worktree の `remove --force` → `worktree prune` → `refs/heads/orch/` の全ブランチを
   `branch -D` → worktrees ディレクトリごと削除)。**すべて best-effort で、失敗を無視する。**
9. すべての git 呼び出しは `ExecGit.run(ctx, dir, args...)` に集約する(`Git` インターフェース経由で
   注入され、テストでは差し替えられる)。標準出力と標準エラーを合わせて返す。

## 呼び出され方

- 契機: `MODULE-orchestrator-worker` がタスク実行の直前に、`MODULE-orchestrator-controller` が
  統合時に、`MODULE-orchestrator-main` が起動時の掃除で呼ぶ。
- 前提条件: workspace が git リポジトリであること。`--workspace` が絶対パスであること
  (相対だと worktree パスが二重ネストして exit 128 になる)。
- 引数:

| 引数 | 型 | 必須 | 実装が行う検証 | 制約と結果 |
|---|---|---|---|---|
| `t *Task`(`taskID` を含む) | 構造体 | 必須 | **検証しない** | `taskID` は `.orchestrator/worktrees/<taskID>` と `workers/<taskID>.log` のパス、およびブランチ名 `orch/<taskID>` になる。**許容文字・長さの制限は無い** |
| `repoDir` | パス文字列 | 必須 | 検証しない | 呼び出し側が workspace の絶対パスを渡す |
| `branch` | 文字列 | 必須 | 検証しない | `orch/<taskID>` |
| `strategy` | 文字列 | `Merge` で必須 | **列挙を検証しない** | `rebase` のときだけ rebase。**それ以外(空文字・綴り間違いを含む)はすべて `merge`** |

**`taskID` の実際の扱い**(ブレインストーミングが `plan.json` に書いた値がそのまま使われる。
`lintPlan` は完了条件の非空だけを見るので、ID の形は検査されない):

| 入力 | 実際の結果 |
|---|---|
| `t1` のような短い英数(通常) | `.orchestrator/worktrees/t1` と `orch/t1` になる |
| `/` を含む | `filepath.Join` がそのままパス区切りとして解釈し、**worktrees 配下に入れ子のディレクトリ**ができる。ブランチ名も多階層になる |
| `..` を含む | `filepath.Join` が `..` を解決するため、**store の外のパスを指しうる**(パストラバーサル)。ログのパスも同様 |
| 空文字 | パスが `worktrees` ディレクトリ自身を指し、ブランチ名が `orch/` になって git が拒否する |
| git のブランチ名として不正な文字(空白・`~` `^` `:` `?` `*` `[` 等) | `git worktree add` が失敗し、タスクは実行できない |
| 極端に長い | パス長の上限に達すると `git worktree add` が失敗する。**事前チェックは無い** |

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
| worktree ディレクトリが既に存在する | **git を呼ばずに再利用する**(中身の妥当性は確認しない) | 前回の作業内容が引き継がれる。他 run の残骸でも同じ扱いになる |
| `CurrentBranch` が失敗した(detached HEAD 等) | エラーを返さず基点を `HEAD` にフォールバックする | worktree は作られる |
| `taskID` に `..` や `/` が含まれる | **検証せずパスへ結合する**。store の外にディレクトリやログが作られうる | 実行は続く(`docs/issues/011`) |
| マージが競合する | `Merge` が git の出力を含むエラーを返す | controller は `accept` 経路で done にせずタスクを `pending` へ戻す |
| `strategy` が未知の値 | **エラーにせず `merge` として実行する** | 利用者は rebase したつもりでマージされる |
| workspace が git リポジトリでない | `git worktree add` が失敗する | タスクが実行できない |
| `CleanOrchWorktrees` が消せない | **エラーを握りつぶして起動を続ける**(戻り値そのものが無い) | 残骸が残り、次の `PrepareWorktree` が再利用する |
| ctx がキャンセルされた | 実行中の git プロセスが終了させられ、エラーが返る | 呼び出し側の中断処理に従う |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | git 操作を `Git` インターフェース経由の動的束縛にする(テストで差し替えるため)。この結果、静的解析では `ExecGit.*` への呼び出し辺が見えない | D0-orch-02 |
| 2 | 統合は controller が直列に行い、worker からは呼ばない(並列マージの競合を避ける) | D0-orch-04 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| `Git` インターフェース経由のためコールグラフに `ExecGit.*` への辺が出ない | 静的な影響範囲解析ではこの機能への依存が見えない。機能表で明示して補っている | なし(閾値の外: 観測可能な被害が無い。機能表で補っている) |
| `taskID` を検証せずパスへ結合する | plan が汚染された場合に store の外へ書きうる(パストラバーサル) | `docs/issues/011-modify-taskid-is-not-validated-before-path-join.md` |
| `merge_strategy` の列挙を検証しない | 綴り間違いが黙って `merge` になる(**利用者が失敗に気づけない**) | `docs/issues/022-modify-merge-strategy-enum-is-not-validated.md` |
| worktree ディレクトリの再利用時に中身を確認しない | 別 run の残骸がそのまま作業ディレクトリになりうる(`CleanOrchWorktrees` は `--fresh` の経路でしか走らない) | なし(閾値の外: 再利用は `--fresh` を使わない選択の帰結で、成果は git のコミットとして**worktree 内で確認できる**) |

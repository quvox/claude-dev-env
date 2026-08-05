---
target: docs/03-impl/relations/MODULE-orchestrator-worktree.md
change: replace
sections:
  - "## 処理の流れ"
  - "## 異常系"
  - "## 既知の制限"
  - "## 戻り値・副作用"
deletes: []
reason: HasCommits を「統合前の状態確認に使う」と書くが製品コードに呼び出しが無い(docs/issues/038 #19)。「git の stderr はエラーに含めて返す」と書くが公開メソッドが結合出力を捨てている(同 #20)
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
updated: 2026-08-05
summary: worker ごとの git worktree を作成・撤去し、統合の git 操作を実行する
---

<!-- 変更指示。反映後の最終形を書く。version / verified は持たない。frontmatter は `updated` の日付以外変更なし
     (HasCommits は到達不能だが impl から外さない: 実在するシンボルであり、
     callgraph-check.py の CG4「仕様書に無い実装」を誘発しないため。既知の制限へ2行足して追跡する)。 -->

## 処理の流れ

1. `PrepareWorktree(ctx, t *Task)` が `CurrentBranch` で基点ブランチを求める(失敗したら `HEAD`)。
2. worktree ディレクトリが**既に存在すれば再利用**し、パスをタスクに記録して戻る(git は呼ばない)。
3. ディレクトリが無く、ブランチ `orch/<taskID>` だけが残っている場合は `BranchExists` で検出し、
   `-b` を付けない `WorktreeAddExisting(ctx, repoDir, path, branch)` で再接続する
   (そのまま `-b` を付けると `git worktree add` が exit 128 で失敗し、タスクが再試行ループに落ちる)。
4. どちらでもなければ `WorktreeAdd(ctx, repoDir, path, branch, base)` =
   `git worktree add <abs> -b orch/<taskID> <base>` を実行する。
5. `CurrentBranch(ctx, repoDir)` は手順1 の基点ブランチの決定に使う。
   **`HasCommits(ctx, repoDir, branch, base)` は製品コードから呼ばれていない**:
   `Git` インターフェースの宣言(`orchestrator/worker.go:69`〜`:70`)と実装
   (`:465`〜`:472`。`git rev-list --count <base>..<branch>` の出力が `""` でも `0` でもないことで
   判定する)があるだけで、**統合前の状態確認には使っていない**(統合の可否は
   `MODULE-orchestrator-review` のゲート結果で決まる)。到達不能シンボルとして
   `docs/issues/001` の対象と同じ性質である。
6. `Merge(ctx, repoDir, branch, strategy)` が worker のコミットを作業ブランチへ取り込む。
   **`strategy` が `rebase` のときだけ `git rebase <branch>`、それ以外はすべて
   `git merge --no-edit <branch>`**(未知の値は `merge` として実行される)。
7. `WorktreeRemove(ctx, repoDir, path)` = `git worktree remove --force <path>` が使い終わった
   worktree を外す。
8. `CleanOrchWorktrees(ctx, repoDir, worktreesDir)` が **`--fresh` 指定の起動時にだけ**前回 run の
   残骸をまとめて掃除する(`orchestrator/main.go:84`。通常の起動と再開では呼ばれない)
   (各 worktree の `remove --force` → `worktree prune` → `refs/heads/orch/` の全ブランチを
   `branch -D` → worktrees ディレクトリごと削除)。**すべて best-effort で、失敗を無視する。**
9. すべての git 呼び出しは `ExecGit.run(ctx, dir, args...)`(`orchestrator/worker.go:423`〜`:427`)に
   集約する(`Git` インターフェース経由で注入され、テストでは差し替えられる)。`run` 自身は
   `CombinedOutput()` で標準出力と標準エラーを合わせて返すが、**公開メソッドの側でその出力を
   捨てているものがある**: `WorktreeAdd`(`:429`)/ `WorktreeAddExisting`(`:434`)/
   `WorktreeRemove`(`:449`)/ `Merge`(`:454`)は `_, err := g.run(...)` と書いており、
   **git のメッセージは呼び出し元へ渡らない**(`error` は `*exec.ExitError` = 終了コードだけである)。
   出力を使うのは `BranchExists`(`:439`)/ `HasCommits`(`:465`)/ `CurrentBranch`(`:474`)の3つで、
   いずれも**値の取り出しにだけ使い、失敗時のメッセージには使わない**。

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| ブランチ `orch/<taskID>` だけが残っている | `-b` なしで再接続する(exit 128 を回避) | なし |
| worktree ディレクトリが既に存在する | **git を呼ばずに再利用する**(中身の妥当性は確認しない) | 前回の作業内容が引き継がれる。他 run の残骸でも同じ扱いになる |
| `CurrentBranch` が失敗した(detached HEAD 等) | エラーを返さず基点を `HEAD` にフォールバックする | worktree は作られる |
| `taskID` に `..` や `/` が含まれる | **検証せずパスへ結合する**。store の外にディレクトリやログが作られうる | 実行は続く(`docs/issues/011`) |
| マージが競合する | `Merge` が**終了コードだけのエラー**を返す(`_, err := g.run(...)` で `CombinedOutput` を捨てるため、**どのファイルが競合したかは呼び出し元に伝わらない**)。監査ログの `merge_error` に載る `err` も同じ内容である | controller は `accept` 経路で done にせずタスクを `pending` へ戻す。**競合の中身は worktree を直接見ないと分からない** |
| `strategy` が未知の値 | **エラーにせず `merge` として実行する** | 利用者は rebase したつもりでマージされる |
| workspace が git リポジトリでない | `git worktree add` が失敗する。**git の出力(`not a git repository`)は捨てられる**ので、表示されるのは終了コード由来のエラーだけである | タスクが実行できない |
| `CleanOrchWorktrees` が消せない | **エラーを握りつぶして起動を続ける**(戻り値そのものが無い) | 残骸が残り、次の `PrepareWorktree` が再利用する |
| ctx がキャンセルされた | 実行中の git プロセスが終了させられ、エラーが返る | 呼び出し側の中断処理に従う |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| `Git` インターフェース経由のためコールグラフに `ExecGit.*` への辺が出ない | 静的な影響範囲解析ではこの機能への依存が見えない。機能表で明示して補っている | なし(閾値の外: 観測可能な被害が無い。機能表で補っている) |
| `taskID` を検証せずパスへ結合する | plan が汚染された場合に store の外へ書きうる(パストラバーサル) | `docs/issues/011-modify-taskid-is-not-validated-before-path-join.md` |
| `merge_strategy` の列挙を検証しない | 綴り間違いが黙って `merge` になる(**利用者が失敗に気づけない**) | `docs/issues/022-modify-merge-strategy-enum-is-not-validated.md` |
| worktree ディレクトリの再利用時に中身を確認しない | 別 run の残骸がそのまま作業ディレクトリになりうる(`CleanOrchWorktrees` は `--fresh` の経路でしか走らない) | なし(閾値の外: 再利用は `--fresh` を使わない選択の帰結で、成果は git のコミットとして**worktree 内で確認できる**) |
| **`HasCommits` が製品コードから呼ばれていない** | 「worker が1つもコミットしていないのに統合へ進む」ことを検出する手段が実装に無い(統合の可否はレビューゲートの結果だけで決まる)。静的解析では到達不能に見える | `docs/issues/001-modify-orchestrator-test-only-symbols.md`(同種の到達不能シンボル) |
| **git の出力を捨てる公開メソッドがある**(`WorktreeAdd` / `WorktreeAddExisting` / `WorktreeRemove` / `Merge`) | 失敗の理由(競合ファイル・`not a git repository` など)が呼び出し元にも監査ログにも残らない。原因の切り分けには worktree を直接見る必要がある | なし(閾値の外: **失敗そのものは終了コードで必ず気づける**。出力を通す改修は `Git` インターフェースの戻り値を変えるため 02 の契約に触る) |

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | `PrepareWorktree` は worktree の絶対パスとエラー。`BranchExists` / `HasCommits` は `(bool, error)`。`CurrentBranch` は `(string, error)`。`WorktreeAdd` / `WorktreeAddExisting` / `WorktreeRemove` / `Merge` は `error` だけ。`CleanOrchWorktrees` は**戻り値を持たない** |
| 永続化 | `.orchestrator/worktrees/<taskID>/` のディレクトリ、git ブランチ `orch/<taskID>`、作業ブランチへのマージコミット |
| 発火するイベント | なし |
| ログ | なし。**git の標準出力・標準エラーは呼び出し元へ渡らない**: `ExecGit.run` は結合出力を返すが、`WorktreeAdd` / `WorktreeAddExisting` / `WorktreeRemove` / `Merge` がそれを `_` に捨てるため、`error` は終了コード由来の `*exec.ExitError` だけになる |

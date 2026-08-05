---
target: docs/03-impl/relations/MODULE-orchestrator-session.md
change: replace
sections:
  - "## 処理の流れ"
  - "## 呼び出され方"
deletes: []
reason: 処理の流れの3点(dashboard の remain-on-exit・tmux 呼び出しの集約・Run のクォート)がコードと食い違う(docs/issues/038 #18)
id: MODULE-orchestrator-session
module: MOD-orchestrator
kind: function-call
sync: sync
impl: orchestrator/session.go::NewSessionManager, orchestrator/session.go::SessionManager.Ensure, orchestrator/session.go::SessionManager.EnsureAll, orchestrator/session.go::SessionManager.SetupMainSession, orchestrator/session.go::SessionManager.LaunchInteractive, orchestrator/session.go::SessionManager.SwitchTo, orchestrator/session.go::SessionManager.Kill, orchestrator/session.go::SessionManager.Run, orchestrator/session.go::SessionManager.MainSession, orchestrator/session.go::SessionManager.Has, orchestrator/session.go::SessionManager.BrainstormingWindow, orchestrator/session.go::SessionManager.WorkerWindow, orchestrator/session.go::SessionManager.DashboardWindow, orchestrator/session.go::SessionManager.DetectSession, orchestrator/session.go::SessionManager.ExpectedWindows, orchestrator/session.go::SessionManager.PaneDead, orchestrator/session.go::splitTarget, orchestrator/session.go::tmuxRun
callers: MODULE-orchestrator-controller, MODULE-orchestrator-dashboard, MODULE-orchestrator-main
callees: MODULE-orchestrator-mode
contracts: なし
design: DSN-mod-01, DSN-orch-02, DSN-ui-02
requirements: FR-orch-02, FR-orch-08
tests: orchestrator/session_test.go::TestNormalizeCName, orchestrator/session_test.go::TestSessionNames, orchestrator/session_test.go::TestSplitTarget, orchestrator/session_test.go::TestExpectedWindows, orchestrator/session_test.go::TestNewSessionManager_UsesComposeProjectName
updated: 2026-08-05
summary: tmux セッションとウィンドウを作成・切替・破棄する
---

<!-- 変更指示。反映後の最終形を書く。version / verified は持たない。frontmatter は `updated` の日付以外変更なし。

     docs/issues/017 が挙げていた本ファイルの「shellSingleQuote で引数を安全にクォートする」は
     現行 SSOT に存在せず(該当文は「## 連携先と連携内容」ではなく処理の流れ9 にある形へ既に
     書き替わっている)、本変更では手順9 を「シェルの語分割・展開が起きない形にする」と
     具体化した。 -->

## 処理の流れ

1. `NewSessionManager()` が**引数なし**でセッション名を決める。**環境変数 `COMPOSE_PROJECT_NAME`
   (無ければホスト名)を読み**、`normalizeCName` で tmux で使える形へ正規化する。
2. `MainSession()` が `orch-<CNAME>-main` を、`DashboardWindow()` / `BrainstormingWindow()` /
   `WorkerWindow(taskID)`(= `w-<taskID>`)が各ウィンドウ名を返す。
3. `DetectSession(ctx)` は `$TMUX` があるとき `tmux display-message -p '#{session_name}'` で
   実測のセッション名に束縛する(CLI 側が別名で作っていても追従する)。
4. `SetupMainSession(ctx)` が自分のウィンドウを `dashboard` へ改名し、`mouse on` を設定する。
5. `Ensure(ctx, target)` が `new-window -d` でウィンドウを作る(冪等)。**対象を問わず
   `remain-on-exit on` を設定する**(既存のときも設定し直す。`session.go:167`〜`:178`)。
   `/exit` 後もウィンドウを残して次のコマンドを流し込めるようにするためである。
   **`dashboard` ウィンドウをこの関数が作ることはない**(コントローラ自身のウィンドウであり、
   `claude-dev orchestrate` が作る)。**「`dashboard` だけ `remain-on-exit off`」という分岐は無い。**
6. `Run(ctx, target, cmd)` は `Ensure` を通したうえで `respawn-pane -k` で既存ウィンドウの中身を
   差し替える。**`cmd` はクォートせずそのまま tmux へ渡す**(`session.go:215`)。
   したがって**空白やメタ文字を含むコマンドの引用は呼び出し元の責任**である。
7. `Has(ctx, target)` は `list-windows -F '#{window_name}'` で厳密に照合する
   (`display-message -t session:window` は窓が無くても現在の窓へフォールバックして誤って成功を返す)。
8. `SwitchTo(ctx, target)` が `select-window`、`Kill(ctx, target)` が `kill-window`、
   `PaneDead(ctx, target)` が `list-panes -F '#{pane_dead}'` の出力に `1` を含むかで
   ペインの死活を返す(**問い合わせが失敗したら「死んでいない」と読む**。`session.go:186`〜`:190`)。
9. `LaunchInteractive(ctx, target, scriptPath)` が対話 claude を指定ウィンドウで起動する。
   渡すコマンドは `sh <スクリプトパス>` の形で、**パスだけを `MODULE-orchestrator-mode` の
   `shellSingleQuote` で単引用符で囲む**(`session.go:201`。シェルの語分割・展開が起きない形にする)。
   起動後に `SwitchTo` でそのウィンドウを選択する。
10. `EnsureAll(ctx, phase string, plan *Plan)` が **`ExpectedWindows(phase, plan)` が返す並び**
    (フェーズと plan のタスク状態から決まる期待ウィンドウ)と突き合わせ、消えたウィンドウを
    `Ensure` で作り直す。
11. **tmux 呼び出しは `tmuxRun` に集約していない。** 終了ステータスだけを見る操作
    (`new-window` / `set-option` / `respawn-pane` / `select-window` / `kill-window`)は
    `tmuxRun`(`session.go:118`〜`:120`)を通すが、**出力を読む必要がある3つは
    `exec.CommandContext` を直接呼ぶ**: `DetectSession`(`:89`)/ `Has`(`:150`)/
    `PaneDead`(`:186`)である。`splitTarget` が `session:window` を分解する。

## 呼び出され方

- 契機: `MODULE-orchestrator-main` の初期化時、および controller / dashboard が画面を作る・切り替える
  たび。
- 前提条件: コンテナ内で `tmux` が使えること(使えない場合は前景フォールバックへ倒れる)。
- 引数:

| 引数 | 型 | 必須 | 制約 | 実装が行う検証 |
|---|---|---|---|---|
| (`NewSessionManager` は引数を取らない) | — | — | セッション名の元は**引数ではなく環境変数**。`COMPOSE_PROJECT_NAME` を読み、空白のみ/未設定なら `os.Hostname()`、それも取れなければ空文字。`normalizeCName` で正規化して `Prefix = "orch-" + <正規化名>` にする(`orchestrator/session.go:50`〜`:58`) | **検証しない**。セッション名は `normalizeCName` で tmux が受ける形へ正規化する(小文字化し `[a-z0-9_-]` 以外を `-` に置換、前後の `-` を落とし、空なら既定名) |
| `ctx` | `context.Context` | `DetectSession` / `Has` / `SwitchTo` / `Ensure` / `Run` / `SetupMainSession` で必須 | `tmux` 子プロセスの中断に使う | 同上 |
| `target` | 文字列 | `Ensure` / `Run` で必須 | `<セッション名>:<ウィンドウ名>`。ウィンドウ名は `dashboard` / `brainstorming` / `w-<taskID>` | 同上 |
| `taskID` | 文字列 | `WorkerWindow` で必須 | ウィンドウ名 `w-<taskID>` の元。**検証は無い**(`MODULE-orchestrator-worktree` の `taskID` と同じ値) | 同上 |
| `cmd` | 文字列 | `Run` で必須 | ウィンドウで実行するコマンド。**`Run` はこれをクォートせず `respawn-pane -k` の引数へそのまま渡す**(`session.go:215`)ので、**引用は呼び出し元の責任**である。実際の呼び出し元は2つで、`controller.go:224` は `sh ` + `shellSingleQuote(script)` と囲み、`controller.go:280` は `tail -n +1 -F ` + ログパスを**囲まずに**渡す(ログパスは `.orchestrator/workers/<taskID>.log` 形式) | 同上 |

- 認可: プロセス内呼び出し。

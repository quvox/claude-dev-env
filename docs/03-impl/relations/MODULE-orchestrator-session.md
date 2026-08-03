---
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
updated: 2026-08-02
summary: tmux セッションとウィンドウを作成・切替・破棄する
---

# MODULE-orchestrator-session tmux ウィンドウ管理

## 目的

コントローラを tmux に常駐させる方式(DSN-orch-02・FR-orch-02)の実体。唯一のセッション
`orch-<CNAME>-main` の配下に dashboard / brainstorming / worker のウィンドウを作り、
端末が壊れてもセッションが残るようにする。画面遷移(FR-orch-08)もここが実行する。

## 処理の流れ

1. `NewSessionManager(cname)` がセッション名を決める。`normalizeCName` で
   `COMPOSE_PROJECT_NAME` 由来の名前を tmux で使える形へ正規化する。
2. `MainSession()` が `orch-<CNAME>-main` を、`DashboardWindow()` / `BrainstormingWindow()` /
   `WorkerWindow(taskID)`(= `w-<taskID>`)が各ウィンドウ名を返す。
3. `DetectSession()` は `$TMUX` があるとき `tmux display-message -p '#{session_name}'` で
   実測のセッション名に束縛する(CLI 側が別名で作っていても追従する)。
4. `SetupMainSession()` が自分のウィンドウを `dashboard` へ改名し、`mouse on` を設定する。
5. `Ensure(window, cmd)` が `new-window -d` でウィンドウを作る(冪等)。worker と brainstorming の
   ウィンドウは `remain-on-exit on` にして `/exit` 後も残す。`dashboard` は `remain-on-exit off`。
6. `Run(window, cmd)` は `respawn-pane -k` で既存ウィンドウの中身を差し替える。
7. `Has(window)` は `list-windows -F '#{window_name}'` で厳密に照合する
   (`display-message -t session:window` は窓が無くても現在の窓へフォールバックして誤って成功を返す)。
8. `SwitchTo(window)` が `select-window`、`Kill(window)` が `kill-window`、
   `PaneDead(window)` がペインの死活を返す。
9. `LaunchInteractive(window, script)` が対話 claude を指定ウィンドウで起動する
   (`MODULE-orchestrator-mode` の `shellSingleQuote` で引数をクォートする)。
10. `EnsureAll()` が `ExpectedWindows()` の並びと突き合わせ、消えたウィンドウを作り直す。
11. すべての tmux 呼び出しは `tmuxRun` に集約し、`splitTarget` が `session:window` を分解する。

## 呼び出され方

- 契機: `MODULE-orchestrator-main` の初期化時、および controller / dashboard が画面を作る・切り替える
  たび。
- 前提条件: コンテナ内で `tmux` が使えること(使えない場合は前景フォールバックへ倒れる)。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `cname` | 文字列 | 必須 | セッション名の元。`normalizeCName` で正規化する |
| `window` | 文字列 | 必須 | ウィンドウ名。`dashboard` / `brainstorming` / `w-<taskID>` |
| `cmd` | 文字列 | 一部で必須 | ウィンドウで実行するコマンド |

- 認可: プロセス内呼び出し。

## 連携先と連携内容

### MODULE-orchestrator-mode

- 何のために呼ぶか: `LaunchInteractive` が起動コマンドを組み立てる際に、`shellSingleQuote` で
  引数を安全にクォートするため。
- 何を渡すか: クォート対象の文字列。 / 何を受け取るか: クォート済み文字列。
- **失敗したときどうなるか**: 想定されない(純粋な文字列変換)。クォートを誤ると tmux へ渡す
  コマンドが壊れ、ウィンドウが即座に終了する。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | セッション名・ウィンドウ名の文字列、`Has` / `PaneDead` の真偽値、エラー |
| 永続化 | tmux サーバ上のセッション `orch-<CNAME>-main` とその配下のウィンドウ(プロセス外の状態) |
| 発火するイベント | なし |
| ログ | なし(tmux の stderr は呼び出し元が扱う) |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| `tmux` が無い / サーバに接続できない | `tmuxRun` がエラーを返す | controller は前景フォールバック(`RunInteractive`)へ倒れる |
| 対象ウィンドウが存在しない | `Has` が偽を返す。`SwitchTo` はエラーになる | `EnsureAll` が作り直す |
| ウィンドウが `remain-on-exit on` で空き殻になっている | `PaneDead` が真を返す | controller は `WaitConsume` の停止条件として使い、再ディスパッチできる |
| セッション名が tmux で使えない文字を含む | `normalizeCName` が置換する | なし |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 存在確認に `list-windows` を使う(`display-message -t session:window` は窓が無くても現在の窓へフォールバックして誤って成功を返すことが実機で判明したため) | D0-orch-02 |
| 2 | worker / brainstorming のウィンドウを `remain-on-exit on` にする(`/exit` 後もログを残し、tail → 介入 → 再ディスパッチを同じウィンドウで駆動するため) | D0-orch-02 |
| 3 | セッションは1つだけにし、役割はウィンドウで分ける(複数セッションにすると attach 先が曖昧になる) | D0-orch-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| `tmuxRun` の `exec.Cmd.Run()` が、静的解析では `Controller.Run` / `SessionManager.Run` への呼び出し候補として現れる | コールグラフに実在しない候補辺が立つ(棄却済み。下記参照) | なし |

<!-- 棄却した候補辺: `orchestrator/session.go::tmuxRun` → `Controller.Run` は、
     `exec.CommandContext(...).Run()`(session.go:119)の `Run` を同名衝突で誤解決したもの。
     `cluster-features.py` は確度「候補」として出すが、コードを読むと標準ライブラリの
     `*exec.Cmd.Run` であり、機能間の連携ではない。 -->

---
id: MODULE-orchestrator-dashboard
module: MOD-orchestrator
kind: function-call
sync: sync
impl: orchestrator/dashtui.go::newDashProgram, orchestrator/dashtui.go::dashModel.Init, orchestrator/dashtui.go::dashModel.Update, orchestrator/dashtui.go::dashModel.View, orchestrator/dashboard.go::DashboardState.Set
callers: MODULE-orchestrator-controller
callees: MODULE-orchestrator-session, MODULE-orchestrator-state
contracts: なし
design: DSN-mod-01, DSN-ui-01, DSN-ui-02
requirements: FR-orch-08
tests: orchestrator/dashtui_test.go::TestDashView_RendersTasksAndCursor, orchestrator/dashtui_test.go::TestDashCursor_MovesAndClamps, orchestrator/dashtui_test.go::TestDashEnter_OnWaitingHumanSendsResolve, orchestrator/dashtui_test.go::TestDashQuit_SendsQuit, orchestrator/dashtui_test.go::TestDashView_BrainstormingIsCursorSelect, orchestrator/dashboard_test.go::TestReadVMHealthBanner_WarnFresh, orchestrator/dashboard_test.go::TestReadVMHealthBanner_OKIsSilent, orchestrator/dashboard_test.go::TestReadVMHealthBanner_StaleIgnored, orchestrator/dashboard_test.go::TestReadVMHealthBanner_NonVMMode
updated: 2026-08-02
summary: 進捗ダッシュボード(bubbletea TUI)を表示し操作を受ける
---

# MODULE-orchestrator-dashboard 進捗ダッシュボード

## 目的

実行中に何が起きているかを一望でき、判断待ちへ最短で入れるようにする(FR-orch-08)。
UI 設計の `orch-dashboard` 画面の実体である。

## 処理の流れ

1. `DashboardState.Set(...)`(dashboard.go)が共有状態を更新する。controller が最新のタスク状態・
   サマリ・仮定件数・判断待ち一覧を書き込む。
2. `newDashProgram(...)`(dashtui.go)が bubbletea のプログラムを作る
   (`WithAltScreen` と `WithContext`)。controller は `isTTY()` が真のときだけ起動する。
3. `dashModel.Init` / `Update` / `View` が TUI を回す。
4. `View()` はヘッダ(`● 実行中` / `⏸ 一時停止`)、goal、各タスク行(状態ラベル・経過時間・
   試行回数)、直近サマリ、仮定カウント、**判断待ちの一覧(`open.json` の TaskID → タスク名)**、
   実行中数、キーヒントを描画する。
5. **カーソル(↑↓ / jk)で選び Enter で確定したときだけ移動する**。実行中タスクなら
   `MODULE-orchestrator-session` の `SwitchTo` で直接 `select-window`、判断待ちなら
   `actions` チャネルへ `{resolve, taskID}` を送る。
6. キー操作: `p` で一時停止のトグル、`d` で出力 tail のトグル(`detailTails` / `tailFile` が
   `MODULE-orchestrator-state` の `WorkerLogPath` を読む)、`i` で先頭の判断待ちへ、`q` で中断。
7. `View()` は毎描画で `readVMHealthBanner` を best-effort に呼ぶ(VM モードのとき
   `$HOME/.claude-dev-vm/health` が `STATE=WARN` かつ鮮度内なら赤いバナーを出す)。

## 呼び出され方

- 契機: `MODULE-orchestrator-controller` が実行モードに入ったとき(TTY のときのみ)。
- 前提条件: 標準出力が TTY であること。tmux の `dashboard` ウィンドウで動くこと。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `state` | `*DashboardState` | 必須 | controller と共有する。描画のたびに読む |
| `actions` | チャネル | 必須 | `{resolve, taskID}` などの操作を controller へ返す |

- 認可: 端末を見ている人間。

## 連携先と連携内容

### MODULE-orchestrator-session

- 何のために呼ぶか: 実行中タスクを選んで Enter したときに、その worker ウィンドウへ移動するため
  (`BrainstormingWindow` / `WorkerWindow` / `SwitchTo`)。
- 何を渡すか: タスク ID。 / 何を受け取るか: 成否。
- **失敗したときどうなるか**: ウィンドウが無ければ移動できず、TUI に留まる。controller 側の
  ウィンドウ再構築で次の tick に復旧する。

### MODULE-orchestrator-state

- 何のために呼ぶか: `detailTails` が worker のログ(`WorkerLogPath`)を tail するため。
- 何を渡すか: タスク ID。 / 何を受け取るか: ログのパス。
- **失敗したときどうなるか**: ログが無ければ tail の表示が空になるだけ。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | なし(bubbletea のイベントループ)。操作は `actions` チャネルで返す |
| 永続化 | なし。読む資源は `workers/<taskID>.log`、`intervention/open.json`(controller 経由)、`$HOME/.claude-dev-vm/health` |
| 発火するイベント | `actions` チャネルへの `{resolve, taskID}` / `{quit}` |
| ログ | なし(画面描画のみ) |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 非 TTY | controller が `isTTY()` で判定し TUI を起動しない | 実行は続く(表示が無いだけ) |
| worker ログが存在しない | `d` の tail 表示が空になる | なし |
| VM health ファイルが古い / 存在しない | バナーを出さない(`StaleIgnored` / `NonVMMode`) | なし |
| カーソルが範囲外へ動く | 端でクランプする | なし |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | Enter で確定したときだけウィンドウを移動する(カーソル移動だけで画面が飛ぶと操作を見失うため) | D0-orch-06 |
| 2 | VM health の読み取りは best-effort とし、失敗しても描画を止めない | D0-orch-06 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| `DashboardState.SelectableWorker` / `SelectableWorkerStatus`(と私有ヘルパ2件)は製品コードから呼ばれず、テストからのみ参照される | 到達不能コードの疑い | `docs/issues/001-modify-orchestrator-test-only-symbols.md` |
| `dashboard.go::oneline` は整形ユーティリティとして畳み込んでいる(独立した機能にしていない) | 機能表の粒度の判断 | なし |

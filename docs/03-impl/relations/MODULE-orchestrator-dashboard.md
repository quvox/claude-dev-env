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
updated: 2026-08-05
summary: 進捗ダッシュボード(bubbletea TUI)を表示し操作を受ける
---

# MODULE-orchestrator-dashboard 進捗ダッシュボード

## 目的

実行中に何が起きているかを一望でき、判断待ちへ最短で入れるようにする(FR-orch-08)。
UI 設計の `orch-dashboard` 画面の実体である。

## 処理の流れ

1. `DashboardState.Set(...)`(dashboard.go)が共有状態を更新する。controller が書き込むのは
   **`Phase` / `Goal` / `Tasks` / `Paused` / `InterventionsOpen`** である。
   **`LastSummary` / `LastSummaryTS` / `AssumptionsN` / `InterventionsN` は構造体に定義があるだけで、
   製品コードから代入している箇所が1件も無い**(`dashboard.go:66`〜`:69` に定義、
   `dashtui.go:233`・`:239` が表示に使う)。したがって**直近サマリ欄は常に空**、
   **仮定件数は常に 0** で描画される(`docs/issues/032` #6 で人間が「記述を直すだけ」と裁定済み)。
2. `newDashProgram(ctx, st, store, sessions, actions)`(`dashtui.go:55`)が bubbletea の
   プログラム(`*tea.Program`)を作る(`WithAltScreen` と `WithContext`)。
   controller は `isTTY()` が真のときだけ起動する。
3. `dashModel.Init() tea.Cmd` / `Update(msg tea.Msg) (tea.Model, tea.Cmd)` /
   `View() string` が TUI を回す(bubbletea の `tea.Model` 実装)。
4. `View()` はヘッダ(`● 実行中` / `⏸ 一時停止`)、goal、各タスク行(状態ラベル・経過時間・
   試行回数)、直近サマリ、仮定カウント、**判断待ちの一覧(`open.json` の TaskID → タスク名)**、
   実行中数、キーヒントを描画する。
5. **カーソル(↑↓ / jk)で選び Enter で確定したときだけ移動する**。実行中タスクなら
   `MODULE-orchestrator-session` の `SwitchTo` で直接 `select-window`、判断待ちなら
   `actions` チャネルへ `{resolve, taskID}` を送る。
6. キー操作: `p` で一時停止のトグル、`d` で出力 tail のトグル(`detailTails` / `tailFile` が
   `MODULE-orchestrator-state` の `WorkerLogPath` を読む)、`i` で `{intervene}` を送る、
   **`q` と `ctrl+c` の両方**で `{quit}` を送って `tea.Quit` する(`dashtui.go:123`〜`:125`)。
   `actions` へ流す操作の種別は **`resolve` / `intervene` / `quit` の3つ**である
   (`dashAction.kind`。`dashtui.go:27`〜`:30`)。**送信は取りこぼしを捨てる**:
   `dashModel.send` はチャネルが満杯なら `select` の `default` 節で黙って破棄する
   (`dashtui.go:82`〜`:87`。バッファは 8 件)。
7. **ブレインストーミング中も同じ TUI が動く**(`dashtui.go:69`〜`:71` の `selectable` と
   `:150`〜`:176` の `View`)。この分岐は「brainstorming ウィンドウで AI と対話する」の1行だけを
   選択対象にして**画面を返してしまう**ため、**`readVMHealthBanner` を呼ぶ前に return する**。
8. 実行フェーズの `View()` は毎描画で `readVMHealthBanner` を best-effort に呼ぶ(`dashtui.go:180`。
   VM モードのとき `$HOME/.claude-dev-vm/health` が `STATE=WARN` かつ鮮度内なら赤いバナーを出す)。
   **ブレインストーミング中はバナーが出ない。**

## 呼び出され方

- 契機: `MODULE-orchestrator-controller` が実行モードに入ったとき、および
  **ブレインストーミングに入ったとき**(いずれも TTY のときのみ。`controller.go:243` / `:383`)。
- 前提条件: 標準出力が TTY であること。tmux の `dashboard` ウィンドウで動くこと。
- 引数(実シグネチャは `newDashProgram(ctx context.Context, st *DashboardState, store *Store, sessions *SessionManager, actions chan dashAction) *tea.Program`。`dashtui.go:55`):

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `ctx` | `context.Context` | 必須 | `tea.WithContext` へ渡す。キャンセルで TUI が終わる |
| `st` | `*DashboardState` | 必須 | controller と共有する。描画のたびに `mu` を取って読む |
| `store` | `*Store` | 必須 | `d` の tail 表示が `WorkerLogPath` を引くために使う |
| `sessions` | `*SessionManager` | 任意(`nil` 可) | ウィンドウ移動に使う。**`nil` のときは移動しない**(tmux が無い環境。`dashtui.go:110`〜`:111`) |
| `actions` | `chan dashAction` | 必須 | `{resolve, taskID}` / `{intervene}` / `{quit}` を controller へ返す。**バッファは呼び出し元が 8 件で作る** |

- 戻り値: `*tea.Program`(呼び出し元が `Run` する)。
- 認可: 端末を見ている人間。

### MODULE-orchestrator-session

- 何のために呼ぶか: 選択行で Enter を押したときに、そのウィンドウへ移動するため。
- 何を渡すか: **`SwitchTo` には組み立て済みの tmux ターゲット文字列**を渡す
  (`BrainstormingWindow()` の戻り値、または `WorkerWindow(r.id)` の戻り値。
  `dashtui.go:113` / `:115`)。**タスク ID をそのまま渡すのではない。**
- 何を受け取るか: `error`。**ただし `_ =` で捨てている**(`dashtui.go:113` / `:115`)。
- **失敗したときどうなるか**: **移動できなかったことは画面にも表示されない**(TUI に留まる)。
  controller 側の 5 秒ごとのウィンドウ再構築で次の tick に復旧しうる。
  `sessions` が `nil`(tmux 無し)のときは呼び出し自体を行わない。

## 連携先と連携内容

### MODULE-orchestrator-session

- 何のために呼ぶか: 選択行で Enter を押したときに、そのウィンドウへ移動するため。
- 何を渡すか: **`SwitchTo` には組み立て済みの tmux ターゲット文字列**を渡す
  (`BrainstormingWindow()` の戻り値、または `WorkerWindow(r.id)` の戻り値。
  `dashtui.go:113` / `:115`)。**タスク ID をそのまま渡すのではない。**
- 何を受け取るか: `error`。**ただし `_ =` で捨てている**(`dashtui.go:113` / `:115`)。
- **失敗したときどうなるか**: **移動できなかったことは画面にも表示されない**(TUI に留まる)。
  controller 側の 5 秒ごとのウィンドウ再構築で次の tick に復旧しうる。
  `sessions` が `nil`(tmux 無し)のときは呼び出し自体を行わない。

### MODULE-orchestrator-state

- 何のために呼ぶか: `detailTails` が worker のログ(`WorkerLogPath`)を tail するため。
- 何を渡すか: タスク ID。 / 何を受け取るか: ログのパス。
- **失敗したときどうなるか**: ログが無ければ tail の表示が空になるだけ。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | `newDashProgram` が `*tea.Program` を返す。`Init` は `tea.Cmd`、`Update` は `(tea.Model, tea.Cmd)`、`View` は `string`。操作は `actions` チャネルで返す |
| 永続化 | なし。読む資源は `workers/<taskID>.log`、`intervention/open.json`(controller 経由)、`$HOME/.claude-dev-vm/health` |
| 発火するイベント | `actions` チャネルへの `{resolve, taskID}` / `{intervene}` / `{quit}`。**チャネルが満杯のときは送らずに捨てる** |
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

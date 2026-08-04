---
id: MODULE-orchestrator-controller
module: MOD-orchestrator
kind: function-call
sync: sync
impl: orchestrator/controller.go::Controller.Run, orchestrator/controller.go::newRunID
callers: MODULE-orchestrator-main
callees: MODULE-orchestrator-claude-exec, MODULE-orchestrator-dashboard, MODULE-orchestrator-handoff, MODULE-orchestrator-mode, MODULE-orchestrator-plan, MODULE-orchestrator-review, MODULE-orchestrator-session, MODULE-orchestrator-state, MODULE-orchestrator-state-intervention, MODULE-orchestrator-term, MODULE-orchestrator-trigger, MODULE-orchestrator-worker, MODULE-orchestrator-worktree
contracts: CTR-orchestrator-prompt
design: DSN-mod-01, DSN-orch-01, DSN-orch-02, DSN-ui-02
requirements: FR-orch-01, FR-orch-02, FR-orch-03, FR-orch-04, FR-orch-05, FR-orch-06, FR-orch-07
tests: orchestrator/controller_test.go::TestExecuting_RespectsMaxWorkers, orchestrator/controller_test.go::TestExecuting_DependencyOrder, orchestrator/controller_test.go::TestExecuting_TriggerParksTaskPeersContinue, orchestrator/controller_test.go::TestExecuting_Trigger1Irreversible, orchestrator/controller_test.go::TestIntervene_ResolveApprovesIrreversible, orchestrator/controller_test.go::TestResume_UsesResumeFlagAfterCrash, orchestrator/controller_test.go::TestRunGate_ReviseDispatchErrorPreservesStuck, orchestrator/controller_test.go::TestExecuting_RecordsAssumptions, orchestrator/controller_test.go::TestReportNotExecutable_MissingCompletion, orchestrator/controller_test.go::TestReportNotExecutable_NotReady, orchestrator/controller_test.go::TestFreshDispatch_NewSession, orchestrator/controller_test.go::TestResolveOne, orchestrator/accept_test.go::TestReconcileAndAccept_MarksDoneAndMerges, orchestrator/accept_test.go::TestReconcileAndAccept_NoAnswerLeavesOpen, orchestrator/worker_stream_test.go::TestParseCompletionVerdict
updated: 2026-08-04
summary: ブレインストーミング→実行→統合の状態機械を統括する
---

# MODULE-orchestrator-controller 外部制御ループ

## 目的

**推論は Claude に委ね、制御は Go が所有する**という設計(DSN-orch-01)の中核。
状態機械(brainstorming / executing / done)と run loop を回し、worker の並列ディスパッチ
(FR-orch-03)、タスク単位の介入(FR-orch-04)、品質ゲート(FR-orch-06)、状態の保全
(FR-orch-05)、通知(FR-orch-07)をすべてここから駆動する。

## 処理の流れ

1. `newRunID()` で run ID を採番する。
2. `Controller.Run(ctx)` が状態機械を回す。`LoadState` で現在のフェーズを確定し(未作成なら
   `brainstorming` を `SaveState` する。**ここは失敗すると `return err` で止まる**)。
   **残存 `control.json` の破棄は「起動時」ではなく2箇所に限られる**:
   フェーズが `executing` の再開時(`controller.go:76`)と、tmux でブレインストーミングを起こす直前
   (`:215`)である。
3. **brainstorming**: `MODULE-orchestrator-session` の `Run`(`new-window -d`)で
   `brainstorming` ウィンドウを起こし、`MODULE-orchestrator-mode` の `BrainstormingArgs` で
   対話 claude を起動する。着地先は初回が `dashboard`、続行/差し戻しが `brainstorming`。
   `MODULE-orchestrator-handoff` の `WaitConsume`(停止条件 = ウィンドウ消失または `PaneDead`)で
   人間の `/exit` を待つ。戻ったら TUI を `Quit` し `MODULE-orchestrator-term` の
   `ttyRestoreSane` で端末を戻す。
   handoff の分岐: `execute` かつ `plan.Ready` かつ lint clean → executing /
   `execute` だが実行不可 → `reportNotExecutable`(端末 stderr・audit・Slack に理由を明示し
   `handoff_note.md` へ前置して対話継続) / `continue_brainstorming` → 対話継続 /
   `abort` → done / control 無しまたは不明 → `MODULE-orchestrator-term` の `selectMenu` で
   「続ける / 実行(実行可のときのみ) / 終了」を選ばせる。tmux が無ければ `RunInteractive` の
   前景フォールバック。
4. **executing(スケジューラ)**: 1 tick ごとに `MODULE-orchestrator-plan` の `ReadyTasks` で
   依存解決済みの `pending` を取り、`max_workers` まで goroutine で起動する。
   各タスクは `worker 実装 → review →(重大指摘)revise → … → done` のパイプラインを通る
   (`MODULE-orchestrator-worker` と `MODULE-orchestrator-review`)。
   `MODULE-orchestrator-trigger` の `Evaluate` を条件1 = 起動前、条件2〜5 = 結果後に呼ぶ。
   **発火したタスクだけを `waiting_human` にして `intervention/open.json` へ積む**
   (`MODULE-orchestrator-state-intervention`)。peer もループも止めない。
   数秒ごとに、実行中/判断待ちタスクの消えた worker ウィンドウを作り直す(誤 kill からの復旧)。
5. **介入解決**: `MODULE-orchestrator-dashboard` の TUI で ⏸ を選ぶか `[i]` を押すと、
   当該 `w-<taskID>` ウィンドウで `LaunchInteractive` → `WaitConsume` → dashboard 復帰。
   handoff の分岐: `accept` → 回答確定 + worktree 統合(`MODULE-orchestrator-worktree` の
   `Merge`)+ done 確定(merge 失敗のみ pending へ戻す) / `resume` または未指定 →
   **共有メモリの plan** に反映して `SavePlan` / `abort` → run done。
6. **完了検証**: 判断待ち0かつ全タスク settled(`MODULE-orchestrator-plan` の `AllSettled`)で
   `verifyCompletion` へ。`plan.completion` が非空なら `MODULE-orchestrator-claude-exec` 経由で
   `claude -p`(completionProfile = sonnet / high)を走らせ助言的に検証する。
   **ブロックしない**(エラー・空・解析不能は満たしたものとして扱う)。未充足なら不足点を添えて
   Slack で人間へ促す(自動タスク化は範囲外)。`failed` / `blocked` を含み全 done でなければ
   「未完了タスクあり」として done にする。最後に最終サマリを Slack へ送る。
7. **中断**: `[q]` / SIGINT / SIGTERM は同じ経路を通る。in-flight worker へ
   `worker_grace_seconds` の中間コミット猶予を与えて停止し、状態を `executing` のまま保存して
   `errSuspended` を返す(`Run` はクリーン終了し `log.Fatal` しない)。

## 呼び出され方

- 契機: `MODULE-orchestrator-main` が初期化を終えた直後に1度だけ呼ぶ。
- 前提条件: 状態ストア・セッション管理・通知が注入済みであること。
- 引数:

| 引数 | 型 | 必須 | 制約 | 実装が行う検証 |
|---|---|---|---|---|
| `ctx` | `context.Context` | 必須 | シグナルでキャンセルされる | **検証しない**(プロセス内呼び出し)。plan は Store から読み、フェーズごとに `runExecuting` へ渡す |
| (`plan` は引数ではない) | — | — | **`Run` の引数は `ctx` だけ**(`orchestrator/controller.go:52`)。plan はフェーズごとに Store から読み、executing 中は**その共有メモリの plan が正本**として `runExecuting` に渡される | 同上 |

- 認可: プロセス内呼び出し。

## 連携先と連携内容

### MODULE-orchestrator-plan

- 何のために呼ぶか: 着手可能タスクの抽出と完了判定、失敗依存の `blocked` 化。
- 何を渡すか: 共有 plan。 / 何を受け取るか: ready タスクの並びと真偽値。
- **失敗したときどうなるか**: 想定されない(純粋論理)。依存が循環していれば ready が空のまま進まない。

### MODULE-orchestrator-worker

- 何のために呼ぶか: タスク1件を `claude -p` で実行させるため。
- 何を渡すか: `Task` と worktree のパス。 / 何を受け取るか: `WorkerResult`(`Done` / `Summary` / `Changes` / `NeedsHuman` / `Assumptions` / `Usage`)。
- **失敗したときどうなるか**: `Attempts++` して再試行する。`stuck_limit` を超えると条件3のトリガーが
  発火し `waiting_human` になる。

### MODULE-orchestrator-review

- 何のために呼ぶか: 実装 worker とは別の worker に独立レビューさせ、重大指摘があれば差し戻すため。
- 何を渡すか: worktree の diff と `Task.Completion`。 / 何を受け取るか: `findings[]`(severity / file / message / aspect)。
- **失敗したときどうなるか**: パース不能なら `ReviewFormatErrors++` し、**実作業を再ディスパッチせず
  レビューだけ再試行**する。`review_format_error_limit` に達すると `review_gate_defect` として介入キューへ積む。

### MODULE-orchestrator-trigger

- 何のために呼ぶか: 介入すべきかを機械判定するため。 / 何を渡すか: `TriggerContext`。
- 何を受け取るか: `(fire, reason)`。
- **失敗したときどうなるか**: 判定は純粋関数なので失敗しない。fire しなければ処理を続ける。

### MODULE-orchestrator-worktree

- 何のために呼ぶか: レビュー合格後に worker のコミットを作業ブランチへ統合するため(`Merge`)。
- 何を渡すか: タスク ID と `merge_strategy`。 / 何を受け取るか: エラー。
- **失敗したときどうなるか**: `accept` 経路では done にせず `pending` へ戻す(統合できていないため)。

### MODULE-orchestrator-session

- 何のために呼ぶか: dashboard / brainstorming / worker のウィンドウを作り、切り替え、消えたものを復旧するため。
- 何を渡すか: ウィンドウ名と起動コマンド。 / 何を受け取るか: 成否と存在判定。
- **失敗したときどうなるか**: tmux が使えない場合は前景フォールバックへ倒れ、TUI は起動しない。

### MODULE-orchestrator-handoff

- 何のために呼ぶか: 対話 claude からの指示(`control.json`)を受け取るため。
- 何を渡すか: 待ち受けの停止条件。 / 何を受け取るか: `Control{Request, InterventionID, TS}`。
- **失敗したときどうなるか**: control が無いまま対話が終わった場合は `selectMenu` で人間に選ばせる。

### MODULE-orchestrator-mode

- 何のために呼ぶか: 対話 claude の起動引数・プロンプト・launch script を組み立てるため。
- 何を渡すか: 介入 ID・ゴール・指示種別。 / 何を受け取るか: 引数配列とスクリプトのパス。
- **失敗したときどうなるか**: スクリプト生成に失敗すると対話ウィンドウが起動せず、そのまま
  `WaitConsume` の停止条件(ペイン死亡)に当たって dashboard へ戻る。

### MODULE-orchestrator-dashboard

- 何のために呼ぶか: 実行状況を TUI に反映し、⏸ の選択を `actions` チャネルで受け取るため。
- 何を渡すか: `DashboardState.Set` で最新のタスク状態。 / 何を受け取るか: `{resolve, taskID}` などの操作。
- **失敗したときどうなるか**: TTY でなければ TUI を起動しない(`isTTY()` で判定)。実行は続く。

### MODULE-orchestrator-state

- 何のために呼ぶか: `state.json` / `plan.json` の読み書き、worktree とログのパス解決、
  `ORCHESTRATOR.md` / VM 前置の取得。
- 何を渡すか: 状態構造体とパス要素。 / 何を受け取るか: 状態とパス、エラー。
- **失敗したときどうなるか**: **エラーを握りつぶして続行する**(`_ =` で捨てるため、端末にも
  `audit.jsonl` にも何も残らない)。保存できていないと次回の再開が古い地点からになる
  (`docs/issues/026-modify-controller-swallows-state-save-failures.md`)。

### MODULE-orchestrator-state-intervention

- 何のために呼ぶか: 判断待ちキューの出し入れ、質問の書き出し、回答の読み取り、監査・仮定の追記。
- 何を渡すか: 介入 ID・タスク ID・記録。 / 何を受け取るか: キューの内容と回答本文。
- **失敗したときどうなるか**: キューに載らないまま `waiting_human` のタスクだけが残ると、
  TUI に判断待ちが表示されない。

### MODULE-orchestrator-term

- 何のために呼ぶか: 対話から戻ったときの端末復元、実行不可時のメニュー選択、モードバナー表示。
- 何を渡すか: 選択肢。 / 何を受け取るか: 選択結果。
- **失敗したときどうなるか**: 非 TTY では既定値が返る(停止しない)。

### MODULE-orchestrator-claude-exec

- 何のために呼ぶか: 完了検証(`checkCompletion`)で `claude -p` を1回実行するため。
- 何を渡すか: プロンプトと profile。 / 何を受け取るか: stream-json の出力。
- **失敗したときどうなるか**: **ブロックしない**。エラー・空・解析不能はいずれも「満たした」と
  みなして先へ進む(助言的検証のため)。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | run の終了理由。**中断(`errSuspended`)は `Run` が吸収して `nil` を返す**(`controller.go:90`〜`:96`)ので、呼び出し元は戻り値では中断と正常終了を区別できない。区別が要る場合は状態(`state.json` の `phase`)を見る |
| 永続化 | `state.json`(フェーズ)、`plan.json`(タスクの状態遷移)、`intervention/open.json`、`audit.jsonl` / `assumptions.jsonl` / `interventions.jsonl`、`history/<run_id>/`。作業ブランチへの git マージ |
| 発火するイベント | Slack 通知(サマリ更新・判断待ちキュー投入・完了) |
| ログ | 端末の stderr(実行不可の理由など)と audit ログ |

### 一貫性境界(トランザクション境界)

**複数ファイルをまたぐトランザクションは存在しない。** 一貫性の単位は **1ファイル1書き込み**で、
書き込み順は下表のとおり固定である。途中で落ちると**先に書いたものだけが残る**。

| 書き込む対象 | 単位 | 原子性 | 落ちたときに残るもの |
|---|---|---|---|
| `plan.json` | 全体を置換 | 原子的(`MODULE-orchestrator-state-io`) | 直前に保存した plan |
| `state.json` | 全体を置換 | 原子的 | 直前のフェーズ |
| `intervention/open.json` | 全体を置換 | 原子的 | 直前のキュー |
| `audit.jsonl` / `assumptions.jsonl` / `interventions.jsonl` | 1行追記 | **原子的でない**(部分行が残りうる) | 途中まで書かれた行 |
| git マージ(作業ブランチ) | git の操作 | git に委ねる | マージ済みの成果 |

**復旧の規約は「plan.json が正」**である。再開時に `NormalizeForResume` が
`running` / `review` / `revise` のタスクを `pending` に戻し、セッション ID があるものには
再開印(`ResumeSession`)を付ける(Attempts は増やさない)。空文字の状態も `pending` にする。
`state.json` の `phase` は plan の完了状況より弱い情報として扱い、**残存する `control.json` は
起動時に破棄する**。

**とくに危険な順序は「git マージ成功 → `plan.json` 保存の前に停止」**である。統合済みなのに
タスクが `done` にならないため、再開後に同じタスクをもう一度実行する(マージ自体は git が
冪等に扱うが、worker の再実行は起きる)。

### 並行性と排他

| 対象 | 排他の単位 | 実装 |
|---|---|---|
| 共有 plan の読み書きと Store への書き込み | **1本のミューテックス**(`planMu`)で直列化する。worker goroutine・TUI 操作・tick・完了処理がすべてこれを取る | `controller.go:47` |
| 作業ブランチへの統合(`integrate`) | **別のミューテックス**(`mergeMu`)で直列化する。並行 worker のマージが競合しない | `controller.go:48`, `:705`〜`:707`, `:988`〜`:990` |
| 並行 worker 数 | `inflight` マップの要素数が `max_workers` に達したらディスパッチしない | `controller.go:395`〜`:398` |
| Slack 通知 | **`planMu` を解放してから**送る(ネットワーク I/O をロック下で行わない) | `controller.go:780`〜(`openInterventionLocked` は文字列を返すだけ) |
| TUI からの操作 | 非ブロッキングに1件ずつ取り出す(`select` の `default` 節)。取りこぼしはチャネルのバッファに残る | `controller.go:473`〜`:516` |
| ループの刻み | **タイマーではなくポーリング**。1周ごとに 20ms、一時停止中と待機中は 50ms スリープする。セッション復旧の点検は 5 秒に1回に間引く | `controller.go:518`〜`:563` |

**冪等性**: 介入の投入は「既に `waiting_human` で介入 ID を持つタスク」には何もしない
(`openInterventionLocked`)。同一 Attempt の再開は完了済みタスクを再実行しない。
**同じイベントが二重に届いた場合の重複排除はこの2つだけ**で、監査ログの行は重複しうる。

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| worker がクラッシュ / タイムアウト | `Attempts++` して再試行。上限超過で条件3のトリガーが発火し `waiting_human` へ | run は止まらない |
| plan が実行不可(completion 欠落・未 ready) | `reportNotExecutable` で端末 stderr・audit・Slack に理由を明示し、`handoff_note.md` に前置してブレインストーミングを継続する(人間に `plan.json` の手編集を促さない) | executing へ遷移しない |
| 未解決の `waiting_human` が残っている | 判断待ちが0になるまで run を終了しない | 人間の回答を待つ |
| 完了基準を満たしていない | ブロックせず、不足点を Slack で人間へ促す(自動タスク化はしない) | run は done になる |
| `[q]` / SIGINT / SIGTERM | in-flight worker に中間コミット猶予を与えて停止し、`executing` のまま状態を保存して終了コード 0 で終わる | `claude-dev orchestrate` の再実行で resume できる |
| **中断とタスク完了が同時に起きた** | `suspend` は worker をキャンセルしてから `wg.Wait()` で全 goroutine の終了を待ち、その後で plan を保存する。**完了処理の途中結果が失われることはない** | 再開時に整合した plan から続く |
| **統合が失敗した** | `merge_error` を監査ログへ記録し、タスクを `pending` に戻して**新しい Attempt として再試行**する(`accept` 経路でも同じ) | 統合できていない成果を done にしない |
| **統合成功後・`plan.json` 保存前に落ちた** | マージは残るがタスクは `done` にならない | 再開後に同じタスクをもう一度実行する |
| 状態の保存に失敗した | **経路によって違う**: 初回の状態作成(`controller.go:70`)とフェーズ遷移(`:1080`)は **`return err` で run を止める**。executing 中の `SavePlan` / `AppendAudit` などは `_ =` で**握りつぶして続行**する(`docs/issues/026`) | 前者は起動・遷移が失敗する。後者は次回の再開が古い地点からになる |
| worker ウィンドウが誤って kill された | 5 秒ごとの点検で `openWorkerSession` により作り直す | 表示上の復旧のみ。worker プロセスは再ディスパッチで復帰する |
| 依存が循環している plan | ready タスクが空のまま、in-flight も無いので `AllSettled` の判定へ落ちる。`blocked` 化されない循環は**待機のまま進まない** | 人間が `[q]` で止める |
| 同じ workspace で2つ目のコントローラが起動した | **ファイルロックが無いため検出しない**。両者が `plan.json` を後勝ちで上書きする | 状態が壊れる(Linux 版 CLI は生存判定で二重起動を防いでいる) |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 最上位状態 `intervening` を廃止し、介入を executing 内のタスク単位イベントとして扱う(旧実装の `runCancel()` による全停止をやめた) | D0-orch-04 |
| 2 | 介入の突合は必ず**共有メモリの plan** に対して行う(ディスクから別コピーを load / save すると共有 plan と乖離して run が恒久停止する) | D0-orch-04 |
| 3 | 完了検証は助言に留めブロックしない(誤判定で run が終われなくなるのを避ける) | D0-orch-02 |
| 4 | レビューのフォーマット違反と内容不合格を分離し、フォーマット違反では実作業を再ディスパッチしない | D0-orch-05 |
| 5 | plan の保護と統合の直列化を**別のミューテックス**に分ける(git マージの数秒を `planMu` で抱えるとダッシュボード更新まで止まるため) | D0-orch-04 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| `Controller.resolveInterventions` / `resolveOne` / `openInterventionCount` は製品コードから呼ばれず、テストからのみ参照される | 到達不能コードの疑い | `docs/issues/001-modify-orchestrator-test-only-symbols.md` |
| 条件4(方針分岐)/ 条件5(前提崩れ)の事前検出はフェーズ2以降(v1 は worker の `NeedsHuman` 報告のみ) | 事前に止められない | なし(閾値の外: **フェーズ2以降として 00 が範囲外と決めている**) |
| 完了基準未充足時の不足分の自動タスク化は範囲外 | 人間が判断する | なし(閾値の外: **`FR-orch-06` が範囲外と定めている**) |
| **store にロックが無い** | 同一 workspace で2つのコントローラが動くと `plan.json` が壊れる。二重起動の防止は CLI 側の生存判定に依存する(macOS 版はそれも無い) | `docs/issues/021-modify-orchestrator-store-has-no-lock.md` / `docs/issues/003-future-macos-orchestrator-scope.md` |
| 状態保存の失敗を握りつぶす | ディスク不足や権限喪失に気づかないまま run が進む | `docs/issues/026-modify-controller-swallows-state-save-failures.md` |
| メインループがポーリング(20ms / 50ms) | アイドル時も CPU を使い続ける | なし(閾値の外: 観測可能な被害はアイドル時の CPU 使用のみで、要件の性能基準に反していない) |

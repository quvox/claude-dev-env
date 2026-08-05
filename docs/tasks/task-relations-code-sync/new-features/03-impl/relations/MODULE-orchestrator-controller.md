---
target: docs/03-impl/relations/MODULE-orchestrator-controller.md
change: replace
sections:
  - "### 並行性と排他"
  - "### MODULE-orchestrator-review"
  - "### 一貫性境界(トランザクション境界)"
deletes: []
reason: 並行性の3点(Store 書き込みの排他範囲・Slack 通知とロックの関係・TUI 操作の取りこぼし)がコードと食い違う(docs/issues/038 #10)。frontmatter の callees に通知経路が無い(同 #11)
id: MODULE-orchestrator-controller
module: MOD-orchestrator
kind: function-call
sync: sync
impl: orchestrator/controller.go::Controller.Run, orchestrator/controller.go::newRunID
callers: MODULE-orchestrator-main
callees: MODULE-orchestrator-claude-exec, MODULE-orchestrator-dashboard, MODULE-orchestrator-handoff, MODULE-orchestrator-mode, MODULE-orchestrator-plan, MODULE-orchestrator-review, MODULE-orchestrator-session, MODULE-orchestrator-slack, MODULE-orchestrator-state, MODULE-orchestrator-state-intervention, MODULE-orchestrator-term, MODULE-orchestrator-trigger, MODULE-orchestrator-worker, MODULE-orchestrator-worktree
contracts: CTR-orchestrator-prompt
design: DSN-mod-01, DSN-orch-01, DSN-orch-02, DSN-ui-02
requirements: FR-orch-01, FR-orch-02, FR-orch-03, FR-orch-04, FR-orch-05, FR-orch-06, FR-orch-07
tests: orchestrator/controller_test.go::TestExecuting_RespectsMaxWorkers, orchestrator/controller_test.go::TestExecuting_DependencyOrder, orchestrator/controller_test.go::TestExecuting_TriggerParksTaskPeersContinue, orchestrator/controller_test.go::TestExecuting_Trigger1Irreversible, orchestrator/controller_test.go::TestIntervene_ResolveApprovesIrreversible, orchestrator/controller_test.go::TestResume_UsesResumeFlagAfterCrash, orchestrator/controller_test.go::TestRunGate_ReviseDispatchErrorPreservesStuck, orchestrator/controller_test.go::TestExecuting_RecordsAssumptions, orchestrator/controller_test.go::TestReportNotExecutable_MissingCompletion, orchestrator/controller_test.go::TestReportNotExecutable_NotReady, orchestrator/controller_test.go::TestFreshDispatch_NewSession, orchestrator/controller_test.go::TestResolveOne, orchestrator/accept_test.go::TestReconcileAndAccept_MarksDoneAndMerges, orchestrator/accept_test.go::TestReconcileAndAccept_NoAnswerLeavesOpen, orchestrator/worker_stream_test.go::TestParseCompletionVerdict, orchestrator/term_test.go::TestBuildQuestion_NumbersOptions
updated: 2026-08-05
summary: ブレインストーミング→実行→統合の状態機械を統括する
---

<!-- 変更指示。反映後の最終形を書く(差分記法は使わない)。version / verified は持たない。
     frontmatter の callees に MODULE-orchestrator-slack を追加した(038 #11)。
     対称性のため MODULE-orchestrator-slack.md の callers 側も同時に直す。
     tests に orchestrator/term_test.go::TestBuildQuestion_NumbersOptions を加えた(038 #29。
     このテストは controller.go:1147 の buildQuestion を検証しており、MODULE-orchestrator-term から移した)。 -->

### 並行性と排他

| 対象 | 排他の単位 | 実装 |
|---|---|---|
| 共有 plan の読み書き | **1本のミューテックス**(`planMu`)で直列化する。worker goroutine・TUI 操作・tick・完了処理がすべてこれを取る | `controller.go:47` |
| Store への書き込み | **すべてが `planMu` の下にあるわけではない。** plan と同時に触るもの(`SavePlan` / `SaveState` / タスク完了時の `AppendAudit`)はロック下で行うが、run の開始・終了・中断・フェーズ遷移の監査ログは**ロックの外**で追記する(`:73` `run_start` / `:467` `suspended` / `:1039` `finished_incomplete` / `:1083` `transition`)。Store 側にもロックは無い(`docs/issues/021`) | `controller.go:73`, `:467`, `:1039`, `:1083` |
| 作業ブランチへの統合(`integrate`) | **別のミューテックス**(`mergeMu`)で直列化する。並行 worker のマージが競合しない | `controller.go:48`, `:705`〜`:707`, `:988`〜`:990` |
| 並行 worker 数 | `inflight` マップの要素数が `max_workers` に達したらディスパッチしない | `controller.go:395`〜`:397` |
| Slack 通知 | **原則は `planMu` を解放してから**送る(`:452` の解放後に `:453`〜`:455` の `notifies` ループを回す。`openInterventionLocked`(`:780`)は文字列を返すだけでネットワーク I/O をしない)。**例外が1つある**: 完了サマリだけは `updateSummaryLocked`(`:720` / `:1004`)が **`planMu` を保持したまま** `updateSummary`(`:1087`〜`:1091`)を呼ぶため、`WriteSummary` と `Notifier.Notify` の I/O がロック下で走る | `controller.go:452`〜`:455`, `:720`, `:1004`, `:1087`〜`:1091` |
| TUI からの操作 | **受け側**(コントローラ)は1周に1件だけ非ブロッキングに取り出す(`case a := <-actions:` と `default:`)。**送り側は取りこぼしを捨てる**: `dashModel.send` はチャネルが満杯のとき `select` の `default` 節で**その操作を黙って破棄する**(バッファは 8 件)。**取りこぼしがバッファに残るのではない** | `controller.go:240`, `:380`(`make(chan dashAction, 8)`), `:477`, `:516`, `orchestrator/dashtui.go:82`〜`:87` |
| ループの刻み | **タイマーではなくポーリング**。1周ごとに 20ms(`:564`)、一時停止中と待機中は 50ms(`:540` / `:560`)スリープする。セッション復旧の点検は 5 秒に1回に間引く(`:521`〜`:522`) | `controller.go:521`〜`:522`, `:540`, `:560`, `:564` |

**冪等性**: 介入の投入は「既に `waiting_human` で介入 ID を持つタスク」には何もしない
(`openInterventionLocked`)。同一 Attempt の再開は完了済みタスクを再実行しない。
**同じイベントが二重に届いた場合の重複排除はこの2つだけ**で、監査ログの行は重複しうる。

### MODULE-orchestrator-review

- 何のために呼ぶか: 実装 worker とは別の worker に独立レビューさせ、重大指摘があれば差し戻すため。
- 何を渡すか: `ctx` と共有 plan(`p`)と対象タスク(`t`)。レビュアが読むのはそのタスクの worktree と
  `Task.Completion` である。 / 何を受け取るか: **`(GateOutcome, error)`**。`GateOutcome` は
  `Passed` / `LastSevere`(重大指摘の要約)/ `FormatError` / `FormatErrorCount` で、
  **`findings[]` そのものは返らない**(指摘の生データはレビュア側で消費される)。
- **失敗したときどうなるか**: パース不能なレビュア出力はレビュア側で数えられ、**実作業を再ディスパッチせず
  レビューだけ再試行**される。上限に達すると `GateOutcome.FormatError` が真で返るので、
  **`Task.ReviewFormatErrors` へ書くのはこの機能**(`controller.go:685`。解消時のリセットは `:699`)で、
  `review_gate_defect` として介入キューへ積む。`error` が非 `nil` になるのは中断と revise の失敗だけである。

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
`state.json` の `phase` は plan の完了状況より弱い情報として扱う。**残存する `control.json` の破棄は
「起動時」ではなく手順の2箇所に限られる**(処理の流れの該当手順を見ること): `executing` で再開すると
判定したときと、対話を起こす直前である。

**とくに危険な順序は「git マージ成功 → `plan.json` 保存の前に停止」**である。統合済みなのに
タスクが `done` にならないため、再開後に同じタスクをもう一度実行する(マージ自体は git が
冪等に扱うが、worker の再実行は起きる)。

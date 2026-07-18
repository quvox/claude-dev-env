---
id: orchestrator
layer: impl
title: orchestrator 実装説明書
version: 1.0.0
updated: 2026-07-18
verified:
  at: 2026-07-18
  version: 1.0.0
  against:
    - doc: docs/02-design/system.md
      version: 1.0
summary: >
  プロジェクトに1体立てる AIオーケストレーター（Go 製単一プロセス `claude-orchestrator`）の実装。
  tmux 常駐（orch-<CNAME>-main:dashboard）で外部制御ループを所有し、ブレインストーミング/実行の2モード状態機械・
  worker 並列ディスパッチ（claude -p on git worktree）・タスク単位介入・相互レビュー品質ゲート・bubbletea TUI・
  Slack 通知・状態ストア（plan.json/control.json/state.json + *.jsonl）による中断復旧を実装する。
keywords: [オーケストレーター, Go, tmux, 状態ストア, worker並列, 介入, 品質ゲート, bubbletea, 中断復旧]
depends_on: [hooks]
source:
  - docs/02-design/system.md
---

# 実装説明書:orchestrator（AIオーケストレーター）

## 概要

`orchestrator/` は、プロジェクトごとに 1 体立てる AI オーケストレーター（Go 製単一プロセス
`claude-orchestrator`）の実装である。**外部制御ループ**をコード（Go）が所有し、推論（分解・実装・レビュー・
判断）はすべて Claude に委ねる。`orch-<CNAME>-main` tmux セッションの `dashboard` ウィンドウに常駐し、
ブレインストーミング/実行の 2 モード状態機械を回す。実行モードでは依存解決済みタスクを `max_workers` まで
`claude -p`（git worktree 分離）で並列ディスパッチし、別 worker による相互レビューを通し、介入トリガー該当タスク
だけを `waiting_human` にして人間を待つ（他 worker は継続）。状態は `/workspace/.orchestrator/` に永続化し、
中断・端末破壊から resume する。上流: [全体設計](../02-design/system.md)（`orchestrator` 行、cli(orchestrate)→
orchestrator 契約、orchestrator→worker/対話Claude 契約、UI設計 orch-* 画面、要件 orchestration/12〜19）。
本モジュールは Slack 通知の思想を hooks（`sendslackmsg.sh`）と共有する（depends_on: hooks）。

## ファイル構成

| パス | 役割 |
|---|---|
| orchestrator/go.mod / go.sum / vendor/ | 独立 Go モジュール（Go 1.24）。TUI 用に `bubbletea`/`lipgloss` へ依存。vendoring（`-mod=vendor`）でオフライン再現ビルド |
| orchestrator/main.go | エントリ。`--workspace` 絶対パス化、`--fresh`/`--start-executing`/`--instructions`/`--print-main-session` 解析、再開/新規判定、Store 初期化、SIGINT/SIGTERM ハンドラ、`Sessions` 注入、`defer ttyRestoreSane()` |
| orchestrator/controller.go | 状態機械（brainstorming/executing/done）と run loop（中核）。`runBrainstorming`/`runExecuting`/介入解決/worker ウィンドウ結線 |
| orchestrator/state.go | 状態ストアの読み書きとスキーマ（State/Plan/Task/Control/Open*）、audit/assumptions/interventions.jsonl 追記、`ArchiveRun`、`NormalizeForResume`、`VMModePreamble` |
| orchestrator/plan_test.go 由来のプラン論理 | 依存解決（`ReadyTasks`）・状態遷移・`AllDone`/`AllSettled`・`MarkBlockedByFailedDeps`（state.go/plan 系に実装） |
| orchestrator/mode.go | 対話 claude（ブレスト/介入）の instruction 組立・launch script 生成（`WriteLaunchScript`）・`RunInteractive`（tmux 無しフォールバック）・`ORCHESTRATOR.md`/VM前置 |
| orchestrator/session.go | tmux ウィンドウ管理（`SessionManager`）。`DetectSession`/`SetupMainSession`/`Ensure`/`Run`/`Kill`/`Has`/`SwitchTo`/`LaunchInteractive`/`EnsureAll`/`normalizeCName` |
| orchestrator/term.go | 端末モード制御（stty raw/カノニカル復元 `ttyRestoreSane`）・`selectMenu`/`terminalConfirm`・`printModeBanner`・`buildQuestion` |
| orchestrator/claudebin.go | `claude` 実行ファイル解決（`claudePath`＝LookPath→`$HOME/.local/bin/claude`）と子プロセス環境（`claudeChildEnv`：PATH 補完・`SLACK_BOT_TOKEN` 除去） |
| orchestrator/handoff.go | 対話 claude→コントローラの受け渡し（`control.json`）。`Consume`/`WaitConsume`/`DiscardStale` |
| orchestrator/worker.go | worker ディスパッチ（`claude -p`）・worktree 準備/再接続・構造化結果解析（`ParseWorkerResult`）・`workerResultGuide` |
| orchestrator/models.go | モデル/effort 選択ポリシー表（`deepTaskKinds`/`profileDeep`/`profileDefault`・各ロール profile 関数）。唯一の編集ポイント |
| orchestrator/review.go | 品質ゲート（review→revise ループ、`completion` 採点、構造化出力解析 `findReviewResultJSON`、`reformatToJSON`） |
| orchestrator/trigger.go | 介入トリガー判定（`Evaluate(TriggerContext)→(fire,reason)`。条件1=pre-dispatch、2/3/4/5=post） |
| orchestrator/slack.go | Slack 通知（`chat.postMessage` 直接 POST、未設定 no-op、失敗握りつぶし） |
| orchestrator/dashboard.go | 実行モードの共有状態 `DashboardState` と純ヘルパ（`selectableWorker`/`statusLabel`/`readVMHealthBanner`） |
| orchestrator/dashtui.go | 実行モードのカーソル選択式 TUI（bubbletea `dashModel`：Init/Update/View、`detailTails`/`tailFile`） |
| orchestrator/streamlog.go | stream-json をログへ Claude Code 風に整形（`streamPrettyWriter`/`formatStreamLine`）。表示専用・解析非関与 |
| orchestrator/config.go | 設定マージ（組込既定→`~/.config/claude-dev.yaml`→`.orchestrator/config.yaml`）。stdlib のみの簡易 YAML パーサ |
| orchestrator/instructions/{brainstorming,intervene}.md | 対話 claude 用テンプレート（イメージ同梱） |
| orchestrator/*_test.go | 単体テスト群（§テスト） |

イメージへは `claude-orchestrator` として `/usr/local/bin/` に焼き込み、プロジェクトコンテナ内で実行する
（tmux・`claude` CLI・git worktree を同コンテナ内で扱う）。

## モジュール別実装詳細

### controller（controller.go）

- **責務:** 設計 `orchestrator` の中核。状態機械（brainstorming/executing/done）と run loop の駆動、
  ブレスト/worker/介入の tmux ウィンドウ群の生成・終了・復旧。
- **処理の要点:**
  - **起動判定（main.go 連携）:** `--workspace` を `filepath.Abs` で絶対化（相対だと worktree パス二重ネストで
    `git worktree add` が exit 128）。`state.json`/`plan.json` を読み、**plan の完了状況で再開/新規を判定**
    （§設定・環境変数の判定ロジック）。
  - **brainstorming:** `runBrainstorming` は内部ループ。tmux 有り時 `runBrainstormingSession(ctx, enterConversation)`
    で `orch-<CNAME>-main:brainstorming` を `Sessions.Run`（`new-window -d`）で起こす。**脳起動直前に
    `Handoff.DiscardStale()`** で残存 control.json を破棄。着地は `enterConversation`：初回は
    `SwitchTo(DashboardWindow)`（カーソル選択式ホーム）、続ける/実行不可差し戻しは `SwitchTo(BrainstormingWindow)`
    （対話へ直接戻す）。`WaitConsume(until=!Has||PaneDead)` で人間の `/exit` を待ち、戻ったら
    `prog.Quit()`+`Wait()`+`ttyRestoreSane()` で端末復元後 `dashboard` へ。handoff 分岐：`execute`+`plan.Ready`+
    lint clean→executing／`execute` だが実行不可→`reportNotExecutable`（端末 stderr+audit+Slack へ理由明示・
    `handoff_note.md` へ前置）で対話継続／`continue_brainstorming`→対話継続／`abort`→done／control 無・不明→
    `selectMenu`（続ける/実行〔実行可時のみ〕/終了）。tmux 無しは `mode.RunInteractive` 前景フォールバック。
  - **executing（スケジューラ）:** 1 tick ごとに依存解決済み `pending` を `max_workers` まで goroutine 起動。各タスクは
    `worker 実装→review→(重大指摘)revise→…→done` の pipeline。`trigger.Evaluate` を条件1=起動前・条件2-5=結果後に
    呼ぶ。**発火タスクのみ `waiting_human` にして `intervention/open.json` へ積む**（`openInterventionLocked`。
    peer・ループは止めない。旧 `runCancel()` 全停止は廃止）。数秒ごとに実行中/⏸ タスクの消えた worker ウィンドウを
    `openWorkerSession` で再構築（誤 kill 復旧）。**終了判定:** 未解決 `waiting_human` が 1 件でも残る間は run を終了
    しない。判断待ち 0 かつ全タスク settled で完了検証へ。
  - **介入解決:** ⏸ 選択（dashtui `actions` チャネル）または `[i]` で `resolveInterventionInSession(ctx,plan,taskID)`
    ＝当該 `w-<taskID>` へ `LaunchInteractive`→`WaitConsume`→dashboard 復帰→handoff 分岐：`accept`→
    `reconcileAndAccept`（回答確定＋worktree 統合＋done 確定・merge 失敗のみ pending）／`resume`/未指定→`reconcileOne`
    を**共有メモリの plan** に適用し `SavePlan`（`resolveOne` のようにディスクから別コピーを load/save しない＝
    共有 plan 乖離で run 恒久停止する落とし穴の回避）／`abort`→run done。
  - **完了検証:** 判断待ち 0 かつ全 settled で `verifyCompletion`。`plan.completion` 非空なら `claude -p`
    （`completionProfile`＝sonnet/high）で助言的検証（`checkCompletion`→`parseCompletionVerdict`）。**ブロックしない**
    （エラー・空・解析不能は満たしたものとして扱う）。未充足は Slack に不足点を添え人間確認を促す（自動タスク化は範囲外）。
    `failed`/`blocked` を含み全 done でないなら「未完了タスクあり」で done。最終サマリを Slack 送信。
  - **中断:** `[q]`/SIGINT/SIGTERM は同一経路。in-flight worker へ中間コミット猶予（`worker_grace_seconds`）を与えて
    停止し、状態を `executing` のまま保存、`errSuspended` を返して `Run` がクリーン終了（終了コード 0・`log.Fatal` しない）。
- **実装上の判断:** 最上位状態 `intervening` は廃止（介入は executing 内のタスク単位イベント）。介入突合は必ず共有 plan に対して行う。

### state（state.go）

- **責務:** `/workspace/.orchestrator/` 配下の読み書きとスキーマ、追記型ログ、アーカイブ、resume 正規化。
- **主要スキーマ:** `State{Phase,RunID,CurrentTask,StartedAt,UpdatedAt}`／`Plan{Goal,Completion,Ready,Tasks[]}`／
  `Task{ID,Title,Kind,Description,Completion(必須),Deps[],Status,Irreversible,IrrevApproved,Attempts,Worktree,
  SessionID,ResumeSession,OpenInterventionID,ReviewFormatErrors,Result}`／`WorkerResult{Done,Summary,Changes[],
  NeedsHuman,Assumptions[],Usage}`／`Control{Request,InterventionID,TS}`／`OpenInterventions{Items[]}`。
- **処理の要点:**
  - **Task.Status 遷移:** `pending→running→review→(重大)revise→…→done`。トリガー該当は `waiting_human`
    （worker スロットを占有せず他は継続）。回答後 controller が `waiting_human→pending`（trigger1 承認は `IrrevApproved`）。
    起動不能な依存崩れは `MarkBlockedByFailedDeps` で `blocked`（run 内終端）。
  - **ArchiveRun:** 片付けは削除でなく `os.Rename` で `history/<run_id>/` へ退避（plan/state/control/open.json＋
    summary スナップショット）。追記型ログは残す。**起動時自動処理で plan/状態/履歴を `os.Remove` しない**不変条件。
  - **NormalizeForResume:** `done`/`failed`/`blocked` は一切触らない。`waiting_human` は保持。`running`/`review`/`revise`
    のまま落ちたものは `pending` へ戻し、`SessionID` があれば `--resume` 継続（`ResumeSession` フラグ）。
  - **VMModePreamble:** `CLAUDE_DEV_VM=1` のとき VM モードの短い前置文を返す（各プロンプト先頭で `LoadProjectPolicy` と並置）。

### mode（mode.go）

- **責務:** 対話 claude（ブレスト/介入）の起動と instruction 注入。設計 mode コンポーネント。
- **公開インターフェース:** `RunInteractive(ctx)`（tmux 無しフォールバック・子終了までブロック）／
  `BrainstormingArgs()`（`handoff_note.md` を先頭前置し消費後削除）／`IntervenePrompt`／
  `WriteLaunchScript(key, sys, prompt)`（`.orchestrator/sessions/<key>.sh` に launcher 生成：VM env source・
  claude を PATH・`SLACK_BOT_TOKEN` strip・`cd` workspace・巨大 prompt は `.sys`/`.prompt` sidecar から `$(cat)`）。
- **処理の要点:** instruction は `--append-system-prompt` でイメージ同梱テンプレ（`brainstorming.md`/`intervene.md`）を
  渡す。`ORCHESTRATOR.md`（存在時・コミット対象）と VM 前置を各プロンプト先頭へ prepend。model/effort は
  `brainstormingProfile`/`interveneProfile`（＝opus/high）を `--model`/`--effort` として付す。

### session（session.go）

- **責務:** 唯一のセッション `orch-<CNAME>-main` 配下のウィンドウ管理（設計の新アーキ）。
- **公開インターフェース:** `MainSession()`／`DashboardWindow()`/`BrainstormingWindow()`/`WorkerWindow(taskID)`／
  `DetectSession`（`$TMUX` 有り時 `tmux display-message -p '#{session_name}'` で実測名を束縛）／
  `SetupMainSession`（自窓を `dashboard` に改名＋`mouse on`）／`Ensure`（`new-window -d`＋`remain-on-exit on`・冪等）／
  `Run`（`respawn-pane -k`）／`Kill`（`kill-window`）／`Has`／`SwitchTo`（`select-window`）／`LaunchInteractive`／
  `EnsureAll`／`normalizeCName`。
- **実装上の判断:** 存在確認は `list-windows -F '#{window_name}'` で厳密照合する（`display-message -t session:window`
  は窓不在でも現窓へフォールバックし誤って成功を返す＝実機で判明）。worker/brainstorming 窓は `remain-on-exit on`
  で `/exit` 後も残し、tail→介入→再ディスパッチを同一ウィンドウで駆動。`dashboard` 窓は `remain-on-exit off`。

### worker（worker.go）

- **責務:** タスク 1 件を `claude -p` で worktree 上に実行し構造化結果を回収（設計 worker）。
- **処理の要点:**
  1. **worktree 準備:** `git worktree add .orchestrator/worktrees/<taskID> -b orch/<taskID>`。ディレクトリ既存は再利用、
     ブランチ `orch/<taskID>` のみ残存時は `-b` なしで再接続（`BranchExists`→`WorktreeAddExisting`。exit 128 回避）。
  2. **プロンプト構築:** `Task.Description` ＋ 状態ストアからの必要文脈（関連 docs・先行結果サマリ・制約）を過不足なく注入。
  3. **起動:** `claude -p "<prompt>" --output-format stream-json --verbose [--model][--effort] --permission-mode <mode>
     [--session-id|--resume]`、CWD=worktree。出力は `io.MultiWriter` で (a) 生 stream-json バッファ（解析用）と
     (b) `streamPrettyWriter`（`workers/<taskID>.log` へ整形書き込み）へライブ tee。model/effort は `workerTaskProfile(t)`。
     `--permission-mode` 既定 `bypassPermissions`（ヘッドレスで権限プロンプトに答える人間がいないため明示必須）。
  4. **結果回収:** `ParseWorkerResult` が stream-json 最終 result→single envelope→bare の順で内側 JSON をデコード。
     `Usage` を `audit.jsonl` へ、`Assumptions` を `assumptions.jsonl` へ、`NeedsHuman` は trigger へ。
  5. **取り込み:** worker は意味のある区切りで逐次コミット。レビュー合格後 **controller** が worktree コミットを作業
     ブランチへ統合（`merge_strategy`）。worker には後戻り不可操作（push/deploy/削除）と `SLACK_BOT_TOKEN` を渡さない。
  - **セッション継続:** 初期 `system`/`init` の `session_id` を捕捉し `Task.SessionID` 保存。同一 Attempt 再開は `--resume`、
    別アプローチ（新 Attempt）は `SessionID` を空に戻す。`--resume` 失敗時は新規へフォールバックし audit 記録。

### review（review.go）

- **責務:** 実装 worker と別 worker による独立レビューと改訂ループ（設計 review、要件17）。
- **処理の要点:** レビュア（`claude -p`・`reviewerProfile`＝opus/high）へ worktree の diff と 2 観点（①要件充足・動作
  ②セキュリティ・エラー処理・保守性）のチェックリストを 1 回で与える。**採点基準は `Task.Completion` のみ**
  （`Plan.Completion`/`Goal` へのフォールバック禁止）。出力は構造化（findings[]：severity=critical|major|minor, file,
  message, aspect）。`findReviewResultJSON` は (a) 最終行厳密一致優先、(b) フェンス除去・ブレース対応スキャン
  `findJSONObjects` で `findings` キーを持つ最後のオブジェクトを拾う。なおパース不能なら `reformatToJSON`
  （散文結論を haiku/low で規定 JSON へ変換・判定は変えない・`review_reformat_ok` を audit）を 1 回。重大 severity が
  残る間 revise（`max_review_rounds` まで、`Attempts` 増やさない）。
  - **フォーマット違反と内容不合格の分離:** パース不能→`Task.ReviewFormatErrors++`・**実作業を再ディスパッチせず
    レビューのみ再試行**。`review_format_error_limit`（既定 2）到達で `review_gate_defect` として介入キューへ（seed に
    「completion 充足の一次確認」と `accept`/`resume` の指示を添え介入ループを断つ）。内容不合格は `ReviewFormatErrors`
    リセットして revise 継続。上限到達でも重大指摘残存なら trigger3。

### models（models.go）

- **責務:** 工程別 model/effort ポリシー（唯一の編集ポイント、要件18-1）。
- **処理の要点:** `profileDeep={opus,high}`／`profileDefault={sonnet,high}`。`deepTaskKinds`＝
  {design, spec, impl_spec, impl-spec, requirements, usecase, adr, doc, docs, review}。選択関数：`workerTaskProfile(t)`
  （`Task.Kind` 分岐、未知/空→default）／`brainstormingProfile`/`interveneProfile`/`reviewerProfile`（＝deep）／
  `completionProfile`（＝default・助言軽量）。旧 `worker_model` 設定は非推奨・未使用（解析のみ）。

### trigger（trigger.go）

- **責務:** 介入トリガー 5 条件の機械判定（要件15）。
- **公開インターフェース:** `Evaluate(ctx TriggerContext) (fire bool, reason string)`。
- **処理の要点:** 条件1（後戻り不可）＝計画段階で `Irreversible` 印付けタスクを worker 起動**前**に fire（`IrrevApproved`
  で再発火防止）。条件2（曖昧さ）/4（方針分岐）/5（前提崩れ）＝worker の `NeedsHuman.Reason`
  （ambiguity/policy_branch/prerequisite_broken）を実行後に検出。条件3（行き詰まり）＝`Attempts>=stuck_limit`、または
  Attempt 内 `max_review_rounds` 到達後も重大指摘残存（controller 検出・`NeedsHuman` を使わない）。軽微は fire せず
  `assumptions.jsonl` へ記録して続行。

### dashboard / dashtui（dashboard.go / dashtui.go）

- **責務:** 実行モードのカーソル選択式 TUI（要件19、UI設計 orch-dashboard）。`dashboard.go`＝共有状態と純ヘルパ、
  `dashtui.go`＝bubbletea モデル。
- **処理の要点:** `dashModel`（Init/Update/View）が稼働 worker と ⏸ 要判断を差分描画。ヘッダにモード
  （`● 実行中`/`⏸ 一時停止`）、goal、各タスク行（状態ラベル・経過時間・試行回数）、直近サマリ、仮定カウント・
  **要判断の一覧（open.json の TaskID→タスク名）**・実行中数、キーヒント。**カーソル（↑↓/jk）で選び Enter で確定
  したときだけ移動**：実行中はモデルが直接 `select-window`、⏸ は `actions` チャネルへ `{resolve,taskID}`。`p`
  （`dash.Paused` トグル）・`d`（出力 tail トグル・`detailTails`/`tailFile`）・`i`（先頭要判断）・`q`（中断）。
  `View()` は毎描画 `readVMHealthBanner`（VM モード時 `$HOME/.claude-dev-vm/health` が `STATE=WARN` かつ鮮度内なら赤
  バナー）をベストエフォートで呼ぶ。controller が `isTTY()` 時のみ `newDashProgram`（`WithAltScreen`＋`WithContext`）起動。

### slack（slack.go）/ handoff（handoff.go）/ streamlog（streamlog.go）/ config（config.go）

- **slack:** `net/http` で `https://slack.com/api/chat.postMessage` へ `Bearer $SLACK_BOT_TOKEN` JSON POST。未設定 no-op、
  失敗握りつぶし（ログのみ）。宛先 `SLACK_CHANNEL`。送信契機＝サマリ更新／要判断キュー投入（件数アラート）／完了。
  **発信源はコントローラに一本化**（worker・対話 claude には `SLACK_BOT_TOKEN` を渡さない）。
- **handoff:** `control.json` の `Consume`/`WaitConsume`（ポーリング＋until）/`DiscardStale`。書込は一時ファイル→rename の原子的操作、消費後 controller が削除。
- **streamlog:** `streamPrettyWriter`（改行区切りで stream-json を受け部分行バッファ）＋`formatStreamLine`
  （assistant text／tool_use＝`⏺ 名前(要約)`／tool_result＝`⎿ …`／result＝区切り＋完了。未知はそのまま）。表示専用・解析非関与。
- **config:** 組込既定→`~/.config/claude-dev.yaml` の `orchestrator:` セクション→`/workspace/.orchestrator/config.yaml`
  の順にマージ（stdlib のみの簡易 `key: value` パーサ）。model/effort は config で変えない（`models.go` が決定）。

## データアクセス

| データ | 操作 | 実施モジュール | 備考 |
|---|---|---|---|
| state.json | 読み書き | state / controller | Phase・RunID・タイムスタンプ。原子的書込 |
| plan.json | 読み書き | state / controller / worker / review | 実行の中核状態。executing 中は共有メモリの plan を正本に `SavePlan` |
| control.json | 読み書き | handoff / 対話claude | モード引き渡し・介入回答。消費後削除・再開時は無視して消す |
| intervention/open.json | 読み書き | controller | 未解決要判断キュー（タスク単位・複数同時可） |
| intervention/<id>/{question,answer}.md | 読み書き | controller / 介入脳 | 介入 1 件の質問・回答 |
| audit/assumptions/interventions.jsonl | 追記 | state / controller | 監査・仮定・介入の追記型ログ。Archive 時も残す |
| workers/<taskID>.log | 追記/tail | worker(streamlog) / dashtui | 整形済みライブログ。`[d]`/`tail -F` で表示 |
| worktrees/<taskID>/ | git worktree | worker / controller | worker 作業コピー。統合は controller が直列化 |
| history/<run_id>/ | os.Rename 退避 | state(ArchiveRun) | 新規/`--fresh` 時の退避。削除しない |

## 設定・環境変数

| 名前 | 用途 | デフォルト | 必須 |
|---|---|---|---|
| max_workers | 並行 worker 数（コスト・競合上限） | 5 | 任意 |
| stuck_limit | トリガー3（行き詰まり）の Attempt 総数上限 | 3 | 任意 |
| max_review_rounds | Attempt 内 review→revise 反復上限 | 10 | 任意 |
| review_format_error_limit | 連続パース不能で `review_gate_defect` 介入へ | 2 | 任意 |
| worker_grace_seconds | 中断時に in-flight worker へ与える中間コミット猶予秒 | 10 | 任意 |
| merge_strategy | worktree 取り込み方式（merge/rebase） | merge | 任意 |
| worker_permission_mode | worker/レビュア `claude -p` の `--permission-mode`（空文字で無指定） | bypassPermissions | 任意 |
| reviewer_vendor | レビュア種別。**v1 は読むだけで未使用**（常に Claude・codex はフェーズ2） | claude | 任意 |
| worker_model | **DEPRECATED**（models.go が決定・解析のみ） | （未使用） | 任意 |
| SLACK_BOT_TOKEN / SLACK_CHANNEL | Slack 送信（controller のみ保持） | — / 既存同値 | 任意 |
| CLAUDE_DEV_VM | VM モード（`=1` で VM 前置文を各プロンプトへ付加） | 未設定 | 任意 |

config は 3 段マージ（下ほど強い）：組込既定 → `~/.config/claude-dev.yaml` の `orchestrator:` → `/workspace/.orchestrator/config.yaml`。

**再開/新規の判定（main.go・要件16-2）:** plan の完了状況で判定（`--fresh` を除く）。未完了 plan が残る（`AllDone==false`）
→その run を継続（`plan.Ready` なら executing、未 ready なら brainstorming）。`AllDone==true`／plan 不在→新規開始。
`--fresh`→現 run を `history/` 退避してから新規。`--start-executing`＋ready な seed plan→executing 直接開始（検証専用）。

## エラーハンドリング実装

| 異常系 | 実装箇所 | 実際の振る舞い | 対応する要件 |
|---|---|---|---|
| worker クラッシュ/タイムアウト | controller/worker | `Attempts++` で再試行、上限超過で trigger3 | orchestration/17 |
| レビュー結果パース不能 | review | `reformatToJSON` で回収→なお不能で `ReviewFormatErrors++`・実作業やり直さず・limit で `review_gate_defect` 介入 | orchestration/17-4,17-5 |
| plan 実行不可（completion 欠落/未 ready） | controller(`reportNotExecutable`) | 端末 stderr+audit+Slack へ理由明示、`handoff_note.md` へ前置しブレスト継続（人間に plan.json 編集を促さない） | orchestration/17-3,19-4 |
| SIGINT/SIGTERM/`[q]` | main/controller | 中間コミット猶予後 `errSuspended` でクリーン終了（コード0）、executing のまま保存 | orchestration/16-4 |
| 端末破壊（tmux クライアント全終了） | cli/session | コントローラは tmux サーバ上で生存、`orchestrate` 再実行で attach、不在なら resume | orchestration/16, UC-5 |
| `claude` が PATH に無い | claudebin | `claudePath`（LookPath→`$HOME/.local/bin/claude`）で絶対解決・`claudeChildEnv` で PATH 補完 | orchestration/13 |
| Slack 送信失敗/未設定 | slack | no-op・握りつぶし（ログのみ） | orchestration/18-3 |
| 完了基準未充足 | controller(`checkCompletion`) | ブロックせず Slack で人間へ促す（自動タスク化しない） | orchestration/18-2 |

## テスト

| テスト(ファイル::ケース名) | レベル | 検証内容 | 対応する受け入れ基準/契約 |
|---|---|---|---|
| controller_test.go::TestExecuting_RespectsMaxWorkers | 単体 | 同時実行数 ≤ max_workers | 要件14-3 |
| controller_test.go::TestExecuting_DependencyOrder / plan_test.go::TestDependencyChainOrder | 単体 | 依存解決順で起動 | 要件14 |
| controller_test.go::TestExecuting_TriggerParksTaskPeersContinue | 単体 | 発火タスクのみ waiting_human・peer 継続 | 要件15-1 |
| controller_test.go::TestExecuting_Trigger1Irreversible / trigger_test.go::TestEvaluate_PreDispatchIrreversible | 単体 | 後戻り不可の事前審査 fire | 要件15-1（トリガー1） |
| controller_test.go::TestIntervene_ResolveApprovesIrreversible | 単体 | 介入承認で IrrevApproved・再発火せず再ディスパッチ | 要件15-3 |
| controller_test.go::TestResume_UsesResumeFlagAfterCrash | 単体 | クラッシュ後 SessionID で `--resume` 再開 | 要件16-5 |
| controller_test.go::TestRunGate_ReviseDispatchErrorPreservesStuck | 単体 | revise エラー時の trigger3・Attempts 保持 | 要件17-6 |
| controller_test.go::TestExecuting_RecordsAssumptions | 単体 | 軽微仮定を assumptions.jsonl へ記録 | 要件15-4 |
| controller_test.go::TestReportNotExecutable_MissingCompletion / _NotReady | 単体 | 実行不可で executing 遷移せず理由明示 | 要件17-3, 19-4 |
| accept_test.go::TestReconcileAndAccept_MarksDoneAndMerges / _NoAnswerLeavesOpen | 単体 | accept で done 確定＋統合／未回答は open 維持 | 要件15-3, 17-5 |
| accept_test.go::TestReview_ReformatsProseToJSON / review_parse_test.go::TestFindReviewResultJSON_StrictAndTolerant | 単体 | 構造化出力の厳密＋寛容パース・散文再整形 | 要件17-4 |
| trigger_test.go::TestEvaluate_*（NeedsHumanReasons/StuckLimitBoundary/StuckThisAttempt/StuckTakesPrecedence/…） | 単体 | 5 トリガーの発火/非発火・stuck 境界・優先順 | 要件15-1, 17-6 |
| models_test.go::TestTaskKindProfile / TestWorkerTaskProfile / TestRoleProfiles | 単体 | kind→profile 分類・ロール profile・effort 妥当性 | 要件18-1 |
| plan_test.go::TestReadyTasks_* / TestMarkBlockedByFailedDeps / TestAllDoneAndSettled / TestStatusTransition_HappyPath / TestReviseDoesNotIncrementAttempts | 単体 | 依存解決・並行上限・失敗依存除外・状態遷移・revise で Attempts 不変 | 要件14, 16-3, 17-6 |
| state_test.go::TestStateRoundTrip / TestPlanRoundTrip / TestControlRoundTripAndDelete / TestAuditAppend / TestSidecarRoundTrip / TestResumeContinuationPoint / TestWorktreePaths | 単体 | JSON ラウンドトリップ・追記ログ・再開継続点・worktree パス | 要件16, 12-4 |
| archive_test.go::TestArchiveRun_MovesNotDeletes / _NoState / TestCountUndone | 単体 | 片付けは削除でなく退避 | 要件16-1 |
| worker_stream_test.go::TestParseWorkerResult*（StreamJSON/Bare/RealSample） / TestParseCompletionVerdict | 単体 | stream-json 結果解析・完了検証パース | 要件14, 18-2 |
| streamlog_test.go::TestFormatStreamLine / TestStreamPrettyWriter_SplitsAndBuffersPartialLines | 単体 | ログ整形・部分行バッファ | 要件14-2 |
| session_test.go::TestNormalizeCName / TestSessionNames / TestSplitTarget / TestExpectedWindows / TestNewSessionManager_UsesComposeProjectName | 単体 | セッション命名・ウィンドウターゲット・復旧対象算出 | 要件13-2, 14-2 |
| mode_test.go::TestWriteLaunchScript / _NoPromptOmitsPositional / TestShellSingleQuote | 単体 | launch script 生成（model/effort・quoting・sidecar） | 要件13-3, 18-1 |
| dashtui_test.go::TestDashView_RendersTasksAndCursor / TestDashCursor_MovesAndClamps / TestDashEnter_OnWaitingHumanSendsResolve / TestDashQuit_SendsQuit / TestDashView_BrainstormingIsCursorSelect | 単体 | カーソル選択・Enter 移動・⏸ で resolve・q で中断・ホーム描画 | 要件19-1 |
| dashboard_test.go::TestReadVMHealthBanner_*（WarnFresh/OKIsSilent/StaleIgnored/NonVMMode） | 単体 | VM 資源逼迫バナー | 要件（可観測性・VMモード） |
| term_test.go::TestResolveMenu_*（EnterPicksDefault/ArrowThenEnter/JKMovement/NumberImmediate/NoInputReturnsCurrent） / TestSelectMenu_NonTTYReturnsDefault / TestTerminalConfirm_NonTTYContinue / TestBuildQuestion_NumbersOptions | 単体 | 選択メニュー・非 TTY 既定・質問の番号付き整形 | 要件19-1, 19-2, 19-3 |
| policy_test.go::TestLoadProjectPolicy_* / TestBuildPrompt_* / TestBuildReviewPrompt_* / TestModeArgs_* / TestVMModePreamble_* | 単体 | ORCHESTRATOR.md 前置・VM 前置の各プロンプトへの反映 | 要件19-5 |
| handoff_test.go::TestWaitConsume_ReturnsWhenControlAppears / _UntilEndsWithoutControl | 単体 | control.json 出現検知・until 終了 | 契約: 対話Claude→orchestrator |
| controller_test.go::TestFreshDispatch_NewSession / TestResolveOne | 単体 | 新 Attempt の新規セッション・介入 1 件解決 | 要件16-5, 15-3 |

**cli(orchestrate)→orchestrator 契約**（生存判定による attach/resume 分岐・設定受け渡し）の結合テスト対象は
02-design のテスト戦略上 orchestrator 担当だが、実 tmux＋実 claude を要するため自動単体テストでは検証不能。
生存判定ロジック（`--print-main-session`・pgrep 判定）と設定受け渡しはコード実装済みで、実機（`make orch-sample`）と
E2E-4/E2E-5 で確認する（03-impl/e2e.md 側の対応表が持つ）。

実行方法: `cd orchestrator && go test -mod=vendor ./...`（[tech steering](../_steering/tech.md)。`-race` 併用可）。

## 既知の制限・技術的負債

- **本モジュールは最大モジュールであり、本 03-impl は目標語数を超える。** 詳細がさらに増える場合は、02-design/system.md
  の分割定義を /change で見直し `docs/02-design/orchestrator.md`（詳細設計）を抽出する判断を要する（system.md の注記に対応）。
- **レビュー構造化出力はスキーマ強制（tool-forced structured output）ではない。** 現状は「最終行 JSON＋寛容パース＋
  散文の再整形」で実現。tool による厳密スキーマ強制は将来強化点。
- **reviewer_vendor: codex（別ベンダーレビュー）はフェーズ2**（v1 は値を読むのみで常に Claude）。
- **Slack は一方向通知のみ**（interactive ボタン等の双方向はフェーズ2以降）。
- **完了基準未充足時の不足分自動タスク化は範囲外**（助言通知のみ・人間が判断。要件・制約に明記）。
- 条件4（方針分岐）/条件5（前提崩れ）の計画マーク/自動検出による事前検出はフェーズ2以降（v1 は worker の `NeedsHuman` 報告のみ）。

## 運用メモ

- **単一コマンド復旧:** `claude-dev orchestrate` は `claude-orchestrator` プロセス生存（`pgrep`。`has-session` ではない
  ＝`remain-on-exit on` の空き殻セッションを誤検出するため）で分岐。生存→attach、不在→空き殻を `kill-session` してから
  `new-session -d -n dashboard` で再起動（状態から resume）→不足ウィンドウ再構築→attach。
- **失われないことの担保:** ゴール/仕様＝`docs/`、運用状態＝`.orchestrator/`、実装＝worktree コミット。tmux セッション/
  クライアントは使い捨てビュー。`.orchestrator/` 配下は機械所有・人間は手編集しない（修正は対話へ誘導）。
- **端末健全化:** 対話 claude 復帰後は必ず `ttyRestoreSane()`（stty カノニカル復元）を通す（怠ると Enter が `\r` のまま
  行バッファ読取が永久ブロック）。`main.go` は経路によらず `defer ttyRestoreSane()`。
- **ビルド:** `.devcontainer/Dockerfile.claude` の `orch-builder`（golang:1.24-alpine・`-mod=vendor`）で焼き込み、
  `Makefile` の `build-orchestrator` でローカルビルド。instructions もイメージへ COPY。

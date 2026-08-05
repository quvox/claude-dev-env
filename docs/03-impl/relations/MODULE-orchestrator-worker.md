---
id: MODULE-orchestrator-worker
module: MOD-orchestrator
kind: function-call
sync: sync
impl: orchestrator/worker.go::Worker.Dispatch, orchestrator/worker.go::Worker.BuildPrompt, orchestrator/worker.go::ParseWorkerResult, orchestrator/worker.go::extractFromClaudeEnvelope, orchestrator/worker.go::resultFromStream
callers: MODULE-orchestrator-controller, MODULE-orchestrator-review
callees: MODULE-orchestrator-claude-exec, MODULE-orchestrator-state, MODULE-orchestrator-state-intervention, MODULE-orchestrator-worktree
contracts: CTR-orchestrator-prompt
design: DSN-mod-01, DSN-orch-01
requirements: FR-orch-03
tests: orchestrator/worker_stream_test.go::TestParseWorkerResultStreamJSON, orchestrator/worker_stream_test.go::TestParseWorkerResultBare, orchestrator/worker_stream_test.go::TestParseWorkerResultRealSample, orchestrator/policy_test.go::TestBuildPrompt_IncludesPolicyWhenPresent
updated: 2026-08-05
summary: タスクを worker へ割り当てて並列実行し結果を解釈する
---

# MODULE-orchestrator-worker worker ディスパッチと結果解析

## 目的

タスク1件を `claude -p` のヘッドレス実行として起動し、構造化された結果を回収する
(FR-orch-03)。worker 同士は git worktree で分離され、`max_workers` まで並列に走る。
契約 `CTR-orchestrator-prompt` の worker 側のプロンプト注入もここが実装する。

## 処理の流れ

1. `Worker.Dispatch(ctx context.Context, p *Plan, t *Task, feedback string)`
   (`orchestrator/worker.go:221`)が `MODULE-orchestrator-worktree` の `PrepareWorktree` を呼び、
   `worktrees/<taskID>/` を用意する。`p` は先行タスクの結果を引くための計画全体、`feedback` は
   差し戻し時にレビュー指摘を渡すための文字列(初回は空)。
2. `Worker.BuildPrompt(p *Plan, t *Task, feedback string)` がプロンプトを組み立てる。
   `MODULE-orchestrator-state` の `VMModePreamble` と `LoadProjectPolicy`(`ORCHESTRATOR.md`)を
   先頭へ前置し、`# Goal` / `# Completion criteria` / `# Task:` とタスクの説明、
   (非空なら)タスク固有の完了条件、(あれば)`dependencySummaries` が作る先行タスクの結果要約、
   (あれば)フィードバックを順に連ね、最後に結果スキーマの指示(`workerResultGuide`)を付す。
   **構成と省略規則の正は契約 `CTR-orchestrator-prompt`。**
3. `claude -p "<prompt>" --output-format stream-json --verbose [--model][--effort]
   [--permission-mode <mode>] [--session-id|--resume]` を worktree を CWD にして起動する。
   model / effort は `workerTaskProfile(t)` が `Task.Kind` から選ぶ。`--permission-mode` の既定は
   `bypassPermissions`(ヘッドレスで権限プロンプトに答える人間がいないため明示が必須。
   **空文字ならフラグを付けない**)。
4. 出力は `io.MultiWriter` で二手に流す: (a) 生の stream-json バッファ(解析用)、
   (b) `MODULE-orchestrator-claude-exec` 経由の整形ライタ(`workers/<taskID>.log` へ)。
5. `ParseWorkerResult` が結果を解釈する。stream-json の最終 `result`(`resultFromStream`)→
   single envelope(`extractFromClaudeEnvelope`)→ 生の出力全体 の順に試し、いずれも
   `findWorkerResultJSON` で**末尾から**「`{` で始まり `}` で終わり `"done"` を含む1行」を探す。
6. **`Usage` が非 `null` のときだけ**監査レコードを `audit.jsonl` へ追記する
   (`orchestrator/worker.go:240` の `AppendAudit`)。**`Assumptions` をこの機能は書かない** —
   戻り値として controller へ返し、`assumptions.jsonl` への追記は controller が行う
   (`orchestrator/controller.go:637` の `AppendAssumption`)。`NeedsHuman` も同様に controller が
   `MODULE-orchestrator-trigger` に渡す。
7. **セッション継続**: セッション ID は**この機能ではなく controller が dispatch の直前に
   `newSessionID()`(RFC 4122 v4)で採番**し、`Task.SessionID` に保存して渡す。
   新しい Attempt では新しい ID を発行して `--session-id` で渡し、中断からの再開
   (`ResumeSession` が真)では**同じ ID を `--resume` で渡し Attempts を増やさない**。
   再開印は dispatch の直前に消費されるため、**その試行が失敗した場合の再試行は新しい
   Attempt・新しいセッション ID で始まる**。

## 呼び出され方

- 契機: `MODULE-orchestrator-controller` が ready タスクを起動するとき、および
  `MODULE-orchestrator-review` が revise(差し戻し)を走らせるとき。
- 前提条件: worktree が用意でき、`claude` が PATH 上にあること。
- 引数(実シグネチャは `Worker.Dispatch(ctx context.Context, p *Plan, t *Task, feedback string)`。
  `orchestrator/worker.go:221`):

| 引数 | 型 | 必須 | 制約 | 実装が行う検証 |
|---|---|---|---|---|
| `ctx` | `context.Context` | 必須 | 中断時にキャンセルされる。キャンセルは `RunOpts.GraceSeconds` の猶予つきで子プロセスへ伝わる | **検証しない**(プロセス内呼び出し) |
| `p` | `*Plan` | 必須 | **plan 全体を受け取る**。`Goal` と `Completion` をプロンプトの文脈に使い、`Tasks` は完了済み依存タスクの要約(`dependencySummaries`)を組むために走査する | 検証しない。`nil` は想定していない |
| `t` | `*Task` | 必須 | `ID` / `Description` / `Completion` / `Kind` / `SessionID` / `ResumeSession` / `Attempts` を参照する | 検証しない。`ID` はそのまま worktree 名とログのパス要素になる(`docs/issues/011`) |
| `feedback` | 文字列 | 任意(空文字可) | 直前の Attempt からの差し戻し内容。**呼び出し契約の一部**であり、レビュアの重大指摘がここを通って worker へ戻る | 空文字なら該当見出しを出さない(`BuildPrompt`) |

- **呼び出し元は plan のスナップショットを渡す**: `controller.go:596`(`snapshotPlan`)が `planMu` の下で
  深いコピーを作り、`Dispatch` はロックの外で走る。したがって `Dispatch` が受け取る `p` / `t` は
  **live な plan ではない**(並行 worker の書き込みと競合しない)。
- 認可: プロセス内呼び出し。worker には後戻り不可の操作(push / deploy / 削除)と
  `SLACK_BOT_TOKEN` を渡さない。

## 連携先と連携内容

### MODULE-orchestrator-claude-exec

- 何のために呼ぶか: worker 本体である `claude -p` の子プロセスを起動するため
  (`orchestrator/worker.go:231`)。**インターフェース `ClaudeRunner`
  (`orchestrator/worker.go:47`〜`:52`)越しの呼び出し**なので、静的コールグラフには呼び出し辺が
  出ない(実体は `orchestrator/worker.go:350` の `ExecClaude.RunPrompt`)。
- 何を渡すか: worktree の絶対パス(CWD になる)・`workerTaskProfile(t)` が選んだモデル・
  `BuildPrompt` が組んだプロンプト・ログのパス(`workers/<taskID>.log`)・
  `RunOpts{SessionID, Resume, GraceSeconds, Effort}`。**セッション ID の採番は controller の責務**
  であり、この機能は `Task.SessionID` をそのまま渡す。 / 何を受け取るか: **生の stream-json
  バイト列**(`[]byte`)とエラー。ログのパスが非空のときは、同じ出力が
  `orchestrator/streamlog.go` の整形ライタ経由でそのファイルにも書かれる
  (`io.MultiWriter`。`orchestrator/worker.go:396`〜`:398`)。この整形は
  `MODULE-orchestrator-claude-exec` の内部で行われ、この機能は関与しない。
- **失敗したときどうなるか**: `Dispatch` は `(nil, err)` を返して即座に戻る(結果の解析は行わない)。
  呼び出し元の `MODULE-orchestrator-controller` が `Attempts++` して再試行し、`stuck_limit` を
  超えると条件3のトリガーが発火して `waiting_human` になる。中断時は `GraceSeconds` の猶予つきで
  SIGINT が子プロセスへ伝わる。

### MODULE-orchestrator-worktree

- 何のために呼ぶか: タスク専用の作業コピーを用意するため(`Worker.PrepareWorktree`。
  `orchestrator/worker.go:222` から呼ぶ)。 / 何を渡すか: `ctx` と `*Task`。
- 何を受け取るか: **`error` だけである**(`func (w *Worker) PrepareWorktree(ctx, t) error`。
  `orchestrator/worker.go:114`)。**作った worktree の相対パスは戻り値ではなく `t.Worktree` への
  代入という副作用で渡る**ので、`Dispatch` は CWD を得るために別途
  `MODULE-orchestrator-state` の `Store.WorktreeAbs(t.ID)` を呼ぶ(`:226`)。
- **失敗したときどうなるか**: エラーを返し、タスクは実行されずに再試行対象になる。

### MODULE-orchestrator-state

- 何のために呼ぶか: `ORCHESTRATOR.md` と VM 前置文の取得、worktree の絶対パスと
  ログ出力先の解決。
- 何を渡すか: `Store.WorktreeAbs` / `Store.WorkerLogPath` にはタスク ID(`:226`・`:227`)、
  `LoadProjectPolicy` には**ワークスペースのパス `w.Workspace`**(`:173`)。
  **`VMModePreamble` は引数を取らず、環境変数 `CLAUDE_DEV_VM` を自分で読む**(`:172`)。
   / 何を受け取るか: 前置文と、worktree の絶対パス・ログのパス。
- **失敗したときどうなるか**: 前置なしで続行する。ログ先が作れない場合は整形出力が失われる
  (`os.Create` の失敗は握りつぶされ、生の出力だけがバッファに残る)。

### MODULE-orchestrator-state-intervention

- 何のために呼ぶか: `Usage` を含む監査レコードを `audit.jsonl` へ追記するため
  (`assumptions.jsonl` への追記は controller の責務であり、この機能は行わない)。
- 何を渡すか: 記録するレコード。 / 何を受け取るか: エラー。
- **失敗したときどうなるか**: ログが欠落するだけで実行は止めない。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | `WorkerResult{Done, Summary, Changes[], NeedsHuman, Assumptions[], Usage}` とエラー |
| 永続化 | `workers/<taskID>.log`(整形済みライブログ)、`audit.jsonl`、worktree 内の git コミット(worker が意味のある区切りで逐次コミットする)。**`assumptions.jsonl` は controller が書く**(この機能は `Assumptions` を戻り値で返すだけ) |
| 発火するイベント | なし(Slack 通知は controller に一本化してある) |
| ログ | `workers/<taskID>.log` |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| `claude` プロセスがクラッシュ / 非0終了 | エラーを返す。controller が `dispatch_error` を記録し `Attempts++` して再試行する | 上限超過で条件3のトリガーが発火する |
| 結果 JSON が解析できない | stream-json の最終 result → envelope → 生出力 の順に試し、いずれも失敗ならエラーを返す(**推測で補完しない**) | controller が再試行する |
| 結果 JSON に `"done"` を含む行が無い | 上と同じ扱い(`"done"` の有無が結果行の判定条件) | 同上 |
| **`--resume` が失敗する** | **専用のフォールバックは無い。** 通常の dispatch 失敗として扱われ、次の Attempt が新しいセッション ID で始まる(文脈は失われる) | Attempt を1つ消費する |
| worker が `NeedsHuman` を返す | 結果に載せて controller へ返す(**`reason` の値は検証しない**) | controller が trigger 経由で `waiting_human` にする |
| worktree を用意できない | `worktree: <原因>` を包んだエラーを返し、`claude` を起動しない | controller が再試行する |
| 中断(ctx キャンセル) | `worker_grace_seconds` の猶予後に停止する。controller は `resetToPending` でタスクを `pending` に戻し、**セッション ID を保って再開印を立てる** | 中間コミットは残り、再開は同じ Attempt の続きになる |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | `--permission-mode bypassPermissions` を既定にする(ヘッドレスでは権限プロンプトに答える人間がいないため) | D0-orch-02 |
| 2 | worktree への取り込み(統合)は worker ではなく controller が直列に行う(並列マージの競合を避ける) | D0-orch-04 |
| 3 | worker に `SLACK_BOT_TOKEN` を渡さない(通知の発信源をコントローラに一本化する) | D0-sec-03 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 結果の構造化はスキーマ強制ではない(最終行 JSON + 寛容パース) | 形式崩れの回収に再試行を要する | なし |

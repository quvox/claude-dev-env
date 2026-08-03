---
target: docs/03-impl/relations/MODULE-orchestrator-worker.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
id: MODULE-orchestrator-worker
module: MOD-orchestrator
kind: function-call
sync: sync
impl: orchestrator/worker.go::Worker.Dispatch, orchestrator/worker.go::Worker.BuildPrompt, orchestrator/worker.go::ParseWorkerResult, orchestrator/worker.go::extractFromClaudeEnvelope, orchestrator/worker.go::resultFromStream
callers: MODULE-orchestrator-controller, MODULE-orchestrator-review
callees: MODULE-orchestrator-state, MODULE-orchestrator-state-intervention, MODULE-orchestrator-worktree
contracts: CTR-orchestrator-prompt
design: DSN-mod-01, DSN-orch-01
requirements: FR-orch-03
tests: orchestrator/worker_stream_test.go::TestParseWorkerResult_StreamJSON, orchestrator/worker_stream_test.go::TestParseWorkerResult_Bare, orchestrator/worker_stream_test.go::TestParseWorkerResult_RealSample, orchestrator/policy_test.go::TestBuildPrompt_IncludesPolicy
updated: 2026-08-02
summary: タスクを worker へ割り当てて並列実行し結果を解釈する
---

# MODULE-orchestrator-worker worker ディスパッチと結果解析

## 目的

タスク1件を `claude -p` のヘッドレス実行として起動し、構造化された結果を回収する
(FR-orch-03)。worker 同士は git worktree で分離され、`max_workers` まで並列に走る。
契約 `CTR-orchestrator-prompt` の worker 側のプロンプト注入もここが実装する。

## 処理の流れ

1. `Worker.Dispatch(ctx, task)` が `MODULE-orchestrator-worktree` の `PrepareWorktree` を呼び、
   `worktrees/<taskID>/` を用意する。
2. `Worker.BuildPrompt(task)` がプロンプトを組み立てる。`Task.Description` に、状態ストアからの
   必要文脈(関連ドキュメント・先行タスクの結果サマリ・制約)を加え、
   `MODULE-orchestrator-state` の `LoadProjectPolicy`(`ORCHESTRATOR.md`)と `VMModePreamble` を
   先頭へ前置する。
3. `claude -p "<prompt>" --output-format stream-json --verbose [--model][--effort]
   --permission-mode <mode> [--session-id|--resume]` を worktree を CWD にして起動する。
   model / effort は `workerTaskProfile(t)` が `Task.Kind` から選ぶ。`--permission-mode` の既定は
   `bypassPermissions`(ヘッドレスで権限プロンプトに答える人間がいないため明示が必須)。
4. 出力は `io.MultiWriter` で二手に流す: (a) 生の stream-json バッファ(解析用)、
   (b) `MODULE-orchestrator-claude-exec` 経由の整形ライタ(`workers/<taskID>.log` へ)。
5. `ParseWorkerResult` が結果を解釈する。stream-json の最終 `result` → single envelope
   (`extractFromClaudeEnvelope`)→ bare JSON の順に内側の JSON をデコードする
   (`resultFromStream`)。
6. `Usage` を `audit.jsonl` へ、`Assumptions` を `assumptions.jsonl` へ追記する
   (`MODULE-orchestrator-state-intervention`)。`NeedsHuman` は controller が
   `MODULE-orchestrator-trigger` に渡す。
7. **セッション継続**: 最初の `system` / `init` イベントから `session_id` を捕まえ `Task.SessionID`
   に保存する。同じ Attempt の再開は `--resume`、別アプローチ(新しい Attempt)は `SessionID` を
   空へ戻す。`--resume` に失敗したら新規セッションへフォールバックし、その旨を audit に残す。

## 呼び出され方

- 契機: `MODULE-orchestrator-controller` が ready タスクを起動するとき、および
  `MODULE-orchestrator-review` が revise / レビュアを走らせるとき。
- 前提条件: worktree が用意でき、`claude` が PATH 上にあること。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `task` | `*Task` | 必須 | `Description` / `Completion` / `Kind` / `SessionID` を参照する |
| `ctx` | `context.Context` | 必須 | 中断時にキャンセルされる |

- 認可: プロセス内呼び出し。worker には後戻り不可の操作(push / deploy / 削除)と
  `SLACK_BOT_TOKEN` を渡さない。

## 連携先と連携内容

### MODULE-orchestrator-worktree

- 何のために呼ぶか: タスク専用の作業コピーを用意するため。 / 何を渡すか: タスク ID。
- 何を受け取るか: worktree のパス。
- **失敗したときどうなるか**: エラーを返し、タスクは実行されずに再試行対象になる。

### MODULE-orchestrator-state

- 何のために呼ぶか: `ORCHESTRATOR.md` と VM 前置文の取得、`WorkerLogPath` によるログ出力先の解決。
- 何を渡すか: タスク ID。 / 何を受け取るか: 前置文とログのパス。
- **失敗したときどうなるか**: 前置なしで続行する。ログ先が作れない場合は整形出力が失われる。

### MODULE-orchestrator-state-intervention

- 何のために呼ぶか: `Usage` を `audit.jsonl` へ、`Assumptions` を `assumptions.jsonl` へ追記するため。
- 何を渡すか: 記録するレコード。 / 何を受け取るか: エラー。
- **失敗したときどうなるか**: ログが欠落するだけで実行は止めない。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | `WorkerResult{Done, Summary, Changes[], NeedsHuman, Assumptions[], Usage}` とエラー |
| 永続化 | `workers/<taskID>.log`(整形済みライブログ)、`audit.jsonl`、`assumptions.jsonl`、worktree 内の git コミット(worker が意味のある区切りで逐次コミットする) |
| 発火するイベント | なし(Slack 通知は controller に一本化してある) |
| ログ | `workers/<taskID>.log` |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| `claude` プロセスがクラッシュ / タイムアウト | エラーを返す。controller が `Attempts++` して再試行する | 上限超過で条件3のトリガーが発火する |
| 結果 JSON が解析できない | stream-json の最終 result → envelope → bare の順に試し、いずれも失敗ならエラーを返す | controller が再試行する |
| `--resume` が失敗する | 新規セッションへフォールバックし、その旨を audit に残す | 文脈は失われるが実行は続く |
| worker が `NeedsHuman` を返す | 結果に載せて controller へ返す | controller が trigger 経由で `waiting_human` にする |
| 中断(ctx キャンセル) | `worker_grace_seconds` の猶予後に停止する | 中間コミットは残る |

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

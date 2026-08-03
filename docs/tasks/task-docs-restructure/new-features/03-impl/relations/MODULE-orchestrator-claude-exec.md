---
target: docs/03-impl/relations/MODULE-orchestrator-claude-exec.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
id: MODULE-orchestrator-claude-exec
module: MOD-orchestrator
kind: function-call
sync: sync
impl: orchestrator/worker.go::ExecClaude.RunPrompt, orchestrator/claudebin.go::claudeChildEnv, orchestrator/claudebin.go::claudePath, orchestrator/claudebin.go::localBinDir
callers: MODULE-orchestrator-controller, MODULE-orchestrator-mode
callees: MODULE-orchestrator-streamlog
contracts: CTR-orchestrator-prompt
design: DSN-mod-01, DSN-orch-01
requirements: FR-orch-03, FR-orch-07
tests: なし(未実装。claudebin.go に対応する単体テストが無く、E2E-4 の実機確認で代替する)
updated: 2026-08-02
summary: Claude CLI を子プロセスとして起動し環境と PATH を整える
---

# MODULE-orchestrator-claude-exec claude 子プロセスの起動

## 目的

`claude` をヘッドレスで安全に起動する経路を1か所に閉じる(FR-orch-03)。実行ファイルの解決と、
子プロセスへ渡す環境の取捨(とくに `SLACK_BOT_TOKEN` の除去。FR-orch-07)がここの責務である。

## 処理の流れ

1. `localBinDir()` が `$HOME/.local/bin` を返す。
2. `claudePath()` が `exec.LookPath("claude")` を試し、見つからなければ
   `$HOME/.local/bin/claude` を絶対パスとして返す。
3. `claudeChildEnv()` が子プロセスの環境を作る。PATH に `localBinDir()` を補い、
   **`SLACK_BOT_TOKEN` を取り除く**(通知の発信源をコントローラに一本化するため)。
4. `ExecClaude.RunPrompt(ctx, args, out)` が `claude` を起動し、標準出力を呼び出し元の
   `io.Writer` へ流す。整形表示が要る場合は `MODULE-orchestrator-streamlog` の
   `newStreamPrettyWriter` を通す。

## 呼び出され方

- 契機: `MODULE-orchestrator-worker` がタスクを実行するとき、`MODULE-orchestrator-review` が
  レビュアを走らせるとき、`MODULE-orchestrator-controller` が完了検証を行うとき、
  `MODULE-orchestrator-mode` が launch script を組み立てるとき。
- 前提条件: `claude` がイメージに同梱されていること。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `args` | 文字列の並び | 必須 | `claude` へ渡す引数(`-p` / `--output-format` / `--model` など) |
| `out` | `io.Writer` | 必須 | 標準出力の流し先 |
| `ctx` | `context.Context` | 必須 | 中断時にキャンセルされる |

- 認可: プロセス内呼び出し。

## 連携先と連携内容

### MODULE-orchestrator-streamlog

- 何のために呼ぶか: stream-json の出力を人が読める形に整形して `workers/<taskID>.log` へ書くため
  (`newStreamPrettyWriter`)。
- 何を渡すか: 出力先の `io.Writer`。 / 何を受け取るか: 整形ライタ。
- **失敗したときどうなるか**: 整形に失敗しても解析用の生バッファは別系統(`io.MultiWriter`)なので、
  結果の解釈には影響しない。ログの見た目が崩れるだけ。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 子プロセスの終了状態とエラー |
| 永続化 | なし(ログの書き出し先は呼び出し元が指定する) |
| 発火するイベント | なし |
| ログ | 呼び出し元が渡した `io.Writer`(通常は `workers/<taskID>.log`) |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| `claude` が PATH に無い | `claudePath` が `$HOME/.local/bin/claude` を返す。それも無ければ起動時に「実行ファイルが無い」で失敗する | worker は再試行対象になる |
| 子プロセスが非0で終了 | エラーを返す | controller が `Attempts++` して再試行する |
| ctx がキャンセルされた | 子プロセスを止める(`worker_grace_seconds` の猶予は呼び出し元が与える) | 中間コミットは残る |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 子プロセス環境から `SLACK_BOT_TOKEN` を除去する(worker と対話 claude に通知手段を持たせない) | D0-sec-03 |
| 2 | `claude` を絶対パスで解決する(tmux 経由の非対話シェルで PATH が細ることがあるため) | D0-orch-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| `ExecClaude.RunPrompt` の `cmd.Run()`(worker.go:403)が、静的解析では `Controller.Run` / `SessionManager.Run` への候補辺として現れる | 実在しない候補辺。標準ライブラリの `*exec.Cmd.Run` であり**棄却した** | なし |
| 単体テストが無い | 回帰検出は E2E-4 の実機確認に依存する | なし |

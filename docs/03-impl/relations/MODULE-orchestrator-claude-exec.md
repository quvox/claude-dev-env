---
id: MODULE-orchestrator-claude-exec
module: MOD-orchestrator
kind: function-call
sync: sync
impl: orchestrator/worker.go::ExecClaude.RunPrompt, orchestrator/claudebin.go::claudeChildEnv, orchestrator/claudebin.go::claudePath, orchestrator/claudebin.go::localBinDir
callers: MODULE-orchestrator-controller, MODULE-orchestrator-mode, MODULE-orchestrator-review, MODULE-orchestrator-worker
callees: MODULE-orchestrator-streamlog
contracts: CTR-orchestrator-prompt
design: DSN-mod-01, DSN-orch-01
requirements: FR-orch-03, FR-orch-07
tests: なし(未実装。claudebin.go に対応する単体テストが無く、E2E-04 の実機確認で代替する)
updated: 2026-08-05
summary: Claude CLI を子プロセスとして起動し環境と PATH を整える
---

# MODULE-orchestrator-claude-exec claude 子プロセスの起動

## 目的

`claude` をヘッドレスで起動する経路を1か所に閉じ、**通知トークンを子プロセスへ渡さない**ことを保証する(FR-orch-03)。実行ファイルの解決と、
子プロセスへ渡す環境の取捨(とくに `SLACK_BOT_TOKEN` の除去。FR-orch-07)がここの責務である。

## 処理の流れ

1. `localBinDir()` が `$HOME/.local/bin` を返す(ホームが解決できなければ空文字)。
2. `claudePath()` が `exec.LookPath("claude")` → `$HOME/.local/bin/claude`(ディレクトリでない
   ことを確認)→ **最後の手段として文字列 `"claude"`** の順で解決する
   (最後の場合、`exec` が「実行ファイルが無い」という明示的なエラーを出す)。
3. `claudeChildEnv()` が子プロセスの環境を作る。現在の環境から **`SLACK_BOT_TOKEN` を取り除き**
   (通知の発信源をコントローラに一本化するため)、PATH の先頭に `localBinDir()` を補う
   (既に含まれていれば何もしない)。
4. `ExecClaude.RunPrompt(ctx, dir, model, prompt, logPath string, opts RunOpts) ([]byte, error)` が
   `claude` を起動する。
   - 引数は常に `-p <prompt> --output-format stream-json --verbose`。`model` / `opts.Effort` /
     セッション指定(`opts.SessionID` / `opts.Resume`)は**非空のときだけ**足す。
     `--permission-mode` は**引数ではなく設定** `worker_permission_mode`(`CTR-cli-orchestrator`)から採り、
     **空文字ならフラグ自体を付けない**。`RunOpts` に権限モードのフィールドは無い。
   - 作業ディレクトリを `dir` に、環境を `claudeChildEnv()` にする。
   - `opts.GraceSeconds > 0` のとき、ctx キャンセル時に **`SIGINT` を送り**、その秒数まで
     待ってから強制終了する。
   - **生の stream-json をメモリ上のバッファへ集める**(戻り値。`ParseWorkerResult` 用)。
     `logPath` が非空なら同じ出力を `MODULE-orchestrator-streamlog` の整形ライタ経由で
     ログファイルへも流す(`io.MultiWriter`)。**ログファイルは毎回切り詰めて作り直す。**
   - 標準出力と標準エラーを**同じ流し先**にまとめる。
5. 子プロセスの終了を待ち、**バッファの内容とエラーの両方を返す**(エラーでも出力は返る)。

**この機能はタイムアウトを持たない。** 実行時間の上限は呼び出し側が渡す ctx にのみ依存し、
**再試行もバックオフも行わない**(再試行は `MODULE-orchestrator-controller` の Attempt 管理が担う)。

## 呼び出され方

- 契機: `MODULE-orchestrator-worker` がタスクを実行するとき、`MODULE-orchestrator-review` が
  レビュアを走らせるとき、`MODULE-orchestrator-controller` が完了検証を行うとき、
  `MODULE-orchestrator-mode` が launch script を組み立てるとき。
- 前提条件: `claude` がイメージに同梱されていること。
- 引数:

| 引数 | 型 | 必須 | 制約 | 実装が行う検証 |
|---|---|---|---|---|
| `ctx` | `context.Context` | 必須 | 中断時にキャンセルされる。**唯一の実行時間の制御手段** | **検証しない**(プロセス内呼び出し)。空文字の引数は対応するフラグを付けないという意味になる |
| `dir` | パス文字列 | 必須 | 子プロセスの作業ディレクトリ(タスクの worktree) | 同上 |
| `model` | 文字列 | 任意 | 空なら `--model` を付けない。値の妥当性は検証しない | 同上 |
| `prompt` | 文字列 | 必須 | `-p` の値。**長さの上限を課さない** | 同上 |
| `logPath` | パス文字列 | 任意 | 空ならログファイルを作らない。作成に失敗しても実行は続ける | 同上 |
| `opts.SessionID` / `opts.Resume` | 文字列 / 真偽 | 任意 | 空なら両フラグとも付けない。`Resume` が真なら `--resume`、偽なら `--session-id` | 同上 |
| `opts.GraceSeconds` | 整数 | 任意 | **0 以下なら猶予なし**(既定の強制終了) | 同上 |
| `opts.Effort` | 文字列 | 任意 | 空なら `--effort` を付けない。値の妥当性は検証しない | 同上 |

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
| 戻り値 | `([]byte, error)`。第1返値は**子プロセスの標準出力と標準エラーを混ぜて捕捉したバイト列**で、非0終了・中断のときも**それまでの出力をそのまま返す**(空にしない)。第2返値は起動失敗・非0終了・中断のエラーで、**終了コードの区別を持たない**(`*exec.ExitError` のまま)。終了状態そのものは返さない |
| 永続化 | なし(ログの書き出し先は呼び出し元が指定する) |
| 発火するイベント | なし |
| ログ | 呼び出し元が渡した**パス** `logPath`(通常は `workers/<taskID>.log`)。`io.Writer` は受け取らない。非空のときだけ作成し、**毎回切り詰めて作り直す**。作成に失敗しても実行は続き、整形ログが無いだけになる(失敗自体はどこにも表示しない) |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| `claude` が PATH にも `$HOME/.local/bin` にも無い | `claudePath` が文字列 `"claude"` を返し、起動時に「実行ファイルが無い」エラーになる | worker は再試行対象になる(Attempt を消費する) |
| **子プロセスが非0で終了した** | **エラーと、それまでの出力の両方を返す**。エラーは終了コードの区別を持たない(`*exec.ExitError` のまま) | 呼び出し元は結果を解釈せず失敗として扱う |
| **ctx がキャンセルされた(中断)** | `GraceSeconds > 0` なら `SIGINT` → 猶予後に強制終了。0 なら即座に強制終了。**エラーとして返る** | 呼び出し元は `ctx.Err()` を見て「中断」と「実行失敗」を区別する |
| **応答が返らない(ハング)** | **この機能は検出しない。** ctx がキャンセルされるまで待ち続ける | run は進まない。人間が `[q]` で止める |
| **ストリームが途中で切れた / 壊れた JSON が混ざった** | ここでは検出しない(バイト列をそのまま返す)。判定は `ParseWorkerResult` が行い、解釈できなければ失敗として扱う | `MODULE-orchestrator-worker` の異常系に従う |
| ログファイルを作れない | **エラーにせず**、整形ログ無しで実行する(解析用のバッファは無関係) | 表示が減るだけ |
| 標準エラーへの出力 | 標準出力と同じ流し先へ混ざる | 解析側は「`done` を含む1行の JSON」を探すため、通常は影響しない |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 子プロセス環境から `SLACK_BOT_TOKEN` を除去する(worker と対話 claude に通知手段を持たせない) | D0-sec-03 |
| 2 | `claude` を絶対パスで解決する(tmux 経由の非対話シェルで PATH が細ることがあるため) | D0-orch-02 |
| 3 | 中断時に `SIGKILL` ではなく `SIGINT` を送る(worker が作業中コミットを残せるようにする) | D0-orch-04 |
| 4 | タイムアウトを内部に持たず ctx に委ねる(工程ごとに妥当な上限が違い、ここで一律に決められないため) | D0-orch-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| `ExecClaude.RunPrompt` の `cmd.Run()`(worker.go:403)が、静的解析では `Controller.Run` / `SessionManager.Run` への候補辺として現れる | 実在しない候補辺。標準ライブラリの `*exec.Cmd.Run` であり**棄却した** | なし(閾値の外: 誤検出であり実装の欠陥ではない) |
| 単体テストが無い | 回帰検出は E2E-04 の実機確認に依存する | なし(閾値の外: テストの不足は `03-impl/tests/` の「未検証」で追跡する) |
| **実行時間の上限が無い**(ctx 任せ) | 応答が返らない子プロセスがあると、そのタスクは人間が止めるまで滞留する | なし(閾値の外: 滞留はダッシュボードに `running` として表示される=**気づける**) |
| 出力を**全量メモリに保持する** | 極端に長い出力でメモリを消費する(上限も切り詰めも無い) | なし(閾値の外: 観測可能な被害の実例が無い(出力長の上限に達した事例は未観測)) |
| 終了コードを区別しない | 「モデル側のエラー」と「起動失敗」と「中断」を、`ctx.Err()` 以外の手掛かりで分けられない | なし(閾値の外: 失敗そのものは監査ログの `dispatch_error` に残る=**気づける**) |

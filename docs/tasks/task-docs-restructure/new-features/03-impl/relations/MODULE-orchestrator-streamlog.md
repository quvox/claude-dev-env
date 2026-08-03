---
target: docs/03-impl/relations/MODULE-orchestrator-streamlog.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
id: MODULE-orchestrator-streamlog
module: MOD-orchestrator
kind: function-call
sync: sync
impl: orchestrator/streamlog.go::newStreamPrettyWriter, orchestrator/streamlog.go::streamPrettyWriter.Write
callers: MODULE-orchestrator-claude-exec
callees: なし
contracts: なし
design: DSN-mod-01, DSN-ui-01
requirements: FR-orch-08
tests: orchestrator/streamlog_test.go::TestFormatStreamLine, orchestrator/streamlog_test.go::TestStreamPrettyWriter_SplitsAndBuffersPartialLines
updated: 2026-08-02
summary: Claude の stream-json 出力を人が読める形へ整形する
---

# MODULE-orchestrator-streamlog stream-json のログ整形

## 目的

worker のログを人間が追えるようにする(FR-orch-08)。`--output-format stream-json` の生出力は
そのままでは読めないため、Claude Code の画面に近い形へ整形して書き出す。
**表示専用であり、結果の解析には一切関与しない**。

## 処理の流れ

1. `newStreamPrettyWriter(out)` が `io.Writer` をラップした整形ライタを作る。
2. `streamPrettyWriter.Write(p)` が受け取ったバイト列を改行で区切って処理する。
   行が途中で切れている場合は内部バッファに溜め、次の `Write` で続きを結合する。
3. 完成した1行ごとに `formatStreamLine` が種別で整形する:
   assistant の text はそのまま、`tool_use` は `⏺ 名前(要約)`、`tool_result` は `⎿ …`、
   `result` は区切り線と完了表示。未知の種別はそのまま出す。
4. 整形結果をラップした `io.Writer` へ書く。

## 呼び出され方

- 契機: `MODULE-orchestrator-claude-exec` が `claude` の標準出力を `io.MultiWriter` で
  (a) 解析用の生バッファ と (b) この整形ライタ へ同時に流すとき。
- 前提条件: 出力先が書き込み可能であること。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `out` | `io.Writer` | 必須 | 通常は `workers/<taskID>.log` のファイルハンドル |
| `p` | `[]byte` | 必須 | 部分行を含んでよい(内部でバッファする) |

- 認可: プロセス内呼び出し。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | `io.Writer` の契約どおり書き込みバイト数とエラー |
| 永続化 | ラップした writer 越しに `workers/<taskID>.log` へ追記される。**この書式を `MODULE-orchestrator-dashboard` の tail 表示が読む** |
| 発火するイベント | なし |
| ログ | 自身がログの書き手 |

## 連携先と連携内容

連携先なし。

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 行が途中で切れて届く | 内部バッファに溜め、次の `Write` で結合して処理する | 整形が壊れない |
| JSON として解釈できない行 | そのまま出力する | ログに生の行が混じる |
| 出力先への書き込みが失敗 | エラーを返す | `io.MultiWriter` 経由なので解析用バッファへの書き込みも中断しうる |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 整形と解析を分離する(整形の失敗が結果解釈に影響しないようにする) | D0-orch-06 |
| 2 | 未知の種別は落とさずそのまま出す(情報を減らさない) | D0-orch-06 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 整形結果は機械可読ではない | ログから結果を再解析することはできない(解析は生 stream-json 側で行う) | なし |

---
target: docs/03-impl/relations/MODULE-orchestrator-slack.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
id: MODULE-orchestrator-slack
module: MOD-orchestrator
kind: function-call
sync: sync
impl: orchestrator/slack.go::NewSlackNotifier, orchestrator/slack.go::SlackNotifier.Notify, orchestrator/slack.go::NopNotifier.Notify
callers: MODULE-orchestrator-main
callees: なし
contracts: なし
design: DSN-mod-01, DSN-orch-01
requirements: FR-orch-07
tests: なし(未実装。slack.go に対応する単体テストが無い)
updated: 2026-08-02
summary: 節目の出来事を Slack へ通知する(未設定時は無通知)
---

# MODULE-orchestrator-slack Slack 通知

## 目的

人間がずっと画面を見ていなくても、判断待ちと完了に気づけるようにする(FR-orch-07)。
通知の発信源は**コントローラに一本化**してあり、worker と対話 claude には
`SLACK_BOT_TOKEN` を渡さない。

## 処理の流れ

1. `NewSlackNotifier()` が `SLACK_BOT_TOKEN` と `SLACK_CHANNEL` を読む。
   トークンが未設定なら `NopNotifier`(何もしない実装)を返す。
2. `SlackNotifier.Notify(text)` が `net/http` で
   `https://slack.com/api/chat.postMessage` へ JSON を POST する
   (`Authorization: Bearer $SLACK_BOT_TOKEN`)。
3. 送信に失敗してもエラーを握りつぶし、ログに残すだけで実行は続ける。
4. `NopNotifier.Notify(text)` は何もしない。

## 呼び出され方

- 契機: `MODULE-orchestrator-main` が生成し、`MODULE-orchestrator-controller` が
  サマリ更新時・判断待ちキュー投入時(件数アラート)・完了時に呼ぶ。
- 前提条件: なし(未設定でも動く)。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `text` | 文字列 | 必須 | 送信する本文 |

- 認可: プロセス内呼び出し。送信先は `SLACK_CHANNEL`。

## 連携先と連携内容

連携先なし(Slack API への HTTP POST は外部システムへの呼び出しで、機能間の辺には現れない)。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | なし(エラーは握りつぶす) |
| 永続化 | なし |
| 発火するイベント | Slack チャンネルへのメッセージ投稿 |
| ログ | 送信失敗時に標準エラーへ1行 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| `SLACK_BOT_TOKEN` が未設定 | `NopNotifier` になり何も送らない | 実行は通常どおり続く |
| ネットワーク不通 / API エラー | 握りつぶしてログに残す | 実行は続く。通知は失われる |
| `SLACK_CHANNEL` が未設定 | API がエラーを返し、握りつぶされる | 通知は届かない |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 送信失敗で run を止めない(通知は補助であり、実行の可否を左右させない) | D0-orch-07 |
| 2 | Slack SDK を使わず `net/http` で直接 POST する(vendoring する依存を増やさない) | D0-orch-02 |
| 3 | 発信源をコントローラだけにする(worker と対話 claude にはトークンを渡さない) | D0-sec-03 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 一方向の通知のみ(interactive ボタン等の双方向はフェーズ2以降) | Slack から回答はできない | なし |
| 単体テストが無い | 送信経路の回帰を機械検出できない | なし |

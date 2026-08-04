---
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
updated: 2026-08-04
summary: 節目の出来事を Slack へ通知する(未設定時は無通知)
---

# MODULE-orchestrator-slack Slack 通知

## 目的

人間がずっと画面を見ていなくても、判断待ちと完了に気づけるようにする(FR-orch-07)。
通知の発信源は**コントローラに一本化**してあり、worker と対話 claude には
`SLACK_BOT_TOKEN` を渡さない。

## 処理の流れ

1. `NewSlackNotifier(cfg Config)` が `cfg.SlackBotToken` / `cfg.SlackChannel` と、
   **タイムアウト 10 秒の HTTP クライアント**を持つ `*SlackNotifier` を返す。
   **環境変数を読むのはこの機能ではなく `MODULE-orchestrator-config` の設定読み込み**である
   (`SLACK_BOT_TOKEN` は常に環境の値、`SLACK_CHANNEL` は非空のときだけ環境の値)。
   **トークンが空でも `*SlackNotifier` を返す**(実装を差し替えない)。
2. `SlackNotifier.Notify(text)`:
   - **トークンが空なら何もせず戻る**(no-op)。
   - `{"channel": <SlackChannel>, "text": <text>}` を JSON にして
     `https://slack.com/api/chat.postMessage` へ POST する
     (`Authorization: Bearer <token>` / `Content-Type: application/json; charset=utf-8`)。
   - **呼び出しごとに 10 秒のコンテキストタイムアウト**を設ける(クライアント側の 10 秒と二重)。
   - **応答本文を読まない・解析しない。ステータスコードも見ない。**
3. 送信の**通信エラーだけ**を標準エラーへ1行(`slack: post: …`)残し、実行は続ける。
   **再試行もバックオフも行わない**(1回だけ送る)。
4. `NopNotifier.Notify(text)` は何もしない。**製品コードからは使われず、テストでのみ使う。**

## 呼び出され方

- 契機: `MODULE-orchestrator-main` が生成し、`MODULE-orchestrator-controller` が
  サマリ更新時・判断待ちキュー投入時(件数アラート)・完了時に呼ぶ。
- 前提条件: なし(未設定でも動く)。
- 引数:

| 引数 | 型 | 必須 | 制約 | 実装が行う検証 |
|---|---|---|---|---|
| `text` | 文字列 | 必須 | 送信する本文 | 呼び出し元が組み立てた文字列をそのまま送る。**長さも内容も検証しない**(Slack 側の上限超過は検出しない) |

- 認可: プロセス内呼び出し。送信先は `SLACK_CHANNEL`。

## 連携先と連携内容

連携先なし(Slack API への HTTP POST は外部システムへの呼び出しで、機能間の辺には現れない)。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | なし(エラーは握りつぶす) |
| 永続化 | なし |
| 発火するイベント | Slack チャンネルへのメッセージ投稿 |
| ログ | **通信に失敗したときだけ**標準エラーへ1行(`slack: marshal:` / `slack: new request:` / `slack: post:`)。**トークンは出さない**。送信成功・API エラーは何も出さない |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| `SLACK_BOT_TOKEN` が未設定 | `Notify` が即座に戻る(no-op)。ログも出さない | 実行は通常どおり続く。**通知が無効であることは表示されない** |
| ネットワーク不通・名前解決失敗・接続断 | 標準エラーへ1行残して握りつぶす | 実行は続く。通知は失われる |
| **10 秒以内に応答が無い** | コンテキストのタイムアウトで打ち切り、通信エラーと同じ扱い | 同上 |
| **4xx / 5xx が返った** | **検出しない**(ステータスコードを見ない)。ログも出ない | 通知が届かないのに成功と区別できない |
| **レート制限(429)** | 同上。**待ち直しも再試行もしない** | 通知が失われる |
| **Slack API が `{"ok":false,…}` を返した**(チャンネル不正・トークン失効など) | 同上。HTTP 200 で返るため通信エラーにもならない | 通知が失われる |
| `SLACK_CHANNEL` が未設定 | 既定値(`U5SJG0XEK`)が使われる。設定が空文字なら環境の段で上書きされない | 意図しない宛先に届きうる |
| 本文が Slack の上限を超える | API 側で拒否されるが**検出しない** | 通知が失われる |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 送信失敗で run を止めない(通知は補助であり、実行の可否を左右させない) | D0-orch-07 |
| 2 | Slack SDK を使わず `net/http` で直接 POST する(vendoring する依存を増やさない) | D0-orch-02 |
| 3 | 発信源をコントローラだけにする(worker と対話 claude にはトークンを渡さない) | D0-sec-03 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 一方向の通知のみ(interactive ボタン等の双方向はフェーズ2以降) | Slack から回答はできない | なし(閾値の外: **フェーズ2以降として 00 が範囲外と決めている**) |
| 単体テストが無い | 送信経路の回帰を機械検出できない | なし(閾値の外: テストの不足は `03-impl/tests/` の「未検証」で追跡する) |
| **応答を検査しないため、API レベルの失敗(4xx / 5xx / 429 / `ok:false`)を検出できない** | 通知が届いていないことに誰も気づけない。`02-design/logging.md` が求める「通知の送信失敗を WARN で出す」を、通信エラー以外では満たしていない | `docs/issues/013-modify-slack-api-level-failures-are-undetected.md` |
| 再試行もバックオフも無い | 一時的な不通で通知が失われる | `docs/issues/013-modify-slack-api-level-failures-are-undetected.md` |
| `NopNotifier` が製品コードから使われていない | 到達不能コードの疑い(テスト専用シンボル) | `docs/issues/001-modify-orchestrator-test-only-symbols.md` |

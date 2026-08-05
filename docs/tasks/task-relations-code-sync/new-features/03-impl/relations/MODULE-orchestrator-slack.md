---
target: docs/03-impl/relations/MODULE-orchestrator-slack.md
change: replace
sections:
  - "## 処理の流れ"
  - "## 既知の制限"
deletes: []
reason: 処理の流れ4 が「NopNotifier はテストでのみ使う」と書くが、テストにも参照が無く意図の記述になっている(docs/issues/038 #30)。frontmatter の callers に controller が無い(同 #11。対称性)
reflected: 2026-08-05
id: MODULE-orchestrator-slack
module: MOD-orchestrator
kind: function-call
sync: sync
impl: orchestrator/slack.go::NewSlackNotifier, orchestrator/slack.go::SlackNotifier.Notify, orchestrator/slack.go::NopNotifier.Notify
callers: MODULE-orchestrator-controller, MODULE-orchestrator-main
callees: なし
contracts: なし
design: DSN-mod-01, DSN-orch-01
requirements: FR-orch-07
tests: なし(未実装。slack.go に対応する単体テストが無い)
updated: 2026-08-05
summary: 節目の出来事を Slack へ通知する(未設定時は無通知)
---

<!-- 変更指示。反映後の最終形を書く。version / verified は持たない。
     callers に MODULE-orchestrator-controller を追加した(controller.go:323/:454/:741/:1038/:1050/
     :1053/:1090 が Notifier.Notify を呼ぶ)。対称性は controller 側の callees と対応する。 -->

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
4. `NopNotifier.Notify(text)` は何もしない。**製品コードからもテストからも参照が無い**
   (`orchestrator/slack.go:61`〜`:65` に定義があるだけで、`orchestrator/` 全体で他に出現しない)。
   通知を無効化する経路は `NopNotifier` への差し替えではなく、**トークンが空のときの手順2 の no-op**
   である(`docs/issues/001` で追跡する到達不能シンボル)。

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 一方向の通知のみ(interactive ボタン等の双方向はフェーズ2以降) | Slack から回答はできない | なし(閾値の外: **フェーズ2以降として 00 が範囲外と決めている**) |
| 単体テストが無い | 送信経路の回帰を機械検出できない | なし(閾値の外: テストの不足は `03-impl/tests/` の「未検証」で追跡する) |
| **応答を検査しないため、API レベルの失敗(4xx / 5xx / 429 / `ok:false`)を検出できない** | 通知が届いていないことに誰も気づけない。`02-design/logging.md` が求める「通知の送信失敗を WARN で出す」を、通信エラー以外では満たしていない | `docs/issues/013-modify-slack-api-level-failures-are-undetected.md` |
| 再試行もバックオフも無い | 一時的な不通で通知が失われる | `docs/issues/013-modify-slack-api-level-failures-are-undetected.md` |
| **`NopNotifier` が製品コードからもテストからも参照されていない** | 到達不能コード(`orchestrator/slack.go:61`〜`:65` に定義があるだけ)。**テスト専用シンボルでもない** | `docs/issues/001-modify-orchestrator-test-only-symbols.md` |

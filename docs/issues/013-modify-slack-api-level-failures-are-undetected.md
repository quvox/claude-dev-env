---
id: 013-modify-slack-api-level-failures-are-undetected
type: modify
severity: 中
found: 2026-08-03
found_in: task-impl-depth のドライラン パス2(コード精読。issue 004 の観点4「外部依存の失敗時の挙動」)
related: MODULE-orchestrator-slack, FR-orch-07, docs/02-design/logging.md
summary: Slack 通知が応答を検査しないため 4xx/5xx・レート制限・ok:false を検出できず、通知が届かなくても誰も気づけない
---

# 013 Slack 通知の API レベルの失敗が検出されない

## 事象

`orchestrator/slack.go::SlackNotifier.Notify` は `chat.postMessage` へ POST したあと、
**ステータスコードも応答本文も見ずに戻る**。

```go
resp, err := s.Client.Do(req)
if err != nil {
    log.Printf("slack: post: %v", err) // swallow
    return
}
defer resp.Body.Close()
// We intentionally do not parse the response; failures are non-fatal.
```

したがって次の失敗は**すべて成功と区別できない**:

| 失敗 | 検出 |
|---|---|
| 通信エラー(不通・名前解決失敗・10 秒タイムアウト) | **される**(標準エラーへ1行) |
| 4xx / 5xx | されない |
| レート制限(429) | されない |
| HTTP 200 + `{"ok":false,…}`(トークン失効・チャンネル不正・本文長超過) | されない |

再現手順:

1. `SLACK_BOT_TOKEN` に無効な値を設定して orchestrator を起動する。
2. 判断待ちが発生する状況を作る(通知が送られる契機)。
3. Slack にメッセージが届かないことを確認する。
4. 端末の標準エラーにも `.orchestrator/audit.jsonl` にも、失敗を示す記録が無いことを確認する。

また、**再試行もバックオフも無い**(1回だけ送る)。

## 影響

`FR-orch-07` は「人間が画面を見ていなくても判断待ちと完了に気づける」ことを目的とする。
API レベルの失敗が黙って捨てられると、**利用者は通知が来ないことを「まだ何も起きていない」と
誤解する**。オーケストレーターは判断待ちで停止したまま待ち続けるため、無人実行の価値が失われる。

`docs/02-design/logging.md` の「主要イベントのログ仕様」は
**「通知の送信失敗 | WARN | 失敗した旨のみ(トークンは出さない)」** を求めているが、
実装が満たしているのは通信エラーの場合だけである。

severity を「中」とした根拠: 実行そのものは壊れず、tmux のダッシュボードを見れば状態は分かる。
一方で Slack 未設定時と失敗時が同じ「無音」になるため、気づく手段が無い。

## 原因の見当

コメント(`failures are non-fatal`)から、**「通知の失敗で run を止めない」という設計判断
(`D0-orch-07`)を、「応答を検査しない」まで拡大して実装したと推測する**。止めないことと
検出しないことは別であり、`sendslackmsg.sh` の堅牢性方針(コメントに言及がある)を踏襲した
可能性もある。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| 送信失敗で run を止めるか | 止めない | `D0-orch-07`「通知は補助。実行の可否を左右させない」 | **一致** |
| 送信失敗を記録するか | 通信エラーのみ標準エラーへ1行。API レベルの失敗は無記録 | `logging.md`「通知の送信失敗 → WARN」 | **設計が正**(実装が要求を満たしていない) |

## 対処案

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | ステータスコードと `ok` フィールドを検査し、失敗なら WARN を1行出す(**再試行はしない**)。トークン・本文は出さない | `orchestrator/slack.go` のみ。`MODULE-orchestrator-slack` と `tests/orchestrator.md` の更新 |
| B | A に加えて 429 と 5xx に限り指数バックオフで数回再試行する | A + 再試行の設定値を `CTR-cli-orchestrator` に追加 |
| C | 失敗を `audit.jsonl` にも記録する(`event: notify_error`) | A + `MODULE-orchestrator-state-intervention` の追記経路 |

推奨は **A**(最小の変更で「気づけない」を解消する)。B は通知の遅延が run の進行に影響しないか
確認が要る。

## 経緯

- 2026-08-03 起票。`task-impl-depth` のフェーズ2で `MODULE-orchestrator-slack` の異常系を
  コードから書き下ろす際に発見。**本タスクではコードを変更しないため issue のみ**とし、
  事実は `MODULE-orchestrator-slack` の「異常系」「既知の制限」に記載する。

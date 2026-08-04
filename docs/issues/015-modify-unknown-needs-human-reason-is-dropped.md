---
id: 015-modify-unknown-needs-human-reason-is-dropped
type: modify
severity: 中
found: 2026-08-03
found_in: task-impl-depth のフェーズ2 ドライラン(独立レンズ=Codex の readiness 監査が契約間の矛盾として指摘し、Claude がコードで裏取り)
related: MODULE-orchestrator-trigger, MODULE-orchestrator-worker, CTR-orchestrator-prompt, FR-orch-04
summary: worker が4区分以外の理由で「人間が必要」と申告すると、介入が開かれず黙って再試行に回り、申告が失われる
---

# 015 未知の `needs_human.reason` が黙って捨てられる

## 事象

worker は結果 JSON の `needs_human.reason` に
`critical_decision` / `ambiguity` / `policy_branch` / `prerequisite_broken` のいずれかを載せる
ことになっている(プロンプト定数 `orchestrator/worker.go::workerResultGuide`)。

`orchestrator/trigger.go::Evaluate` はこの4値だけを `switch` で見る(`:76`〜`:88`)。
**4値以外のときは `fire=false` を返す**ため、`orchestrator/controller.go:644` の介入分岐に入らない。
続く `if !res.Done` の経路で行き詰まり判定に落ち、行き詰まりでなければ**タスクは通常の再試行に回る**。

`needs_human` の中身は `Task.Result` に保持されるが、**介入キュー(`intervention/open.json`)にも
`interventions.jsonl` にも入らず、Slack 通知も出ない**。ログにも「未知の理由を受け取った」旨は
残らない。

再現手順:

1. worker が `{"done":false,"needs_human":{"reason":"blocked_by_external","question":"…"}}` を返す
   状況を作る(例: プロンプト指示を無視したモデル出力、あるいは将来の理由区分を足したとき)。
2. ダッシュボードにそのタスクが `waiting_human` として現れないことを確認する。
3. `.orchestrator/intervention/open.json` と `interventions.jsonl` に該当行が無いことを確認する。
4. `stuck_limit` に達するまでタスクが再試行されることを確認する。

## 影響

`FR-orch-04` は「worker が人間を必要としたとき、そのタスクを待機させて人間へ回す」ことを求める。
未知の理由区分では**この要件が満たされない**。しかも失敗が「静か」で、利用者からは
「同じタスクが何度も失敗して行き詰まった」ようにしか見えない(申告の内容は表示されない)。

severity を「中」とした根拠: 正常系(4区分)では動作し、行き詰まり判定が最終的に人間を呼ぶため
**恒久的な停止にはならない**。一方で `stuck_limit` 回ぶんの無駄な実行が起き、worker が伝えたかった
質問は失われる。

## 原因の見当

推測: 判定を純粋関数として書くときに、既知の理由だけを列挙する `switch` にしたため、
**「未知だが申告はある」という状態が抜け落ちた**。`default:` 節が無い。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| 未知の理由の扱い | `Evaluate` は発火させない(4値のみ) | `FR-orch-04` 受入基準1 は「介入トリガーに該当したとき」としか書かず、未知区分を規定していない。`D0-orch-18` は発火条件を4区分+行き詰まり+不可逆に限定した | **要確認**(実装のまま「4区分だけ」を正とするか、`needs_human` が非 null なら理由に依らず介入を開くか) |

## 対処案

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | `Evaluate` に `default:` を足し、**`needs_human` が非 null なら理由に依らず介入を開く**(理由は受け取った文字列のまま記録) | `trigger.go` と `trigger_test.go`、`MODULE-orchestrator-trigger`、`CTR-orchestrator-prompt`、`FR-orch-04` の受入基準1行 |
| B | 未知の理由を**監査ログに WARN 相当で残すだけ**にして、発火はさせない(現状の意味を保ちつつ可視化する) | `trigger.go` / `controller.go` と 03 の2ファイル |
| C | 現状を仕様として確定させ、`D0-orch-18` に「4区分以外は自律継続」と明記する | ドキュメントのみ(00 と 03) |

推奨は **A**(申告を落とさないほうが `FR-orch-04` の意図に近い)。ただし
**`D0-orch-18` で確定した発火条件を広げる判断なので、人間の合意が要る**。

## 経緯

- 2026-08-03 起票。`task-impl-depth` のフェーズ2で、独立レンズ(Codex `readiness`)が
  「02/03 の契約は介入を開くと書き、trigger 仕様は発火させないと書いていて矛盾する」と指摘。
  コードで裏取りしたところ**発火しないのが実装の事実**だったので、契約側の記述を実装に合わせて
  訂正し、振る舞いそのものの是非を本 issue に切り出した。**本タスクではコードを変更しない。**

## 裁定の記録(2026-08-04)

**人間の裁定: 先送り(次タスクへ)。**
`task-impl-depth` の質問キュー #3「`issue 015` / `issue 016` の扱い」に対する回答であり、
015 は次タスクへ、016 は同 #5=C により本タスクで解消する、と分けられた。

- 「正はどちらか」は**引き続き要確認**。本タスクは 02/03 の記述を実装の事実
  (列挙外の `reason` では介入が開かれない)へ揃えるところまでを行い、
  **振る舞いの是非は決めない**。
- 記録先をこの issue にした理由: 判断の経緯がタスクの `memo.md` にしか無いと、
  `/task-close` が memo.md を削除した時点で「誰がいつ先送りを決めたか」が失われる。

★2026-08-04 `/doc-check task-impl-depth` が「人間の裁定が memo.md にしか無い」ことを検出して追記した。

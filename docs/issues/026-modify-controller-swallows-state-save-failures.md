---
id: 026-modify-controller-swallows-state-save-failures
type: modify
severity: 中
found: 2026-08-03
found_in: task-impl-depth のフェーズ2(D0-scope-07 の起票の閾値を 03-impl 全体へ掃引した際に確定)
related: MODULE-orchestrator-controller, MODULE-orchestrator-state-io, FR-orch-05, docs/02-design/logging.md
summary: コントローラは plan.json / state.json / 追記型ログの書き込み失敗をすべて破棄し、ログにも残さないため、状態が保存できていないまま run が進む
---

# 026 状態保存の失敗が握りつぶされる

## 事象

`orchestrator/controller.go` の永続化呼び出しは**すべて戻り値を捨てている**。

```
_ = c.Store.SavePlan(plan)
_ = c.Store.AppendAudit(AuditEntry{…})
_ = c.Store.AddOpenIntervention(…)
```

`controller.go` 内に `log.Printf` は **1件も無く**(走査結果)、保存失敗を表示する経路も
`audit.jsonl` へ記録する経路も無い。したがってディスク不足・権限喪失・`.orchestrator/` の
削除などで保存が失敗しても、**run は成功しているかのように進み続ける**。

`writeAtomic` は `os.Rename` が失敗したときに一時ファイル `.tmp-*` を残すため、
**残骸が溜まるだけで誰も気づかない**という副作用も伴う。

再現手順:

1. orchestrator を executing で走らせる。
2. `.orchestrator/` を読み取り専用にする(`chmod a-w`)。
3. タスクの状態遷移が起きても端末に何も表示されず、run が進み続けることを確認する。
4. 中断して再開すると、**状態が古い地点から復元される**(進捗が失われる)ことを確認する。

## 影響

`FR-orch-05`(中断・再開で完了済み作業をやり直さない)の前提が静かに崩れる。
`NFR-ops-01`(実行の経過を後から追える)も満たされない。
表示は成功時と同一なので、**利用者は失敗に気づけない**(`D0-scope-07` の起票の閾値 (a))。

severity を「中」とした根拠: 通常の環境では保存は成功する。発生した場合の被害は
「やり直しが起きる」ことであり、成果物(git のコミット)は worktree に残る。

## 原因の見当

推測: 「保存に失敗しても run を止めない」という方針を、**エラーを捨てる**という実装で表現した。
`02-design/logging.md` は WARN/ERROR の出し分けを定めているが、orchestrator 側は
`log` パッケージをほとんど使っていない(唯一の利用箇所は `slack.go`)。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| 保存失敗の扱い | 握りつぶし、表示も記録もしない | `02-design/logging.md`「主機能は続くが期待した状態になっていないことは WARN」/ `NFR-ops-01` | **設計が正** |

## 対処案

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | 保存系の失敗を **WARN で1行**出す(run は止めない)。同じ失敗の連続は間引く | `orchestrator/controller.go` の永続化呼び出し、`MODULE-orchestrator-controller`、`tests/orchestrator.md` |
| B | A に加えて、**連続 N 回失敗したら中断**して `errSuspended` を返す(状態が保存できないなら進む意味が無い) | 同上 + `FR-orch-05` の受入基準 |
| C | 現状を仕様として確定させ、`logging.md` に「orchestrator の保存失敗は記録しない」例外を明記する | ドキュメントのみ |

推奨は **A**(止めない方針を保ちつつ可視化する)。`issue 014`(追記型ログの必須フィールド)と
同時に扱うと、可観測性の修正を1回で済ませられる。

## 経緯

- 2026-08-03 起票。`task-impl-depth` のフェーズ2で `MODULE-orchestrator-controller` の
  「既知の制限」を書き下ろす際に確定し、起票の閾値の掃引で issue 化した。**コードは変更しない。**

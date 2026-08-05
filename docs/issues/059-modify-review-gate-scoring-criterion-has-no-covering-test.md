---
id: 059-modify-review-gate-scoring-criterion-has-no-covering-test
type: modify
severity: 中
found: 2026-08-05
found_in: /doc-check ssot task-relations-code-sync(独立レンズ Codex docs の A3 指摘を検証中に発見)
related: FR-orch-06, MODULE-orchestrator-review, docs/03-impl/tests/orchestrator.md, docs/issues/019
summary: tests/orchestrator.md が FR-orch-06 受入基準2 を「実装済み」としているが、挙げているテストは採点基準を検証しておらず、覆うテストが実在しない
---

# 059 品質ゲートの採点基準に対応するテストが無い

## 事象

`docs/03-impl/tests/orchestrator.md` の受入基準 ⇄ テスト対応表は、

| 要件 ID | 受入基準 # | テスト識別子 | 状態 |
|---|---|---|---|
| FR-orch-06 | 2 | `orchestrator/review_parse_test.go` | 実装済み |

としている。`FR-orch-06` 受入基準2 は
**「WHEN レビューを採点するとき、システムはレビューを当該タスクの完了条件のみを基準に採点しなければならない(プランのゴールで採点しない)」**である。

ところが `orchestrator/review_parse_test.go` が持つテスト関数は
`TestFindReviewResultJSON_StrictAndTolerant` の**1件だけ**で、これは
レビュア出力から JSON を取り出す経路(`findReviewResultJSON`)を検証するものであり、
**採点基準が `Task.Completion` に限られること**は一切検証していない。

リポジトリ全体を走査しても、採点基準を固定するテストは見つからない:

- `orchestrator/policy_test.go::TestBuildReviewPrompt_IncludesPolicyWhenPresent` /
  `::TestBuildReviewPrompt_NoPolicyWhenAbsent` は `ORCHESTRATOR.md` の前置の有無だけを見る。
- `orchestrator/accept_test.go::TestReview_ReformatsProseToJSON` は再整形の経路を見る。
- `buildReviewPrompt` が `Plan.Goal` を「採点に使うな」と明示して載せること、
  `Plan.Completion` へフォールバックしないことを固定するテストは無い。

**2026-08-05 の `/doc-check` では、他の2件(FR-orch-06 受入基準7 / FR-orch-07 受入基準1)は
ファイル名だけの引用を実在するテスト関数へ機械的に置き換えて解消したが、本件だけは
「実装済み」を支えるテストが実在しないため、置き換え先が無い。**

## 影響

`FR-orch-06` 受入基準2 は品質ゲートの中核(自己レビュー回避と並ぶ、採点の恣意性を防ぐ要件)で
あり、`docs/00-requests/decisions/orch.md` の `D0-orch-15` が根拠を持つ。
その受入基準が**テストで固定されていないのに「実装済み」と記録されている**ため、

- `03-impl/tests/orchestrator.md`「未検証(テスト未実装)の全件」表(48 行)から漏れている。
- 採点基準を将来変えたときに、どのテストも落ちない。

振る舞いそのものは実装されている(`orchestrator/review.go::buildReviewPrompt` が
`Task.Completion` を `# This task's completion criteria (the ONLY scoring basis)` として渡し、
`Plan.Goal` は `context only — do NOT score against it` と明示する)ので severity は「中」。

## 正はどちらか

**ドキュメントが誤っている**(実装は要件を満たしている)。取りうる対処は2つで、
どちらを採るかは**テスト方針の判断**なので `/doc-check` の委任範囲を超える。

| 案 | 内容 | 影響 |
|---|---|---|
| A | 状態を「未検証(テスト未実装)」へ落とし、「なぜ未実装か」「閉じる予定」を書いて全件表へ 1 行足す | 全件表が 47 → 48 行、表全体は 49 行になる。`03-impl/tests/orchestrator.md` は MINOR |
| B | `buildReviewPrompt` の出力に `Task.Completion` が入り `Plan.Completion` が入らないことを固定する単体テストを書き、その識別子を表に入れる | コードを触るタスクが要る(テストの追加のみ) |

**推奨は B**(要件の中核であり、テストが無いまま「実装済み」でも「未検証」でも
`FR-orch-06` の保証は薄いままであるため)。ただし B はコードを書くので、
`task-relations-code-sync`(記述をコードへ合わせるタスク。コード変更は「やらないこと」)では
実施できない。

## 経緯

- 2026-08-05 `/doc-check ssot task-relations-code-sync`。独立レンズ Codex(`docs` モード)が
  「テスト識別子欄がテスト関数ではなくファイル名だけを記す行が3件ある」と指摘し、
  その検証中に本件が判明した。同レンズが挙げた3件のうち2件は機械的に解消済み。
- 同じ性質の「実在しないテスト識別子」を追跡していた `docs/issues/019` は
  `task-relations-code-sync` の完了時に削除されるため、本件を独立の issue として残す。

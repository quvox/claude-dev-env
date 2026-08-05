---
target: docs/03-impl/relations/MODULE-orchestrator-plan.md
change: replace
sections:
  - "## 処理の流れ"
  - "## 異常系"
deletes: []
reason: 不存在の依存 ID を「ready にならず永久に着手されない」と書くが実際は blocked へ遷移する(docs/issues/032 #9)。NormalizeForResume が空文字の Status も正規化することが書かれていない(同 #19)
reflected: 2026-08-05
id: MODULE-orchestrator-plan
module: MOD-orchestrator
kind: function-call
sync: sync
impl: orchestrator/controller.go::ReadyTasks, orchestrator/controller.go::AllDone, orchestrator/controller.go::AllSettled, orchestrator/controller.go::MarkBlockedByFailedDeps, orchestrator/controller.go::NormalizeForResume
callers: MODULE-orchestrator-controller, MODULE-orchestrator-main
callees: なし
contracts: なし
design: DSN-mod-01, DSN-orch-01
requirements: FR-orch-03, FR-orch-05
tests: orchestrator/plan_test.go::TestReadyTasks_DependencyResolution, orchestrator/plan_test.go::TestReadyTasks_ParallelLimit, orchestrator/plan_test.go::TestReadyTasks_FailedDepExcluded, orchestrator/plan_test.go::TestDependencyChainOrder, orchestrator/plan_test.go::TestMarkBlockedByFailedDeps, orchestrator/plan_test.go::TestAllDoneAndSettled, orchestrator/plan_test.go::TestStatusTransition_HappyPath, orchestrator/plan_test.go::TestReviseDoesNotIncrementAttempts
updated: 2026-08-05
summary: 計画の依存関係から着手可能タスクと完了判定を導く
---

<!-- 変更指示。反映後の最終形を書く。version / verified は持たない。
     frontmatter の変更は `updated` と `tests` の2つだけ。
     tests に orchestrator/plan_test.go::TestReadyTasks_ParallelLimit と ::TestReadyTasks_FailedDepExcluded を
     足した(2026-08-05 の /doc-check(task) が検出): 同じ変更指示群の
     03-impl/tests/orchestrator.md「機能間連携仕様書 ⇄ テスト」の MODULE-orchestrator-plan 行は
     この2件を含んでおり、frontmatter だけが実在しない TestReadyTasks_Basic を1件へ置換したままで
     食い違っていた。2件とも実在し(orchestrator/plan_test.go:28・:42)、いずれも本機能の impl である
     ReadyTasks を検証する。docs/issues/019 対処案A の
     「relations の tests: と3つの表の表記を揃える」に含まれる。 -->

## 処理の流れ

1. `ReadyTasks(plan *Plan, limit int)`(`orchestrator/controller.go:1330`): `Status == pending` かつ
   依存タスクがすべて `done` のものを返す。依存に `failed` / `blocked` を含むものは返さない。
   `limit` は返す件数の上限(並行度)で、**`limit <= 0` は上限なし**を意味する。
2. `AllDone(plan)`: すべてのタスクが `done` なら真。
3. `AllSettled(plan)`: すべてのタスクが終端状態(`done` / `failed` / `blocked`)なら真。
   `waiting_human` が1件でも残っていれば偽。
4. `MarkBlockedByFailedDeps(plan)`(`controller.go:1353`): 依存が満たされない `pending` タスクを
   `blocked`(run 内の終端)へ落とす。「満たされない」の判定は `depsFailed`(`:1306`〜`:1318`)で、
   **依存 ID が plan に存在しないときも「満たされない」に含める**(`:1310`〜`:1312` が
   `missing dependency: unsatisfiable` として真を返す)。したがって
   **存在しない依存 ID を持つタスクは `blocked` へ落ちる**(`failed` 依存と同じ扱い)。
5. `NormalizeForResume(plan)`(`controller.go:1402`〜`:1414`): 中断時の状態を再開可能な形へ整える。
   `done` / `failed` / `blocked` は一切触らない。`waiting_human` は保持する。
   `running` / `review` / `revise` のまま落ちたものは `pending` へ戻し、`SessionID` があれば
   `--resume` で継続するよう `ResumeSession` を立てる。
   **加えて `Status` が空文字のタスクも `pending` へ正規化する**(`:1412`〜`:1413`。
   手書きや外部生成の `plan.json` で `status` を省いたタスクが着手されないまま残るのを防ぐ)。

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 依存 ID が存在しないタスクを指す | その依存は満たされないものとして扱われ ready にならず、**`MarkBlockedByFailedDeps` が呼ばれた時点で `blocked` へ落ちる**(`failed` 依存と同じ扱い。`depsFailed` が `controller.go:1310`〜`:1312` で真を返す) | **待ち続けるのではなく run 内の終端になる**。`AllSettled` が真になりうるので run は終了できる(plan の不備は `blocked` として残る) |
| 依存が循環している | 双方が ready にならず、`AllSettled` も偽のまま残る | run が進まなくなる。人間が plan を直す必要がある |
| `waiting_human` が残っている | `AllSettled` が偽を返し、run は終了しない | 判断待ちが解消されるまで待つ(意図した設計) |

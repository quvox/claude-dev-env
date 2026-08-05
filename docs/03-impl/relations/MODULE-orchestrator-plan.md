---
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

# MODULE-orchestrator-plan 計画論理(依存解決と完了判定)

## 目的

「次に何を起動してよいか」「run を終えてよいか」を計画データだけから決める純粋論理
(FR-orch-03)。副作用を持たないため単体テストで網羅でき、スケジューラの正しさをここで担保する。
中断からの復帰時に状態を整える `NormalizeForResume` も含む(FR-orch-05)。

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

## 呼び出され方

- 契機: `MODULE-orchestrator-controller` が実行ループの各 tick で、`MODULE-orchestrator-main` が
  再開/新規の判定時に呼ぶ。
- 前提条件: `Plan` が読み込まれていること。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `plan` | `*Plan` | 必須 | `Tasks[]` の `Status` / `Deps` を参照する。関数によっては書き換える |

- 認可: プロセス内呼び出し。

## 連携先と連携内容

連携先なし(純粋論理。永続化は呼び出し元が `SavePlan` で行う)。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | `ReadyTasks` はタスクの並び、`AllDone` / `AllSettled` は真偽値 |
| 永続化 | 自身では行わない。`MarkBlockedByFailedDeps` と `NormalizeForResume` は**メモリ上の plan を書き換える**ので、呼び出し元が `MODULE-orchestrator-state` の `SavePlan` で `plan.json` へ書く |
| 発火するイベント | なし |
| ログ | なし |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 依存 ID が存在しないタスクを指す | その依存は満たされないものとして扱われ ready にならず、**`MarkBlockedByFailedDeps` が呼ばれた時点で `blocked` へ落ちる**(`failed` 依存と同じ扱い。`depsFailed` が `controller.go:1310`〜`:1312` で真を返す) | **待ち続けるのではなく run 内の終端になる**。`AllSettled` が真になりうるので run は終了できる(plan の不備は `blocked` として残る) |
| 依存が循環している | 双方が ready にならず、`AllSettled` も偽のまま残る | run が進まなくなる。人間が plan を直す必要がある |
| `waiting_human` が残っている | `AllSettled` が偽を返し、run は終了しない | 判断待ちが解消されるまで待つ(意図した設計) |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 計画論理を副作用の無い関数として `controller.go` 内に置き、`plan.go` は作らない(ファイルを増やさずテスト境界だけ `plan_test.go` で切る) | D0-orch-02 |
| 2 | `NormalizeForResume` は終端状態を触らない(再開のたびに完了済みが巻き戻る事故を構造的に防ぐ) | D0-orch-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 依存の循環を検出しない | 循環があると run が進まないまま止まる | なし |

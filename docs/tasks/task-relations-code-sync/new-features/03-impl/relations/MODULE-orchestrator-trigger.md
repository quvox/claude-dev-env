---
target: docs/03-impl/relations/MODULE-orchestrator-trigger.md
change: replace
sections:
  - "## 呼び出され方"
  - "## 異常系"
deletes: []
reason: 引数表に Phase / Result / StuckThisAttempt が無く、値域が書かれていないため呼び出し元が判定を誤りうる(docs/issues/038 #31)
reflected: 2026-08-05
id: MODULE-orchestrator-trigger
module: MOD-orchestrator
kind: function-call
sync: sync
impl: orchestrator/trigger.go::Evaluate
callers: MODULE-orchestrator-controller
callees: なし
contracts: なし
design: DSN-mod-01, DSN-orch-01
requirements: FR-orch-04
tests: orchestrator/trigger_test.go::TestEvaluate_PreDispatchIrreversible, orchestrator/trigger_test.go::TestEvaluate_NeedsHumanReasons, orchestrator/trigger_test.go::TestEvaluate_StuckLimitBoundary, orchestrator/trigger_test.go::TestEvaluate_StuckThisAttempt, orchestrator/trigger_test.go::TestEvaluate_StuckTakesPrecedenceOverNeedsHuman
updated: 2026-08-05
summary: 停滞・介入要求などの発火条件を判定する
---

<!-- 変更指示。反映後の最終形を書く。version / verified は持たない。frontmatter は `updated` の日付以外変更なし。 -->

## 呼び出され方

- 契機: `MODULE-orchestrator-controller` が worker 起動前(条件1)と結果受領後(条件2〜5)に呼ぶ。
- 前提条件: なし(純粋関数)。
- 引数(1つの構造体 `TriggerContext` を値で渡す。`orchestrator/trigger.go:29`〜`:40`):

| フィールド | 型 | 必須 | 制約 | 実装が行う検証 |
|---|---|---|---|---|
| `Phase` | `TriggerPhase` | 必須 | **`PhasePreDispatch`(= 0。起動前。条件1 だけを見る)/ `PhasePostDispatch`(= 1。結果受領後。条件2 / 4 / 5 を見る)の2値**(`trigger.go:17`〜`:24`)。**`Evaluate` はこの値で判定内容を分ける**(`:53`)ので、呼び出し元が誤ると起動前に結果由来の条件を評価してしまう | **検証しない**。ゼロ値が `PhasePreDispatch` なので、**未設定は「起動前」として扱われる** |
| `Task` | `*Task` | 必須 | `Irreversible` / `IrrevApproved` / `Attempts` を見る | **`nil` なら発火させず空の理由を返す** |
| `Plan` | `*Plan` | 任意 | 判定の文脈 | 検証しない |
| `State` | `*State` | 任意 | 判定の文脈 | 検証しない |
| `Result` | `*WorkerResult` | **`PhasePostDispatch` のとき必須** | 直近の worker 結果。`NeedsHuman` の有無と `Reason` を見る。**起動前の評価では使わない** | 検証しない。`NeedsHuman.Reason` の**値域も検証しない**(4区分以外は発火しない = `docs/issues/015`) |
| `Config` | `Config` | 必須 | `stuck_limit` を見る | 検証しない |
| `StuckThisAttempt` | 真偽 | 任意 | **その Attempt が `max_review_rounds` を使い切ってなお重大指摘が残った**ことを呼び出し元が伝える印(条件3b)。この機能自身はレビュー往復数を数えない | 検証しない。ゼロ値(偽)は「行き詰まっていない」を意味する |

- 認可: プロセス内呼び出し。

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| `Task` が nil | 発火させず空の理由を返す | なし |
| `NeedsHuman.Reason` が上表の4値以外 | **発火させない**(未知の値は無視する) | 人間を呼ぶべき申告を見落としうる |
| `NeedsHuman` が nil | 条件2 / 4 / 5 は評価されない | 条件3 だけが残る |
| `stuck_limit` が 0 以下 | 回数による発火を**行わない**。判定は `StuckLimit > 0 && Attempts >= StuckLimit` であり、0 以下は「回数判定を無効にする」意味になる(`orchestrator/trigger.go:69`) | 行き詰まりが回数では検出されなくなる(同一 Attempt 内の連続失敗による発火だけが残る) |
| **`Phase` が `PhasePreDispatch` のとき** | **条件1 だけを評価して返る**(`orchestrator/trigger.go:53`〜`:63`)。条件2〜5 は評価されないので、**条件1 と条件3 が同じ呼び出しで競合することはない** | 起動前は不可逆操作のゲートだけが働く |
| **`Phase` が `PhasePostDispatch` のとき** | **条件3(行き詰まり)を最初に評価する**(`:67`〜`:74`)。`Attempts >= stuck_limit` または `StuckThisAttempt` が真なら、`NeedsHuman` の有無に関わらず行き詰まりとして返す | 条件2 / 4 / 5 より行き詰まりが優先される |

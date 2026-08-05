---
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

# MODULE-orchestrator-trigger 介入トリガーの判定

## 目的

「どこで人間を呼ぶか」を機械的に決める(FR-orch-04)。判断を純粋関数に閉じることで、
発火条件を単体テストで網羅でき、恣意的な停止が起きないようにしている。

## 処理の流れ

1. `Evaluate(ctx TriggerContext) (fire bool, reason string)` が下表の条件だけを見る。
   **I/O も推論も行わない純粋関数**である。
2. **条件1(後戻り不可)**: 計画段階で `Irreversible` の印が付いたタスクを、worker 起動**前**に
   発火させる。`IrrevApproved` が立っていれば再発火しない(再開時の無限再発火を防ぐ)。
3. **条件3(行き詰まり)**: 実行後の判定で**最初に**見る。
   `stuck_limit > 0` かつ `Attempts >= stuck_limit`、または同一 Attempt 内で
   `max_review_rounds` に到達しても重大指摘が残っている場合(後者は controller が検出し、
   `NeedsHuman` は使わない)。
4. **条件2 / 4 / 5**: worker の `NeedsHuman.Reason` を実行後に検出する。
   `ambiguity` → 条件2、`policy_branch` → 条件4、`prerequisite_broken` → 条件5。
   **`critical_decision` は条件1(後戻り不可)として発火する**
   (本来は起動前に止まるはずだが、worker が申告してきた場合も尊重する)。
5. **上記のいずれにも当たらない場合は発火しない**(= `D0-orch-18` が定義する
   「自律継続してよい判断」)。worker はその判断を `assumptions` に載せて返し、
   controller が `assumptions.jsonl` へ記録して実行を続ける。
6. 複数条件が同時に成立する場合、**行き詰まり(条件3)が優先される**(判定順による)。

**発火する条件の一覧(これ以外では発火しない)**:

| 局面 | 発火する条件 | 返す理由 |
|---|---|---|
| 起動前 | `Irreversible` かつ `IrrevApproved` でない | `irreversible` |
| 実行後 | `stuck_limit > 0` かつ `Attempts >= stuck_limit` | `stuck` |
| 実行後 | 同一 Attempt で `max_review_rounds` 到達後も重大指摘が残る | `stuck` |
| 実行後 | `NeedsHuman.Reason == "ambiguity"` | `ambiguity` |
| 実行後 | `NeedsHuman.Reason == "policy_branch"` | `policy_branch` |
| 実行後 | `NeedsHuman.Reason == "prerequisite_broken"` | `prerequisite` |
| 実行後 | `NeedsHuman.Reason == "critical_decision"` | `irreversible` |

なお `review_gate_defect`(レビュア出力が規定回数続けて解釈できない)は**この機能の判定では
なく** `MODULE-orchestrator-review` が返す結果を controller が介入へ回すもので、5条件には含まれない。

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

## 連携先と連携内容

連携先なし(純粋関数。永続化も通知も呼び出し元が行う)。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | `(fire bool, reason string)`。`reason` は介入キューと Slack 通知の文面に使われる |
| 永続化 | なし |
| 発火するイベント | なし |
| ログ | なし |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| `Task` が nil | 発火させず空の理由を返す | なし |
| `NeedsHuman.Reason` が上表の4値以外 | **発火させない**(未知の値は無視する) | 人間を呼ぶべき申告を見落としうる |
| `NeedsHuman` が nil | 条件2 / 4 / 5 は評価されない | 条件3 だけが残る |
| `stuck_limit` が 0 以下 | 回数による発火を**行わない**。判定は `StuckLimit > 0 && Attempts >= StuckLimit` であり、0 以下は「回数判定を無効にする」意味になる(`orchestrator/trigger.go:69`) | 行き詰まりが回数では検出されなくなる(同一 Attempt 内の連続失敗による発火だけが残る) |
| **`Phase` が `PhasePreDispatch` のとき** | **条件1 だけを評価して返る**(`orchestrator/trigger.go:53`〜`:63`)。条件2〜5 は評価されないので、**条件1 と条件3 が同じ呼び出しで競合することはない** | 起動前は不可逆操作のゲートだけが働く |
| **`Phase` が `PhasePostDispatch` のとき** | **条件3(行き詰まり)を最初に評価する**(`:67`〜`:74`)。`Attempts >= stuck_limit` または `StuckThisAttempt` が真なら、`NeedsHuman` の有無に関わらず行き詰まりとして返す | 条件2 / 4 / 5 より行き詰まりが優先される |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 判定を純粋関数に閉じ、キューへの登録・通知・状態遷移は呼び出し元に任せる(テスト可能性のため) | D0-orch-04 |
| 2 | **発火条件を列挙し、それ以外はすべて自律継続とする**(「重要度が低いかどうか」という主観の判断余地を残さない)。自律継続した判断は `assumptions.jsonl` に残す | D0-orch-04, D0-orch-18 |
| 3 | 実行後は行き詰まりを最初に判定する(`NeedsHuman` の有無に依存せず、回数超過を確実に捕まえるため) | D0-orch-04 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 条件4 / 条件5 の事前検出(計画マーク・自動検出)はフェーズ2以降 | v1 は worker の `NeedsHuman` 報告に依存する | なし |

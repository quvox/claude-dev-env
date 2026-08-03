---
target: docs/03-impl/relations/MODULE-orchestrator-trigger.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
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
tests: orchestrator/trigger_test.go::TestEvaluate_PreDispatchIrreversible, orchestrator/trigger_test.go::TestEvaluate_NeedsHumanReasons, orchestrator/trigger_test.go::TestEvaluate_StuckLimitBoundary, orchestrator/trigger_test.go::TestEvaluate_StuckThisAttempt, orchestrator/trigger_test.go::TestEvaluate_StuckTakesPrecedence
updated: 2026-08-02
summary: 停滞・介入要求などの発火条件を判定する
---

# MODULE-orchestrator-trigger 介入トリガーの判定

## 目的

「どこで人間を呼ぶか」を機械的に決める(FR-orch-04)。判断を純粋関数に閉じることで、
発火条件を単体テストで網羅でき、恣意的な停止が起きないようにしている。

## 処理の流れ

1. `Evaluate(ctx TriggerContext) (fire bool, reason string)` が5条件を順に見る。
2. **条件1(後戻り不可)**: 計画段階で `Irreversible` の印が付いたタスクを、worker 起動**前**に
   発火させる。`IrrevApproved` が立っていれば再発火しない。
3. **条件2(曖昧さ)**/ **条件4(方針分岐)**/ **条件5(前提崩れ)**: worker の
   `NeedsHuman.Reason`(`ambiguity` / `policy_branch` / `prerequisite_broken`)を実行後に検出する。
4. **条件3(行き詰まり)**: `Attempts >= stuck_limit`、または同一 Attempt 内で
   `max_review_rounds` に到達しても重大指摘が残っている場合(こちらは controller が検出し、
   `NeedsHuman` は使わない)。
5. 軽微なものは発火させず、`assumptions.jsonl` へ記録して続行する。
6. 複数条件が同時に成立する場合、行き詰まり(条件3)が優先される。

## 呼び出され方

- 契機: `MODULE-orchestrator-controller` が worker 起動前(条件1)と結果受領後(条件2〜5)に呼ぶ。
- 前提条件: なし(純粋関数)。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `ctx` | `TriggerContext` | 必須 | タスクの `Irreversible` / `IrrevApproved` / `Attempts`、worker の `NeedsHuman`、設定の `stuck_limit` を含む |

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
| `NeedsHuman.Reason` が未知の値 | 発火させない(既知の3種のみ判定する) | 見落としの可能性がある |
| `stuck_limit` が 0 以下 | 境界判定は `Attempts >= stuck_limit` なので即座に発火する | 設定ミスで常に判断待ちになる |
| 条件1と条件3が同時に成立 | 行き詰まり(条件3)を優先して返す | 理由の文面が行き詰まりになる |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 判定を純粋関数に閉じ、キューへの登録・通知・状態遷移は呼び出し元に任せる(テスト可能性のため) | D0-orch-04 |
| 2 | 軽微な判断は発火させず `assumptions.jsonl` に残す(人間を呼ぶ回数を要件の範囲に絞る) | D0-orch-04 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 条件4 / 条件5 の事前検出(計画マーク・自動検出)はフェーズ2以降 | v1 は worker の `NeedsHuman` 報告に依存する | なし |

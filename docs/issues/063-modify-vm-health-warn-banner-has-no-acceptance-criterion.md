---
id: 063-modify-vm-health-warn-banner-has-no-acceptance-criterion
type: modify
severity: 中
found: 2026-08-05
found_in: /doc-check task-spec-measurability(独立レンズ readiness の指摘を裁定して確定。合成ビューの D13 走査)
related: FR-orch-08, FR-env-08, MODULE-orchestrator-dashboard, docs/01-requirements/functional.md, docs/00-requests/terminology.md, docs/03-impl/tests/orchestrator.md
summary: ダッシュボードが VM の資源逼迫(STATE=WARN)で赤いバナーを出す振る舞いは実装済み・単体テスト4件つきだが、これを要求する受け入れ基準がどこにも無い。FR-orch-08 受入基準7 は「取得に失敗しても描画を止めない」という異常系だけを課しており、正常系(WARN なら出す)を課す基準が無い
---

# 063 ダッシュボードの VM 資源逼迫バナーに受け入れ基準が無い

## 事象

`MODULE-orchestrator-dashboard` は実行フェーズの描画のたびに
`$HOME/.claude-dev-vm/health` を読み、`STATE=WARN` かつ鮮度内なら赤いバナーを出す
(`orchestrator/dashtui.go:180`。`MODULE-orchestrator-dashboard.md` の「処理の流れ」8)。
単体テストも4件ある(`orchestrator/dashboard_test.go::TestReadVMHealthBanner_WarnFresh` /
`_OKIsSilent` / `_StaleIgnored` / `_NonVMMode`)。

ところが、この**正常系の振る舞いを要求する受け入れ基準が 01 に無い**。

| 要件 | 何を課しているか | バナーの表示を課すか |
|---|---|---|
| `FR-orch-08` 受入基準7(異常系) | 「補助情報(VM のヘルス等)の取得に失敗したならば、描画を止めてはならない」 | **課さない**(失敗時の振る舞いだけ) |
| `FR-env-08` 受入基準4 | ヘルスファイルへ `STATE=WARN` を書き、tmux のステータス行へ警告を表示する | **課さない**(VM モード側の2出力だけ) |

`MODULE-orchestrator-dashboard.md` の `requirements` は `FR-orch-08` だけであり、
モジュールの割り当て自体は `02-design/system.md` と整合している(`MOD-orchestrator` は
`FR-orch-08` を持つ)。**割り当ての穴ではなく、受け入れ基準の穴**である。

## なぜ気づかれなかったか

`docs/00-requests/terminology.md` の「資源逼迫」の定義が
「この状態で監視デーモンがヘルスファイルに `STATE=WARN` を書き、**tmux とダッシュボードが
警告を表示する**」と両方を挙げているため、用語集だけを読むと受け入れ基準に落ちているように見える。
`task-spec-measurability` の走査でも、独立レンズ(readiness)がこの食い違いを指摘するまで
検出されなかった。

## 影響

テストで固定された観測可能な振る舞いが、要件の裏付けを持たない。
`docs/03-impl/tests/orchestrator.md` の受入基準⇄テスト対応表にも、この4テストを紐づける行が無い
(テストは `MODULE-orchestrator-dashboard` の `tests` にだけ現れる)。
`FR-orch-08` の受入基準を1行足すだけで閉じるが、01 の変更なので
`task-spec-measurability`(記述の精密化。要件を増やさない)の範囲外である。

## 対処案

- **案A**: `FR-orch-08` に正常系の受入基準を1行足す
  (「WHILE 実行フェーズを描画している間、VM モードでヘルスファイルが `STATE=WARN` かつ鮮度内
  ならば、システムは警告バナーを表示しなければならない」)。あわせて
  `03-impl/tests/orchestrator.md` に既存の4テストを紐づける行を足す。**実装は変えない。**
- **案B**: バナーを `D0-orch-06`(ダッシュボードの描画と操作の規則)の委任の範囲内の実装判断と
  みなし、受け入れ基準を設けずに `MODULE-orchestrator-dashboard` の「実装上の判断」へ
  `D0-orch-06` つきで記録する。

案A を推す(テストが4件あるということは、この振る舞いは判断の余地なく期待されている)。
どちらも 01 または 03 を触るので、独立したタスクで行う。

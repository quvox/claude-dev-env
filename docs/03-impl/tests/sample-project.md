---
id: sample-project
scope: MOD-sample-project
version: 1.1.0
updated: 2026-08-07
source:
  - docs/01-requirements/functional.md
  - docs/02-design/system.md
summary: MOD-sample-project(自己検証用サンプル)の受入基準⇄テスト対応
keywords: [テスト]
verified:
  at: 2026-08-06
  version: 1.0.1
  against:
    - doc: docs/01-requirements/functional.md
      version: 1.8.1
    - doc: docs/02-design/system.md
      version: 2.4.0
---

# MOD-sample-project のテスト対応

## 受入基準 ⇄ テスト対応表


| 受入基準 ID | 種別 | レベル | テスト識別子 | 状態 |
|---|---|---|---|---|
| FR-orch-09-1 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-09-3 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-09-4 | 正常系 | 単体 | `examples/orch-sample` の pytest 一式 | 実装済み |
| FR-orch-09-5 | 境界値 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-09-6 | 異常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |

## 契約の結合テスト

| 契約 ID | 相手 | テスト識別子 | 状態 |
|---|---|---|---|
| (なし) | — | - | 対象外(理由: 02 の「結合テスト対象」でこのモジュールが責任を持つ契約は無い) |

## 機能間連携仕様書 ⇄ テスト

| MODULE-ID | テスト識別子 | 状態 |
|---|---|---|
| MODULE-sample-project-mathkit | `examples/orch-sample/tests/test_geometry.py`, `examples/orch-sample/tests/test_stats.py`, `examples/orch-sample/tests/test_strings.py` | 実装済み |
| MODULE-sample-project-scaffold | - | 未検証(テスト未実装) |

## 未検証(テスト未実装)の全件

| # | 対象 | なぜ未実装か | 解消の条件 |
|---|---|---|---|
| 1 | FR-orch-09 — 受入基準 1(正常系) | 題材の配置はシェル実装であり自動テストランナーを持たない(`DSN-test-01`)。題材そのものの合否は pytest で機械判定できる | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 2 | FR-orch-09 — 受入基準 3(正常系) | 題材の配置はシェル実装であり自動テストランナーを持たない(`DSN-test-01`)。題材そのものの合否は pytest で機械判定できる | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 3 | FR-orch-09 — 受入基準 5(境界値) | 題材の配置はシェル実装であり自動テストランナーを持たない(`DSN-test-01`)。題材そのものの合否は pytest で機械判定できる | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 4 | FR-orch-09 — 受入基準 6(異常系) | 題材の配置はシェル実装であり自動テストランナーを持たない(`DSN-test-01`)。題材そのものの合否は pytest で機械判定できる | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 5 | MODULE-sample-project-scaffold — 機能全体 | シェル実装のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |

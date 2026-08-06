---
id: cli-reset
scope: MOD-cli-reset
version: 1.2.0
updated: 2026-08-07
source:
  - docs/01-requirements/functional.md
  - docs/02-design/system.md
summary: MOD-cli-reset(環境の初期化)の受入基準⇄テスト対応
keywords: [テスト]
verified:
  at: 2026-08-06
  version: 1.1.1
  against:
    - doc: docs/01-requirements/functional.md
      version: 1.8.1
    - doc: docs/02-design/system.md
      version: 2.4.0
---

# MOD-cli-reset のテスト対応

## 受入基準 ⇄ テスト対応表


| 受入基準 ID | 種別 | レベル | テスト識別子 | 状態 |
|---|---|---|---|---|
| (なし) | — | — | - | 対象外(理由: このモジュールを主担当とする受入基準は無い。担当する要件の受入基準は主担当モジュールの対応表が持つ。`tests/strategy.md`「状態列の語彙の定義」) |

## 契約の結合テスト

| 契約 ID | 相手 | テスト識別子 | 状態 |
|---|---|---|---|
| CTR-cli-container(破壊的操作の対象の識別) | MOD-cli-start(管理ラベルの発行側) | E2E-01(実機確認手順 手順8-9・8-10・8-12・8-13) | 未検証(テスト未実装) |

## 機能間連携仕様書 ⇄ テスト

| MODULE-ID | テスト識別子 | 状態 |
|---|---|---|
| MODULE-cli-reset | - | 未検証(テスト未実装) |

## 未検証(テスト未実装)の全件

| # | 対象 | なぜ未実装か | 解消の条件 |
|---|---|---|---|
| 1 | MODULE-cli-reset — 機能全体 | シェル実装のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |

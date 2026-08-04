---
id: cli-logout
scope: MOD-cli-logout
version: 1.0.0
updated: 2026-08-03
source:
  - docs/01-requirements/functional.md
  - docs/02-design/system.md
summary: MOD-cli-logout(認証情報の破棄)の受入基準⇄テスト対応
keywords: [テスト]
verified:
  at: 2026-08-04
  version: 1.0.0
  against:
    - doc: docs/01-requirements/functional.md
      version: 1.4.0
    - doc: docs/02-design/system.md
      version: 2.0.0
---

# MOD-cli-logout のテスト対応

## 受入基準 ⇄ テスト対応表

| 要件 ID | 受入基準 # | 種別 | レベル | テスト識別子 | 状態 |
|---|---|---|---|---|---|
| FR-env-03 | 5 | 正常系 | — | - | 未検証(テスト未実装) |

## 契約の結合テスト

| 契約 ID | 相手 | テスト識別子 | 状態 |
|---|---|---|---|
| (なし) | — | - | 対象外(理由: 02 の「結合テスト対象」でこのモジュールが責任を持つ契約は無い) |

## 機能間連携仕様書 ⇄ テスト

| MODULE-ID | テスト識別子 | 状態 |
|---|---|---|
| MODULE-cli-logout | - | 未検証(テスト未実装) |

## 未検証(テスト未実装)の全件

| # | 対象 | なぜ未実装か | 閉じる予定 |
|---|---|---|---|
| 1 | FR-env-03 — 受入基準 5(正常系) | 自動テストランナーを設けない方針(`DSN-test-01` / `SR-32`)。実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 2 | MODULE-cli-logout — 機能全体 | シェル実装のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |

---
id: cli-firewall
version: 1.1.1
updated: 2026-08-12
scope: MOD-cli-firewall
source:
  - docs/01-requirements/functional.md
  - docs/02-design/system.md
summary: MOD-cli-firewall(ファイアウォール状態の表示)の受入基準⇄テスト対応
keywords: [テスト]
verified:
  at: 2026-08-12
  version: 1.1.1
  against:
    - {doc: docs/01-requirements/functional.md, version: 1.16.0}
    - {doc: docs/02-design/system.md, version: 2.12.0}
---

# MOD-cli-firewall のテスト対応

## 受入基準 ⇄ テスト対応表


| 受入基準 ID | 種別 | レベル | テスト識別子 | 状態 |
|---|---|---|---|---|
| (なし) | — | — | - | 対象外(理由: このモジュールを主担当とする受入基準は無い。担当する要件の受入基準は主担当モジュールの対応表が持つ。`tests/strategy.md`「状態列の語彙の定義」) |

## 契約の結合テスト

| 契約 ID | 相手 | テスト識別子 | 状態 |
|---|---|---|---|
| (なし) | — | - | 対象外(理由: 02 の「結合テスト対象」でこのモジュールが責任を持つ契約は無い) |

## 機能間連携仕様書 ⇄ テスト

| MODULE-ID | テスト識別子 | 状態 |
|---|---|---|
| MODULE-cli-firewall | - | 未検証(テスト未実装) |

## テスト設計の判断

- 判断なし: **このモジュールについて AI が決めたテスト設計の判断は無い。** 自動テストを置かない範囲は `SR-32`(Bash 実装に自動テストランナーを設けない)と 02 のテスト戦略 `DSN-test-01` が既に決めており、**「テストを書かない」「手動テストで代替する」は 標準委任 `DS-01` の対象外**である(`.claude/directions/delegation.md` §2)。何を検証するかは受入基準が正で、確認は E2E の実機確認手順(`tests/e2e.md`)が持つ。

## 未検証(テスト未実装)の全件

| # | 対象 | なぜ未実装か | 解消の条件 |
|---|---|---|---|
| 1 | MODULE-cli-firewall — 機能全体 | シェル実装のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |

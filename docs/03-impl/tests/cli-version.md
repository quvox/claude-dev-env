---
id: cli-version
version: 1.0.0
updated: 2026-11-23
scope: MOD-cli-version
source:
  - docs/01-requirements/functional.md
  - docs/02-design/system.md
summary: MOD-cli-version(claude-dev の版の名乗り)の受入基準⇄テスト対応
keywords: [テスト]
---

# MOD-cli-version のテスト対応

## 受入基準 ⇄ テスト対応表

| 受入基準 ID | 種別 | レベル | テスト識別子 | 状態 |
|---|---|---|---|---|
| FR-env-01-37 | 正常系 | unit | `scripts/test-cli-version.sh`「台帳の先頭の版を3つ組で名乗る」(`--version` / `-v`、Linux 版・macOS 版) | 実装済み |
| FR-env-01-38 | 境界値 | unit | `scripts/test-cli-version.sh`「台帳が無ければ / 空なら「未リリース」」 | 実装済み |
| FR-env-01-39 | 異常系 | unit | `scripts/test-cli-version.sh`「壊れた台帳は失敗」「3つ組でない版は名乗らない」 | 実装済み |

## 契約の結合テスト

| 契約 ID | 相手 | テスト識別子 | 状態 |
|---|---|---|---|
| (なし) | — | - | 対象外(理由: このモジュールは契約を持たない) |

## 機能間連携仕様書 ⇄ テスト

| MODULE-ID | テスト識別子 | 状態 |
|---|---|---|
| MODULE-cli-version | `scripts/test-cli-version.sh` | 実装済み |

## テスト設計の判断

- [DS-01] 版の名乗りは自己完結した1本のシェルスクリプトで自動テストを持つ(`scripts/e2e6-codex.sh` と同じ置き場と形)。
  台帳を自由に作れる使い捨てのリポジトリ形を一時ディレクトリに組んで CLI を叩くので、本物の台帳にも Docker にも触れない
  — 理由: `BR-12` が版の名乗りの自動テストを必須にしており、`SR-32` が禁じるのはテストランナーの導入であって
  単体のスクリプトではない / 見直す条件: Bash 向けのテストランナーを導入すると決めたとき。
  欠陥注入: 「終了コード 1 を常に未リリースと読む」欠陥を入れて 4 件が赤になることを確かめ、戻して全件 green を確かめた(2026-11-23)。

## 未検証(テスト未実装)の全件

- なし

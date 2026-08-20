---
id: makefile
version: 1.3.0
updated: 2026-08-20
scope: MOD-makefile
source:
  - docs/01-requirements/functional.md
  - docs/02-design/system.md
summary: MOD-makefile(ビルド・導入・運用ターゲット)の受入基準⇄テスト対応
keywords: [テスト]
verified:
  at: 2026-08-12
  version: 1.2.1
  against:
    - {doc: docs/01-requirements/functional.md, version: 1.16.0}
    - {doc: docs/02-design/system.md, version: 2.12.0}
---

# MOD-makefile のテスト対応

## 受入基準 ⇄ テスト対応表


| 受入基準 ID | 種別 | レベル | テスト識別子 | 状態 |
|---|---|---|---|---|
| FR-env-10-1 | 正常系 | E2E | E2E-01(実機確認手順) | 未検証(テスト未実装) |
| NFR-ops-03 | 非機能 | E2E | E2E-01(実機確認手順) | 未検証(テスト未実装) |

## 契約の結合テスト

| 契約 ID | 相手 | テスト識別子 | 状態 |
|---|---|---|---|
| (なし) | — | - | 対象外(理由: 02 の「結合テスト対象」でこのモジュールが責任を持つ契約は無い) |

## 機能間連携仕様書 ⇄ テスト

| MODULE-ID | テスト識別子 | 状態 |
|---|---|---|
| MODULE-makefile-build | - | 未検証(テスト未実装) |
| MODULE-makefile-build-claude | - | 未検証(テスト未実装) |
| MODULE-makefile-build-claude-vnc | - | 未検証(テスト未実装) |
| MODULE-makefile-build-docker-proxy | - | 未検証(テスト未実装) |
| MODULE-makefile-clean | E2E-01(実機確認手順 手順10-4。削除対象の集合の確認まで) | 実装済み |
| MODULE-makefile-env | - | 未検証(テスト未実装) |
| MODULE-makefile-help | - | 未検証(テスト未実装) |
| MODULE-makefile-install | - | 未検証(テスト未実装) |
| MODULE-makefile-login | - | 未検証(テスト未実装) |
| MODULE-makefile-network | - | 未検証(テスト未実装) |
| MODULE-makefile-setup | - | 未検証(テスト未実装) |
| MODULE-makefile-status | E2E-01(実機確認手順 手順10-3) | 実装済み |
| MODULE-makefile-uninstall | - | 未検証(テスト未実装) |
| MODULE-makefile-update-claude | - | 未検証(テスト未実装) |
| MODULE-makefile-upgrade | - | 未検証(テスト未実装) |
| MODULE-makefile-volumes | - | 未検証(テスト未実装) |

## 未検証(テスト未実装)の全件

| # | 対象 | なぜ未実装か | 解消の条件 |
|---|---|---|---|
| 1 | FR-env-10-1(正常系) | 自動テストランナーを設けない方針(`DSN-test-01` / `SR-32`)。実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 2 | NFR-ops-03 — 操作の一覧性 | 自動テストランナーを設けない方針(`DSN-test-01` / `SR-32`)。実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 3 | MODULE-makefile-build — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 4 | MODULE-makefile-build-claude — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 5 | MODULE-makefile-build-claude-vnc — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 6 | MODULE-makefile-build-docker-proxy — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 7 | MODULE-makefile-env — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 8 | MODULE-makefile-help — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 9 | MODULE-makefile-install — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 10 | MODULE-makefile-login — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 11 | MODULE-makefile-network — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 12 | MODULE-makefile-setup — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 13 | MODULE-makefile-uninstall — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 14 | MODULE-makefile-update-claude — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 15 | MODULE-makefile-upgrade — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 16 | MODULE-makefile-volumes — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |

## テスト設計の判断

<!-- このファイルのテストの作り方(DS-01 で AI が決めた部分)の理由を置く。何を検証するかは 01 が正である。 -->

- 判断なし: このファイルが持つ 16 行はいずれも `未検証(テスト未実装)` であり、テストの作り方を選ぶ余地が生じていない。Makefile に自動テストランナーを設けないのは `DSN-test-01` / `SR-32` の既定であり、そこから動かしていない。**`make status` と `make clean` の2行(2026-08-20 に `実装済み` へ移した)の作り方の判断は `docs/03-impl/tests/e2e.md` の「テスト設計の判断」に在る**(手順の持ち主がそちらである)

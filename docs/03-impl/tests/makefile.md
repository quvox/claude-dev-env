---
id: makefile
scope: MOD-makefile
version: 1.0.1
updated: 2026-08-06
source:
  - docs/01-requirements/functional.md
  - docs/02-design/system.md
summary: MOD-makefile(ビルド・導入・運用ターゲット)の受入基準⇄テスト対応
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

# MOD-makefile のテスト対応

## 受入基準 ⇄ テスト対応表

| 要件 ID | 受入基準 # | 種別 | レベル | テスト識別子 | 状態 |
|---|---|---|---|---|---|
| FR-env-10 | 1 | 正常系 | E2E | E2E-01(実機確認手順) | 未検証(テスト未実装) |
| NFR-ops-03 | — | 非機能 | E2E | E2E-01(実機確認手順) | 未検証(テスト未実装) |

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
| MODULE-makefile-build-orchestrator | - | 未検証(テスト未実装) |
| MODULE-makefile-clean | - | 未検証(テスト未実装) |
| MODULE-makefile-env | - | 未検証(テスト未実装) |
| MODULE-makefile-help | - | 未検証(テスト未実装) |
| MODULE-makefile-install | - | 未検証(テスト未実装) |
| MODULE-makefile-login | - | 未検証(テスト未実装) |
| MODULE-makefile-network | - | 未検証(テスト未実装) |
| MODULE-makefile-orch-sample | - | 未検証(テスト未実装) |
| MODULE-makefile-orch-sample-clean | - | 未検証(テスト未実装) |
| MODULE-makefile-setup | - | 未検証(テスト未実装) |
| MODULE-makefile-status | - | 未検証(テスト未実装) |
| MODULE-makefile-uninstall | - | 未検証(テスト未実装) |
| MODULE-makefile-update-claude | - | 未検証(テスト未実装) |
| MODULE-makefile-upgrade | - | 未検証(テスト未実装) |
| MODULE-makefile-volumes | - | 未検証(テスト未実装) |

## 未検証(テスト未実装)の全件

| # | 対象 | なぜ未実装か | 解消の条件 |
|---|---|---|---|
| 1 | FR-env-10 — 受入基準 1(正常系) | 自動テストランナーを設けない方針(`DSN-test-01` / `SR-32`)。実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 2 | NFR-ops-03 — 操作の一覧性 | 自動テストランナーを設けない方針(`DSN-test-01` / `SR-32`)。実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 3 | MODULE-makefile-build — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 4 | MODULE-makefile-build-claude — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 5 | MODULE-makefile-build-claude-vnc — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 6 | MODULE-makefile-build-docker-proxy — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 7 | MODULE-makefile-build-orchestrator — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 8 | MODULE-makefile-clean — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 9 | MODULE-makefile-env — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 10 | MODULE-makefile-help — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 11 | MODULE-makefile-install — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 12 | MODULE-makefile-login — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 13 | MODULE-makefile-network — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 14 | MODULE-makefile-orch-sample — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 15 | MODULE-makefile-orch-sample-clean — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 16 | MODULE-makefile-setup — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 17 | MODULE-makefile-status — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 18 | MODULE-makefile-uninstall — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 19 | MODULE-makefile-update-claude — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 20 | MODULE-makefile-upgrade — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 21 | MODULE-makefile-volumes — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |

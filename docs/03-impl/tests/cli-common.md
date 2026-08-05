---
id: cli-common
scope: MOD-cli-common
version: 1.1.0
updated: 2026-08-04
source:
  - docs/01-requirements/functional.md
  - docs/02-design/system.md
summary: MOD-cli-common(CLI 共有基盤の11関数)の受入基準⇄テスト対応
keywords: [テスト]
verified:
  at: 2026-08-05
  version: 1.1.0
  against:
    - doc: docs/01-requirements/functional.md
      version: 1.6.0
    - doc: docs/02-design/system.md
      version: 2.3.0
---
# MOD-cli-common のテスト対応

## 受入基準 ⇄ テスト対応表

<!-- 受入基準 `FR-env-01` 16・17 は `start` / `stop` / `logout` / `reset` / `login` / `login-codex` の6コマンドすべてに効くが、
     振る舞いの実体は共有基盤の `MODULE-cli-common-lock` である。重複を作らないため、
     対応表は主担当である本ファイルだけが持つ。実機確認は6コマンドすべてについて実施する。 -->

| 要件 ID | 受入基準 # | 種別 | レベル | テスト識別子 | 状態 |
|---|---|---|---|---|---|
| FR-env-01 | 16 | 異常系 | E2E | E2E-01(実機確認手順。6コマンドすべて) | 未検証(テスト未実装) |
| FR-env-01 | 17 | 境界値 | E2E | E2E-01(実機確認手順) | 未検証(テスト未実装) |
| FR-env-05 | 2 | 正常系 | E2E | E2E-01(実機確認手順) | 未検証(テスト未実装) |
| FR-env-07 | 4 | 正常系 | E2E | E2E-01(実機確認手順) | 未検証(テスト未実装) |
| FR-env-10 | 4 | 正常系 | E2E | E2E-01(実機確認手順) | 未検証(テスト未実装) |
| FR-env-11 | 8 | 異常系 | E2E | E2E-01(実機確認手順) | 未検証(テスト未実装) |
| NFR-ops-02 | — | 非機能 | E2E | E2E-01(実機確認手順) | 未検証(テスト未実装) |

## 契約の結合テスト

| 契約 ID | 相手 | テスト識別子 | 状態 |
|---|---|---|---|
| (なし) | — | - | 対象外(理由: 02 の「結合テスト対象」でこのモジュールが責任を持つ契約は無い) |

## 機能間連携仕様書 ⇄ テスト

| MODULE-ID | テスト識別子 | 状態 |
|---|---|---|
| MODULE-cli-common-container-exists | - | 未検証(テスト未実装) |
| MODULE-cli-common-container-name | - | 未検証(テスト未実装) |
| MODULE-cli-common-dev-agent-path | - | 未検証(テスト未実装) |
| MODULE-cli-common-ensure-infrastructure | - | 未検証(テスト未実装) |
| MODULE-cli-common-get-novnc-url | - | 未検証(テスト未実装) |
| MODULE-cli-common-image-exists | - | 未検証(テスト未実装) |
| MODULE-cli-common-is-running | - | 未検証(テスト未実装) |
| MODULE-cli-common-lock | - | 未検証(テスト未実装) |
| MODULE-cli-common-require-setup | - | 未検証(テスト未実装) |
| MODULE-cli-common-resolve-container-user | - | 未検証(テスト未実装) |
| MODULE-cli-common-select-ssh-keys | - | 未検証(テスト未実装) |
| MODULE-cli-common-write-project-ssh-keys | - | 未検証(テスト未実装) |

## 未検証(テスト未実装)の全件

| # | 対象 | なぜ未実装か | 閉じる予定 |
|---|---|---|---|
| 1 | FR-env-01 — 受入基準 16(異常系) | 自動テストランナーを設けない方針(`DSN-test-01` / `SR-32`)。2つのコマンドを同時に走らせる必要があるため実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 2 | FR-env-01 — 受入基準 17(境界値) | 自動テストランナーを設けない方針(`DSN-test-01` / `SR-32`)。ロック残骸を人為的に作る必要があるため実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 3 | FR-env-05 — 受入基準 2(正常系) | 自動テストランナーを設けない方針(`DSN-test-01` / `SR-32`)。実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 4 | FR-env-07 — 受入基準 4(正常系) | 自動テストランナーを設けない方針(`DSN-test-01` / `SR-32`)。実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 5 | FR-env-10 — 受入基準 4(正常系) | 自動テストランナーを設けない方針(`DSN-test-01` / `SR-32`)。実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 6 | FR-env-11 — 受入基準 8(異常系) | 自動テストランナーを設けない方針(`DSN-test-01` / `SR-32`)。実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 7 | NFR-ops-02 — OS 依存をホスト CLI に閉じる | 自動テストランナーを設けない方針(`DSN-test-01` / `SR-32`)。実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 8 | MODULE-cli-common-container-exists — 機能全体 | シェル実装のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 9 | MODULE-cli-common-container-name — 機能全体 | シェル実装のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 10 | MODULE-cli-common-dev-agent-path — 機能全体 | シェル実装のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 11 | MODULE-cli-common-ensure-infrastructure — 機能全体 | シェル実装のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 12 | MODULE-cli-common-get-novnc-url — 機能全体 | シェル実装のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 13 | MODULE-cli-common-image-exists — 機能全体 | シェル実装のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 14 | MODULE-cli-common-is-running — 機能全体 | シェル実装のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 15 | MODULE-cli-common-lock — 機能全体 | シェル実装のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 16 | MODULE-cli-common-require-setup — 機能全体 | シェル実装のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 17 | MODULE-cli-common-resolve-container-user — 機能全体 | シェル実装のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 18 | MODULE-cli-common-select-ssh-keys — 機能全体 | シェル実装のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 19 | MODULE-cli-common-write-project-ssh-keys — 機能全体 | シェル実装のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |

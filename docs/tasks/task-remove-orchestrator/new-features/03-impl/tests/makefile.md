---
target: docs/03-impl/tests/makefile.md
change: replace
version_bump: minor
sections:
  - "## 機能間連携仕様書 ⇄ テスト"
  - "## 未検証(テスト未実装)の全件"
  - "## テスト設計の判断"
anchors:
  - { section: "## テスト設計の判断", after: "## 未検証(テスト未実装)の全件" }
deletes: []
reason: 'オーケストレーターの全面削除にともなう `MOD-makefile` のテスト対応の更新(決定シート 概念1)。(1) `## 機能間連携仕様書 ⇄ テスト` から削除する 3 機能の行を外す: `MODULE-makefile-build-orchestrator` / `MODULE-makefile-orch-sample` / `MODULE-makefile-orch-sample-clean`(19 → 16 行)。(2) `## 未検証(テスト未実装)の全件` から同じ 3 件を外し、`#` 列を 1 から振り直す(21 → 18 行)。**`## 受入基準 ⇄ テスト対応表` と `## 契約の結合テスト` は変えない** — `MOD-makefile` の受入基準は `FR-env-10-1` と `NFR-ops-03` で、どちらも残る要件である。**あわせて `## テスト設計の判断` を新設する** — `CS19` はこの節が非空であることを要求し、このファイルはそれを持っていなかった(`docs/issues/084` が 03-impl/tests/ の全 32 ファイルについて追跡している欠落である)。本タスクがこのファイルを触る以上、節を置かずに通すことはできない。**本タスクで解消するのはこのファイルの分だけで、`084` は残りのファイルについて開いたままにする**'
reflected: 2026-08-10
---

## 機能間連携仕様書 ⇄ テスト

| MODULE-ID | テスト識別子 | 状態 |
|---|---|---|
| MODULE-makefile-build | - | 未検証(テスト未実装) |
| MODULE-makefile-build-claude | - | 未検証(テスト未実装) |
| MODULE-makefile-build-claude-vnc | - | 未検証(テスト未実装) |
| MODULE-makefile-build-docker-proxy | - | 未検証(テスト未実装) |
| MODULE-makefile-clean | - | 未検証(テスト未実装) |
| MODULE-makefile-env | - | 未検証(テスト未実装) |
| MODULE-makefile-help | - | 未検証(テスト未実装) |
| MODULE-makefile-install | - | 未検証(テスト未実装) |
| MODULE-makefile-login | - | 未検証(テスト未実装) |
| MODULE-makefile-network | - | 未検証(テスト未実装) |
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
| 7 | MODULE-makefile-clean — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 8 | MODULE-makefile-env — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 9 | MODULE-makefile-help — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 10 | MODULE-makefile-install — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 11 | MODULE-makefile-login — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 12 | MODULE-makefile-network — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 13 | MODULE-makefile-setup — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 14 | MODULE-makefile-status — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 15 | MODULE-makefile-uninstall — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 16 | MODULE-makefile-update-claude — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 17 | MODULE-makefile-upgrade — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 18 | MODULE-makefile-volumes — 機能全体 | Makefile のため自動テストランナーが無く実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |

## テスト設計の判断

<!-- このファイルのテストの作り方(DS-01 で AI が決めた部分)の理由を置く。何を検証するかは 01 が正である。 -->

- 判断なし: このファイルが持つ全 18 行はいずれも `未検証(テスト未実装)` であり、テストの作り方を選ぶ余地が生じていない。Makefile に自動テストランナーを設けないのは `DSN-test-01` / `SR-32` の既定であり、そこから動かしていない

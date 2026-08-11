---
target: docs/03-impl/tests/makefile.md
change: replace
version_bump: patch
sections:
  - "## 未検証(テスト未実装)の全件"
  - "## テスト設計の判断"
deletes: []
reason: 'issue 077(条項ID への移行が「受入基準 ⇄ テスト対応表」だけに適用され、「未検証(テスト未実装)の全件」節の「対象」列が旧表記のまま残っている)。`FR-<domain>-nn — 受入基準 N` を条項ID `FR-<domain>-nn-N` へ機械的に置き換える。**種別の注記・理由・解消の条件は1文字も変えない**(表記だけを揃える)(このファイルは 1 箇所)'
---

## 未検証(テスト未実装)の全件

| # | 対象 | なぜ未実装か | 解消の条件 |
|---|---|---|---|
| 1 | FR-env-10-1(正常系) | 自動テストランナーを設けない方針(`DSN-test-01` / `SR-32`)。実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
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

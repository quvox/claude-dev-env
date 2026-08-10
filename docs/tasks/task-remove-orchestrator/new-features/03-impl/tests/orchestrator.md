---
target: docs/03-impl/tests/orchestrator.md
change: delete
deletes: []
reason: 'オーケストレーターの全面削除(決定シート 概念1)。`MOD-orchestrator` の受入基準 ⇄ テスト対応表・契約の結合テスト・機能間連携仕様書 ⇄ テストのすべてが、削除される要件(`FR-orch-01`〜`08` / `NFR-perf-03` / `NFR-avail-01` / `NFR-sec-03` / `NFR-ops-04`)・契約(`CTR-cli-orchestrator` / `CTR-orchestrator-prompt`)・機能(`MODULE-orchestrator-*` 19 本)を対象にしている。テストの実体(`orchestrator/*_test.go`)もモジュールごと消える。`docs/issues/019` が追跡していた「実在しないテスト識別子」も、`docs/issues/059`(レビューゲートの採点基準を覆うテストが実在しない)も、対象ごと消えるので `059` を削除する'
---

削除の理由: 上の `reason` のとおり。

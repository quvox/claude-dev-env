---
target: docs/03-impl/relations/MODULE-sample-project-mathkit.md
change: delete
deletes: []
reason: 'オーケストレーターの全面削除(決定シート 概念1)。この機能の実装は `examples/orch-sample/src/mathkit/` の 5 関数で、自己検証題材ごと削除する。対応要件は `FR-orch-09`、システム要件 `SR-23`(題材は Python + 自動テスト)も 01 から消える。`docs/issues/033`(`cd examples/orch-sample && pytest` がテンプレート上では必ず失敗する)は対象ごと消えるので同 issue を削除する。**同時に `docs/03-impl/features.md` の同名の行も `種別: delete` で消す**'
---

削除の理由: 上の `reason` のとおり。

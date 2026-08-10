---
target: docs/03-impl/relations/MODULE-makefile-build-orchestrator.md
change: delete
deletes: []
reason: 'オーケストレーターの全面削除(決定シート 概念1)。この機能の実装は `Makefile` の `build-orchestrator` ターゲットで、ビルド対象の `orchestrator/` ごと削除する。対応要件は `FR-orch-01` である。`docs/issues/062`(このファイルに残る程度語「高速ループ」)は対象ごと消えるので同 issue を削除する。**同時に `docs/03-impl/features.md` の同名の行も `種別: delete` で消す**'
---

削除の理由: 上の `reason` のとおり。

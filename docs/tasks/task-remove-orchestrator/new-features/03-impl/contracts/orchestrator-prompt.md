---
target: docs/03-impl/contracts/orchestrator-prompt.md
change: delete
deletes: []
reason: 'オーケストレーターの全面削除(決定シート 概念1)。03 側の実装仕様としての `CTR-orchestrator-prompt` は、`orchestrator/worker.go` と `orchestrator/mode.go` と `orchestrator/review.go` が実際に組み立てるプロンプトと解釈する結果 JSON の形を書いている。実装(`orchestrator/`)が消えるので、写す対象が無くなる。設計側の `docs/02-design/contracts/orchestrator-prompt.md` も同時に削除する。この文書の「必須フィールドが欠けているとき」が持っていた実値も、対象の実装ごと消える'
---

削除の理由: 上の `reason` のとおり。

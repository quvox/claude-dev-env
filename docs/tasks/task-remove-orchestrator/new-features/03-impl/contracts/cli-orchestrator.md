---
target: docs/03-impl/contracts/cli-orchestrator.md
change: delete
deletes: []
reason: 'オーケストレーターの全面削除(決定シート 概念1)。03 側の実装仕様としての `CTR-cli-orchestrator` は、`claude-dev orchestrate` が `claude-orchestrator` を起動・合流させる実際の形(設定の 4 段マージ・生存判定・分岐)を書いている。実装(`claude-dev` の `orchestrate` と `orchestrator/`)が消えるので、写す対象が無くなる。設計側の `docs/02-design/contracts/cli-orchestrator.md` も同時に削除する。この文書の「設計との差異」が持っていた macOS 版の未適合(`docs/issues/003`)も、双方が消えることで解消する'
---

削除の理由: 上の `reason` のとおり。

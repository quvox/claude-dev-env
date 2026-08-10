---
target: docs/02-design/contracts/cli-orchestrator.md
change: delete
deletes: []
reason: 'オーケストレーターの全面削除(決定シート 概念1)。`CTR-cli-orchestrator` はホスト CLI(`orchestrate`)がオーケストレーターを起動・合流させるときの取り決めで、当事者は `MOD-cli-orchestrate` → `MOD-orchestrator`、対応要件は `FR-orch-01` / `FR-orch-02` / `FR-orch-05` である。当事者の 2 モジュールも 3 要件もすべて削除されるため、契約そのものが対象を持たなくなる。この契約が追跡していた `docs/issues/003`(macOS 版がコントローラの生存判定を実装しておらず契約と食い違う)も、契約と実装の双方が消えることで解消するので同 issue を削除する。**原文は `docs/orch/02.md` が保持している**(2026-08-08 の抽出物)'
reflected: 2026-08-10
---

削除の理由: 上の `reason` のとおり。

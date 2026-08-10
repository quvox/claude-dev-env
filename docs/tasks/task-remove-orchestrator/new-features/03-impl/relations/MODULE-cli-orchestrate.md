---
target: docs/03-impl/relations/MODULE-cli-orchestrate.md
change: delete
deletes: []
reason: 'オーケストレーターの全面削除(決定シート 概念1)。この機能の実装は `claude-dev` と `claude-dev-mac` の `orchestrate` サブコマンドで、ディスパッチごと削除する(サブコマンドは 18 → 17 になる)。対応要件は `FR-orch-01` / `FR-orch-02`、契約は `CTR-cli-orchestrator` で、いずれも削除される。所属モジュール `MOD-cli-orchestrate` も 02 のモジュール分割定義から消える。この機能が呼んでいた共有基盤(`MODULE-cli-common-container-name` / `-is-running` / `-require-setup` / `-resolve-container-user`)と `MODULE-cli-start` の `callers` からも本 ID を外す(それぞれ別の変更指示が持つ)。**同時に `docs/03-impl/features.md` の同名の行も `種別: delete` で消す**'
reflected: 2026-08-10
---

削除の理由: 上の `reason` のとおり。

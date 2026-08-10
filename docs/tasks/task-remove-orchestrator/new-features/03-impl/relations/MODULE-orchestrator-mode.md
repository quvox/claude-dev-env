---
target: docs/03-impl/relations/MODULE-orchestrator-mode.md
change: delete
deletes: []
reason: 'オーケストレーターの全面削除(決定シート 概念1)。この機能の実装は Go モジュール `orchestrator/` の中にあり、ディレクトリごと削除する。対応要件は `FR-orch-*` のいずれかで、要件そのものが `01-requirements/functional.md` から消える。所属モジュール `MOD-orchestrator` も `02-design/system.md` のモジュール分割定義から削除する。**同時に `docs/03-impl/features.md` の同名の行も `種別: delete` で消す**(機能表と `MODULE-*` は 1:1 であり、片側だけ消すと `CS10` / `FT3` が落ちる)'
reflected: 2026-08-10
---

削除の理由: 上の `reason` のとおり。

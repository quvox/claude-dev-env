---
target: docs/02-design/contracts/orchestrator-prompt.md
change: delete
deletes: []
reason: 'オーケストレーターの全面削除(決定シート 概念1)。`CTR-orchestrator-prompt` はオーケストレーターが worker / 対話 Claude へ渡すプロンプトと受け取る結果の取り決めで、当事者は `MOD-orchestrator` → worker / 対話 Claude、対応要件は `FR-orch-01` / `FR-orch-03` / `FR-orch-04` / `FR-orch-05` / `FR-orch-06` / `FR-orch-08` である。当事者も 6 要件もすべて削除される。この契約が持つ設計判断 `DSN-prompt-01`(指示テンプレートはイメージへ同梱)/ `DSN-prompt-02`(採点基準はタスクの完了条件のみ)/ `DSN-prompt-03`(worker へ渡す文脈は必要な最小限を選ぶ)も同時に消える — `DSN-prompt-03` は `NFR-perf-03` 第2文を 2026-08-04 に降ろした先だが、その `NFR-perf-03` も削除されるため引き取り手を必要としない。この契約が追跡していた `docs/issues/015`(列挙外の `needs_human.reason` が捨てられる)/ `docs/issues/058`(未知の `severity` が品質ゲートを通過する)/ `docs/issues/064`(`DSN-prompt-03` が共通の前置を書き落としている)も、対象の実装ごと消えるので同 issue を削除する。**原文は `docs/orch/02.md` が保持している**(2026-08-08 の抽出物)'
---

削除の理由: 上の `reason` のとおり。

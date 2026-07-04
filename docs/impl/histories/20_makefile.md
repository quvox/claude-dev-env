# 変更履歴: 20_makefile.md

> 対応文書: `docs/impl/20_makefile.md`

## 2026-06-08
- 新規作成。`Makefile` の変数・全ターゲット・マルチステージビルド構成・CLI との関係を記述。zrt-tools 削除後の最終状態（`build-claude` の `sync-zrt-tools` 依存なし）を反映。

## 2026-06-28
- AI オーケストレーター実装に伴い `build-orchestrator` ターゲット（`cd orchestrator && go build/vet/test`。ローカル build/test 用、イメージ用バイナリは base ビルドに同梱）をターゲット表に追記。詳細は 60_orchestrator.md。

## 2026-06-29
- 自己検証用サンプルの scaffold ターゲット `orch-sample`（`FORCE=1`/`SEED=1`）・`orch-sample-clean` をターゲット仕様に追加（[70_sample-project.md] / [docs/07_self-verification.md]）。

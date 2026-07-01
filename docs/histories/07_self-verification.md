## 2026-06-29（新規作成）
- 新規作成。オーケストレーター自身を、リポジトリ同梱の小さなサンプルサブプロジェクトに対して実際に動かして検証・改善するドッグフーディングの設計文書。
- 方式：テンプレート `examples/orch-sample/` と使い捨て作業コピー `workspace/orch-sample/`（独立 git リポジトリ）を分離。本番同等（イメージ同梱バイナリ）とローカルビルド高速ループ（`--workspace`/`--instructions`/`--start-executing`）の 2 系統で回す。
- サンプル設計要件（複数独立タスク・決定論的に介入を起こす irreversible タスク・タスク固有 completion・機械検証可能）と、本改訂で直す不具合に対応する検証シナリオ S1〜S5 を定義。実装仕様の正本は docs/impl/70_sample-project.md。

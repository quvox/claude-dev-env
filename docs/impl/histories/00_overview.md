# 変更履歴: 00_overview.md

> 対応文書: `docs/impl/00_overview.md`

## 2026-06-08
- 新規作成。実装全体のコンポーネント構成・制御/データフロー・Docker リソース命名・ルート直下設定ファイルの役割・実装全体の不変条件を記述。
- `docker-proxy/` の構成ファイル記載を修正。存在しない `go.sum` への言及を削除し、`main.go` / `main_test.go` / `go.mod` のみとした（実装に一致させるため）。

## 2026-06-29
- 「実装は大きく 4 系統」を 5 系統へ更新し、第 5 系統として **AI オーケストレーター（`orchestrator/`）** と自己検証用サンプル（`examples/orch-sample/`）を明記（これまで overview に未掲載だった orchestrator を補完）。

## 2026-07-18（Chrome プロファイルをコンテナごとに分離）
- ボリューム一覧の記述を更新。共有ボリューム（`claude-dev-auth` / `claude-dev-history` / `claude-dev-config`）と、コンテナごとのボリューム（`claude-dev-chrome-<name>`＝Chrome プロファイル、`claude-dev-vm-<name>`＝VM モード）を区別して明記した。旧記載の固定名 `claude-dev-chrome-data`（全コンテナ共有）は廃止（詳細は 10_cli.md 履歴参照）。

# INDEX — ドキュメント索引

プロジェクト関連ドキュメントの地図。情報や文書を探すときは**まずここ**を見る（各パスの存在は
念のため確認すること。ズレていれば通常の探索にフォールバックし、更新を提案する）。
体系の考え方は `docs/README.md` / `docs/WORKFLOW-GUIDE.md` を参照。

## 規範・ガイド（汎用／キット管理）

| パス | 概要 |
|---|---|
| CLAUDE.md | プロジェクト運用規範（4層 document-driven 開発のルール）。最上位の正 |
| docs/README.md | docs/ 体系の説明（4階層の役割・ディレクトリ地図） |
| docs/WORKFLOW-GUIDE.md | 人間向け運用ガイド（新規開発／変更／ブラウンフィールドの手順） |
| docs/ONBOARDING.md | メンバー向け導入資料 |
| docs/RATIONALE.md | 体系の背景・設計理由 |
| docs/_templates/ | 各ドキュメントのテンプレート（生成・更新時に必ず参照） |

## _steering（プロジェクト共通前提。全セッション常時読込）

| パス | 概要 |
|---|---|
| docs/_steering/product.md | プロダクト概要（何であり誰の何を解決するか） |
| docs/_steering/tech.md | 技術スタックと標準コマンド（テスト/ビルドの唯一の正） |
| docs/_steering/structure.md | リポジトリ構造とモジュール境界の規約 |

## 00-requests（要求・WHY／判断台帳）

| パス | 概要 |
|---|---|
| docs/00-requests/request.md | 要求定義（隔離Docker開発環境＋AIオーケストレーター。並列開発力の向上） |
| docs/00-requests/decisions.md | 決定台帳（決定20・委任2・要確認3） |
| docs/00-requests/glossary.md | 用語集 |
| docs/00-requests/acceptance.md | 受入シナリオ AS-1〜5 |

## 01-requirements（要件・WHAT／ユースケース）

| パス | 概要 |
|---|---|
| docs/01-requirements/core.md | 開発環境基盤の要件（コンテナ/認証/SSH/FW/ブラウザ/ポート/docker-proxy/VM/配布/mac）。UC-1〜3 |
| docs/01-requirements/orchestration.md | オーケストレーションの要件（2モード/介入/品質ゲート/復旧）。UC-4〜5 |

## 02-design（全体設計・モジュール分割定義）

| パス | 概要 |
|---|---|
| docs/02-design/system.md | 全体設計。14モジュール分割定義・契約・UI設計・テスト戦略・E2Eシナリオ一覧 |

## 03-impl（実装説明書。モジュール1ファイル）

| パス | 対応コード |
|---|---|
| docs/03-impl/cli.md | `claude-dev`（Linux CLI） |
| docs/03-impl/cli-mac.md | `claude-dev-mac`（macOS 差分） |
| docs/03-impl/makefile.md | `Makefile` |
| docs/03-impl/entrypoint.md | `scripts/entrypoint-claude.sh` |
| docs/03-impl/firewall.md | `scripts/init-firewall-claude.sh` |
| docs/03-impl/devcontainer.md | `.devcontainer/Dockerfile.claude` / `Dockerfile.docker-proxy` |
| docs/03-impl/docker-proxy.md | `docker-proxy/`（Go） |
| docs/03-impl/orchestrator.md | `orchestrator/`（Go） |
| docs/03-impl/sample-project.md | `examples/orch-sample/` / `scripts/orch-sample.sh` |
| docs/03-impl/vm-mode.md | `scripts/vm` / `vm-up.sh` / `vm-portsync.sh` / `vm-healthd.sh` |
| docs/03-impl/ghcr-workflow.md | `.github/workflows/ghcr-images.yml` |
| docs/03-impl/hooks.md | `scripts/save_prompt.sh` / `sendslackmsg.sh` |
| docs/03-impl/container-tools.md | `scripts/wait-limit-reset.sh` / `scripts/tmux.conf` |
| docs/03-impl/portsync.md | `scripts/dood-portsync.sh` |
| docs/03-impl/e2e.md | E2Eテスト実装（E2E-1〜5、実機＋自己検証） |

## 補助

| パス | 概要 |
|---|---|
| docs/knowledge/ | 設計判断・教訓（1知見1ファイル。仕様ドキュメントではない） |
| docs/feedback/log.md | 上流キット向けテレメトリ（質問/修正/委任判断） |
| docs/histories/ | ドキュメント変更履歴（変更発生時に追記。初期1.0.0は記録なし） |
| docs/tasks/ | AI 作業用タスク（進行中のみ存在） |

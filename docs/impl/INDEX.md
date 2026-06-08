# 実装仕様一覧 (INDEX)

> **この文書の役割**: `docs/impl/` 配下の実装仕様書群の全体構成と、各文書が対応する実装コードの一覧を示す目次。実装仕様書は要求定義・設計文書とは別種であり、**実装コードを自然言語で表現した Single Source of Truth (SSOT)** である。設計の俯瞰は `docs/02_architecture.md`、利用者向け情報は `docs/01_getting-started.md` / `docs/04_cli-reference.md` を参照。

## 実装仕様書とは

- 要件や設計を検討した後、コードを実装する前に作成・更新する。常に「成果物（実装）が**どういうものか**」を表す。
- 細かな処理コードは書かず、**データ構造・インタフェース・ロジック**を詳細に記述する。
- 各文書は「カバーする実装コード」と 1 対 1（または 1 対多）で対応し、同じソースコードが複数文書に重複して現れないようにする。

## 文書 ↔ コード 対応表

| 文書 | 対応コード | 概要 |
|------|-----------|------|
| [00_overview.md](00_overview.md) | リポジトリ全体構成 / ルート直下ファイル（`.env.example`, `.mcp.json`, `CLAUDE.md`, `README.md`, `PREPARATION.md`） | 実装全体のコンポーネント構成と制御/データフロー、ルート設定ファイルの役割 |
| [10_cli.md](10_cli.md) | `claude-dev` | CLI 本体。全サブコマンドとヘルパー関数 |
| [20_makefile.md](20_makefile.md) | `Makefile` | セットアップ・ビルド・メンテナンスのタスク定義 |
| [30_scripts.md](30_scripts.md) | `scripts/` ディレクトリ概要 / `scripts/save_prompt.sh` / `scripts/sendslackmsg.sh` / `scripts/tmux.conf` | スクリプト群の概要と、小スクリプト（hook 2 種 + tmux 設定）の仕様 |
| [31_entrypoint.md](31_entrypoint.md) | `scripts/entrypoint-claude.sh` | Claude コンテナのエントリポイント処理 |
| [32_firewall.md](32_firewall.md) | `scripts/init-firewall-claude.sh` | ブラックリスト方式ファイアウォール |
| [40_devcontainer.md](40_devcontainer.md) | `.devcontainer/Dockerfile.claude` / `.devcontainer/Dockerfile.docker-proxy` / `.devcontainer/tmux.conf` / `.zshrc` | Docker イメージのビルド仕様とビルド入力設定ファイル |
| [50_docker-proxy.md](50_docker-proxy.md) | `docker-proxy/main.go` / `docker-proxy/main_test.go` / `docker-proxy/go.mod` | Docker Socket Proxy（Go）の検査ロジックとテスト |

## カバー範囲（ディレクトリツリー）

```
claude-dev-env/
├── claude-dev              → 10_cli.md
├── Makefile                → 20_makefile.md
├── .zshrc                  → 40_devcontainer.md（ビルド入力）
├── .env.example            → 00_overview.md
├── .mcp.json               → 00_overview.md
├── scripts/
│   ├── entrypoint-claude.sh    → 31_entrypoint.md
│   ├── init-firewall-claude.sh → 32_firewall.md
│   ├── save_prompt.sh          → 30_scripts.md
│   ├── sendslackmsg.sh         → 30_scripts.md
│   └── tmux.conf               → 30_scripts.md
├── .devcontainer/
│   ├── Dockerfile.claude       → 40_devcontainer.md
│   ├── Dockerfile.docker-proxy → 40_devcontainer.md
│   └── tmux.conf               → 40_devcontainer.md
└── docker-proxy/
    ├── main.go                 → 50_docker-proxy.md
    ├── main_test.go            → 50_docker-proxy.md
    └── go.mod                  → 50_docker-proxy.md
```

## 変更履歴の管理

- 実装仕様書を変更した際の履歴は、**この文書群には書かず** `docs/impl/histories/` 配下に出力する。
- 履歴ファイルは対象の実装仕様書と同じサブディレクトリ・ファイル名で保存する（例: `30_scripts.md` の履歴 → `docs/impl/histories/30_scripts.md`）。
- 各実装仕様書本体は常に「最新の成果物」を表し、修正履歴を含めない。

---
summary: リポジトリの実装全体を俯瞰し、コンポーネントの責務・制御フロー・Dockerリソース命名・ルート設定ファイルの役割・設計上の不変条件を示す。
keywords: [ 実装仕様, コンポーネント構成, 制御フロー, Dockerリソース, 不変条件, 設計概要, CLI ]
---

# 実装全体構成 (Overview)

> **この文書の役割**: 本リポジトリの実装全体を俯瞰し、コンポーネントの責務分担・制御/データフロー・ルート直下の設定ファイルの役割を示す。個別コードの詳細仕様は各実装仕様書（[INDEX.md](INDEX.md)）へ委譲する。

## 要件（なぜ必要か）

Linux サーバ上で Claude Code を「承認待ちなし・コンテナ隔離下」で安全に常駐運用したい。利用者は任意のプロジェクトディレクトリで `claude-dev start` を実行するだけで、隔離された Claude Code 環境（必要なら GUI/Chrome 付き）を起動できる必要がある。本実装はそのための CLI・コンテナイメージ・補助プロセス群から成る。

## 要約

実装は大きく次の 5 系統に分かれる。

1. **ホスト側オーケストレーション** — `claude-dev`（Linux 版 CLI）／`claude-dev-mac`（macOS 版 CLI。→ [11_cli-mac.md](11_cli-mac.md) / [docs/09_macos-support.md](../09_macos-support.md)）と `Makefile`。Docker リソース（ネットワーク・ボリューム・イメージ）の用意、コンテナのライフサイクル管理、認証情報の受け渡し、ポートフォワードを担う。OS 依存はこのホスト側 CLI に閉じ、コンテナ内資産（Dockerfile・entrypoint・firewall・docker-proxy）は両 OS で共有する。
2. **コンテナイメージ定義** — `.devcontainer/Dockerfile.claude`（開発環境 + 任意で GUI）と `.devcontainer/Dockerfile.docker-proxy`（Docker API プロキシ）。
3. **コンテナ内ランタイム処理** — `scripts/entrypoint-claude.sh`（起動時初期化）、`scripts/init-firewall-claude.sh`（FW）、`scripts/save_prompt.sh` / `scripts/sendslackmsg.sh`（Claude Code hook）、`scripts/tmux.conf`。
4. **Docker API ガード** — `docker-proxy/`（Go: `main.go` / `main_test.go` / `go.mod`）。生 Docker ソケットを渡さず、危険な操作を拒否しつつ API を中継する。
5. **AI オーケストレーター** — `orchestrator/`（Go）。プロジェクトごとに 1 体立て、壁打ち（人間との検討）→ 実行（`claude -p` worker への並行委譲・品質ゲート・タスク単位の介入）を駆動する。イメージへ `claude-orchestrator` として同梱（→ [60_orchestrator.md](60_orchestrator.md)）。自己検証用のサンプルサブプロジェクトは `examples/orch-sample/`（→ [70_sample-project.md](70_sample-project.md) / [docs/07_self-verification.md](../07_self-verification.md)）。

## コンポーネント関係と制御フロー

```
ホスト
  claude-dev (CLI) ──┐
  Makefile        ───┤ docker build / network / volume / run
                     ▼
  ┌─ Claude コンテナ (claude-dev-claude / -vnc) ─────────────┐
  │  ENTRYPOINT: scripts/entrypoint-claude.sh               │
  │    ├─ UID/GID をホストの /workspace 所有者に追従          │
  │    ├─ 認証ファイル共有（~/.claude → /workspace/.claude） │
  │    ├─ init-firewall.sh 実行                              │
  │    ├─ CLAUDE.md へ環境情報を追記、MCP 設定（VNC 時）       │
  │    ├─ VNC/Chrome 起動（VNC 時）                          │
  │    └─ tmux セッション開始                                 │
  │  hook: save_prompt.sh / sendslackmsg.sh（任意）          │
  └──────────────────────────────────────────────────────────┘
                     │ DOCKER_HOST=tcp://claude-dev-docker-proxy:2375
                     ▼
  ┌─ Docker Socket Proxy コンテナ (claude-dev-docker-proxy) ─┐
  │  docker-proxy (Go): 危険操作を拒否し /var/run/docker.sock │
  │  へ中継                                                   │
  └──────────────────────────────────────────────────────────┘
```

詳細な設計図（認証フロー・ポートフォワード・ブラウザ操作）は `docs/02_architecture.md` を参照。

## Docker リソース命名（CLI と Makefile で共通）

| 種別 | 名前 |
|------|------|
| ネットワーク | `claude-dev-net` |
| ボリューム | `claude-dev-auth` / `claude-dev-history` / `claude-dev-config` / `claude-dev-chrome-data` |
| イメージ | `claude-dev-claude`（base） / `claude-dev-claude-vnc`（vnc） / `claude-dev-docker-proxy` |
| 共有コンテナ | `claude-dev-docker-proxy` |
| プロジェクトコンテナ | プロジェクトディレクトリ名（小文字化・記号は `-`） |
| フォワードコンテナ | `fwd-<name>-<port>` |

## ルート直下の設定ファイル

| ファイル | 役割 | 参照元 |
|----------|------|--------|
| `.env.example` → `.env` | CLI が起動時に `source` する環境設定テンプレート。`SLACK_BOT_TOKEN` / `SLACK_CHANNEL` 等を定義可能。`.env` は `.gitignore` 済み | `claude-dev`（先頭で `source`）、`make env` / `claude-dev setup` が生成 |
| `.mcp.json` | リポジトリ自身を Claude Code で扱う際の MCP サーバー設定（`chrome-devtools`）。コンテナ内では entrypoint が `/workspace/.mcp.json` を別途生成・マージする | 開発時の Claude Code |
| `CLAUDE.md` | コンテナ内 Claude Code 向けの開発ルール。`claude-dev start` が `~/CLAUDE.md` として読み取り専用マウントし、entrypoint が `/workspace/CLAUDE.md` にも環境情報を追記する | `claude-dev`（マウント）、`scripts/entrypoint-claude.sh`（追記） |
| `README.md` | リポジトリの概要・クイックスタート・ファイル構成 | 利用者 |
| `PREPARATION.md` | ホストサーバ側の事前準備手順（Docker 導入等）を説明する利用者向け文書 | 利用者 |
| `.zshrc` | コンテナイメージに焼き込む既定のユーザー `.zshrc`（→ [40_devcontainer.md](40_devcontainer.md)） | `Dockerfile.claude` の COPY |

## 設計上の不変条件（実装全体で守られる前提）

- **生 Docker ソケットをコンテナに渡さない**。Docker API はすべて Proxy 経由（`DOCKER_HOST`）。
- **SSH 秘密鍵ファイルをマウントしない**。署名は ssh-agent ソケット転送で行う。
- **認証ファイル（`.credentials.json`, `.claude.json`）のみ**をコンテナ間共有し、セッション・設定はプロジェクトごとに独立。
- **コンテナ内ユーザーの UID/GID はホストに一致**させ、`/workspace` の編集で所有権の齟齬を生まない。

# Claude Code 安全開発環境

Linux サーバ上で Claude Code を承認待ちなし・安全に使うための Docker 環境。

任意のプロジェクトディレクトリで `claude-dev start` を実行するだけで、コンテナ隔離された Claude Code 環境が起動する。

## 特徴

| 課題 | 解決方法 |
|------|----------|
| 承認待ちで止まる | コンテナ隔離下で `--dangerously-skip-permissions` |
| SSH 切断で中断 | tmux でセッション永続化 |
| 複数プロジェクト | プロジェクトごとに独立コンテナを起動 |

## アーキテクチャ

```
Linux サーバ (SSH)
│
├── Makefile         セットアップ・ビルド・管理
├── claude-dev CLI   日常の開発操作（どこからでも実行可能）
│
├── プロジェクトコンテナ（都度起動）
│   ├── claude-project-a     ~/repos/project-a → /workspace
│   ├── claude-project-b     ~/repos/project-b → /workspace
│   └── ...                  同時に複数起動可能
│
├── claude-dev-net           コンテナ間ネットワーク
│
└── claude-dev-auth (volume) 認証情報（~/.claude/ に直接マウント）
```

## クイックスタート

```bash
# 1. クローン & 設定
git clone https://github.com/quvox/claude-dev-env.git ~/claude-dev-env
cd ~/claude-dev-env
cp .env.example .env && vim .env

# 2. セットアップ（初回のみ。ビルド + PATH 登録）
make setup

# 3. OAuth ログイン
make login

# 4. 開発開始
cd ~/repos/my-project
claude-dev start
```

> `make setup` は .env 作成、Docker ネットワーク/ボリューム作成、イメージビルド、CLI の PATH 登録を一括で行う。個別に実行する場合は `make help` を参照。

## 日常の使い方

```bash
# プロジェクトで作業開始
cd ~/repos/my-project
claude-dev start              # 起動 & tmux 接続

# tmux 内で Claude Code を起動
claude

# 切断（SSH 切れても OK）
Ctrl-B D

# 再接続
claude-dev start              # 同じディレクトリなら自動再接続
claude-dev attach my-project  # 名前指定も可

# 別プロジェクトも同時に
cd ~/repos/other-project
claude-dev start

# Chrome が必要なプロジェクト（OAuth 認証、Web テスト等）
cd ~/repos/web-project
claude-dev start --chrome     # VNC 付きで起動
# → http://localhost:6080/vnc.html で Chrome を操作

# 管理
claude-dev list               # 実行中セッション一覧（noVNC URL も表示）
claude-dev stop my-project    # 停止
claude-dev upgrade            # Claude Code 更新
make status                   # 全体の状態確認
```

## セキュリティ

多層防御で Claude Code の暴走リスクを軽減する。

1. **Docker コンテナ隔離** — ホストファイルシステムへのアクセスを遮断
2. **マウント制限** — `~/.ssh`, `~/.aws`, `.env` 等はコンテナに存在しない
3. **認証情報の保護** — 専用ボリュームにマウント。ファイアウォールで窃取先をブロック
4. **Docker ソケット非共有** — コンテナ脱獄を防止
5. **ブラックリスト FW** — ペーストサイト、Webhook、メタデータエンドポイント、SMTP、外部 SSH をブロック
6. **非 root 実行** — ホストと同じユーザー名で実行。UID/GID はホストに自動追従
7. **git ロールバック** — 変更はすべて `git diff` で確認、`git checkout` で復元可能

## ドキュメント

| ドキュメント | 内容 |
|------------|------|
| [docs/getting-started.md](docs/getting-started.md) | インストール手順と基本的な使い方 |
| [docs/architecture.md](docs/architecture.md) | システム設計・コンテナ構成・認証フロー |
| [docs/security.md](docs/security.md) | 脅威モデルと防御層の詳細 |
| [docs/cli-reference.md](docs/cli-reference.md) | 全コマンドのリファレンス |
| [docs/customization.md](docs/customization.md) | ファイアウォール・CLAUDE.md・tmux 等のカスタマイズ |

## ファイル構成

```
claude-dev-env/
├── Makefile                           セットアップ・ビルド・管理タスク
├── claude-dev                         CLI ツール本体
├── .env.example                       設定テンプレート
├── CLAUDE.md                          コンテナ内の Claude Code 向け指示
├── .devcontainer/
│   └── Dockerfile.claude              Claude Code コンテナ (Ubuntu 24.04)
├── scripts/
│   ├── init-firewall-claude.sh        ブラックリスト FW
│   ├── entrypoint-claude.sh           コンテナ起動スクリプト
│   └── tmux.conf                      tmux 設定
└── docs/                              ドキュメント
```

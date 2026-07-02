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
│   ├── project-a  (VNC あり)   Chrome + noVNC + chrome-devtools MCP
│   ├── project-b  (--no-vnc)   軽量・ブラウザなし
│   └── ...                     同時に複数起動可能
│
├── claude-dev-docker-proxy (共有) Docker Socket Proxy（危険操作をブロック）
├── claude-dev-net              コンテナ間ネットワーク
│
├── claude-dev-auth (volume)    認証情報
├── claude-dev-config (volume)  共有シェル設定
├── claude-dev-chrome-data (volume) Chrome プロファイル
└── claude-dev-history (volume) コマンド履歴
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
Ctrl-_ D

# 再接続
claude-dev start              # 同じディレクトリなら自動再接続
claude-dev attach my-project  # 名前指定も可

# 別プロジェクトも同時に
cd ~/repos/other-project
claude-dev start

# VNC ありならブラウザで Chrome を確認できる
# → noVNC URL は起動時に表示される

# ブラウザ不要なプロジェクトは軽量モードで起動
cd ~/repos/cli-tool
claude-dev start --no-vnc

# Web アプリのポートを動的にフォワード
claude-dev forward 3000       # → host:8100 → container:3000
claude-dev ports              # アクティブなフォワード一覧
claude-dev unforward 3000     # フォワード解除

# 管理
claude-dev list               # 実行中セッション一覧（noVNC URL + フォワード状況も表示）
claude-dev stop my-project    # 停止（フォワード用プロキシも自動クリーンアップ）
claude-dev upgrade            # Claude Code + Chrome + Docker Proxy 更新
make status                   # 全体の状態確認
```

## VM モード（Docker を多用する開発）

bind mount や docker compose を使う「Docker 中心のシステム」を開発する場合、既定構成（Docker Socket Proxy 経由）ではホスト bind mount が使えない。**VM モード**は、コンテナ内に KVM のゲスト VM を立て、その中で**ネイティブ Docker**（bind mount・compose・privileged 可）を動かすことでこれを解決する。

```bash
cd ~/repos/docker-heavy-project
claude-dev start --vm          # ゲスト VM を起動（--kvm を含意。ホストに /dev/kvm が必要）

# 起動後は普段どおり docker を使うだけ（透過）。裏でゲスト VM の dockerd を指している。
docker compose up              # bind mount もそのまま効く（/workspace 配下のコードは即反映）

# アプリのポートも転送したい場合（起動時に環境変数で指定）
VM_PORTS=3000,8080 claude-dev start --vm

# VM の操作（コンテナ内ヘルパー）
vm status                      # QEMU / dockerd / virtiofs の状態
vm shell                       # ゲストに入る（ssh）
vm logs                        # 起動・ゲストのログ
```

- **仕組み**: ホスト → claude コンテナ → ゲスト VM → VM 内 Docker の層構成。コードは virtiofs で `/workspace` を**同一パス共有**（ホストでの編集がゲスト内 Docker に**ライブ反映**）。`docker` は `DOCKER_HOST` でゲストの daemon を指すため、操作は普段どおり。
- **前提**: ホストに `/dev/kvm`（ベアメタル or ネスト仮想化有効なクラウド）。無い場合は `--vm` は中止する。既存環境から使うにはイメージ再ビルド（`make build-claude` / `claude-dev upgrade`）が必要。
- **初回**: ゲストイメージのダウンロードと provision に数分かかる（以降のブートは短い）。
- **注意点**: bind mount の source は `/workspace` 配下のみ有効。ゲスト内サービスは `claude-dev forward` で公開する。詳細は起動時に生成される `/workspace/VM_DEV.md`、設計は [docs/08_vm-mode.md](docs/08_vm-mode.md) を参照。
- 既定は従来の軽量コンテナ。VM モードは Docker を多用する案件のときだけ使う（重い・`/dev/kvm` 必須）。

## セキュリティ

多層防御で Claude Code の暴走リスクを軽減する。

1. **Docker コンテナ隔離** — ホストファイルシステムへのアクセスを遮断
2. **マウント制限** — SSH 秘密鍵、`~/.aws`, `.env` 等はコンテナに存在しない
3. **認証情報の保護** — 専用ボリュームにマウント。ファイアウォールで窃取先をブロック
4. **Docker Socket Proxy** — 生ソケットを渡さず、プロキシ経由でホストマウント・特権モード等の危険操作をブロック
5. **SSH agent 転送** — 秘密鍵ファイルを渡さず、agent ソケット経由で署名操作のみ許可
6. **ブラックリスト FW** — ペーストサイト、Webhook、メタデータエンドポイント、SMTP、外部 SSH をブロック
7. **非 root 実行** — ホストと同じユーザー名・UID/GID で実行（ビルド時に一致させる）
8. **git ロールバック** — 変更はすべて `git diff` で確認、`git checkout` で復元可能

## ドキュメント

| ドキュメント | 内容 |
|------------|------|
| [docs/01_getting-started.md](docs/01_getting-started.md) | インストール手順と基本的な使い方 |
| [docs/02_architecture.md](docs/02_architecture.md) | システム設計・コンテナ構成・認証フロー |
| [docs/03_security.md](docs/03_security.md) | 脅威モデルと防御層の詳細 |
| [docs/04_cli-reference.md](docs/04_cli-reference.md) | 全コマンドのリファレンス |
| [docs/05_customization.md](docs/05_customization.md) | ファイアウォール・CLAUDE.md・tmux・hooks/env 等のカスタマイズ |
| [docs/08_vm-mode.md](docs/08_vm-mode.md) | VM モード（QEMU+virtiofs でゲスト VM 内のネイティブ Docker を使う）の設計 |
| [docs/impl/INDEX.md](docs/impl/INDEX.md) | 実装仕様書（コードと 1 対 1 の Single Source of Truth）一覧 |

## ファイル構成

```
claude-dev-env/
├── Makefile                           セットアップ・ビルド・管理タスク
├── claude-dev                         CLI ツール本体
├── .env.example                       設定テンプレート
├── CLAUDE.md                          コンテナ内の Claude Code 向け指示
├── .devcontainer/
│   ├── Dockerfile.claude              Claude コンテナ (マルチステージ: base → vnc)
│   └── Dockerfile.docker-proxy        Docker Socket Proxy コンテナ
├── docker-proxy/                      Docker Socket Proxy ソースコード
├── scripts/
│   ├── init-firewall-claude.sh        ブラックリスト FW
│   ├── entrypoint-claude.sh           Claude コンテナ起動スクリプト
│   ├── vm-up.sh / vm                  VM モード: ゲスト VM 起動・操作ヘルパー
│   ├── VM_DEV.md.tmpl                 VM モードのエージェント向け情報テンプレート
│   └── tmux.conf                      tmux 設定（prefix: Ctrl-_）
└── docs/                              ドキュメント
```

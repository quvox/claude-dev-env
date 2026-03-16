# セキュリティ設計

## 脅威モデル

Claude Code を `--dangerously-skip-permissions` で実行すると、コマンド実行やファイル操作が無制限になる。想定される脅威:

| 脅威 | 説明 |
|------|------|
| ファイル窃取 | プロジェクト外のファイル（SSH 鍵、AWS 認証等）の読み取り |
| 認証情報窃取 | OAuth トークンの読み取り・外部送信 |
| データ外部送信 | ソースコードや秘密情報をペーストサイトや Webhook へ送信 |
| メタデータアクセス | クラウドインスタンスのメタデータから IAM 認証情報を取得 |
| リバースシェル | 外部への SSH 接続やトンネリングで永続的アクセスを確立 |
| メール送信 | SMTP 経由でデータを送信 |
| コンテナ脱獄 | Docker ソケット経由でホストを操作 |

## 防御層

### 1. Docker コンテナ隔離

Claude Code はコンテナ内で実行される。ホストのファイルシステムには直接アクセスできない。

**マウントされるもの:**
- プロジェクトディレクトリ → `/workspace`（読み書き）
- 認証情報 → `~/.claude-auth/`（読み取り専用）
- CLAUDE.md、tmux.conf（読み取り専用）
- コマンド履歴ボリューム

**マウントされないもの:**
- `~/.ssh/`（SSH 鍵）
- `~/.aws/`（AWS 認証）
- `~/.config/`（各種設定）
- `.env`（環境変数ファイル）
- Docker ソケット

### 2. 認証情報の保護

OAuth トークンは `claude-dev-auth` ボリュームに保存され、プロジェクトコンテナには読み取り専用でマウントされる。

```
claude-dev-auth ボリューム
    │
    ├── login 時: 一時コンテナから書き込み
    │
    └── start 時: /home/devuser/.claude-auth/ (RO) としてマウント
         │
         └── entrypoint が ~/.claude.json にコピー
              → Claude Code が認証に使用
```

**制限事項:** Claude Code は `~/.claude.json` を読み取れるため、認証情報の完全な隔離はできない。ファイアウォールによる窃取先のブロックと組み合わせて防御する。

### 3. ブラックリスト方式ファイアウォール

iptables + ipset による送信トラフィック制御。

#### ブロック対象ドメイン

| カテゴリ | ドメイン |
|----------|---------|
| ペーストサイト | pastebin.com, paste.ee, hastebin.com, dpaste.org |
| ファイル共有 | transfer.sh, file.io, 0x0.st, ix.io, sprunge.us |
| Webhook テスト | webhook.site, requestbin.com, hookbin.com |
| トンネリング | ngrok.io, ngrok-free.app, localtunnel.me, serveo.net |

#### ブロック対象 IP/ポート

| 対象 | 理由 |
|------|------|
| `169.254.169.254` | AWS/GCP メタデータエンドポイント |
| `169.254.169.253` | Azure メタデータエンドポイント |
| TCP 25, 465, 587 | SMTP（メール送信によるデータ窃取） |
| TCP 22（外部向け） | リバースシェル防止（内部ネットワークは許可） |

#### デフォルトポリシー

デフォルトは **ACCEPT**（ブラックリスト方式）。Claude Code が npm, pip, apt, GitHub 等に自由にアクセスできる利便性を維持しつつ、既知の危険な宛先をブロックする。

### 4. Docker ソケット非公開

Docker ソケット (`/var/run/docker.sock`) はどのコンテナにもマウントされない。これにより:

- コンテナから他のコンテナを操作できない
- ファイアウォールを迂回する新しいコンテナを起動できない
- ホストのファイルシステムにアクセスする特権コンテナを作成できない

### 5. 非 root 実行

Claude コンテナは entrypoint で初期設定後、`devuser` に切り替わる。UID/GID はホストの `/workspace` 所有者に自動追従する。

### 6. git による変更の可逆性

プロジェクトディレクトリはホスト上の git リポジトリそのもの。Claude Code が行った変更はすべて `git diff` で確認でき、`git checkout` で元に戻せる。

## ブラックリストの限界と対策

ブラックリスト方式は利便性を優先した設計であり、すべてのデータ窃取を防げるわけではない。

### 防げないケース

- 未知のドメインへの送信
- DNS 経由のデータ窃取（DNS tunneling）
- 許可されたサービス（GitHub 等）を経由した間接的な送信

### 強化方法

#### 本番環境ドメインの追加

`scripts/init-firewall-claude.sh` の `BLACKLIST_DOMAINS` 配列に追加:

```bash
BLACKLIST_DOMAINS=(
    # 既存のリスト...

    # 本番環境
    "production-api.yourcompany.com"
    "prod-db.yourcompany.com"
)
```

#### ホワイトリスト方式への切替

最も安全な構成。必要なドメインのみ許可する:

```bash
# デフォルトポリシーを DROP に変更
iptables -P OUTPUT DROP

# 必要なドメインのみ許可
iptables -A OUTPUT -d <npm-registry-ip> -j ACCEPT
iptables -A OUTPUT -d <github-ip> -j ACCEPT
iptables -A OUTPUT -d <anthropic-api-ip> -j ACCEPT
```

ホワイトリスト方式では `npm install` や `git clone` が制限されるため、必要なドメインを事前に洗い出す必要がある。

## Samba のセキュリティ

- デフォルトのパスワード (`claude`) は必ず変更すること
- Samba ポート (445) はサーバのファイアウォールで信頼できるネットワークからのみアクセスを許可すること
- 共有ディレクトリの範囲は `SAMBA_SHARE_DIR` で最小限に設定すること

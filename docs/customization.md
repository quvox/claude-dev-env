# カスタマイズガイド

## ファイアウォールのカスタマイズ

### ブラックリストにドメインを追加する

`scripts/init-firewall-claude.sh` の `BLACKLIST_DOMAINS` 配列を編集する:

```bash
BLACKLIST_DOMAINS=(
    # 既存のリスト...

    # 自社の本番環境
    "production-api.example.com"
    "prod-db.example.com"

    # その他のブロックしたいサービス
    "some-dangerous-site.com"
)
```

変更後、イメージを再ビルドしてコンテナを再起動すると反映される:

```bash
make build-claude
claude-dev stop my-project
cd ~/repos/my-project
claude-dev start
```

### ポートを追加でブロックする

同ファイル内に iptables ルールを追加する:

```bash
# FTP をブロック
iptables -A OUTPUT -p tcp --dport 21 -j REJECT

# MySQL への直接接続をブロック
iptables -A OUTPUT -p tcp --dport 3306 -j REJECT
```

### ホワイトリスト方式に切り替える

セキュリティを最大化する場合。`scripts/init-firewall-claude.sh` を編集:

```bash
# デフォルトポリシーを DROP に変更
iptables -P OUTPUT DROP

# 必要な宛先のみ許可
# ローカル
iptables -A OUTPUT -o lo -j ACCEPT
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# DNS
iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
iptables -A OUTPUT -p tcp --dport 53 -j ACCEPT

# npm registry
iptables -A OUTPUT -d registry.npmjs.org -p tcp --dport 443 -j ACCEPT

# GitHub
iptables -A OUTPUT -d github.com -p tcp --dport 443 -j ACCEPT

# Anthropic API
iptables -A OUTPUT -d api.anthropic.com -p tcp --dport 443 -j ACCEPT

# PyPI
iptables -A OUTPUT -d pypi.org -p tcp --dport 443 -j ACCEPT
```

## Claude Code の更新

Claude Code はネイティブインストーラー (`curl -fsSL https://claude.ai/install.sh | sh`) でインストールされる。更新するにはイメージを再ビルドする:

```bash
make upgrade
```

実行中のコンテナには反映されないので、再起動が必要:

```bash
claude-dev stop my-project
cd ~/repos/my-project
claude-dev start
```

## CLAUDE.md のカスタマイズ

### グローバル設定（全プロジェクト共通）

`<claude-dev-env>/CLAUDE.md` を編集する。このファイルはコンテナ内のホームディレクトリに読み取り専用でマウントされ、Claude Code がどのプロジェクトでも読み取る。

```markdown
# CLAUDE.md - コンテナ内開発環境

## 環境情報
- Docker コンテナ内で実行中
- API 通信は直接 Anthropic API に接続

## 共通ルール
- テストは必ず実行してからコミットすること
- 日本語でコメントを書くこと
```

### プロジェクト固有の設定

プロジェクトのルートディレクトリに `CLAUDE.md` を配置する:

```markdown
# CLAUDE.md - my-project

## 技術スタック
- TypeScript + React
- PostgreSQL

## コーディング規約
- ...
```

プロジェクトの `CLAUDE.md` はグローバル設定より優先される（より具体的なパスが優先）。

## tmux 設定のカスタマイズ

`scripts/tmux.conf` を編集する。主な設定項目:

```bash
# プレフィックスキーの変更（例: Ctrl-A に変更する場合）
set -g prefix C-a
unbind C-b
bind C-a send-prefix

# 履歴の上限変更
set -g history-limit 100000

# マウス操作の無効化
set -g mouse off
```

変更後、イメージの再ビルドは不要（読み取り専用マウントで直接反映）。ただし実行中のコンテナには再起動が必要:

```bash
claude-dev stop my-project
cd ~/repos/my-project
claude-dev start
```

## Claude コンテナに追加パッケージをインストールする

### 一時的（コンテナ再起動で消える）

コンテナ内で直接インストール:

```bash
# tmux セッション内で
sudo apt-get update && sudo apt-get install -y <package>
```

### 恒久的（Dockerfile を編集）

`.devcontainer/Dockerfile.claude` の apt-get 行に追加:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 既存のパッケージ...
    # 追加パッケージ
    your-package \
    && rm -rf /var/lib/apt/lists/*
```

再ビルド:

```bash
make build-claude
```

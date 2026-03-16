# クイックスタートガイド

## 前提条件

- Linux サーバ（Ubuntu 22.04+ / Debian 12+ 推奨）
- Docker Engine 24+ & Docker CLI
- SSH アクセス
- Claude Pro / Max プラン（OAuth 認証に必要）

## インストール

```bash
# 1. リポジトリを clone
git clone https://github.com/quvox/claude-dev-env.git ~/claude-dev-env
cd ~/claude-dev-env

# 2. 設定ファイルを編集
cp .env.example .env
vim .env
```

`.env` で設定する主要項目:

```bash
# Samba で共有するディレクトリ（プロジェクト群の親ディレクトリ）
SAMBA_SHARE_DIR=/home/user/repos

# Samba 認証（デフォルトから必ず変更すること）
SAMBA_USER=yourname
SAMBA_PASSWORD=your-secure-password
```

```bash
# 3. セットアップ実行（ビルド + Samba 起動 + PATH 登録を一括）
make setup

# 4. OAuth ログイン
make login
```

`make setup` は以下を順に実行する:
1. `.env` ファイルの作成
2. Docker ネットワーク・ボリュームの作成
3. Docker イメージのビルド（claude, samba）
4. Samba コンテナの起動
5. `claude-dev` コマンドを `/usr/local/bin/` にシンボリックリンク

`make login` を実行すると URL が表示されるので、ブラウザでアクセスして認証を完了する。

### 個別に実行する場合

```bash
make build            # イメージビルドのみ
make build-claude     # Claude イメージのみ
make start-services   # Samba 起動のみ
make install          # PATH 登録のみ
```

すべてのターゲットは `make help` で確認できる。

## 基本的な使い方

### プロジェクトで開発を始める

```bash
cd ~/repos/my-project
claude-dev start
```

これだけで:
1. カレントディレクトリがコンテナの `/workspace` にマウントされる
2. 認証情報がセットされる
3. ファイアウォールが設定される
4. tmux セッションが開始される

### Claude Code を起動する

tmux セッション内で:

```bash
claude
```

### 切断と再接続

```
Ctrl-B D          # tmux から切断（コンテナは動き続ける）
claude-dev start  # 同じディレクトリで再実行すると自動で再接続
```

SSH 接続が切れても、コンテナと Claude Code セッションは維持される。

### 複数プロジェクトの同時開発

```bash
# ターミナル 1
cd ~/repos/project-a
claude-dev start

# ターミナル 2
cd ~/repos/project-b
claude-dev start
```

プロジェクトごとに独立したコンテナが起動する。

### セッション管理

```bash
claude-dev list              # 実行中セッション一覧
claude-dev attach project-a  # 名前で接続
claude-dev stop project-a    # 停止
```

## tmux の基本操作

プレフィックスキーは tmux デフォルトの `Ctrl-B`。

| 操作 | キー |
|------|------|
| 切断（デタッチ） | `Ctrl-B D` |
| 新しいウィンドウ | `Ctrl-B C` |
| ウィンドウ切替 | `Ctrl-B 数字` |
| 画面を縦分割 | `Ctrl-B %` |
| 画面を横分割 | `Ctrl-B "` |
| ペイン移動 | `Ctrl-B 矢印キー` |
| スクロールモード | `Ctrl-B [` |

## Samba でファイルにアクセスする

IDE（VS Code, IntelliJ 等）からサーバ上のファイルを直接編集できる。

### macOS から接続

Finder → 移動 → サーバへ接続:
```
smb://<サーバIP>:445/workspace
```

### Windows から接続

エクスプローラのアドレスバーに:
```
\\<サーバIP>\workspace
```

### VS Code Remote で使う場合

SSH Remote で直接サーバにログインする方が高速。Samba はファイルブラウジングや非 SSH 対応のツールから使う場合に有用。

## トラブルシューティング

### `claude-dev start` でエラーが出る

```bash
# セットアップが済んでいるか確認
claude-dev list

# Samba の状態確認
claude-dev services status

# Samba が停止していたら起動
claude-dev services start
```

### OAuth トークンが期限切れ / 再ログインしたい

```bash
claude-dev logout   # 認証情報を削除（実行中コンテナも停止される）
claude-dev login    # 再ログイン（/exit で終了）
```

### Claude Code を更新したい

```bash
# Makefile 経由
make upgrade

# または claude-dev コマンド
claude-dev upgrade

# 実行中のコンテナには反映されないので、再起動が必要
claude-dev stop my-project
cd ~/repos/my-project
claude-dev start
```

### 環境を完全にリセットしたい

```bash
make clean
```

全コンテナ・ボリューム・イメージを削除する（確認プロンプトあり）。

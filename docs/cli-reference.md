# CLI リファレンス

## 概要

操作は **Makefile**（セットアップ・ビルド・管理）と **claude-dev CLI**（日常の開発操作）の 2 系統で提供される。

### Makefile ターゲット一覧

インストールやビルドなどの管理タスクは Makefile で実行する。

| ターゲット | 内容 |
|-----------|------|
| `make setup` | 初回セットアップ一括実行（env + network + volumes + build + services + install） |
| `make login` | OAuth ログイン |
| `make build` | 全イメージビルド |
| `make build-claude` | Claude イメージのみビルド |
| `make build-samba` | Samba イメージのみビルド |
| `make start-services` | Samba 起動 |
| `make stop-services` | Samba 停止 |
| `make upgrade` | Claude Code を最新版にリビルド（`--no-cache`） |
| `make status` | イメージ・コンテナ・ボリュームの状態確認 |
| `make install` | `claude-dev` を `/usr/local/bin/` にシンボリックリンク |
| `make uninstall` | シンボリックリンクを削除 |
| `make clean` | 全リセット（コンテナ・ボリューム・イメージ削除、確認あり） |
| `make help` | ヘルプ表示 |

### claude-dev CLI

`claude-dev` は日常の開発操作を行う CLI ツール。任意のディレクトリから実行できる。

## コマンド一覧

### セットアップ

#### `claude-dev setup`

初回セットアップ。以下を実行する:

1. `.env` ファイルを `.env.example` からコピー（未作成時）
2. Docker ネットワーク `claude-dev-net` を作成
3. Docker ボリューム `claude-dev-auth`, `claude-dev-history` を作成
4. Docker イメージをビルド（claude, samba）
5. Samba コンテナを起動

```bash
claude-dev setup
```

#### `claude-dev login`

OAuth 認証を実行する。Claude イメージを使った一時コンテナを起動し、Claude Code を対話的に起動する。`claude-dev-auth` ボリュームが `~/.claude/` に直接マウントされ、認証情報はそのまま永続化される。

ログイン完了後、`/exit` で Claude Code を終了する。

```bash
claude-dev login
```

トークンが期限切れになったら `logout` → `login` で再認証する。

#### `claude-dev logout`

認証情報を削除する。実行中の全プロジェクトコンテナを停止し、`claude-dev-auth` ボリューム内のファイルをすべて削除する。

```bash
claude-dev logout
```

---

### 開発

#### `claude-dev start`

カレントディレクトリをワークスペースとして Claude Code 環境を起動する。

```bash
cd ~/repos/my-project
claude-dev start
```

動作:
- コンテナ名: `claude-<ディレクトリ名>`（例: `claude-my-project`）
- 同名コンテナが実行中の場合は再接続する
- 停止中のコンテナがある場合は削除して新規起動
- イメージが存在しなければ自動ビルド
- 認証情報がなければエラーで停止

#### `claude-dev code`

実行中のコンテナで、新しい tmux ウィンドウに Claude Code を起動する。

```bash
cd ~/repos/my-project
claude-dev code
```

前提: `claude-dev start` でコンテナが起動済みであること。

#### `claude-dev attach [NAME]`

既存セッションに接続する。

```bash
# カレントディレクトリのプロジェクトに接続
claude-dev attach

# プロジェクト名を指定して接続
claude-dev attach my-project
```

#### `claude-dev stop [NAME]`

プロジェクトのコンテナを停止・削除する。プロジェクトファイルには影響しない。

```bash
# カレントディレクトリのプロジェクトを停止
claude-dev stop

# プロジェクト名を指定して停止
claude-dev stop my-project
```

#### `claude-dev list`

実行中の Claude Code セッションと Samba の状態を表示する。

```bash
claude-dev list
```

出力例:
```
=== 実行中の Claude Code セッション ===
NAMES               STATUS          MOUNTS
claude-my-project   Up 2 hours      /home/user/repos/my-project...
claude-api-server   Up 30 minutes   /home/user/repos/api-server...

=== 共有サービス ===
  ✅ claude-samba
```

---

### メンテナンス

#### `claude-dev upgrade`

Claude Code を更新する。イメージを `--no-cache` でリビルドする。

```bash
claude-dev upgrade
```

更新後、実行中のコンテナには即座に反映されない。`stop` → `start` で新しいイメージが使われる。

#### `claude-dev services [start|stop|status]`

Samba コンテナを管理する。

```bash
claude-dev services status   # 状態確認
claude-dev services start    # 起動
claude-dev services stop     # 停止
```

#### `claude-dev firewall`

カレントディレクトリのプロジェクトコンテナのファイアウォールルールを表示する。

```bash
claude-dev firewall
```

#### `claude-dev reset`

すべてのコンテナ、ボリューム、ネットワーク、イメージを削除する。確認プロンプトあり。

```bash
claude-dev reset
```

削除対象:
- 全プロジェクトコンテナ
- Samba コンテナ
- `claude-dev-auth`, `claude-dev-history` ボリューム
- `claude-dev-net` ネットワーク
- `claude-dev-claude`, `claude-dev-samba` イメージ

---

## 設定ファイル

`<claude-dev-env>/.env` に記述する。

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `SAMBA_SHARE_DIR` | `/home/user/repos` | Samba で共有するディレクトリ |
| `SAMBA_PORT` | `445` | Samba のポート |
| `SAMBA_USER` | `claude` | Samba ユーザー名 |
| `SAMBA_PASSWORD` | `claude` | Samba パスワード |

## コンテナ命名規則

| 種類 | 命名パターン | 例 |
|------|-------------|-----|
| プロジェクト | `claude-<ディレクトリ名>` | `claude-my-project` |
| Samba | `claude-samba` | - |

ディレクトリ名は小文字化され、英数字・ハイフン・ドット・アンダースコア以外は `-` に置換される。

## Makefile と claude-dev の使い分け

| やりたいこと | 使うもの |
|-------------|---------|
| 初回セットアップ | `make setup` |
| イメージビルド | `make build` |
| Claude Code 更新 | `make upgrade` |
| Samba 起動/停止 | `make start-services` / `make stop-services` |
| 状態確認（全体） | `make status` |
| PATH 登録 | `make install` |
| プロジェクトで開発開始 | `claude-dev start` |
| セッション接続/切断 | `claude-dev attach` / `claude-dev stop` |
| セッション一覧 | `claude-dev list` |
| OAuth ログイン | `make login` または `claude-dev login` |
| 認証情報削除 | `claude-dev logout` |
| 全リセット | `make clean` または `claude-dev reset` |
| 全リセット | `make clean` または `claude-dev reset` |

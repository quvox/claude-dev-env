# CLI リファレンス

## 概要

操作は **Makefile**（セットアップ・ビルド・管理）と **claude-dev CLI**（日常の開発操作）の 2 系統で提供される。

### Makefile ターゲット一覧

インストールやビルドなどの管理タスクは Makefile で実行する。

| ターゲット | 内容 |
|-----------|------|
| `make setup` | 初回セットアップ一括実行（env + network + volumes + build + install） |
| `make login` | OAuth ログイン |
| `make build` | イメージビルド |
| `make build-claude` | Claude イメージをビルド |
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
4. Docker イメージをビルド

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

#### `claude-dev start [--chrome]`

カレントディレクトリをワークスペースとして Claude Code 環境を起動する。

```bash
cd ~/repos/my-project
claude-dev start

# Chrome/VNC 付きで起動
claude-dev start --chrome
```

動作:
- コンテナ名: `claude-<ディレクトリ名>`（例: `claude-my-project`）
- 同名コンテナが実行中の場合は再接続する
- 停止中のコンテナがある場合は削除して新規起動
- イメージが存在しなければ自動ビルド
- 認証情報がなければエラーで停止
- 主要な開発ポート（3000, 4200, 5173, 5000, 8000, 8080, 8888）を自動マッピング

`--chrome` オプション:
- コンテナ内に仮想ディスプレイ（Xvfb）+ VNC + noVNC を起動する
- ローカル PC のブラウザから `http://localhost:<port>/vnc.html` で Chrome を操作できる
- noVNC ポートは 6080 から自動割り当て（複数プロジェクト同時起動対応）
- tmux 内で `chromium-browser` や `google-chrome` を起動すると noVNC 画面に表示される

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

#### `claude-dev ports [NAME]`

実行中のコンテナのポートマッピングを表示する。

```bash
# カレントディレクトリのプロジェクト
claude-dev ports

# プロジェクト名を指定
claude-dev ports my-project
```

出力例:
```
📡 claude-my-project port mappings:
  Host :8100 → Container :3000  (React/Next/Express/Rails)
  Host :8101 → Container :4200  (Angular)
  Host :8102 → Container :5173  (Vite)
  Host :8103 → Container :5000  (Flask)
  Host :8104 → Container :8000  (Django/FastAPI/Hugo)
  Host :8105 → Container :8080  (Go/Spring Boot)
  Host :8106 → Container :8888  (Jupyter)
```

#### `claude-dev ssh-forward [NAME]`

クライアント PC で実行する SSH ポートフォワードコマンドを生成・表示する。

```bash
claude-dev ssh-forward
claude-dev ssh-forward my-project
```

出力例:
```
📋 SSH ControlMaster 設定（~/.ssh/config に追加を推奨）:
  Host myserver
      ControlMaster auto
      ControlPath /tmp/ssh-%r@%h:%p
      ControlPersist 10m

📋 ポートフォワード追加コマンド（クライアント PC で実行）:
  ssh -O forward -L 8100:localhost:8100 myserver
  ssh -O forward -L 8102:localhost:8102 myserver
  ssh -O forward -L 8105:localhost:8105 myserver

📋 一括転送（ControlMaster 未使用時）:
  ssh -L 8100:localhost:8100 -L 8102:localhost:8102 -L 8105:localhost:8105 myserver
```

#### `claude-dev list`

実行中の Claude Code セッションを表示する。ポートマッピングと noVNC URL も表示される。

```bash
claude-dev list
```

出力例:
```
=== 実行中の Claude Code セッション ===
NAMES               STATUS          MOUNTS
claude-my-project   Up 2 hours      /home/user/repos/my-project...
claude-api-server   Up 30 minutes   /home/user/repos/api-server...
  📡 claude-my-project → Ports: 8100-8109
  📡 claude-api-server → Ports: 8110-8119
  🖥️  claude-my-project → noVNC: http://localhost:6080/vnc.html
```

---

### メンテナンス

#### `claude-dev upgrade`

Claude Code を更新する。イメージを `--no-cache` でリビルドする。

```bash
claude-dev upgrade
```

更新後、実行中のコンテナには即座に反映されない。`stop` → `start` で新しいイメージが使われる。

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
- `claude-dev-auth`, `claude-dev-history` ボリューム
- `claude-dev-net` ネットワーク
- `claude-dev-claude` イメージ

---

## コンテナ命名規則

| 種類 | 命名パターン | 例 |
|------|-------------|-----|
| プロジェクト | `claude-<ディレクトリ名>` | `claude-my-project` |

ディレクトリ名は小文字化され、英数字・ハイフン・ドット・アンダースコア以外は `-` に置換される。

## Makefile と claude-dev の使い分け

| やりたいこと | 使うもの |
|-------------|---------|
| 初回セットアップ | `make setup` |
| イメージビルド | `make build` |
| Claude Code 更新 | `make upgrade` |
| 状態確認（全体） | `make status` |
| PATH 登録 | `make install` |
| プロジェクトで開発開始 | `claude-dev start` |
| セッション接続/切断 | `claude-dev attach` / `claude-dev stop` |
| ポートマッピング確認 | `claude-dev ports` |
| SSH 転送コマンド生成 | `claude-dev ssh-forward` |
| セッション一覧 | `claude-dev list` |
| OAuth ログイン | `make login` または `claude-dev login` |
| 認証情報削除 | `claude-dev logout` |
| 全リセット | `make clean` または `claude-dev reset` |

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

# 2. 設定ファイルを作成
cp .env.example .env
```

```bash
# 3. セットアップ実行（ビルド + PATH 登録を一括）
make setup

# 4. OAuth ログイン
make login
```

`make setup` は以下を順に実行する:
1. `.env` ファイルの作成
2. Docker ネットワーク・ボリュームの作成
3. Docker イメージのビルド（Claude ベース / Claude VNC / Docker Socket Proxy）
4. `claude-dev` コマンドを `/usr/local/bin/` にシンボリックリンク

`make login` を実行すると URL が表示されるので、ブラウザでアクセスして認証を完了する。

### 個別に実行する場合

```bash
make build            # 全イメージビルド
make build-claude     # Claude イメージのみ（ベース + VNC 両方）
make install          # PATH 登録のみ
```

すべてのターゲットは `make help` で確認できる。

## SSH 鍵の設定

`claude-dev start` 時に ssh-agent に登録する SSH 鍵を `~/.config/claude-dev.yaml` で管理する。初回実行時に `~/.ssh/id_*` を検出して自動生成される。

```yaml
# ~/.config/claude-dev.yaml
ssh_keys:
  - ~/.ssh/id_ed25519
  - ~/.ssh/id_rsa
  # 不要な鍵はコメントアウトまたは削除
```

- パスフレーズなしの鍵は自動で追加される
- パスフレーズ付きの鍵は対話的に入力を求められる
- コンテナには秘密鍵ファイルを渡さず、SSH agent ソケットのみ転送される

## 基本的な使い方

### プロジェクトで開発を始める

```bash
cd ~/repos/my-project
claude-dev start            # Chrome + VNC 付き（デフォルト）
claude-dev start --no-vnc   # Chrome / VNC なし（軽量）
```

デフォルト（VNC あり）の場合:
1. カレントディレクトリがコンテナの `/workspace` にマウントされる
2. 認証情報がセットされる
3. ファイアウォールが設定される
4. TigerVNC + Google Chrome が起動される
5. tmux セッションが開始される

noVNC URL が起動時に表示されるので、ブラウザでアクセスして Chrome 画面を確認できる（日本語入力対応、`Ctrl+\\` または `F3` で切替）。noVNC ポートは 6080〜 から空きを動的に割り当てるため、複数プロジェクト間で衝突しない。あとから `claude-dev list` や `claude-dev ports` でポート番号を確認できる。

Claude Code は chrome-devtools MCP サーバー経由で Chrome を操作する。

`--no-vnc` の場合は Chrome / VNC が起動せず、軽量なコンテナで開発できる。バックエンド開発や CLI ツール開発など、ブラウザ不要なプロジェクト向け。

### Claude Code を起動する

tmux セッション内で:

```bash
claude
```

### 切断と再接続

```
Ctrl-_ D          # tmux から切断（コンテナは動き続ける）
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

プロジェクトごとに独立したコンテナが起動する。VNC ありの場合、各プロジェクトに独立した Chrome/noVNC が割り当てられるため、複数プロジェクトで同時にブラウザを使っても競合しない。

### セッション管理

```bash
claude-dev list              # 実行中セッション一覧
claude-dev attach project-a  # 名前で接続
claude-dev stop project-a    # 停止
```

## Web アプリへのアクセス

コンテナ内で起動した Web アプリにクライアント PC のブラウザからアクセスできる。ポートは `claude-dev forward` で必要なときに動的にフォワードする（`claude-dev start` 時にはポートマッピングは行われない）。

### ワークフロー

```bash
# --- ターミナル 1: サーバ上で開発 ---
$ ssh myserver
$ cd ~/repos/my-webapp
$ claude-dev start                  # ポートマッピングなしで起動

# コンテナ内で Claude が Vite アプリを起動 → localhost:5173

# --- ターミナル 2: サーバ上でポートフォワード ---
$ claude-dev forward 5173           # → ✅ host:8100 → my-webapp:5173
                                    #    SSH: ssh -O forward -L 8100:localhost:8100 <server>

# --- ターミナル 3: クライアント PC で SSH トンネル ---
$ ssh -O forward -L 8100:localhost:8100 myserver

# --- ブラウザ ---
# http://localhost:8100 でアクセス

# 不要になったらフォワード解除
$ claude-dev unforward 5173
```

### SSH ControlMaster の設定（推奨）

`-O forward` を使うには SSH 接続が ControlMaster モードで動作している必要がある。クライアント PC の `~/.ssh/config` に以下を追加しておくと便利:

```
Host myserver
    ControlMaster auto
    ControlPath /tmp/ssh-%r@%h:%p
    ControlPersist 10m
```

この設定があれば、通常の `ssh myserver` だけで ControlMaster が有効になり、別ターミナルから `-O forward` でポートフォワードを動的に追加できる。

### フォワードの確認

```bash
# サーバ上で実行
claude-dev ports              # アクティブなフォワードと noVNC URL を表示
```

### 複数プロジェクト同時開発時

ポートは動的に割り当てられるため、必要なポートだけをフォワードする:

```bash
# Project A
$ cd ~/repos/frontend && claude-dev start
$ claude-dev forward 5173             # → host:8100 → frontend:5173

# Project B
$ cd ~/repos/backend && claude-dev start
$ claude-dev forward 8080 backend     # → host:8101 → backend:8080

# クライアント PC からそれぞれにフォワード
$ ssh -O forward -L 8100:localhost:8100 myserver  # frontend の Vite
$ ssh -O forward -L 8101:localhost:8101 myserver  # backend の Go
```

### 注意事項

- コンテナ内の Web アプリは `0.0.0.0` にバインドする必要がある（`localhost` / `127.0.0.1` ではコンテナ外からアクセスできない）
- 多くのフレームワークはデフォルトで `localhost` にバインドするため、`--host 0.0.0.0` オプションが必要な場合がある:
  - Vite: `vite --host 0.0.0.0`
  - Next.js: デフォルトで `0.0.0.0`（変更不要）
  - Django: `python manage.py runserver 0.0.0.0:8000`
  - Flask: `flask run --host 0.0.0.0`
  - Go: `http.ListenAndServe(":8080", ...)` — デフォルトで全インターフェース

## tmux の基本操作

プレフィックスキーは `Ctrl-_`（`Ctrl-B` からカスタマイズ済み）。

| 操作 | キー |
|------|------|
| 切断（デタッチ） | `Ctrl-_ D` |
| 新しいウィンドウ | `Ctrl-_ C` |
| ウィンドウ切替 | `Ctrl-_ 数字` |
| 画面を縦分割 | `Ctrl-_ %` |
| 画面を横分割 | `Ctrl-_ "` |
| ペイン移動 | `Ctrl-_ 矢印キー` |
| スクロールモード | `Ctrl-_ [` |

## トラブルシューティング

### `claude-dev start` でエラーが出る

```bash
# セットアップが済んでいるか確認
claude-dev list
```

### OAuth トークンが期限切れ / 再ログインしたい

```bash
claude-dev logout   # 認証情報を削除（実行中コンテナも停止される）
claude-dev login    # 再ログイン（/exit で終了）
```

### Claude Code を更新したい

```bash
# Makefile 経由（Claude ベース + VNC + Docker Socket Proxy を一括更新）
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

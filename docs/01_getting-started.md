---
summary: 本環境を初めて導入する利用者向けに、前提条件・インストール手順・基本的な使い方・Webアクセス・トラブルシューティングを説明する導入ガイド。
keywords: [ クイックスタート, インストール, OAuth認証, tmux, ポートフォワード, セッション管理, SSH ]
---

# クイックスタートガイド

> **この文書の役割**: 本環境を初めて導入する利用者向けに、前提条件・インストール手順・基本的な使い方を示す導入ガイド。

## 前提条件

- Linux サーバ（Ubuntu 22.04+ / Debian 12+ 推奨） **または** macOS + Docker Desktop
- Docker Engine 24+ & Docker CLI（macOS は Docker Desktop に同梱）
- SSH アクセス（Linux サーバ運用時）
- `jq`（`claude-dev start` がホスト設定を抽出するのに使用。macOS は `brew install jq`）
- Claude Pro / Max プラン（OAuth 認証に必要）

> **macOS で使う場合**: CLI は macOS 適応版 `claude-dev-mac` を使う。`make install` が OS を判定して `/usr/local/bin/claude-dev` を `claude-dev-mac` への symlink（`sudo ln -sf`）にするため、以降のコマンドはどの OS でも `claude-dev` で共通。macOS 固有の差分（SSH agent 転送・ポート直結・VM/KVM 非対応・Apple Silicon は arm64 ネイティブで GUI ブラウザに Playwright Chromium）は [docs/09_macos-support.md](09_macos-support.md) を参照。以下の手順で「Linux サーバ + SSH トンネル」を前提にした箇所は、macOS では手元マシンが Docker ホストのため SSH トンネルは不要（`http://localhost:<host-port>` に直接アクセス）。

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
make build            # 全イメージビルド（ベース + VNC + Docker Socket Proxy）
make build-claude     # Claude ベースイメージのみ
make build-claude-vnc # Claude VNC イメージ（ベースに続けてビルド）
make install          # PATH 登録のみ
```

すべてのターゲットは `make help` で確認できる。

## SSH 鍵の設定

`claude-dev start` 時にコンテナへ転送する SSH 鍵は、**プロジェクト直下の `.claude-dev.yaml` の `ssh_keys` だけ**で指定する（グローバル設定・自動生成・フォールバックはない）。ディレクトリごとに異なる鍵を使える。

```yaml
# <プロジェクト>/.claude-dev.yaml
ssh_keys:
  - ~/.ssh/id_ed25519        # このプロジェクトで使う鍵
  # 複数指定可。不要な鍵は削除
```

- `claude-dev` はプロジェクトごとに**専用 ssh-agent**（`~/.claude-dev/agents/<ディレクトリ名>.sock`）を起動し、そのプロジェクトの `ssh_keys` の鍵**だけ**を登録・転送する。よって別プロジェクトの鍵はコンテナから見えない。
- `.claude-dev.yaml` が無い/`ssh_keys` が空のディレクトリでは **SSH 転送なし**で起動する（案内メッセージが出る）。
- パスフレーズなしの鍵は自動追加、パスフレーズ付きは初回登録時のみ対話入力（既登録の鍵は再入力不要）。
- コンテナには秘密鍵ファイルを渡さず、SSH agent ソケット（mac は socat TCP ブリッジ）のみ転送する。
- 記載するのは鍵ファイルの**パスのみ**（秘密情報は含まない）。リポジトリにコミットするかは運用次第（コミットしたくなければ `.gitignore` に追加）。

> **ヒント**: `claude-dev ssh-keys`（Linux / macOS 共通）を実行すると `~/.ssh` の鍵を対話選択して、カレントプロジェクトの `.claude-dev.yaml` を生成できる。`claude-dev ssh-keys reset` でその選択と専用 agent を初期化する。

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

noVNC URL が起動時に表示されるので、ブラウザでアクセスして Chrome 画面を確認できる（日本語入力対応、`Super+Space` で切替。`Ctrl+Shift+Space` / `Ctrl+\` / `F3` も予備として有効だが、ホスト OS やブラウザに横取りされる場合があるので `Super+Space` を推奨）。noVNC ポートは 6080〜 から空きを動的に割り当てるため、複数プロジェクト間で衝突しない。あとから `claude-dev list` や `claude-dev ports` でポート番号を確認できる。

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

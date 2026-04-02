# ホストサーバ準備ガイド (Ubuntu 24.04)

claude-dev-env を動かすための Ubuntu 24.04 サーバのセットアップ手順。

## 前提

- Ubuntu 24.04 LTS (desktop) がインストール済み（最小構成でも可）
- root または sudo 権限でログインできる
- インターネット接続がある
- Claude Pro / Max プラン（OAuth 認証に必要）

## 1. システムの更新

```bash
sudo apt-get update && sudo apt-get upgrade -y
```

## 2. 基本パッケージのインストール

```bash
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    git \
    make \
    ufw \
    python3 \
    python3-pip \
    python3-venv \
    iputils-ping \
    iproute2
```

## 3. Claude Code のインストール（ホスト）

ホスト上でも Claude Code を使えるようにする。

```bash
# ネイティブインストーラーで一括インストール（Node.js 同梱）
curl -fsSL https://claude.ai/install.sh | bash

# 確認
claude --version
```

### 初回認証

```bash
claude
```

起動すると OAuth 認証の URL が表示される。ホストに GUI がセットアップ済みなら Chrome で、そうでなければ手元の PC のブラウザで URL を開いて認証する。

## 4. Docker Engine のインストール

公式リポジトリから最新版をインストールする。

```bash
# GPG キーの追加
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# リポジトリの追加
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# インストール
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin
```

### 動作確認

```bash
docker --version   # 24+ であること
sudo docker run --rm hello-world
```

## 5. 作業ユーザーの準備

root 以外のユーザーで開発する。既存ユーザーがあればそのまま使ってもよい。

```bash
# ユーザー作成（既存ユーザーを使う場合はスキップ）
sudo adduser devuser

# docker グループに追加（sudo なしで docker を実行するため）
sudo usermod -aG docker devuser
```

**以降の手順はこの作業ユーザーで実行する。** グループ変更を反映するため、一度ログアウトして再ログインする。

```bash
# docker が sudo なしで動くか確認
docker run --rm hello-world
```

## 6. SSH の設定

### 鍵認証の設定（推奨）

```bash
# クライアント側で鍵を生成（まだなければ）
ssh-keygen -t ed25519

# 公開鍵をサーバに登録（Tailscale IP でも物理 IP でも可）
ssh-copy-id devuser@<サーバIP>
```

### sshd の強化（推奨）

```bash
sudo vim /etc/ssh/sshd_config
```

```
PermitRootLogin no
PasswordAuthentication no
```

```bash
sudo systemctl restart sshd
```

## 7. Tailscale のインストール

Tailscale を使うと、サーバをインターネットに直接公開せずに、手元の PC から安全にアクセスできる。SSH、RDP、Samba すべて Tailscale ネットワーク経由で接続する。

### インストール

```bash
curl -fsSL https://tailscale.com/install.sh | bash
```

### 起動と認証

```bash
sudo tailscale up
```

表示される URL をブラウザで開き、Tailscale アカウントで認証する。

### 動作確認

```bash
# Tailscale IP の確認
tailscale ip -4

# 状態確認
tailscale status
```

表示された Tailscale IP（`100.x.x.x`）が、以降の SSH・RDP・Samba 接続先になる。

### Tailscale SSH（任意）

Tailscale SSH を有効にすると、SSH 鍵の管理なしで Tailscale 認証だけでログインできる。

```bash
sudo tailscale up --ssh
```

Tailscale Admin Console でも SSH の ACL を設定できる。有効にした場合、`ssh devuser@<Tailscale IP>` で鍵なしログインが可能。

### 自動起動の確認

```bash
# systemd で自動起動が有効になっているか確認
sudo systemctl is-enabled tailscaled
# enabled でなければ有効化
sudo systemctl enable tailscaled
```

## 8. ホストのファイアウォール設定

Tailscale を使う場合、SSH・RDP・Samba は Tailscale ネットワーク（`100.64.0.0/10`）からのみ許可すればよい。

```bash
# Tailscale インターフェースからの通信はすべて許可
sudo ufw allow in on tailscale0

# 物理ネットワークからの SSH（Tailscale 接続前に必要）
sudo ufw allow 22/tcp

# 有効化
sudo ufw enable
sudo ufw status
```

Tailscale SSH を有効にしている場合、物理ネットワークの SSH (22/tcp) は閉じることもできる:

```bash
# Tailscale SSH のみにする場合（物理 SSH を閉じる）
# sudo ufw delete allow 22/tcp
```

> **注意:** 物理 SSH を閉じる前に、Tailscale SSH で接続できることを必ず確認すること。ロックアウトされると復旧にコンソールアクセスが必要になる。

> Samba (445) や RDP (3389) の個別ルールは不要。`tailscale0` からの全通信を許可しているため、Tailscale 経由でアクセスできる。

## 9. 環境のセットアップ

Desktop版をデフォルトのままインストールしていれば、Gnomeがセットアップされているはず。そこで以下の設定を行う。

### ファイル共有の有効化

```
sudo apt install nautilus-share samba
sudo gpasswd -a <yourname> sambashare
sudo smbpasswd -a <yourname>
sudo systemctl restart smbd
# ユーザが有効かを確認
sudo pdbedit -L
```

ここで、念の為一度リブートする（ログアウトでもいいかも。グループ追加が有効化されればOK）

「ファイル」アプリで、フォルダ（homeのworkspace/）を選択して、右クリック→「共有のオプション」から共有を有効化する。

### デスクトップ共有（できない）

リモートデスクトップで接続させたいなら、デスクトップ共有などを設定すること。ただ、MacのWindowsAppのアプリでリモートデスクトップすると画面が真っ黒になるので使い物にならない（既知のバグっぽい）。なので、デスクトップ共有は諦めて、おとなしくsshオンリーにした方がいい。

### Google Chrome のインストール（ターミナルから実施）

```bash
curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | sudo gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg

echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | \
  sudo tee /etc/apt/sources.list.d/google-chrome.list > /dev/null

sudo apt-get update
sudo apt-get install -y google-chrome-stable
```

### 日本語環境の設定

Chrome で日本語を正しく表示するために、日本語フォントとロケールを設定する。

```bash
# 日本語フォント
sudo apt-get install -y fonts-noto-cjk fonts-noto-cjk-extra

# 日本語ロケール
sudo apt-get install -y language-pack-ja
sudo update-locale LANG=ja_JP.UTF-8

# 日本語入力（任意）
sudo apt-get install -y fcitx5-mozc
```

ロケール変更は再ログイン後に反映される。

### 接続方法

接続先は Tailscale IP（`100.x.x.x`）を使う。`tailscale ip -4` で確認。

#### macOS からの接続

Microsoft Remote Desktop（App Store から無料）を使う。

1. アプリを起動 → 「Add PC」
2. PC name: `<Tailscale IP>`
3. User account: 作業ユーザーの認証情報を入力
4. 接続

#### Windows からの接続

1. 「リモート デスクトップ接続」を起動（`mstsc`）
2. コンピューター: `<Tailscale IP>`
3. 接続 → ユーザー名・パスワードを入力

#### Linux からの接続

```bash
# Remmina（Ubuntu デフォルト）または xfreerdp
xfreerdp /v:<Tailscale IP> /u:devuser /size:1920x1080
```

### 動作確認

RDP で接続後、ターミナルを開いて:

```bash
google-chrome --no-sandbox &
```

Chrome が起動すれば OK。OAuth ログイン時のブラウザ認証もこの Chrome で行える。

## 10. Chrome/VNC によるリモート操作

`claude-dev start` を実行すると、Chrome + TigerVNC + noVNC がコンテナ内で起動する。ローカル PC のブラウザから noVNC 経由で Google Chrome を操作できる。

### 構成

```
ローカル PC のブラウザ
    │
    │ http://<Tailscale IP>:<noVNC port>/vnc.html
    ▼
┌─ Claude コンテナ (claude-dev-claude-vnc) ─────┐
│  Xvnc :99 (port 5999)  ← コンテナ内のみ       │
│  noVNC (websockify)     ← HTTP port <動的> → 5999 │
│  openbox     (ウィンドウマネージャ)             │
│  ibus-daemon (日本語入力, IBus-Mozc)           │
│  Google Chrome  ← 自動起動                    │
│                                               │
│  Claude Code  ← chrome-devtools MCP で Chrome 操作     │
│  tmux         ← 開発作業                      │
└───────────────────────────────────────────────┘
※ VNC 生ポート 5999 はホストに公開しない
※ noVNC の HTTP ポートのみホストに公開（6080〜 動的割当）
```

ホスト側に追加パッケージのインストールは不要。すべてコンテナ内に含まれている。

### 使い方

```bash
cd ~/repos/my-project
claude-dev start
# → noVNC URL が表示される（例: http://localhost:6080/vnc.html?autoconnect=true）

# ブラウザ不要なプロジェクトは軽量モードで起動
claude-dev start --no-vnc

# あとからポート番号を確認
claude-dev list                # 全セッションの noVNC URL を表示
claude-dev ports my-project    # プロジェクト単位の詳細
```

ローカル PC のブラウザで表示された noVNC URL にアクセスすると、コンテナ内の Google Chrome を操作できる。日本語入力は `Ctrl+\\` または `F3` で切り替え（IBus-Mozc）。

noVNC ポート（HTTP/WebSocket）は起動時に 6080〜 から空きを動的割り当て。VNC 生ポートはホストに公開しない。複数プロジェクトで同時にブラウザを使っても競合しない。

## 11. プロジェクトディレクトリの準備

```bash
# Claude Code で開発するリポジトリを置くディレクトリ
mkdir -p ~/repos
```

## 12. claude-dev-env のセットアップ

```bash
# クローン
git clone https://github.com/quvox/claude-dev-env.git ~/claude-dev-env
cd ~/claude-dev-env

# 設定ファイルの作成・編集
cp .env.example .env
vim .env
```

```bash
# 一括セットアップ（ビルド + PATH 登録）
make setup

# OAuth ログイン（表示される URL をブラウザで開いて認証）
make login
```

## 13. 動作確認

```bash
cd ~/repos

# テスト用リポジトリを用意
mkdir test-project && cd test-project && git init

# Claude Code 環境を起動
claude-dev start

# tmux 内で Claude Code を起動
claude
```

正常に起動したら `Ctrl-_ D` で tmux から切断し、以下で後片付け:

```bash
claude-dev stop test-project
```

## ハードウェア目安

| 項目 | 最小 | 推奨 |
|------|------|------|
| CPU | 2 コア | 4 コア以上 |
| メモリ | 4 GB | 8 GB 以上 |
| ディスク | 20 GB | 50 GB 以上 |

Docker イメージ（Claude コンテナ）が約 2.5 GB、加えてプロジェクトのビルド成果物や `node_modules` 等の容量が必要。

## チェックリスト

セットアップが完了したら以下を確認:

- [ ] `tailscale status` で接続済み（online）になっている
- [ ] `claude --version` でホストの Claude Code が動く
- [ ] `python3 --version` / `pip3 --version` が動く
- [ ] `docker run --rm hello-world` が sudo なしで動く
- [ ] `claude-dev list` でエラーが出ない
- [ ] `make login` で OAuth 認証が完了している
- [ ] `claude-dev start` でコンテナが起動し tmux に接続できる
- [ ] ホストの ufw が有効で、必要なポートのみ開放されている
- [ ] `claude-dev start` で noVNC URL が表示される
- [ ] noVNC にブラウザでアクセスし、コンテナ内で Google Chrome が表示される

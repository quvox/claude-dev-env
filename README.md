# Claude Code 安全開発環境

Claude Code を **承認待ちで止まらず・コンテナ隔離で安全に・SSH 切断でも継続** して使うための Docker 開発環境。**Linux サーバ**と **macOS（Docker Desktop）**の両方で動く。

任意のプロジェクトディレクトリで `claude-dev start` を実行するだけで、隔離された Claude Code 環境（必要なら GUI/Chrome 付き）が起動する。

## 目的・背景

Claude Code をそのまま使うと、ファイル変更やコマンド実行のたびに承認を求められて自律作業が止まり、SSH が切れれば作業も中断する。かといってホストで `--dangerously-skip-permissions` を使うのは危険。本ツールは次を目的とする。

- **承認待ちをなくす**: コンテナで隔離した中でだけ権限バイパスを効かせ、ホストを危険に晒さずに Claude Code を自律実行させる。
- **中断させない**: tmux でセッションを永続化し、SSH 切断・再接続をまたいで作業を継続する。
- **複数案件を並行**: プロジェクトごとに独立コンテナを起動し、同時に走らせる。
- **実ブラウザで検証**: コンテナ内の Chrome を noVNC で覗きつつ、Claude Code に chrome-devtools MCP で操作させて Web アプリを動作確認する。
- **多層防御**: 生 Docker ソケット・SSH 秘密鍵をコンテナに渡さず、ファイアウォールで情報漏洩先を遮断する。

## 使い方（まずこれだけ）

`claude-dev` は「**プロジェクトのディレクトリごとに、隔離された Claude Code 環境（コンテナ）を 1 つ立て、その中で作業する**」ツール。要点は次のとおり（1〜5 が基本、6・7 は SSH 鍵と noVNC の使い方）。

> はじめて使うホストでは、先に下記「**セットアップ**」（`claude-dev` の導入）を済ませてから読むと分かりやすい。

### 1. コンテナは「ディレクトリ単位」

- **`claude-dev start` は claude-dev コンテナを起動するコマンド**。**起動したディレクトリに紐づいたコンテナ**が立ち、**別のディレクトリで `claude-dev start` すると別のコンテナ**が立つ（＝案件ごとに独立・同時並行できる）。
- 起動したディレクトリ**全体がコンテナ内にマウント**され、コンテナの中では **`/workspace`** として見える（ホストでの編集は即コンテナに反映、その逆も同様）。
- **同じディレクトリで既にコンテナが起動済みなら、`claude-dev start` は起動中コンテナへ「再ログイン」**する（新しく立て直さず、作業をそのまま継続できる）。
- 起動すると、そのコンテナ内の **tmux セッションに接続**された状態になる。

### 2. コンテナの中で Claude を動かす — 2 通り

tmux に接続されたら、Claude の動かし方は 2 つ。**どちらも中身は同じ Claude Code**で、違いは「**作業全体を監視・指揮する司令塔（AI オーケストレーター）を挟むかどうか**」だけ（オーケストレーターも内部では結局 Claude Code を動かす）。

- **① 素の Claude Code**：`claude-dev start` で入った後、tmux 内で **`claude`** を実行 → 承認待ちなしの Claude Code がそのまま起動する（1 エージェントで対話しながら作業。オーケストレーターは付かない）。
- **② AI オーケストレーター**：ブレインストーミング（検討）→ 実行計画 → 複数 worker への並列委譲 → 相互レビュー、までを**自律で回す司令塔**（設計は [docs/06](docs/06_orchestration.md)）。起動は 2 通り：
  - **`claude-dev start` した後、tmux 内で `claude-orchestrator` を実行**すると AI オーケストレーターが起動する。
  - **`claude-dev orchestrate` を実行**すると、（コンテナ未起動なら）**`start` した後に tmux 内で自動的に** AI オーケストレーターが起動する。ゴールを渡すこともできる：`claude-dev orchestrate "ユーザー認証を実装"`。

> 「素の Claude Code が欲しい → tmux 内で `claude`」「全体を任せて自律で回したい → `claude-dev orchestrate`（または tmux 内で `claude-orchestrator`）」。

### 3. 抜け方（コンテナは裏で動き続ける）

tmux の prefix は **`Ctrl-_`**（Ctrl とアンダースコア）。

- **一時的に離れる（デタッチ）**：`Ctrl-_` → `d` で tmux を抜ける。tmux セッションは生きたまま、作業は継続する。
- **コンテナから完全に出る**：デタッチした後、シェルで **`Ctrl-D`**（ログアウト）。**コンテナは裏で動き続ける**（Claude の作業も止まらない）。
- **戻る**：同じディレクトリで **`claude-dev start`**（または `claude-dev attach <名前>`）→ 元のセッションに再接続。
- **完全に止める**：`claude-dev stop <名前>`。

### 4. コンテナでできること（Docker・Chrome・VM）

コンテナには **Docker と Chrome が入っている**ので、環境構築なしで次ができる：

- **Docker を使う開発**：`docker compose up` などをコンテナ内から実行できる。
- **実ブラウザでの E2E**：noVNC で画面を見ながら、Claude Code に chrome-devtools MCP で Chrome を操作させ、Web アプリの動作を確認できる。
- **VM モード（Linux のみ）**：さらに仮想度の高い環境。**コンテナの中にゲスト VM を立て、その VM の中でネイティブ Docker を動かす**ことで、bind mount・compose・privileged がそのまま使える（bind mount を多用する「Docker 中心」の開発向け。後述「VM モード」）。

### 5. イメージを最新に保つ（定期的に `claude-dev pull`）

配布イメージは日次で更新される。**定期的に `claude-dev pull` で最新のコンテナイメージを取得**しておくとよい（`make build` の再ビルドは不要。後述「GHCR からイメージを取得」）。

- **重要**：pull しても**起動中のコンテナには即座には反映されない**。取得したイメージを使うには、対象コンテナを一度 **`claude-dev stop` してから `claude-dev start` し直す**（＝新しいイメージでコンテナを作り直す）。

```bash
claude-dev pull                  # 最新イメージを取得
claude-dev stop  my-project      # 起動中コンテナを停止
cd ~/repos/my-project && claude-dev start   # 新しいイメージで起動し直す
```

### 6. SSH 鍵の設定・解除（コンテナから git push / SSH する場合）

コンテナ内から `git push` や SSH 接続をしたいときは、ホストの SSH 鍵を **agent 転送**で使える（**秘密鍵ファイルはコンテナに渡さず、署名操作だけを転送**）。どの鍵を使うかは**プロジェクト直下の `.claude-dev.yaml`**（`ssh_keys:`）に記録され、**ディレクトリ（プロジェクト）ごとに独立**する。

- **初回 `claude-dev start`（`.claude-dev.yaml` が無いとき）**：`~/.ssh` の鍵一覧から**使う鍵を選ぶ画面**が出る（番号をカンマ/空白区切り・`a`=全部・`n`=なし）。**`n`（なし）を選べば SSH 転送なし**で始まり、`ssh_keys:` は空配列で保存される（以後は聞かれない）。
- **後から設定・変更**：`claude-dev ssh-keys`（対話選択して `.claude-dev.yaml` に保存）。
- **解除・初期化**：`claude-dev ssh-keys reset`（`.claude-dev.yaml` の `ssh_keys` を空にし、そのプロジェクト専用 ssh-agent を停止）。
- **手で書く**：`.claude-dev.yaml` を直接編集してもよい。
  ```yaml
  ssh_keys:
    - ~/.ssh/id_ed25519    # 使う鍵を列挙。空（何も書かない）なら SSH 転送なし
  ```
- 設定を変えたら反映のため、対象コンテナを **`claude-dev stop` → `start`** し直す。
- macOS は `socat`（TCP ブリッジ）が必須（`brew install socat`）。詳細設計は [docs/03_security.md](docs/03_security.md) / [docs/09_macos-support.md](docs/09_macos-support.md)。

### 7. noVNC でコンテナ内 Chrome を見る

VNC あり（既定）で起動すると、コンテナ内の Chrome を**ブラウザからリアルタイムに閲覧・操作**できる（Claude に E2E させている様子を目視できる）。

- **URL を知る**：`claude-dev start` 時に表示される noVNC URL（`http://localhost:<port>/vnc.html`）。後からは **`claude-dev ports`** または **`claude-dev list`** でも表示される。
- **同じマシンで見る**：その URL をブラウザで開くだけ。
- **リモートサーバの場合**：SSH トンネルでその noVNC ポートを手元へ転送してから開く。
  ```bash
  ssh -L <port>:localhost:<port> <server>     # <port> は上の noVNC URL のポート
  # → 手元のブラウザで http://localhost:<port>/vnc.html を開く
  ```
- 日本語入力の切替は `Super+Space`（IBus-Mozc）。ブラウザ不要なら **`claude-dev start --no-vnc`**（noVNC なしの軽量モード）。

## 主な機能

| 機能 | 概要 |
|------|------|
| 承認待ちなし実行 | コンテナ隔離下で `bypassPermissions`。ホストは保護 |
| セッション永続化 | tmux（prefix `Ctrl-_`）。SSH 切断でも継続、再接続で復帰 |
| 複数プロジェクト並列 | ディレクトリ名ごとに独立コンテナ |
| GUI / ブラウザ | Chrome + TigerVNC + noVNC + chrome-devtools MCP（日本語入力 IBus-Mozc）。`--no-vnc` で軽量化 |
| Docker Socket Proxy | Docker API を検査中継し、ホスト bind・privileged 等の危険操作をブロック |
| SSH agent 転送 | 秘密鍵ファイルを渡さず署名操作のみ許可 |
| ブラックリスト FW | ペーストサイト・Webhook・メタデータ・SMTP・外部 SSH を遮断 |
| AI オーケストレーター | `claude-dev orchestrate`：ブレインストーミング→ worker への並列委譲で自律実行（[docs/06](docs/06_orchestration.md)） |
| VM モード（Linux） | コンテナ内ゲスト VM でネイティブ Docker（bind/compose/privileged 可） |
| GHCR 配布 | GitHub Actions が毎日ビルドしたイメージを `claude-dev pull` で取得（amd64/arm64） |

## アーキテクチャ

```
ホスト（Linux サーバ / macOS）
│
├── Makefile         セットアップ・ビルド・管理（OS 判定で CLI を選択）
├── claude-dev CLI   日常の開発操作（macOS では claude-dev-mac が claude-dev として動く）
│
├── プロジェクトコンテナ（都度起動）
│   ├── project-a  (VNC あり)   Chrome + noVNC + chrome-devtools MCP
│   ├── project-b  (--no-vnc)   軽量・ブラウザなし
│   └── ...                     同時に複数起動可能
│
├── claude-dev-docker-proxy (共有) Docker Socket Proxy（危険操作をブロック）
├── claude-dev-net              コンテナ間ネットワーク
│
├── claude-dev-auth (volume)        認証情報（.credentials.json / .claude.json）
├── claude-dev-config (volume)      共有シェル設定（.zshrc）
├── claude-dev-chrome-data (volume) Chrome プロファイル
└── claude-dev-history (volume)     コマンド履歴
```

- コンテナ内資産（イメージ・entrypoint・ファイアウォール・docker-proxy）は OS 非依存で共有し、**OS 差分はホスト側 CLI に閉じる**。詳細設計は [docs/02_architecture.md](docs/02_architecture.md)。

## 前提条件

| | Linux サーバ | macOS |
|---|---|---|
| OS / ランタイム | Ubuntu 22.04+ / Debian 12+、Docker Engine 24+ & CLI | macOS + Docker Desktop（Apple Silicon / Intel） |
| 必須ツール | `jq`、`git`、`make` | `jq`・`socat`（`brew install jq socat`）、`git`、`make`（Xcode CLT）。※`socat` は SSH agent 転送に必須 |
| アカウント | Claude Pro / Max（OAuth 認証） | 同左 |
| その他 | SSH アクセス | — |

> ホストサーバ側の事前準備（Docker 導入等）は [PREPARATION.md](PREPARATION.md) を参照。

---

## セットアップと使い方 — Linux の場合

```bash
# 1. クローン & 設定
git clone https://github.com/quvox/claude-dev-env.git ~/claude-dev-env
cd ~/claude-dev-env
cp .env.example .env && vim .env      # 任意（SSH 鍵/GHCR 設定など）

# 2. セットアップ（初回のみ：ビルド + PATH 登録を一括）
make setup

# 3. OAuth ログイン（表示される URL をブラウザで開いて認証 → /exit）
make login

# 4. 開発開始
cd ~/repos/my-project
claude-dev start                      # VNC + Chrome 付きで起動 & tmux 接続
```

- `make setup` は `.env` 作成 → Docker ネットワーク/ボリューム作成 → イメージビルド → `claude-dev` を `/usr/local/bin` に **symlink** 登録、を一括で行う（`/usr/local/bin` に書けなければ `sudo ln -sf` を案内）。
- イメージは **ホストのユーザー名・UID/GID を焼き込んで**ビルドされる（`/workspace` の所有権が一致）。
- **Web アプリのリモート確認**: サーバ上で `claude-dev forward <port>` → クライアント PC で `ssh -O forward -L <host-port>:localhost:<host-port> <server>` → ブラウザで `http://localhost:<host-port>`（[docs/01](docs/01_getting-started.md) 参照）。

---

## セットアップと使い方 — macOS の場合

macOS では CLI 本体は macOS 適応版 `claude-dev-mac` を使う。`make install` が OS を判定し `claude-dev-mac` を `/usr/local/bin/claude-dev` として登録するため、**利用者コマンド名はどの OS でも `claude-dev`** で同じ。

```bash
# 1. クローン & 前提ツール
git clone https://github.com/quvox/claude-dev-env.git ~/claude-dev-env
cd ~/claude-dev-env
brew install jq

# 2. セットアップ（macOS では claude-dev-mac を /usr/local/bin/claude-dev へ sudo symlink）
make setup                            # sudo パスワードを求められる

# 3. OAuth ログイン
make login

# 4. 開発開始
cd ~/repos/my-project
claude-dev start
```

macOS 固有のふるまい（詳細設計は [docs/09_macos-support.md](docs/09_macos-support.md)）:

- **SSH agent**: macOS の Unix ソケットは直接マウントできないため、Docker Desktop の魔法ソケット `/run/host-services/ssh-auth.sock` 経由でホストの ssh-agent を転送する。
- **Web アプリ**: 手元マシン = Docker ホストなので、`claude-dev forward <port>` の後は **`http://localhost:<host-port>` に直接アクセス**できる（SSH トンネル不要）。
- **Apple Silicon（arm64）**: ネイティブ arm64 でビルド/実行する。Google Chrome は Linux arm64 版が無いため、VNC の GUI ブラウザは **Playwright Chromium**（arm64 対応）を使う（chrome-devtools MCP はそのまま動作）。Intel Mac は従来どおり Google Chrome。
- **VM/KVM モード（`--vm` / `--kvm`）は非対応**（`/dev/kvm` が無く、ネスト仮想化も使えない）。Docker を多用する開発は通常起動（Docker Socket Proxy 経由）で行う。

---

## 日常のコマンド早見表

```bash
# 起動・接続
cd ~/repos/my-project
claude-dev start                 # そのディレクトリ用コンテナを起動 & tmux 接続（再実行で再接続）
claude-dev start --no-vnc        # Chrome/VNC なしの軽量モード
claude-dev attach my-project     # 名前指定で接続

# tmux 内で（コンテナの中）
claude                           # 素の Claude Code を起動
claude-orchestrator              # AI オーケストレーターを起動（orchestrate と同じ司令塔）
Ctrl-_ d                         # tmux をデタッチ（コンテナは動き続ける）→ さらに Ctrl-D でコンテナを抜ける

# AI オーケストレーター（コンテナ未起動なら自動起動 → tmux 内で司令塔を起動 → 接続）
claude-dev orchestrate                       # ブレインストーミングから開始
claude-dev orchestrate "ユーザー認証を実装"   # ゴールを与えて開始

# Web アプリのポートフォワード
claude-dev forward 3000          # host:8100 → container:3000
claude-dev ports                 # アクティブなフォワード + noVNC URL
claude-dev unforward 3000

# 管理
claude-dev list                  # 実行中セッション一覧（noVNC URL・フォワードも表示）
claude-dev stop my-project       # 停止（フォワードも自動クリーンアップ）
claude-dev upgrade               # 全イメージを更新（--no-cache 再ビルド）
make status                      # 全体の状態確認
```

VNC ありの場合、起動時に表示される noVNC URL（`http://localhost:<port>/vnc.html`）をブラウザで開くと、コンテナ内 Chrome の画面をリアルタイムに確認できる。日本語入力は `Super+Space`（IBus-Mozc）。全コマンドは [docs/04_cli-reference.md](docs/04_cli-reference.md)。

## GHCR からイメージを取得（ビルド不要）

`make build` の代わりに、GitHub Actions が毎日ビルドして GitHub Container Registry(GHCR) に push したイメージを pull して使える（amd64/arm64 両対応）。

```bash
cd ~/claude-dev-env
cp .env.example .env             # 必要なら CLAUDE_DEV_REGISTRY / CLAUDE_DEV_IMAGE_TAG を編集
claude-dev pull                  # 最新(latest)を取得しローカル名に retag
claude-dev pull 202607041830     # 特定バージョン(YYYYMMDDHHmm)に固定して取得
cd ~/repos/my-project && claude-dev start   # pull 済みイメージを使う（再ビルドなし）
```

- タグは `YYYYMMDDHHmm`（JST）と `latest`。private パッケージなら事前に `docker login ghcr.io`（PAT）が必要。
- 配布イメージは generic user（`dev`）で焼かれ、UID/GID は起動時に `/workspace` 所有者へ追従する。
- 仕組み・定期ビルドの設計は [docs/10_ghcr-images.md](docs/10_ghcr-images.md)。

## VM モード（Linux 専用・Docker を多用する開発）

bind mount や docker compose を使う「Docker 中心のシステム」を開発する場合、既定構成（Docker Socket Proxy 経由）ではホスト bind mount が使えない。**VM モード**は、コンテナ内に KVM のゲスト VM を立て、その中で**ネイティブ Docker**（bind mount・compose・privileged 可）を動かすことでこれを解決する。**macOS では非対応**。

```bash
cd ~/repos/docker-heavy-project
claude-dev start --vm            # ゲスト VM を起動（--kvm を含意。ホストに /dev/kvm が必要）
docker compose up                # bind mount もそのまま効く（/workspace 配下は即反映）
VM_PORTS=3000,8080 claude-dev start --vm   # アプリのポートも転送する場合

vm status | vm shell | vm logs   # コンテナ内 VM ヘルパー
```

- **仕組み**: ホスト → claude コンテナ → ゲスト VM → VM 内 Docker。コードは virtiofs で `/workspace` を同一パス共有（ライブ反映）、`docker` は `DOCKER_HOST` でゲストの daemon を指す。
- **前提**: ホストに `/dev/kvm`（ベアメタル or ネスト仮想化有効なクラウド）。設計は [docs/08_vm-mode.md](docs/08_vm-mode.md)。

## セキュリティ

多層防御で Claude Code の暴走・情報漏洩リスクを軽減する（詳細 [docs/03_security.md](docs/03_security.md)）。

1. **Docker コンテナ隔離** — ホストファイルシステムへのアクセスを遮断
2. **マウント制限** — SSH 秘密鍵、`~/.aws`、`.env` 等はコンテナに存在しない
3. **認証情報の保護** — 専用ボリュームにマウントし、ファイアウォールで窃取先をブロック
4. **Docker Socket Proxy** — 生ソケットを渡さず、ホスト bind・privileged・host ネットワーク等をブロック
5. **SSH agent 転送** — 秘密鍵ファイルを渡さず署名操作のみ許可
6. **ブラックリスト FW** — ペーストサイト・Webhook・メタデータ・SMTP・外部 SSH を遮断
7. **非 root 実行** — UID/GID をホストに合わせて実行（ローカルビルドはユーザー名も一致。GHCR 配布版は generic user で UID/GID を起動時に追従）
8. **git ロールバック** — 変更はすべて `git diff` で確認、`git checkout` で復元可能

## ディレクトリ構成

```
claude-dev-env/
├── Makefile                     セットアップ・ビルド・管理タスク（OS 判定で CLI を選択）
├── claude-dev                   CLI 本体（Linux 版）
├── claude-dev-mac               CLI 本体（macOS 版。make install が claude-dev として配置）
├── .env.example                 設定テンプレート（SSH 鍵・GHCR レジストリ/タグ等）
├── CLAUDE.md                    コンテナ内 Claude Code 向けの開発ルール
├── INDEX.md                     ドキュメント索引（まずここを見る）
├── PREPARATION.md               ホスト側の事前準備手順
│
├── .devcontainer/
│   ├── Dockerfile.claude        Claude コンテナ（マルチステージ base→vnc。arm64 対応）
│   └── Dockerfile.docker-proxy  Docker Socket Proxy コンテナ
│
├── .github/workflows/
│   └── ghcr-images.yml          GHCR へ毎日・マルチアーキで push する CI
│
├── docker-proxy/                Docker Socket Proxy ソース（Go）
├── orchestrator/                AI オーケストレーター ソース（Go。claude-orchestrator）
├── examples/orch-sample/        オーケストレーター自己検証用サンプル
│
├── scripts/
│   ├── entrypoint-claude.sh     コンテナ起動スクリプト（UID/GID 追従・認証共有・VNC/Chrome 起動）
│   ├── init-firewall-claude.sh  ブラックリスト方式ファイアウォール
│   ├── dood-portsync.sh         DooD 時のホスト公開ポートを 127.0.0.1 へ同期
│   ├── vm-up.sh / vm / vm-*.sh  VM モード：ゲスト VM 起動・操作・ポート同期・監視
│   ├── VM_DEV.md.tmpl           VM モードのエージェント向け情報テンプレート
│   ├── save_prompt.sh / sendslackmsg.sh  Claude Code hook（履歴保存・Slack 通知）
│   ├── orch-sample.sh           サンプル scaffold
│   └── tmux.conf                tmux 設定（prefix: Ctrl-_）
│
└── docs/                        設計・実装仕様・レビュー（下表）
```

## ドキュメント

| ドキュメント | 内容 |
|------------|------|
| [INDEX.md](INDEX.md) | ドキュメント全体の索引（要約・キーワード付き） |
| [docs/01_getting-started.md](docs/01_getting-started.md) | インストール手順と基本的な使い方 |
| [docs/02_architecture.md](docs/02_architecture.md) | システム設計・コンテナ構成・認証フロー |
| [docs/03_security.md](docs/03_security.md) | 脅威モデルと防御層の詳細 |
| [docs/04_cli-reference.md](docs/04_cli-reference.md) | 全コマンドのリファレンス |
| [docs/05_customization.md](docs/05_customization.md) | ファイアウォール・CLAUDE.md・tmux・hooks/env 等のカスタマイズ |
| [docs/06_orchestration.md](docs/06_orchestration.md) | AI オーケストレーターの設計 |
| [docs/08_vm-mode.md](docs/08_vm-mode.md) | VM モード（Linux）の設計 |
| [docs/09_macos-support.md](docs/09_macos-support.md) | macOS（Docker Desktop）対応の設計（claude-dev-mac） |
| [docs/10_ghcr-images.md](docs/10_ghcr-images.md) | GHCR への定期 push・pull 運用の設計 |
| [docs/impl/INDEX.md](docs/impl/INDEX.md) | 実装仕様書（コードと 1 対 1 の Single Source of Truth）一覧 |

# claude-dev — Claude Code / Codex CLI の隔離開発環境

エージェント CLI（Claude Code・OpenAI Codex CLI）を、**承認待ちで止まらず・コンテナで隔離して・
SSH が切れても動き続ける**状態で使うための Docker 開発環境です。**Linux サーバ**と
**macOS（Docker Desktop）**で動きます。

任意のプロジェクトディレクトリで `claude-dev start` と打つと、そのディレクトリ専用のコンテナが
立ち上がり、tmux の中で `claude` や `codex` がすぐ動きます。

```bash
cd ~/repos/my-project
claude-dev start      # → コンテナ起動 & tmux に接続
claude                # → 承認待ちなしの Claude Code
```

---

## 目次

- [1. これは何か（考え方）](#1-これは何か考え方)
- [2. 全体像](#2-全体像)
- [3. 必要なもの](#3-必要なもの)
- [4. 導入手順](#4-導入手順)
- [5. 最初の 5 分](#5-最初の-5-分)
- [6. 日常の使い方](#6-日常の使い方)
- [7. プロジェクトの設定（`.claude-dev.yaml`）](#7-プロジェクトの設定claude-devyaml)
- [8. コマンド一覧](#8-コマンド一覧)
- [9. イメージの入手と更新](#9-イメージの入手と更新)
- [10. VM モード（Linux 専用）](#10-vm-モードlinux-専用)
- [11. セキュリティ](#11-セキュリティ)
- [12. 保守者向け](#12-保守者向け)
- [13. 困ったときは](#13-困ったときは)
- [14. リポジトリの構成とドキュメント](#14-リポジトリの構成とドキュメント)

---

## 1. これは何か（考え方）

### 解きたい問題

エージェントにコードを書かせ、実行させると、次の 3 つが同時に起きます。

1. **承認待ちで止まる。** ファイル変更やコマンド実行のたびに確認を求められ、自律作業が進まない。
   かといってホストで `--dangerously-skip-permissions` を使うと、レビュー前のコードがホストの
   ファイルシステムや認証情報へ到達しうる。
2. **SSH が切れると作業も切れる。** サーバ上で走らせているエージェントが、接続断で止まる。
3. **環境が人ごと・案件ごとにばらつく。** 再現性がない。

### 出している答え

| 問題 | この環境の答え |
|---|---|
| 承認待ち | **コンテナの中でだけ**権限バイパスを効かせる。ホストの資産はそもそもコンテナに存在しない |
| 中断 | コンテナ内の **tmux** でセッションを永続化する。SSH を切っても、コンテナは動き続ける |
| ばらつき | 環境一式を **Docker イメージ**として配布する。`claude-dev pull` で全員が同じ構成を得る |

### 中心にある 1 つの考え方 — 「1 ディレクトリ = 1 コンテナ」

`claude-dev start` は、**実行したディレクトリに紐づいたコンテナ**を起動します。

- コンテナ名は**ディレクトリ名**から決まります。別のディレクトリで `start` すれば、別のコンテナが
  立ちます（案件ごとに独立し、同時に走らせられます）。
- 起動したディレクトリが、コンテナの中では **`/workspace`** として見えます。ホストでの編集は即座に
  コンテナへ、その逆も同様に反映されます。
- 同じディレクトリで再度 `start` すると、**起動中のコンテナへ再接続**します（立て直しません）。

したがって「プロジェクトを開く」＝「そのディレクトリで `claude-dev start` する」だけです。

### 隔離の考え方 — 何を渡さないか

コンテナには、**ホストの秘密鍵ファイルも、Docker の生ソケットも入っていません。**

- SSH は**鍵ファイルではなく ssh-agent のソケット**だけを渡します（署名操作だけが転送され、鍵の
  中身はコンテナに存在しません）。
- Docker は**生ソケットではなく検査つきの中継（docker-proxy）**を経由します。ホストのルートを
  持ち込む bind mount や特権コンテナは拒否されます。
- 外向き通信は**ブラックリスト型のファイアウォール**を通ります（ペーストサイト・Webhook 収集
  サイト・クラウドメタデータ・SMTP・GitHub 以外の外部 SSH を遮断）。

### 前提（この環境が守る範囲）

**信頼できる社内開発用途に限定**した設計です。信頼できない第三者のコードを持ち込んで実行する用途や、
本番に近い環境での利用は対象外です。隔離境界は**コンテナとホストの間の 1 本だけ**に置いており、
コンテナ内のプロセス単位の隔離は行いません（`docs/00-requests/request.md`「やらないこと」）。

---

## 2. 全体像

```
ホスト（Linux サーバ / macOS）
│
├── claude-dev            ホスト側 CLI。起動・停止・ポート・認証・鍵をすべてここから操作する
│                         （macOS では claude-dev-mac が claude-dev という名前で入る）
├── Makefile              セットアップ・イメージビルド・状態確認
│
├── Claude コンテナ（プロジェクトごとに 1 つ、同時に何個でも）
│   ├── my-project        /workspace ← ホストの ~/repos/my-project
│   │   ├─ tmux           セッション永続化（prefix: Ctrl-_）
│   │   ├─ claude / codex エージェント CLI
│   │   ├─ Chrome + noVNC ブラウザ確認（--no-vnc で省ける）
│   │   └─ firewall       ブラックリスト型の外向き通信制御
│   └── another-project   別コンテナ。互いのファイルも鍵も見えない
│
├── claude-dev-docker-proxy   全コンテナで共有。Docker API を検査して危険な操作を拒否する
├── claude-dev-net            コンテナ間ネットワーク
│
├── claude-dev-auth (volume)          認証情報（Claude / Codex）※全プロジェクトで共有
├── claude-dev-config (volume)        共有シェル設定
├── claude-dev-history (volume)       コマンド履歴
└── claude-dev-chrome-<name> (volume) Chrome プロファイル ※コンテナごと
```

OS による違いは**ホスト側 CLI の中だけ**に閉じてあります。コンテナの中身（イメージ・起動処理・
ファイアウォール・docker-proxy）は Linux でも macOS でも同一です。

設計の詳細は [docs/02-design/architecture.md](docs/02-design/architecture.md)。

---

## 3. 必要なもの

| | Linux サーバ | macOS |
|---|---|---|
| OS | Ubuntu 22.04+ / Debian 12+ | macOS（Apple Silicon / Intel） |
| ランタイム | Docker Engine 24+ | Docker Desktop |
| 必須ツール | `jq` `git` `make` | `jq` `socat`（`brew install jq socat`）、`git`、`make`（Xcode CLT） |
| アカウント | Claude Pro / Max（OAuth）。Codex を使うなら OpenAI アカウント | 同左 |

- macOS の `socat` は **SSH agent 転送に必須**です（Docker Desktop では Unix ソケットを直接
  マウントできないため、TCP ブリッジを立てます）。
- サーバを一から用意する場合の手順（Docker 導入・SSH・ファイアウォール・Tailscale 等）は
  [PREPARATION.md](PREPARATION.md) にあります。

---

## 4. 導入手順

### Linux

```bash
git clone https://github.com/quvox/claude-dev-env.git ~/claude-dev-env
cd ~/claude-dev-env

make setup      # .env 作成 → ネットワーク/ボリューム作成 → イメージビルド → CLI を PATH へ登録
make login      # Claude の OAuth ログイン（表示された URL をブラウザで開いて認証 → /exit）
```

### macOS

```bash
brew install jq socat
git clone https://github.com/quvox/claude-dev-env.git ~/claude-dev-env
cd ~/claude-dev-env

make setup      # sudo パスワードを求められます（/usr/local/bin への symlink 作成のため）
make login
```

### `make setup` が実際にやること

1. `.env.example` を `.env` へコピー（既にあれば触りません）
2. Docker ネットワーク `claude-dev-net` と共有ボリューム 4 本を作成
3. イメージ 3 種をビルド（`claude-dev-claude` / `claude-dev-claude-vnc` /
   `claude-dev-docker-proxy`）
4. `/usr/local/bin/claude-dev` を CLI 本体への symlink として作成（`sudo ln -sf`）

**コマンド名はどの OS でも `claude-dev`** です。macOS では `claude-dev-mac` の中身が呼ばれます。

> **ビルドせずに始めることもできます。** `make setup` の代わりに `make install`（PATH 登録だけ）
> を行い、`claude-dev pull` で GHCR のビルド済みイメージを取得する方法があります
> （→ [9. イメージの入手と更新](#9-イメージの入手と更新)）。ローカルビルドはホストのユーザー名と
> UID/GID をイメージへ焼き込むため `/workspace` の所有権がそのまま一致し、GHCR 版は起動時に
> `/workspace` の所有者へ UID/GID を合わせます。

---

## 5. 最初の 5 分

```bash
mkdir -p ~/repos/hello && cd ~/repos/hello && git init

claude-dev start
```

初回起動時、そのプロジェクトに `.claude-dev.yaml` が無ければ **SSH 鍵を選ぶ画面**が出ます
（`~/.ssh` の鍵一覧。番号をカンマ・空白区切りで指定、`a` で全部、`n` で使わない）。`n` を選べば
SSH 転送なしで始まり、以後は聞かれません。

起動すると tmux に接続された状態になります。ここから先はコンテナの中です。

```
claude          # Claude Code（承認待ちなし）
codex           # OpenAI Codex CLI
docker ps       # 検査つきの中継越しに Docker が使える
```

抜けるときは次のとおりです。

| やりたいこと | 操作 |
|---|---|
| tmux から一時的に離れる（作業は継続） | `Ctrl-_` → `d` |
| コンテナから出る（コンテナは動き続ける） | デタッチしてから `Ctrl-D` |
| 戻る | 同じディレクトリで `claude-dev start`（または `claude-dev attach <名前>`） |
| 完全に止める | `claude-dev stop <名前>` |

tmux の prefix は **`Ctrl-_`**（Ctrl とアンダースコア）です。マウスでのスクロール・ペイン操作も
有効になっています。

---

## 6. 日常の使い方

### 6.1 エージェント CLI

- **`claude`** — Claude Code。コンテナ内では権限バイパスが効くので、承認待ちで止まりません。
- **`codex`** — OpenAI Codex CLI。使う前に一度だけホスト側で `claude-dev login-codex`
  （デバイス認証）を実行してください。認証は共有ボリュームに入るので、**別のプロジェクトでも
  ログインし直す必要はありません**。
  - コンテナ内の `~/.codex/config.toml` には、初回起動時に既定 3 鍵
    （`sandbox_mode = "danger-full-access"` / `approval_policy = "never"` /
    `[features] use_legacy_landlock = true`）が置かれます。既にファイルがある場合は、
    **書かれていない鍵だけが追記**され、既存の値は変わりません。
  - これは codex 自前のサンドボックス（bubblewrap）が Docker の seccomp / AppArmor 下では
    起動できず、**失敗が静かに起きる**ためです。隔離はコンテナ境界が担います。読み取り専用を
    明示した呼び出しだけは landlock バックエンドで成立します
    （[docs/02-design/architecture.md](docs/02-design/architecture.md) `DSN-dist-02`）。
- **`claude-dev code`** — ホスト側から、稼働中コンテナの**新しい tmux ウィンドウ**で Claude Code を
  起動します。

認証（Claude / Codex）は共有ボリュームからコピーされ、トークンが更新されると 30 秒周期で共有側へ
書き戻されます。**プロジェクトをまたいでログイン状態が引き継がれます。**

### 6.2 Web アプリをブラウザで確認する

`claude-dev start` した時点では、**利用者の Web アプリ用のポートは 1 つも公開されていません**。
必要になったときだけ開きます。

```bash
claude-dev forward 3000      # ホスト側ポート（8100 番台）を自動で割り当てて中継する
claude-dev ports             # 今開いているフォワードと noVNC URL の一覧
claude-dev unforward 3000    # 解除
```

- **Linux サーバの場合**：表示されたホスト側ポートを SSH トンネルで手元へ転送します。
  ```bash
  ssh -O forward -L <host-port>:localhost:<host-port> <server>
  # → 手元のブラウザで http://localhost:<host-port>
  ```
- **macOS の場合**：手元のマシンが Docker ホストなので、`http://localhost:<host-port>` へ直接
  アクセスできます（トンネル不要）。

### 6.3 noVNC でコンテナ内 Chrome を見る

既定（VNC あり）で起動すると、コンテナ内の Chrome を**ブラウザから閲覧・操作**できます。
エージェントに E2E をやらせている様子をそのまま目で見られます。

- URL は `claude-dev start` 時に表示されます（`http://localhost:<port>/vnc.html`、6080 番台）。
  後からは `claude-dev ports` か `claude-dev list` で確認できます。
- リモートサーバなら、そのポートを SSH トンネルで手元へ転送してから開きます。
  ```bash
  ssh -L <port>:localhost:<port> <server>
  ```
- 日本語入力（IBus-Mozc）の切り替えは **`Super+Space` / `Ctrl+\` / `F3`** のいずれかです。
  デスクトップ上で右クリックするとメニュー（Chrome / Terminal / IME 切替）が出ます。
- ブラウザが不要なら **`claude-dev start --no-vnc`**（Chrome/VNC なしの軽量構成）で起動します。

コンテナ内の Claude Code には `chrome-devtools` MCP（`http://localhost:9222` 直結）と
`computer-use` MCP（`rmcp-xdotool`、`DISPLAY=:99`）が設定済みです。

### 6.4 停止と後片付け

```bash
claude-dev stop my-project              # 停止（そのセッションが作ったコンテナ・ネットワークも削除）
claude-dev stop my-project --volumes    # 加えて、そのセッションが作ったボリュームも削除
```

`stop` は、**そのコンテナの中から作られた Docker 資源**（`docker run` でも `docker compose up` でも
経路を問わない）を片付けます。ただし**名前付きボリュームだけは既定で残し**、残っていることと
削除方法を表示します。作り直せないものが失われるのはボリュームだけだからです。消してよいと分かって
いるときに `--volumes` を付けてください。

コンテナ内から `docker` を使うときの compose プロジェクト名は、プロジェクトごとに一意化されます
（全プロジェクトが `/workspace` にマウントされるため、既定名のままでは衝突するからです）。

---

## 7. プロジェクトの設定（`.claude-dev.yaml`）

プロジェクトディレクトリ直下に置く設定ファイルです。**キーは 2 つだけ**で、どちらも省略できます。

```yaml
# .claude-dev.yaml
ssh_keys:                        # コンテナへ agent 転送する SSH 鍵
  - ~/.ssh/id_ed25519_github
env_file: .env.project           # コンテナへ渡す環境変数を書いたファイル（相対パス）
```

このファイルは**版管理に入る前提**です。秘密の値そのものは書かず、`env_file` が指す先に置きます。

### 7.1 `ssh_keys` — コンテナから git push / SSH する

コンテナ内から `git push` や SSH をしたいときに使います。**秘密鍵ファイルは渡さず**、ssh-agent の
署名操作だけを転送します。設定はプロジェクトごとに独立します。

| したいこと | 操作 |
|---|---|
| 初回に選ぶ | `.claude-dev.yaml` が無い状態で `claude-dev start`（対話選択が出ます） |
| 後から選び直す | `claude-dev ssh-keys` |
| 解除・初期化 | `claude-dev ssh-keys reset`（`ssh_keys` 節を消し、専用 ssh-agent を停止） |
| 手で書く | `.claude-dev.yaml` を直接編集（`- ~/.ssh/id_ed25519` の形で列挙。空なら転送なし） |

`claude-dev ssh-keys` は `ssh_keys` 節だけを差し替え、**`env_file` 行や自分で書いたコメントは
残します**。設定を変えたら `claude-dev stop` → `start` で反映してください。

### 7.2 `env_file` — プロジェクトごとの環境変数をコンテナへ渡す

案件ごとに違う値（接続先 URL、社内サービスのトークン、動作を切り替えるフラグ）をコンテナ内の
ツールへ渡すための仕組みです。**`.claude-dev.yaml` には場所だけを書き、値の実体は env ファイルに
置きます。**

```yaml
# .claude-dev.yaml
env_file: .env.project
```

```bash
# .env.project（プロジェクトディレクトリ直下に作る）
API_BASE_URL=https://staging.example.com
FEATURE_FLAG_X=1
INTERNAL_TOKEN=xxxxxxxx
```

```bash
claude-dev start
# コンテナ内で
echo $API_BASE_URL     # → https://staging.example.com
```

渡した値は **tmux 配下のすべてのプロセスから見えます**（ビルド・テスト・エージェント CLI を含む）。
**そのプロジェクトのコンテナの中だけ**で見え、別プロジェクトのコンテナには渡りません。

#### 規則（すべて実装どおり）

| 事項 | ふるまい |
|---|---|
| 書式 | 1 行 1 組の `名前=値`。空行と `#` で始まる行は無視 |
| 値の中の `=` | 最初の `=` だけで名前と値を割るので、値に `=` を含められる |
| 引用符 | 値を囲む引用符は**取り除きません**（引用符そのものを値にできます） |
| パス | **プロジェクトディレクトリからの相対パスだけ**を受理。絶対パスと外を指す指定は採用しません |
| 版管理 | 指定すると `.gitignore` へ自動追記し、追跡から外れているかを確認します |
| ファイルが無い / 読めない | 環境変数を渡さずに**起動は続きます**（警告のみ） |
| 指定が無い | 何も表示せずに起動します（正常な省略です） |
| 読めない行 | その行だけ採用せず、**何行目か**を表示します |
| 同じ名前が 2 回 | **後に書いたほう**を採用します |
| 予約名 | 採用せず、**採用しなかった名前**を表示します（下記） |
| ログ | 値そのものは端末にも起動ログにも出ません。出るのは名前と行番号だけです |

**予約名（この仕組み自身が使うため採用されない名前）**:
`CLAUDE_DEV_*` / `DOCKER_HOST` / `COMPOSE_PROJECT_NAME` / `SSH_AUTH_SOCK` / `NODE_OPTIONS` /
`container`。判定は大文字小文字を区別する完全一致（`CLAUDE_DEV_*` のみ前方一致）なので、
`docker_host` のような別名は採用されます。これらを差し替えられると `stop` の後片付けが空振りしたり、
検査を通らない Docker 経路へ切り替わりうるため、上書きを許していません。

> **リポジトリ直下の `.env` とは別物です。**
> `claude-dev-env/.env`（`.env.example` からコピーするもの）は **ホスト側 CLI の設定**
> （GHCR のレジストリ・タグ、Samba 共有、macOS の SSH ブリッジポート）で、コンテナへは渡りません。
> `env_file` が指すのは**コンテナへ渡す値**のファイルです。`env_file: .env` と書くと
> `SAMBA_PASSWORD` などがコンテナへ渡ってしまうので、別のファイル名にしてください。

### 7.3 ホスト側 CLI が読む環境変数

| 変数 | 効果 | 既定 |
|---|---|---|
| `CLAUDE_DEV_REGISTRY` | `claude-dev pull` の取得元 | `ghcr.io/quvox` |
| `CLAUDE_DEV_IMAGE_TAG` | `claude-dev pull` のタグ | `latest` |
| `CLAUDE_DEV_NO_ATTACH` | `1` にすると `start` 後に tmux へ自動接続しない | 未設定 |
| `CLAUDE_DEV_ALLOW_WORKSPACE_BINDS` | 作業領域配下の bind mount を docker-proxy が許可するか | `1`（許可） |
| `CLAUDE_DEV_SSH_BRIDGE_PORT` | macOS の SSH agent ブリッジのポートを固定する | 自動割当（9700〜） |
| `VM_PORTS` `VM_MEM` `VM_SMP` `VM_DISK` `VM_SWAP` | VM モードのゲスト設定 | 各既定値 |

---

## 8. コマンド一覧

```
セットアップ
  claude-dev setup                    イメージビルド + インフラ構築
  claude-dev pull [TAG]               GHCR からビルド済みイメージを取得（既定 latest）
  claude-dev login                    Claude の OAuth ログイン
  claude-dev login-codex              Codex のデバイス認証ログイン
  claude-dev logout [--yes]           認証情報を削除（Claude / Codex 双方）

開発
  claude-dev start                    カレントディレクトリで起動（VNC + Chrome 付き）
  claude-dev start --no-vnc           Chrome / VNC なしの軽量構成で起動
  claude-dev start --vm               VM モードで起動（Linux のみ。--kvm を含意）
  claude-dev start --vm-fresh         ゲスト VM を破棄して再 provision（Linux のみ）
  claude-dev start --kvm              KVM/QEMU デバイスだけを渡して起動（Linux のみ）
  claude-dev code                     新しい tmux ウィンドウで Claude Code を起動
  claude-dev attach [NAME]            既存セッションに接続
  claude-dev stop [NAME] [--volumes]  停止（--volumes でセッション由来のボリュームも削除）
  claude-dev list                     実行中セッション一覧（noVNC URL・フォワードも表示）

SSH 鍵
  claude-dev ssh-keys                 使う鍵を対話選択して .claude-dev.yaml へ保存
  claude-dev ssh-keys reset           このプロジェクトの鍵選択を初期化

ポートフォワード
  claude-dev forward <PORT> [NAME]    ポートを動的に追加
  claude-dev unforward <PORT> [NAME]  解除
  claude-dev ports [NAME]             一覧

メンテナンス
  claude-dev upgrade                  全イメージを --no-cache で再ビルド
  claude-dev firewall                 ファイアウォールルールを表示
  claude-dev reset [--yes] [--volumes] 全削除して初期状態へ戻す
  claude-dev help                     ヘルプ
```

`[NAME]` はプロジェクトのディレクトリ名です。省略するとカレントディレクトリから判定します。
`claude-dev list` で確認できます。

Makefile 側の入口:

```
make setup            初回セットアップ（env + network + volumes + build + install）
make install          CLI を /usr/local/bin/claude-dev へ登録するだけ
make uninstall        その登録を解除
make build            全イメージをビルド
make build-claude / build-claude-vnc / build-docker-proxy   個別ビルド
make update-claude    Claude Code だけを高速更新（他はキャッシュ利用）
make upgrade          全イメージを --no-cache で再ビルド
make login            OAuth ログイン
make status           イメージ・稼働セッション・docker-proxy・ボリュームの状態確認
make clean            全リセット（確認プロンプトあり）
```

---

## 9. イメージの入手と更新

GitHub Actions が**毎日 03:30 JST** にイメージをビルドし、GitHub Container Registry へ push して
います（amd64 / arm64 の両対応）。タグは `YYYYMMDDHHmm`（JST）と `latest` です。

```bash
claude-dev pull                  # latest を取得してローカル名へ retag
claude-dev pull 202608200330     # 特定ビルドに固定して取得
```

- 取得後の `claude-dev start` は、そのイメージをそのまま使います（再ビルドしません）。
- **pull しても、起動中のコンテナには反映されません。** 反映するには
  `claude-dev stop` → `claude-dev start` でコンテナを作り直してください。
- private パッケージの場合は事前に `docker login ghcr.io`（PAT）が必要です。

```bash
claude-dev pull
claude-dev stop  my-project
cd ~/repos/my-project && claude-dev start
```

自分でビルドする場合は `make build`（初回）、`make update-claude`（Claude Code だけ差し替え。
Go/Rust/Playwright 等の層はキャッシュを使うので再ビルドしません）、`make upgrade`（全イメージを作り直し）を
使い分けます。

---

## 10. VM モード（Linux 専用）

bind mount や `docker compose` を多用する「Docker 中心」のシステムを開発する場合、既定構成
（docker-proxy 経由）ではホストの bind mount が使えません。**VM モード**は、コンテナの中に
ゲスト VM（QEMU + virtiofs）を立て、その中で**ネイティブ Docker** を動かすことでこれを解決します。

```bash
cd ~/repos/docker-heavy-project
claude-dev start --vm                        # ゲスト VM を起動（ホストに /dev/kvm が必要）
VM_PORTS=3000,8080 claude-dev start --vm     # ゲストのポートも転送する場合
```

コンテナ内には操作用のヘルパー `vm` が入っています。

```
vm status | vm shell | vm restart | vm rebuild | vm portsync | vm down | vm logs
```

- 層構成は「ホスト → Claude コンテナ → ゲスト VM → VM 内 Docker」です。`/workspace` は virtiofs で
  同一パスに共有されるためライブ反映され、`docker` は `DOCKER_HOST` でゲストの daemon を指します。
- Claude コンテナ自体は privileged にしません。
- ホストに `/dev/kvm` が無い場合、`--vm` は起動せずに中止します。
- **macOS では非対応**です（`/dev/kvm` が無く、ネスト仮想化も使えないため、`--vm` / `--kvm` /
  `--vm-fresh` は即座に拒否されます）。Docker を多用する開発は通常起動で行ってください。
- 初回は cloud image の取得と provision で数分かかります（以降は数十秒程度）。

---

## 11. セキュリティ

多層で守ります。詳細は [docs/02-design/architecture.md](docs/02-design/architecture.md) と
[docs/01-requirements/non-functional.md](docs/01-requirements/non-functional.md)。

| 層 | 内容 |
|---|---|
| コンテナ隔離 | ホストのファイルシステムはマウントしない。見えるのは `/workspace`（起動したディレクトリ）だけ |
| 秘密鍵を渡さない | SSH は agent ソケットのみ転送。`~/.ssh` の鍵ファイルはコンテナに存在しない |
| 生ソケットを渡さない | Docker は docker-proxy 経由。ホストのルート持ち込み・特権コンテナ・host ネットワーク/PID 共有を拒否 |
| 外向き通信の制御 | ペーストサイト（pastebin 等）・Webhook 収集サイト・トンネリングサービス・クラウドメタデータ（169.254.169.254 等）・SMTP（25/465/587）・GitHub 以外の外部 SSH を遮断 |
| 認証情報の保護 | 専用ボリュームに置き、イメージには焼き込まない |
| 非 root 実行 | UID/GID をホスト側の `/workspace` 所有者に合わせて実行 |
| 所有者ラベル | セッション内から作られた Docker 資源にラベルを付け、片付けの対象を「自分が作ったもの」に限定 |
| git による復元 | 変更は `git diff` で確認でき、`git checkout` で戻せる |

**この保証の限界**：docker-proxy が拒否できるのは、**要求の中身を検査できた場合に限ります**。
解釈できなかった要求は止められません（正常な操作を誤って止めないための割り切りです）。
残存リスクは `docs/issues/` が追跡しています。

ファイアウォールのブロック対象は**編集される前提のテンプレート**です。現在のルールは
`claude-dev firewall` で確認でき、定義は `scripts/init-firewall-claude.sh` にあります。

---

## 12. 保守者向け

### 社内ツールをイメージへ同梱する（`externals/`）

`externals/` へ置いた実行ファイルは、配布イメージ 2 種の `/usr/local/bin` へ設置され、コンテナ内で
コマンド名だけで起動できるようになります。**ビルド時に外部から何も取得しません** — 置いたものが
そのまま入ります。

| 置き場 | 入るイメージ |
|---|---|
| `externals/` 直下 | すべてのアーキテクチャ |
| `externals/amd64/` | amd64 のイメージにだけ追加 |
| `externals/arm64/` | arm64 のイメージにだけ追加 |

**置く前に**：ここに置いたものは公開リポジトリにコミットされ、公開 GHCR イメージへ焼かれます。
認証情報・秘密鍵・API キーを置かないこと、公開配布してよいものに限ることを確認してください
（一度公開したものは回収できません）。規約の詳細は [externals/README.md](externals/README.md)。

### テスト・lint

| 用途 | コマンド |
|---|---|
| lint | `cd docker-proxy && go vet ./...` |
| 単体・結合テスト | `cd docker-proxy && go test ./...` |
| カバレッジ | `cd docker-proxy && go test -cover ./...` |
| E2E | 自動ランナーはありません。実機で `claude-dev` を操作します（手順は `docs/03-impl/tests/e2e.md`） |

シェルスクリプト側には自動 lint を設けていません。CI（GHCR ビルド）でもテストは実行していません。

### 配布ワークフロー

`.github/workflows/ghcr-images.yml` が毎日 03:30 JST に走り、`prepare` → `build`（アーキ別）→
`merge`（マルチアーキ manifest 作成）の順でイメージを push します。手動実行時は同梱する
Claude Code / Codex CLI のバージョンを指定できます。

---

## 13. 困ったときは

| 症状 | 対処 |
|---|---|
| `claude-dev pull` したのに新しくならない | 起動中コンテナには反映されません。`claude-dev stop` → `start` で作り直してください |
| 「同名のコンテナが既に稼働している」と出る | コンテナ名はディレクトリ名から決まります。別ディレクトリの同名プロジェクトが動いています。表示されるディレクトリで作業するか、`claude-dev stop <名前>` してください |
| コンテナ内から `git push` できない | `claude-dev ssh-keys` で鍵を選び、`stop` → `start` し直してください。macOS では `socat` が必要です |
| env ファイルの値が見えない | 相対パスで書いているか、予約名を使っていないかを確認してください。起動時のメッセージに、採用しなかった名前と行番号が出ます |
| `--vm` が「/dev/kvm が必要」で止まる | ベアメタルか、ネスト仮想化を有効にしたインスタンスが必要です。macOS では VM モード自体が使えません |
| noVNC が開けない | リモートサーバの場合は SSH トンネルが必要です。ポートは `claude-dev ports` で確認できます |
| Codex のコマンドが毎回失敗する | `~/.codex/config.toml` の既定 3 鍵が入っているか確認してください（6.1 節） |
| 全部やり直したい | `claude-dev reset --yes`（初期状態へ戻す）または `make clean` |

現在の状態は `make status` と `claude-dev list` で確認できます。

---

## 14. リポジトリの構成とドキュメント

```
claude-dev-env/
├── claude-dev                   ホスト CLI 本体（Linux 版）
├── claude-dev-mac               ホスト CLI 本体（macOS 版。make install が claude-dev として配置）
├── Makefile                     セットアップ・ビルド・管理（OS 判定で CLI を選択）
├── .env.example                 ホスト側 CLI の設定テンプレート（GHCR・Samba・macOS SSH ブリッジ）
├── PREPARATION.md               サーバを一から用意する手順
├── INDEX.md                     ドキュメント索引
│
├── .devcontainer/
│   ├── Dockerfile.claude        Claude コンテナ（base → vnc-base → claude-cli / claude-vnc）
│   ├── Dockerfile.docker-proxy  Docker Socket Proxy
│   └── tmux.conf                コンテナの /etc/tmux.conf
├── docker-proxy/                Docker Socket Proxy の実装（Go）
├── externals/                   配布イメージへ同梱する外部実行ファイルの置き場
├── scripts/
│   ├── entrypoint-claude.sh     起動処理（UID/GID 追従・認証共有・FW・VNC/Chrome・tmux）
│   ├── init-firewall-claude.sh  ブラックリスト型ファイアウォール
│   ├── dood-portsync.sh         DooD 時の公開ポート同期
│   ├── vm / vm-up.sh / vm-*.sh  VM モード
│   └── tmux.conf                コンテナの ~/.tmux.conf（prefix: Ctrl-_）
├── .github/workflows/
│   └── ghcr-images.yml          GHCR への日次・マルチアーキ push
└── docs/                        仕様ドキュメント（下表）
```

`docs/` は 4 階層の仕様ドキュメント（SSOT）です。**現在のシステムの姿だけ**を書き、計画や TODO は
置きません。

| 層 | 何が書いてあるか | 入口 |
|---|---|---|
| 00-requests | 要求（何が欲しいか）・受け入れ基準・用語・決定台帳 | [docs/00-requests/request.md](docs/00-requests/request.md) |
| 01-requirements | 要件（観測できるふるまい）・ユースケース・システム要件 | [docs/01-requirements/functional.md](docs/01-requirements/functional.md) |
| 02-design | 全体設計・モジュール分割・契約・開発環境・ログ戦略 | [docs/02-design/architecture.md](docs/02-design/architecture.md) |
| 03-impl | 現在の実装の鏡（コードから導出）。機能間連携・契約・テスト | [docs/03-impl/index.md](docs/03-impl/index.md) |

- 体系そのものの説明は [docs/README.md](docs/README.md)、運用規範は
  [CLAUDE.md](CLAUDE.md) が正です。
- 受け入れ基準（利用者視点の合格条件）は
  [docs/00-requests/acceptances.md](docs/00-requests/acceptances.md) にあります。

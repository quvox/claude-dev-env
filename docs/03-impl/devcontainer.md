---
id: devcontainer
layer: impl
title: devcontainer 実装説明書
version: 1.0.0
updated: 2026-07-18
verified:
  at: 2026-07-18
  version: 1.0.0
  against:
    - doc: docs/02-design/system.md
      version: 1.0
summary: >
  Claude コンテナイメージ定義。Dockerfile.claude（orch-builder→base→vnc の多段ビルド）と
  Dockerfile.docker-proxy（Go 多段）、.devcontainer/tmux.conf を持ち、他モジュールの資産を
  イメージへ同梱する。自動テストはなくビルド実機確認で検証する。
keywords: [Dockerfile, マルチステージ, Ubuntu24.04, VNC, noVNC, Chrome, pyenv, fnm, docker-proxy, 同梱]
depends_on: []
source:
  - docs/02-design/system.md
---

# 実装説明書:devcontainer

## 概要

Claude Code を動かすランタイム一式を再現可能にビルドするイメージ定義モジュール（上流:
[全体設計](../02-design/system.md) の `devcontainer` 行、要件 core/1・11・9）。中核は
`.devcontainer/Dockerfile.claude` で、Go オーケストレーターをビルドする `orch-builder`、開発
環境本体の `base`（イメージ `claude-dev-claude`）、GUI/日本語入力を足す `vnc`（イメージ
`claude-dev-claude-vnc`、`FROM base`）の 3 ステージから成る。VNC あり/なしで `base` レイヤーを
共有し、追加分のディスクだけ増やす。加えて `.devcontainer/Dockerfile.docker-proxy`（Go 静的
ビルド + alpine、共有 `docker-proxy` イメージ）と、イメージに焼き込む `.devcontainer/tmux.conf`
を持つ。**このモジュールは他モジュールの成果物（entrypoint・firewall・hooks・container-tools・
portsync・vm-mode・orchestrator の各スクリプト/バイナリ）をイメージへ COPY で同梱する集約点**で
あり、各資産の中身は各モジュールの 03-impl が正本（同梱の宛先は本書「同梱資産」節が正本）。

## ファイル構成

| パス | 役割 |
|---|---|
| .devcontainer/Dockerfile.claude | `orch-builder`→`base`→`vnc` の多段ビルド。開発環境本体と GUI |
| .devcontainer/Dockerfile.docker-proxy | Go 多段（`golang:1.24-alpine`→`alpine:3.21`）。docker-proxy イメージ |
| .devcontainer/tmux.conf | `/etc/tmux.conf` へ焼き込む最小 tmux 設定 |

ビルド入力として参照するリポジトリ直下の `.zshrc`（→ `~/.zshrc.default`）と、`scripts/`・
`orchestrator/` 配下の成果物を COPY する（詳細は「同梱資産」）。

## モジュール別実装詳細

### Dockerfile.claude — ステージ `orch-builder`(orchestrator ビルド)

- **責務:** AI オーケストレーターの Go バイナリを専用ステージで生成（設計: orchestrator 同梱）。
- **処理の要点:**
  - `FROM golang:1.24-alpine`。`orchestrator/go.mod`・`go.sum`・`vendor/`・`*.go` を COPY し、
    `CGO_ENABLED=0 go build -ldflags="-s -w" -mod=vendor -o /claude-orchestrator .`。
  - 依存（bubbletea/lipgloss 等 TUI ライブラリ）は **vendoring** で取り込み、ビルド時ネットワーク
    非依存・再現性を確保する。実ロジックは orchestrator の 03-impl が正本。

### Dockerfile.claude — ステージ `base`(イメージ `claude-dev-claude`)

- **責務:** 言語処理系・CLI・FW ツール・（ヘッドレス）ブラウザを備えた非 GUI 開発環境（core/1・9）。
- **ビルド引数/環境:**
  - `ARG USERNAME=devuser` / `USER_UID=1500` / `USER_GID=1500`（CLI・makefile がホスト値で上書き）。
  - `ARG IMAGE_VERSION=local`。`LABEL io.github.quvox.claude-dev.version` と OCI 標準
    `org.opencontainers.image.version` の両方に同値を設定。専用キーを併設するのは、ubuntu ベースが
    標準キーに `24.04` を入れており衝突するため。CI は `YYYYMMDDHHmm` を渡し、`claude-dev start`
    がこのラベルでバージョン表示する。`vnc` は `FROM base` で継承。
  - `ENV USER_HOME=/home/${USERNAME}`、`CONTAINER_USER=${USERNAME}`（entrypoint が参照）。
- **処理の要点（ビルド順）:**
  1. **システムパッケージ（apt）:** iptables/ipset/dnsutils（FW）、zsh/tmux/vim、git/git-lfs/
     git-secrets/openssh-client、curl/wget/jq/ca-certificates、iproute2/net-tools/iputils-ping、
     make/gcc/g++/pkg-config、sudo/procps、Python3 一式、**pyenv でソースビルドするための依存**
     （libssl-dev, zlib1g-dev, libbz2-dev, libreadline-dev, libsqlite3-dev, libncursesw5-dev,
     tk-dev, libxml2-dev, libxmlsec1-dev, libffi-dev, liblzma-dev。実行時の追加バージョンビルド用に
     残す）、bubblewrap/socat、Playwright Chromium 実行に要る共有ライブラリ・フォント群、
     scrot/ffmpeg/x11-apps、**KVM/QEMU + VM モード用**（qemu-system-x86, qemu-utils, ovmf,
     cpu-checker, bridge-utils, virtiofsd, cloud-image-utils）、unzip/zip/xz-utils/gnupg/locales/
     rsync。続けて Docker 公式 APT で `docker-ce-cli`・`docker-compose-plugin`、GitHub 公式 APT
     （keyring を `/etc/apt/keyrings/`、`arch=$(dpkg --print-architecture)` で amd64/arm64 両対応）で
     **`gh`（GitHub CLI）** を導入。
  2. **ロケール/TZ:** `en_US.UTF-8`、`Asia/Tokyo`。
  3. **非 root ユーザー作成:** `USER_GID`/`USER_UID` が既存と競合すれば当該を 9999 へ退避してから
     `groupadd`/`useradd`（shell zsh）。`NOPASSWD` sudoers 付与、`~/.command_history` 作成。
  4. **言語ランタイム（ユーザー権限）:** fnm を `~/.local/share/fnm` に固定インストールし Node.js
     24/22（既定 24）、Go（`ARG GO_VERSION=1.26.1` を `linux-$(dpkg --print-architecture)` で
     `/usr/local` 展開）、Rust（rustup minimal stable）、**pyenv**（`~/.pyenv` に git clone、
     `ARG PYTHON_VERSION=3.13` の最新パッチを `pyenv latest -k` で解決してソースビルドし
     `pyenv global`。シム高速化の C 拡張はベストエフォート）、pnpm（corepack）。Playwright で
     Chromium を `--with-deps` 導入（24.04 は chromium が snap 専用のため。arm64 でも導入でき、
     arm64 の GUI ブラウザにも流用）。AWS CLI v2（`uname -m`）、Terraform（index から最新解決、
     `dpkg --print-architecture`）、Google Cloud CLI（**アーキ写像: aarch64/arm64→`arm`**、
     gcloud/gsutil/bq を `/usr/local/bin` に symlink）。
  5. **Claude Code CLI:** `curl https://claude.ai/install.sh | bash` を `WORKDIR /tmp` で実行
     （FS 全体スキャン回避）。`ARG CLAUDE_CACHE_BUST` で以降のレイヤーキャッシュを無効化可能。
  6. **コンテナ設定（root）:** Playwright Chromium のラッパー `/usr/local/bin/chromium-browser`
     （`--no-sandbox --headless` 等付与）を生成し `chromium`/`chrome` へ symlink、`CHROME_PATH`/
     `PLAYWRIGHT_*`/`PUPPETEER_*` を `/etc/zsh/zshrc`・`/etc/bash.bashrc` へ追記（ヘッドレステスト用）。
     同 rc に PATH・fnm 初期化・**pyenv 初期化**（`PYENV_ROOT`・PATH・`pyenv init -`）を追記。`.zshrc`
     を `~/.zshrc.default`、`tmux.conf` を `/etc/tmux.conf` へ COPY。各モジュールの資産を COPY
     （「同梱資産」）。`WORKDIR /workspace`、`ENV SHELL=/bin/zsh`、
     `ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]`。
- **実装上の判断:** システム rc とユーザー `.zshrc.default` の両方に pyenv 初期化を置くが、
  `.zshrc.default` 側は二重初期化ガード（`$PYENV_ROOT/shims` が PATH 済みならスキップ）を持つ。

### Dockerfile.claude — ステージ `vnc`(イメージ `claude-dev-claude-vnc`, `FROM base`)

- **責務:** GUI ブラウザ確認と日本語入力（core/11）。base に GUI 層のみ追加。
- **処理の要点:**
  - `ja_JP.UTF-8` ロケール追加。TigerVNC(standalone-server) + python3-websockify + openbox、
    端末/X ユーティリティ（lxterminal, xterm, xclip, x11-xserver-utils, xdotool）、**IBus+Mozc**
    一式（ibus, ibus-mozc, ibus-gtk[3/4], mozc-utils-gui, dbus-x11, im-config）、dconf/dbus 系、
    Chrome 追加依存（libxss1, libatspi2.0-0）、追加フォント（fonts-noto-cjk-extra 等）を apt 導入。
  - **GUI ブラウザ（`dpkg --print-architecture` 分岐）:** amd64 は Google Chrome 安定版を APT 公式
    から導入。arm64 は Linux 版が無く導入せず、base の Playwright Chromium を流用。両者を吸収する
    **共通ランチャー `/usr/local/bin/claude-dev-chrome`**（chrome があればそれ、無ければ Chromium を
    `exec`）を生成。entrypoint/openbox は常にこのランチャーを叩きアーキを意識しない。
  - **noVNC v1.6.0** を `/usr/share/novnc` に展開し `index.html → vnc.html` を symlink。GTK IM
    キャッシュ更新、D-Bus machine-id 生成、`im-config -n ibus`。
  - **IME トグル `/usr/local/bin/toggle-ime`**（mozc-jp ↔ xkb:us::eng を `ibus engine` で切替。
    `DBUS_SESSION_BUS_ADDRESS` を ibus/openbox プロセスの `/proc/<pid>/environ` から復元）。
  - **openbox 設定**（`~/.config/openbox/menu.xml`: Chrome/Terminal/IME 切替/IBus Setup、`rc.xml`:
    `W-space`/`C-backslash`/`F3` で toggle-ime、右クリックでメニュー）。
  - **computer-use MCP `rmcp-xdotool`**: `cargo install rmcp-xdotool` でビルドし `/usr/local/bin`
    へ配置（入力専用、画面取得は scrot 併用）。**ビルド失敗は非致命的**（`|| echo WARN`）で、その
    場合 entrypoint は MCP 登録をスキップ。
  - VNC 系 `ENV`（`DISPLAY=:99`, `GTK_IM_MODULE=ibus`, `QT_IM_MODULE=ibus`, `XMODIFIERS`,
    `IBUS_ENABLE_SYNC_MODE=1`, `CLAUDE_DEV_VNC=1`）、`EXPOSE 6080`、同一 ENTRYPOINT。
- **実装上の判断:** `chrome-devtools-mcp` はイメージに含めず、実行時 `npx` 取得（entrypoint が設定）。

### Dockerfile.claude — 同梱資産(他モジュールの成果物を COPY)

`base` ステージ末尾で、各モジュールが所有するスクリプト/バイナリ/テンプレートをイメージへ焼き込む。
中身の正本は各モジュールの 03-impl。宛先は下表が正本。

| COPY 元 | 宛先 | 所有モジュール |
|---|---|---|
| `.zshrc` | `~/.zshrc.default` | devcontainer（entrypoint が初回 config-shared へ複製） |
| `.devcontainer/tmux.conf` | `/etc/tmux.conf` | devcontainer |
| `scripts/init-firewall-claude.sh` | `/usr/local/bin/init-firewall.sh` | firewall |
| `scripts/entrypoint-claude.sh` | `/usr/local/bin/entrypoint.sh` | entrypoint |
| `scripts/save_prompt.sh` | `/usr/local/bin/save_prompt.sh` | hooks |
| `scripts/sendslackmsg.sh` | `/usr/local/bin/sendslackmsg.sh` | hooks |
| `scripts/wait-limit-reset.sh` | `/usr/local/bin/wait-limit-reset.sh` | container-tools |
| `scripts/vm-up.sh` / `scripts/vm` / `scripts/vm-portsync.sh` / `scripts/vm-healthd.sh` | `/usr/local/bin/`（同名） | vm-mode |
| `scripts/dood-portsync.sh` | `/usr/local/bin/dood-portsync.sh` | portsync |
| `scripts/VM_DEV.md.tmpl` | `/usr/local/share/claude-dev/VM_DEV.md.tmpl` | vm-mode |
| `--from=orch-builder /claude-orchestrator` | `/usr/local/bin/claude-orchestrator` | orchestrator |
| `orchestrator/instructions/` | `/usr/local/share/claude-orchestrator/` | orchestrator |

`/usr/local/bin` 配下のスクリプトとバイナリには `chmod +x` を付与。container-tools の
`scripts/tmux.conf` は**焼き込まず**、実行時に `~/.tmux.conf` へマウントするため本イメージには含めない
（同梱するのは本モジュールの `.devcontainer/tmux.conf` = `/etc/tmux.conf` のみ）。

### Dockerfile.docker-proxy(イメージ `claude-dev-docker-proxy`)

- **責務:** Docker API 検査プロキシの実行イメージ（core/7）。全 Claude コンテナで共有。
- **処理の要点:** ビルダ `golang:1.24-alpine` で `docker-proxy/`（`go.mod` を COPY→`go mod download`
  →`*.go`）を `CGO_ENABLED=0 go build -ldflags="-s -w" -o /docker-proxy` し静的バイナリ生成。
  ランタイムは `alpine:3.21` + `ca-certificates` にバイナリを配置。`ARG IMAGE_VERSION` と同 LABEL
  2 種、`EXPOSE 2375`、`ENTRYPOINT ["/usr/local/bin/docker-proxy"]`。検査ロジックは docker-proxy の
  03-impl が正本。

### .devcontainer/tmux.conf(→ /etc/tmux.conf)

- イメージ焼き込みの最小設定。`set -g escape-time 10`（カーソルキー初回押下の取りこぼし回避）と
  `set -g mouse on` のみ。実開発セッションでは container-tools の `~/.tmux.conf` が優先される。

## データアクセス

該当なし（DB/永続ストアを持たない。生成物は Docker イメージ）。

## API実装詳細

該当なし（本モジュールに外部公開 I/F はない。ビルド後イメージが提供する `EXPOSE 6080`/`2375` は
それぞれ noVNC・docker-proxy の実行時ポートで、実装は entrypoint / docker-proxy が担う）。

## 設定・環境変数

ビルド引数（`docker build --build-arg` で上書き）と、イメージに焼き込む主な実行時環境変数。

| 名前 | 用途 | デフォルト | 必須 |
|---|---|---|---|
| USERNAME | コンテナ内ユーザー名 | devuser | 任意 |
| USER_UID / USER_GID | ホスト UID/GID 追従 | 1500 / 1500 | 任意 |
| IMAGE_VERSION | イメージバージョンラベル | local | 任意（CI は日時） |
| GO_VERSION | Go 展開版 | 1.26.1 | 任意 |
| PYTHON_VERSION | pyenv 既定 CPython 系 | 3.13 | 任意 |
| CLAUDE_CACHE_BUST | Claude CLI 以降のキャッシュ無効化 | none | 任意 |
| LANG / LC_ALL / TZ | ロケール・時刻 | en_US.UTF-8 / Asia/Tokyo | 焼込 |
| SHELL / CONTAINER_USER / USER_HOME | 既定シェル・entrypoint 参照 | /bin/zsh 他 | 焼込 |
| DISPLAY 他 VNC 系（vnc のみ） | GTK/QT IM・sync・VNC 印 | :99 / ibus 等 / CLAUDE_DEV_VNC=1 | 焼込 |

## エラーハンドリング実装

| 異常系 | 実装箇所 | 実際の振る舞い | 対応する要件 |
|---|---|---|---|
| UID/GID がイメージ既存と競合 | base 非 root ユーザー作成 | 既存グループ/ユーザーを 9999 へ退避してから作成 | core/2 |
| arm64 で Google Chrome 非提供 | vnc GUI ブラウザ分岐 | Chrome 導入をスキップし Playwright Chromium を流用（`claude-dev-chrome` で吸収） | core/11 |
| gcloud 配布名のアーキ不一致 | base gcloud 導入 | aarch64/arm64 を `arm` へ写像（写像しないと 404） | core/9 |
| rmcp-xdotool ビルド失敗 | vnc computer-use MCP | `|| echo WARN` で非致命化。バイナリ不在時 entrypoint が MCP 登録をスキップ | core/11 |

## テスト

本モジュールはシェル/Dockerfile 構成物であり、**自動テストは持たない**（02 テスト戦略: シェル系は
実機確認）。検証はイメージのビルド成功と起動時の実機確認で行う。

| テスト(ファイル::ケース名) | レベル | 検証内容 | 対応する受け入れ基準/契約 |
|---|---|---|---|
| （自動テストなし＝実機確認） | 単体 | `make build` 系で base/vnc/docker-proxy が amd64/arm64 でビルド成功 | core/9 ビルド |
| （実機確認 E2E-1 の一部） | 結合 | 起動後にランタイム（node/python/go/rust/gh/docker）と VNC/日本語入力が機能 | core/1,11 |

実行方法: リポジトリの `make`（tech steering のビルドコマンド）でイメージをビルドし、
`claude-dev start`（VNC あり/`--no-vnc`）で起動して確認する。E2E は E2E-1（03-impl/e2e.md）が担う。

## 既知の制限・技術的負債

- Chromium/Chrome・AWS/Terraform/gcloud・Claude CLI 等を外部 URL から取得するため、ビルドは
  ネットワーク接続とアップストリーム可用性に依存する（orchestrator は vendoring で例外）。
- `rmcp-xdotool` はソースビルドで、失敗すると computer-use MCP が使えない（意図的に非致命化）。
- Terraform は index から常に最新を解決するため、ビルド時期によって版が変わる（固定していない）。

## 運用メモ

- `claude-dev start` はイメージの `io.github.quvox.claude-dev.version` ラベルでバージョン表示する。
  ローカルビルドは `local`、CI/GHCR 配布は `YYYYMMDDHHmm`。
- 同梱スクリプト（entrypoint/firewall/hooks/portsync/vm-mode/container-tools）や orchestrator を
  変更した場合、反映にはイメージ再ビルドが必要（COPY 焼き込みのため）。
- base/vnc はレイヤー共有。vnc 更新時も base 差分のみ再ビルドされる。

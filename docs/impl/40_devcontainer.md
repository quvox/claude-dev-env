---
summary: Dockerfile.claude（orch-builder/base/vnc ステージ。orchestrator バイナリと instructions を base へ同梱）・Dockerfile.docker-proxy・tmux.conf・.zshrc のビルド仕様を記述する。
keywords: [ Dockerfile, Docker, VNC, マルチステージ, Go, orchestrator, ビルド ]
---

# 実装仕様: .devcontainer/ Docker イメージ定義

> **この文書の役割**: コンテナイメージのビルド仕様を記述する。`.devcontainer/Dockerfile.claude`（開発環境 base + GUI vnc の 2 ステージ）、`.devcontainer/Dockerfile.docker-proxy`（Go プロキシ）、ビルド入力となる `.devcontainer/tmux.conf` とルートの `.zshrc` を対象とする。

## 要件（なぜ必要か）

Claude Code を安全・快適に動かすためのランタイム一式（言語処理系・CLI・ファイアウォール・任意で GUI/日本語入力）を、ホストのカレントユーザーと同じ UID/GID で再現可能にビルドする必要がある。VNC あり/なしでベースレイヤーを共有し、ディスク効率を保つ。

## カバーするコード

```
.devcontainer/
├── Dockerfile.claude          orch-builder（Go）→ base → vnc のマルチステージ
├── Dockerfile.docker-proxy    Go ビルド + alpine ランタイム
└── tmux.conf                  /etc/tmux.conf に焼き込む最小設定
.zshrc                         ~/.zshrc.default に焼き込む既定シェル設定（ビルド入力）
```

---

## Dockerfile.claude

### ビルド引数 / 環境
- `ARG USERNAME=devuser` / `USER_UID=1500` / `USER_GID=1500`（CLI・Makefile がホスト値で上書き）。
- `ENV USER_HOME=/home/${USERNAME}`、`CONTAINER_USER=${USERNAME}`（entrypoint が参照）。

### ステージ `orch-builder`（`FROM golang:1.24-alpine`、`base` の前）
AI オーケストレーターの Go バイナリをビルドする専用ステージ。`orchestrator/`（`go.mod` + `*.go`）を `CGO_ENABLED=0 go build -ldflags="-s -w" -o /claude-orchestrator` でビルドする。外部依存なし（stdlib のみ）のため `go.sum` は不要。docker-proxy と同方式のマルチステージ。詳細は [60_orchestrator.md](60_orchestrator.md) 参照。

### ステージ `base`（イメージ `claude-dev-claude`）
1. **システムパッケージ**（`apt-get`）: iptables/ipset/dnsutils（FW）、zsh/tmux/vim、git 一式/openssh-client、curl/wget/jq/ca-certificates、ネットワーク系、make/gcc/g++、sudo/procps、Python3 一式、**pyenv で CPython をソースビルドするための依存**（`libssl-dev`/`zlib1g-dev`/`libbz2-dev`/`libreadline-dev`/`libsqlite3-dev`/`libncursesw5-dev`/`tk-dev`/`libxml2-dev`/`libxmlsec1-dev`/`libffi-dev`/`liblzma-dev`。実行時の追加バージョンビルドにも要るので残す）、bubblewrap/socat、Chromium/Playwright 実行に必要な共有ライブラリ・フォント群、scrot/ffmpeg/x11-apps、KVM/QEMU（qemu-system-x86, qemu-utils, ovmf, cpu-checker, bridge-utils）、unzip/zip/xz/gnupg/locales/rsync。続けて Docker 公式 APT リポジトリを追加し `docker-ce-cli` と `docker-compose-plugin` を導入。**VM モード（実装済み・要イメージ再ビルド反映。正本 [80_vm-mode.md](80_vm-mode.md)）**では、これに加えて `virtiofsd`・`cloud-image-utils` を apt 追加し、`scripts/vm-up.sh`・`scripts/vm`・`scripts/vm-portsync.sh`・`scripts/vm-healthd.sh`（`/usr/local/bin`、実行権付与）・`scripts/VM_DEV.md.tmpl`（`/usr/local/share/claude-dev/`）を COPY する（`qemu-system-x86`/`qemu-utils`/`ovmf` は既存）。あわせて DooD モードのポート転送 `scripts/dood-portsync.sh` を `/usr/local/bin` へ COPY・実行権付与する（`socat` は既存。正本 [30_scripts.md](30_scripts.md)）。
2. **ロケール/TZ**: `en_US.UTF-8`、`Asia/Tokyo`。
3. **非 root ユーザー作成**: `USER_GID`/`USER_UID` が既存と競合する場合は 9999 へ退避してから `groupadd`/`useradd`（シェル zsh）。`NOPASSWD` sudoers を付与し、`~/.command_history` を作成。
4. **言語ランタイム（ユーザー権限）**: fnm（`~/.local/share/fnm` に固定インストール）で Node.js 24/22（既定 24）、Go（`GO_VERSION` を `/usr/local` へ展開）、Rust（rustup minimal）、**pyenv（`~/.pyenv` に git clone。ARG `PYTHON_VERSION`（既定 `3.13`）の最新パッチを `pyenv latest -k` で解決してソースビルドし `pyenv global` に設定＝インストール直後から `python`/`pyenv` が使える。シム高速化の C 拡張はベストエフォートでビルド）**、pnpm（corepack）。Playwright 経由で Chromium を `--with-deps` 導入（Ubuntu 24.04 は chromium パッケージが snap 専用のため。この Chromium は arm64 でも導入でき、**arm64 の VNC GUI ブラウザとしても使う**→ ステージ `vnc`）。AWS CLI v2（配布名が `uname -m`=`aarch64`/`x86_64` をそのまま採るため arm64 でも成立）、Terraform（最新版を index から解決、`dpkg --print-architecture` でアーキ選択）、Google Cloud CLI（gcloud/gsutil/bq を `/usr/local/bin` に symlink）。**gcloud のアーキ写像**: 配布名は arm64 が `arm`（`x86_64` はそのまま）のため、`$(uname -m)` が `aarch64`/`arm64` のとき `arm` へ写像してから URL を組む（写像しないと arm64 で 404。amd64 は不変）。Go は `linux-$(dpkg --print-architecture)`、Docker CLI リポジトリは `arch=$(dpkg --print-architecture)` で arm64 も成立。
5. **Claude Code CLI**: 公式ネイティブインストーラー（`curl https://claude.ai/install.sh | bash`）を `WORKDIR /tmp` で実行。
6. **コンテナ設定（root）**:
   - Playwright Chromium のラッパー `/usr/local/bin/chromium-browser`（`--no-sandbox --headless` 等を付与）を生成し `chromium`/`chrome` の symlink を張り、`CHROME_PATH`/`PLAYWRIGHT_*`/`PUPPETEER_*` を `/etc/zsh/zshrc`・`/etc/bash.bashrc` に追記（ヘッドレステスト用）。
   - PATH と fnm 初期化、および **pyenv 初期化**（`PYENV_ROOT=$HOME/.pyenv`・`$PYENV_ROOT/bin` を PATH に追加・`eval "$(pyenv init - <shell>)"`）をシステム rc（`/etc/zsh/zshrc`, `/etc/bash.bashrc`）へ追記。
   - `.zshrc` を `~/.zshrc.default` として COPY。
   - `.devcontainer/tmux.conf` を `/etc/tmux.conf` へ COPY。
   - `scripts/` の 4 スクリプトを `/usr/local/bin/`（`init-firewall.sh`, `entrypoint.sh`, `save_prompt.sh`, `sendslackmsg.sh`）へ COPY し実行権限付与。
   - `orch-builder` から `COPY --from=orch-builder /claude-orchestrator /usr/local/bin/claude-orchestrator`、instruction テンプレートを `COPY orchestrator/instructions/ /usr/local/share/claude-orchestrator/`。バイナリに実行権限付与（[60_orchestrator.md](60_orchestrator.md)）。
   - `WORKDIR /workspace`、`SHELL=/bin/zsh`、`ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]`。

### ステージ `vnc`（イメージ `claude-dev-claude-vnc`、`FROM base`）
- `ja_JP.UTF-8` ロケール追加。
- GUI/入力パッケージ: tigervnc-standalone-server, python3-websockify, openbox、端末/X ユーティリティ（lxterminal, xterm, xclip, xdotool 等）、IBus + Mozc 一式、dbus 系、ブラウザ追加依存、追加フォント。
- **GUI ブラウザ（アーキ別、`dpkg --print-architecture` で分岐）**:
  - **amd64**: Google Chrome 安定版を APT 公式リポジトリから導入（従来どおり）。
  - **arm64**: Google Chrome は Linux arm64 版が無いため導入せず、base の Playwright Chromium を GUI ブラウザに使う。
  - **共通ランチャー `/usr/local/bin/claude-dev-chrome`** を生成する。`google-chrome-stable` があればそれを、無ければ Playwright Chromium（`ms-playwright` 配下の `chrome`）を `exec` する薄いラッパー。entrypoint の VNC 起動・openbox メニューは常にこのランチャーを叩き、アーキを意識しない（正本 [31_entrypoint.md](31_entrypoint.md)）。
- **noVNC v1.6.0** を `/usr/share/novnc` に展開（`index.html → vnc.html`）。
- GTK IM モジュールキャッシュ更新、D-Bus machine-id 生成、`im-config -n ibus`。
- IME トグルスクリプト `/usr/local/bin/toggle-ime`（IBus エンジンを mozc-jp ↔ xkb:us::eng で切替。D-Bus アドレスを ibus/openbox プロセスの environ から復元）。
- openbox 設定（`menu.xml`: ブラウザ（`claude-dev-chrome`）/Terminal/IME 切替/IBus Setup、`rc.xml`: キーバインド `W-space`/`C-backslash`/`F3` で toggle-ime、右クリックでメニュー）。
- **computer-use MCP（`rmcp-xdotool`）**: デスクトップ（X `:99`）をマウス/キーボードで操作する MCP サーバーを `cargo install rmcp-xdotool` でビルドし `/usr/local/bin/rmcp-xdotool` に配置（入力専用。画面取得は `scrot` 併用）。ビルド失敗は非致命的（`|| echo WARN`）とし、その場合 entrypoint は登録をスキップする。
- VNC 系 `ENV`（`DISPLAY=:99`, `GTK_IM_MODULE=ibus` 等）と `CLAUDE_DEV_VNC=1`、`EXPOSE 6080`、同一 ENTRYPOINT。

### 不変条件
- 2 ステージで base レイヤーを共有し、VNC 追加分のみディスク増。
- `chrome-devtools-mcp` はイメージに含めず、実行時に `npx` で取得する（entrypoint が MCP 設定を書く）。

---

## Dockerfile.docker-proxy

- ビルダ: `golang:1.24-alpine` で `docker-proxy/` を `CGO_ENABLED=0 go build -ldflags="-s -w"` し静的バイナリ生成。
- ランタイム: `alpine:3.21` + `ca-certificates` にバイナリを配置。`EXPOSE 2375`、`ENTRYPOINT ["/usr/local/bin/docker-proxy"]`。
- 実装ロジックは [50_docker-proxy.md](50_docker-proxy.md)。

---

## .devcontainer/tmux.conf（→ /etc/tmux.conf）

イメージに焼き込む最小設定。`escape-time 10`（カーソルキー初回押下の取りこぼし回避）と `mouse on` のみ。実際の開発セッションは `scripts/tmux.conf`（`~/.tmux.conf`、[30_scripts.md](30_scripts.md)）が `claude-dev start` のマウントで優先される。

---

## .zshrc（→ ~/.zshrc.default）

イメージに COPY される既定ユーザー設定。entrypoint が初回に `~/.config-shared/.zshrc` へコピーし、以後コンテナ間共有される（[31_entrypoint.md](31_entrypoint.md)）。内容: 一般的なエイリアス（ls/ll, venv 補助等）、`PATH` への `~/.local/bin` 追加、**pyenv 初期化（`PYENV_ROOT=$HOME/.pyenv`。`$PYENV_ROOT/shims` が既に PATH にある＝システム rc が初期化済みの場合は二重初期化を避けるガード付きで `pyenv init - zsh` を eval）**、`SSH_AUTH_SOCK` のエクスポート、色・補完・emacs キーバインド、ヒストリー設定（重複無視・インクリメンタル検索）、`vcs_info` による git ブランチ表示プロンプト。

> pyenv の初期化はシステム rc（`/etc/zsh/zshrc`）にも入っており、そちらが常に適用されるため既存の `~/.zshrc`（ボリューム共有）を使う既存コンテナでも pyenv は有効。`.zshrc.default` 側はガードで二重初期化を防ぐ。

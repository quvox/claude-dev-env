---
summary: ホスト側の claude-dev シェルスクリプトの実装仕様。ヘルパー関数・サブコマンド・コンテナ起動引数などの成果物仕様を記述する。
keywords: [ CLI, claude-dev, bash, ヘルパー関数, コンテナ起動, ポートフォワード, orchestrate ]
---

# 実装仕様: claude-dev CLI

> **この文書の役割**: ホスト側で日常操作を担う `claude-dev` シェルスクリプトの実装仕様。利用者向けのコマンド使用法は `docs/04_cli-reference.md` を参照し、本書は内部のヘルパー関数・分岐・コンテナ起動引数などの**成果物仕様**を記述する。

## 要件（なぜ必要か）

利用者が任意のプロジェクトディレクトリで単一コマンドを実行するだけで、コンテナ隔離された Claude Code 環境を起動・再接続・停止できる必要がある。加えて、認証情報の安全な受け渡し、SSH agent 転送、Docker API のプロキシ経由化、ポートフォワード、VNC ポート割り当てを、ホスト側で一元的に制御する。

## カバーするコード

```
claude-dev      （単一の bash スクリプト）
```

## 全体構造

スクリプトは `set -e` で動作し、次の順で構成される。

1. パス解決と `.env` 読み込み
2. 定数定義
3. ヘルパー関数群
4. `case "${1:-help}"` によるサブコマンドディスパッチ

### 初期化

- `SCRIPT_PATH`: `readlink -f`/`realpath` で自身の実体パスを解決（シンボリックリンク経由実行に対応）。`BASE_DIR` はその親ディレクトリ。
- `CONFIG_FILE="${BASE_DIR}/.env"` が存在すれば `set -a; source; set +a` で環境変数としてエクスポート。
- `DOCKER_CLI_HINTS` を既定 `false` で export（利用者設定は尊重）。`docker run`/`exec` 後（tmux から抜けた時など）に出る Docker CLI の「What's next:」ヒント表示を抑制する。
- `CUSER` / `CHOME="/home/${CUSER}"`: コンテナ内ユーザー名。**実行するイメージ（`IMG_CLAUDE`）に焼き込まれた `CONTAINER_USER` env を優先**して解決し（`docker image inspect ... | sed -n 's/^CONTAINER_USER=//p'`）、取得できなければ `whoami` にフォールバックする。ローカルビルドのイメージは `CONTAINER_USER=<whoami>` のため従来と同一（後方互換）。GHCR の generic user イメージ（`CONTAINER_USER=dev`）を `pull` した場合は `CUSER=dev` となり、マウント先 `/home/dev`・`docker exec -u dev` が自動追従する（設計 [../10_ghcr-images.md](../10_ghcr-images.md)）。UID/GID は entrypoint が `/workspace` 所有者へ実行時に追従させる。

### 定数

| 名前 | 値 | 用途 |
|------|----|------|
| `NETWORK` | `claude-dev-net` | Docker ネットワーク |
| `NOVNC_BASE_PORT` | `6080` | noVNC ポート探索の開始番号 |
| `FWD_PORT_BASE` | `8100` | ポートフォワード用ホストポート開始番号 |
| `VOL_AUTH` / `VOL_HISTORY` / `VOL_CONFIG` / `VOL_CHROME` | `claude-dev-auth` / `-history` / `-config` / `-chrome-data` | ボリューム名 |
| `IMG_CLAUDE` / `IMG_CLAUDE_VNC` / `IMG_DOCKER_PROXY` | `claude-dev-claude` / `-vnc` / `-docker-proxy` | イメージ名 |
| `DOCKER_PROXY_CONTAINER` | `claude-dev-docker-proxy` | プロキシコンテナ名 |
| `DEV_DIR` / `DEV_AGENT_DIR` | `${HOME}/.claude-dev` / `${HOME}/.claude-dev/agents` | プロジェクト専用 ssh-agent の作業ディレクトリとソケット/PID 置き場（`<name>.sock` / `<name>.pid`、`<name>` = `container_name`） |
| `PROJECT_CONFIG_NAME` | `.claude-dev.yaml` | **このプロジェクトで使う SSH 鍵**を定義する、プロジェクト直下（`<PROJECT_DIR>/.claude-dev.yaml`）の設定ファイル名。SSH 鍵は**このファイルの `ssh_keys:` のみ**を見る（グローバル設定へのフォールバックはしない）。**ファイルが無い初回 `start` では `ensure_project_config` が作成する**（TTY は鍵選択を促し、非 TTY は空 `ssh_keys:`）。鍵の推測・グローバルからの流用はしない |

## ヘルパー関数

| 関数 | 責務 |
|------|------|
| `load_ssh_keys_from_config <project_dir>` | 使う鍵リストを **`<project_dir>/.claude-dev.yaml` の `ssh_keys:` からのみ**読み込み `SSH_KEY_LIST` 配列へ格納する。グローバル設定（`~/.config/claude-dev.yaml`）へのフォールバックや雛形自動生成は**行わない**（ローカル設定だけを見る）。採用元（＝そのプロジェクトの `.claude-dev.yaml` パス）は `SSH_CONFIG_SOURCE` に記録。YAML は簡易パース（`ssh_keys:` 開始 → リストアイテム `- path` を読み、`~` を `$HOME` 展開、コメント除去）。 |
| `discover_ssh_keys` | `~/.ssh/id_*`（`.pub` 除く）を `DISCOVERED_KEYS` に列挙（`ssh-keys` の対話選択で使う）。 |
| `write_project_ssh_keys <file> <keys...>` | 選択鍵をプロジェクト直下の `.claude-dev.yaml`（`<file>`）に書き出す（claude-dev 所有ファイルとして再生成）。 |
| `select_ssh_keys_interactive` | `discover_ssh_keys` を番号付きで提示し、カンマ/空白区切り番号 / `a`=全部 / `n`(または空)=なし で選択→`write_project_ssh_keys "$(pwd)/.claude-dev.yaml"` で**カレントプロジェクトの `.claude-dev.yaml`** に保存し `SSH_KEY_LIST` に反映。 |
| `ensure_ssh_agent <project_dir> <name>` | `load_ssh_keys_from_config` で鍵を解決し、**プロジェクト専用 ssh-agent**（`${DEV_AGENT_DIR}/<name>.sock`）を起動/再利用して**解決した鍵だけ**を登録する。ホストの環境 agent（`$SSH_AUTH_SOCK`）は使わない（ディレクトリごとに見える鍵を隔離するため）。登録前に `ssh-add -l` の指紋と各鍵の指紋（`ssh-keygen -lf`、パスフレーズ不要）を突き合わせ、**既に登録済みの鍵はスキップ**（パスフレーズ再入力回避）。未登録分はまずパスフレーズなし（`SSH_ASKPASS=/bin/false SSH_ASKPASS_REQUIRE=force`）で一括 `ssh-add`、失敗分のみ対話追加。存在しない鍵は警告してスキップ。最後に転送用の `SSH_AUTH_SOCK` を専用ソケットへ固定する。鍵が 0 件（`.claude-dev.yaml` が無い/`ssh_keys:` が空）なら `SSH_AUTH_SOCK` を空にして SSH 転送せず、`.claude-dev.yaml` に `ssh_keys:` を記述するよう案内する。 |
| `project_name` | カレントディレクトリ名を小文字化し `[^a-z0-9._-]` を `-` へ置換した文字列を返す。 |
| `container_name` | `project_name` と同値（コンテナ名 = ディレクトリ名）。 |
| `image_exists <image>` | `docker image inspect` の成否。 |
| `is_running <name>` | `docker ps -q -f name=^<name>$` が非空か。 |
| `container_exists <name>` | 停止中含め存在するか（`docker ps -aq`）。 |
| `find_available_novnc_port` | `NOVNC_BASE_PORT` から +100 の範囲で、既存コンテナが公開していない空きポートを返す（見つからなければ基準値）。 |
| `find_available_host_port` | `FWD_PORT_BASE` から +900 の範囲で空きホストポートを返す。 |
| `require_setup` | `IMG_CLAUDE` / `IMG_CLAUDE_VNC` が無ければ `docker build`（`--target base` / `--target vnc`、`USERNAME`/`USER_UID`/`USER_GID` を build-arg で渡す）で自動ビルド。 |
| `check_host_deps` | **起動に必要なホストコマンドを確認**し、無ければ導入方法を案内して `exit 1`。Linux 版の必須は `docker`・`jq`（`docker` は PREPARATION.md を、その他は `sudo apt-get install -y <cmd>` を案内）。`start` の冒頭（`require_setup` の前）で呼ぶ。macOS 版は加えて `socat`（SSH ブリッジ必須）を要求し `brew install` を案内（11_cli-mac.md）。 |
| `ensure_project_config <project_dir>` | **`<project_dir>/.claude-dev.yaml` が無いときだけ**、TTY なら `select_ssh_keys_interactive` で SSH 鍵選択を促し、非 TTY なら `write_project_ssh_keys`（引数なし）で `ssh_keys:` 空配列のファイルを作る。**既存ファイルは尊重して何もしない**（起動のたびに聞かない）。`start` で `PROJECT_DIR` 確定後・鍵解決前に呼ぶ。 |
| `ensure_infrastructure` | ネットワークと 4 ボリュームを冪等に作成。 |
| `get_novnc_url <name>` | `docker port <name> 6080` のホストポートから `http://localhost:<port>/vnc.html?autoconnect=true` を組み立てて返す（VNC なしなら空）。 |
| `image_version <image\|id>` | イメージのバージョン表記を返す。`io.github.quvox.claude-dev.version` ラベル（CI=`YYYYMMDDHHmm` / ローカルビルド=`local`）を優先し、無ければ `unknown`。あわせて短縮イメージ ID と作成日時（`Created`）を付す（例 `202607042010 (id abc123…, built 2026-07-04 08:20)`）。専用ラベルキーを使うのは OCI 標準 `org.opencontainers.image.version` が ubuntu ベースで `24.04` に衝突するため（Dockerfile は両キーへ焼く）。 |
| `stop_proxy_if_idle` | 稼働中の Claude コンテナ数が 0 なら `DOCKER_PROXY_CONTAINER` を `rm -f`。 |
| `ensure_docker_proxy_container` | ホストに `/var/run/docker.sock` がある場合のみ動作。イメージ未ビルドならビルドし、未起動ならプロキシコンテナを `claude-dev-net` 上に `--restart unless-stopped`・ソケットを RO マウント・`-e CLAUDE_DEV_ALLOW_WORKSPACE_BINDS=${CLAUDE_DEV_ALLOW_WORKSPACE_BINDS:-1}`（`/workspace` 配下 bind 許可。既定有効。正本 [50_docker-proxy.md](50_docker-proxy.md) / [../03_security.md](../03_security.md)）付きで起動。無効化や設定変更は proxy を作り直す必要がある（共有・常駐のため）。 |

## サブコマンド仕様

ディスパッチは `case "${1:-help}"`（引数なしは `help`）。

### `setup`
`.env` を生成（無ければ `.env.example` から）、ネットワーク・4 ボリュームを作成、`IMG_CLAUDE`（base）・`IMG_CLAUDE_VNC`（vnc）・`IMG_DOCKER_PROXY` を順にビルド。最後に次手順を案内し、PATH 未登録なら symlink 作成コマンドを表示。

### `login`
`require_setup` → `ensure_infrastructure` 後、一時コンテナ（`--rm -it`、`VOL_AUTH` を `~/.claude-shared` にマウント、`--entrypoint bash`）を起動。コンテナ内で:
- `settings.json` が無ければ root（`su` 前）が `{"permissions":{"defaultMode":"bypassPermissions"},"model":"sonnet"}` を生成して `chown`（共有しない）
- `su` でユーザーに切り替え、共有ボリュームの認証ファイル（`.credentials.json`, `.claude.json`）を `~/.claude/` にコピー
- `~/.claude.json` → `~/.claude/.claude.json` リンク
- `claude` を対話起動（ブラウザ認証）
- 終了後、認証ファイルを `~/.claude-shared/` に書き戻す

**クォート制約**: `docker run ... -c '...'` のコンテナ内スクリプトはホスト側でシングルクォートに括られているため、スクリプト内でシングルクォートを使ってはならない（外側の引用が閉じ、ホストシェルのブレース展開・エスケープ消費で引数が壊れる）。`settings.json` の JSON リテラルはこの制約から `su -c "..."` の内側ではなく root 部で `\"` エスケープの二重引用符により生成する。

### `logout`
全 Claude コンテナとプロキシコンテナを停止し、`VOL_AUTH` の中身を空にする（一時コンテナで `rm -rf /auth/* /auth/.*`）。

### `pull [TAG]`
GHCR のビルド済みイメージを取得してローカルビルドを省く。`.env` の `CLAUDE_DEV_REGISTRY`（既定 `ghcr.io/quvox`）と `CLAUDE_DEV_IMAGE_TAG`（既定 `latest`。引数 `TAG` で上書き）から、`${REG}/claude-dev-claude`・`-claude-vnc`・`-docker-proxy` の各 `:TAG` を `docker pull` し、**ローカル名（`claude-dev-claude` 等）へ `docker tag` で retag** する。以降 `start`/`require_setup` は retag 済みイメージを使い自動ビルドしない。少なくとも 1 つ成功すれば完了メッセージ、全失敗なら private 用の `docker login ghcr.io` を案内して `exit 1`。Docker が対象アーキの manifest を自動選択する（Apple Silicon=arm64 / Linux=amd64）。GHCR への push は GitHub Actions が担う（[90_ghcr-workflow.md](90_ghcr-workflow.md)、設計 [../10_ghcr-images.md](../10_ghcr-images.md)）。

### `start [--no-vnc] [--kvm] [--vm] [--vm-fresh]`
本 CLI の中核。**冒頭で `check_host_deps`**（必要ホストコマンドの確認。無ければ導入案内して `exit 1`）→ `require_setup`。`NAME=container_name`、`PROJECT_DIR=$(pwd)`。`PROJECT_DIR` 確定後・鍵解決前に **`ensure_project_config "$PROJECT_DIR"`**（`.claude-dev.yaml` 不在なら SSH 鍵選択を促す／非 TTY は空 `ssh_keys:` で作成。既存は尊重）。`--no-vnc` で `USE_VNC=0`、`--kvm` で `USE_KVM=1`（既定 `0`）。

> **`--vm`（VM モード。実装済み・要イメージ再ビルド反映。正本: [80_vm-mode.md](80_vm-mode.md) / [docs/08_vm-mode.md](../08_vm-mode.md)）**: `--kvm` を含意し、`CLAUDE_DEV_VM=1` とゲスト qcow2 キャッシュ用ボリューム・アプリポート（`VM_PORTS`）をコンテナへ渡す。コンテナ内でゲスト VM（QEMU+virtiofs）を起動し、その中のネイティブ Docker を `DOCKER_HOST` 経由で使う。`/dev/kvm` がホストに無ければ警告して中止。VM 制御用の `vm` ヘルパー（`status`〔health 表示含む〕/`shell`/`restart`/`down`/`rebuild`/`portsync`/`logs`）はコンテナ内コマンドとして提供する。**`--vm-fresh`**（`--vm` 含意）はコンテナ作成前にゲスト用ボリューム `claude-dev-vm-<name>` を破棄して再 provision する（稼働中コンテナには効かず、`stop` 後に実行するか稼働中は `vm rebuild` を使う）。

1. 既に稼働中なら attach: **使用中イメージのバージョン**（`image_version` にコンテナの `.Image` を渡す）と noVNC URL を表示し、`tmux has-session -t main` が無ければ作成してから `tmux attach`。
2. 停止中コンテナがあれば削除。`ensure_infrastructure`。
3. イメージ選択（VNC: `IMG_CLAUDE_VNC` / それ以外: `IMG_CLAUDE`）。
4. **認証コピー**: 一時コンテナで `VOL_AUTH`（RO）から `${PROJECT_DIR}/.claude/` へ認証ファイルをコピーし、ホスト UID/GID に chown。
5. **ホスト設定の抽出**: `~/.claude/settings.json` から `jq` で `{hooks, env}`（null 除外）を抽出し `${PROJECT_DIR}/.claude/host-hooks.json` へ書き出す（entrypoint がマージ。ファイル名は歴史的経緯で `host-hooks.json` だが env も含む）。
6. **ユーザー hook スクリプト**: ホストの `~/.local/bin/` が非空なら `${PROJECT_DIR}/.claude/host-local-bin/` へコピー（組み込み hook はイメージに焼き込み済みのため対象外）。
7. **.gitignore 追記**: プロジェクトの `.gitignore` に `.claude` が無ければ追記（無く `.git` がある場合は新規作成）。
8. **マウント/オプション組み立て**:
   - `GITCONFIG_OPT`: `~/.gitconfig` があれば RO マウント
   - `GH_CONFIG_OPT`: `~/.config/gh` ディレクトリがあれば `${CHOME}/.config/gh` へ RO マウント（GitHub CLI `gh` の認証＝`hosts.yml` の oauth トークンと設定を共有し、コンテナ内でも `gh` が認証済みで使える。RO なのでホストの認証は書き換わらない）
   - `DOCKER_OPTS`: ソケットがあれば `ensure_docker_proxy_container` 後 `DOCKER_HOST=tcp://<proxy>:2375`
   - `SSH_OPTS`: `ensure_ssh_agent`（引数 `PROJECT_DIR` / `NAME`）が用意した**プロジェクト専用 agent** のソケットを `/tmp/ssh-agent.sock`（RO）転送 + `SSH_AUTH_SOCK` 設定（鍵 0 件で `SSH_AUTH_SOCK` が空なら転送しない）。`known_hosts` を RO マウント。`~/.ssh/config` は `IdentityFile`/`IdentitiesOnly`/`IdentityAgent` 行を `sed` で除去した一時ファイルを RO マウント（`IdentityAgent` はホスト固有 agent パスがコンテナ内で `SSH_AUTH_SOCK` を上書きするのを防ぐため。ホストの config 実体は不変）
   - `NOVNC_PORT_OPT`（VNC 時のみ）: 空き noVNC ポートを `find_available_novnc_port` で確保し `-p <port>:6080` + `VOL_CHROME` を `~/.chrome-profile` にマウント
   - `KVM_OPTS`: **`--kvm` 指定時のみ**、ホストに存在する `/dev/kvm` `/dev/vhost-net` `/dev/net/tun` を `--device` で渡す（既定では渡さない。通常は Chrome 操作のみで十分なため、KVM/QEMU が必要なときだけ明示的に有効化する）。デバイス受け渡しはコンテナ作成時にのみ行われるため、稼働中コンテナへ後付けはできず、`stop` → `start --kvm` で再作成する
9. **コンテナ起動**: 起動直前に **使用イメージ名とバージョン**（`image_version "$RUN_IMAGE"`）を表示する。VM モード（`USE_VM=1`）のときは `docker run` の前に「VM モードで起動する／通常より時間がかかる（初回は cloud image 取得＋provision で数分）」旨を表示する。`docker run -d` で `--cap-add NET_ADMIN`・`NET_RAW`（FW 用）、`--restart unless-stopped`、`/workspace` マウント、各ボリューム、`tmux.conf`/`CLAUDE.md` を RO マウント、上記オプション群、`NODE_OPTIONS=--max-old-space-size=4096`、`-t` を付与。
10. tmux 起動を待つ。待ち時間の上限は通常 30 秒、**VM モードは 420 秒**（ゲスト VM の provision/ブート中は entrypoint が tmux 起動前でブロックするため）。VM モードでは 15 秒ごとに「…VM 起動待ち (Ns / 最大 Ms)」を表示する。準備できたら noVNC URL を表示して `tmux attach -t main`（**`CLAUDE_DEV_NO_ATTACH=1` のときは attach せず戻る**＝`orchestrate` がコンテナだけ起こして orch セッションへ attach するための入口。start 内の「既に稼働中」early-attach 経路と最終 attach の両方がこのフラグを尊重する）。上限を超えても tmux が未起動の場合は**無言で attach 失敗して終了せず**、VM モードなら「provision 継続中。コンテナは起動したまま。再実行 or `vm logs`/`vm status` で確認、準備完了後に再接続される」旨を、通常時は「タイムアウトしたので再実行を」旨を案内して `exit 0` する（コンテナは `docker run -d`＋`--restart unless-stopped` で稼働継続するため、次回 `start` の稼働中 attach 経路で接続できる）。

### `code`
稼働中コンテナで `tmux new-window -t main "claude"` を実行し attach。未起動ならエラー。

### `orchestrate [<ゴール>] [--fresh]`
コンテナに対し AI オーケストレーターを起動／再接続する（**tmux 常駐方式**。60_orchestrator.md「独立ウィンドウ方式」）。引数を走査し、`--fresh` をフラグとして除いた残りの最初の位置引数を `<ゴール>`（任意）として扱う。

**コンテナ未起動なら自動起動する**：`is_running` が偽なら、`CLAUDE_DEV_NO_ATTACH=1 "$SCRIPT_PATH" start` で `start` の全ロジック（認証コピー/マウント/VNC/VM/tmux 起動待ち）を再利用してコンテナを起こす（`start` 側は `CLAUDE_DEV_NO_ATTACH=1` のとき最後の `main` への `tmux attach` をスキップする）。起動後もまだ `is_running` が偽なら（VM モードの provision 途中など）案内して終了。起動できたら下記手順へ進む。※以前の「未起動ならエラー」は廃止。

手順（単一コマンド復旧＝06 §5.9）：
1. コントローラが常駐すべきメインセッション名を得る：`docker exec -u <user> <name> claude-orchestrator --print-main-session`（＝`orch-<CNAME>-main`。`<CNAME>` は正規化コンテナ名）。
2. **コントローラプロセスの生存**を判定する（`has-session` ではない。worker/brainstorming 窓が `remain-on-exit on` でコントローラ死後も空き殻セッションが残り、`has-session` では誤検出するため）：`docker exec -u <user> <name> sh -c 'for p in $(pgrep -f "claude-orchestrator --workspace"); do case "$(tr "\0" " " </proc/$p/cmdline)" in claude-orchestrator*|/*/claude-orchestrator*) exit 0;; esac; done; exit 1'`（cmdline が `claude-orchestrator` で始まるプロセスのみ＝`tmux new-session` 起動ラッパを除外）。**真（常駐中）** → `docker exec -it -u <user> <name> tmux attach -t <main>` するだけ。
3. **不在**（未起動／`[q]` 中断／クラッシュ／tmux サーバ死）→ 延命した空き殻セッションを掃除してから新しい `<main>` セッションでコントローラを起こす：`docker exec -u <user> <name> tmux kill-session -t <main> 2>/dev/null || true` → `docker exec -u <user> <name> tmux new-session -d -s <main> -n dashboard -c /workspace "[ -f /etc/claude-dev/vm.env ] && . /etc/claude-dev/vm.env; claude-orchestrator --workspace /workspace [--fresh] [\"<ゴール>\"]"` → `tmux set-option -t <main> mouse off` → `docker exec -it -u <user> <name> tmux attach -t <main>`。コントローラは状態ストアから resume（Phase=executing なら実行継続）し、起動後に不足ウィンドウ（実行中 worker／ブレインストーミング中なら brainstorming）を再構築する。

ゴールを省略するとブレインストーミング（検討）から開始する。`--fresh` は前回の実行状態を破棄してブレインストーミングから新規開始するフラグで、そのままバイナリへ受け渡す（再開/新規の判定は `claude-orchestrator` 側、[60_orchestrator.md](60_orchestrator.md) 参照）。worker のライブ出力は各 worker ウィンドウ（`orch-<CNAME>-main:w-<taskID>`）で直接確認する（ダッシュボードでカーソル（↑↓/jk）選択＋Enter で当該ウィンドウへ移動（`select-window`）。`prefix+w` でも一覧・選択可。`[d]` は dashboard 内のログ tail トグルとして存置。廃止は `--workers-window`／Config B）。メインセッションの `dashboard` ウィンドウは `remain-on-exit off`（worker/brainstorming ウィンドウは `remain-on-exit on`）。正常完了時は全窓が閉じてセッションが自然消滅するが、中断/クラッシュ時は `remain-on-exit on` 窓が空き殻セッションを残すため、生存判定は `has-session` ではなく上記の**コントローラプロセス生存**で行う（06 §5.9）。**VM モード対応**: コントローラ起動コマンド前に `[ -f /etc/claude-dev/vm.env ] && . /etc/claude-dev/vm.env` を挟み、VM モード時はゲストの `DOCKER_HOST` を orchestrator（および worker）へ引き継ぐ（非対話起動は rc を読まないため。詳細 [80_vm-mode.md](80_vm-mode.md)）。

> オーケストレーター本体（`claude-orchestrator`）はこの CLI が渡す `--workspace`/`--fresh` に加え、自己検証用に `--instructions`（instruction テンプレート上書き）と `--start-executing`（ready な seed plan があればブレインストーミングを飛ばす検証専用 affordance）をバイナリ直叩きで受け付ける。詳細は [60_orchestrator.md](60_orchestrator.md) / [70_sample-project.md](70_sample-project.md)。`claude-dev orchestrate` 自体はこれらを公開しない（検証は本体バイナリを直接起動する）。

### `attach [NAME]`
NAME（省略時カレント）が稼働中なら `tmux attach -t main`。

### `stop [NAME]`
対象コンテナと関連フォワードコンテナ（`fwd-<name>-*`）を `rm -f`。その後 `stop_proxy_if_idle`。

### `forward <container-port> [NAME]`
稼働確認後、`fwd-<name>-<port>` が既存なら現ホストポートを表示。空きホストポートを確保し、`socat` を `--entrypoint` にした使い捨てコンテナ（`-d --rm`、`IMG_CLAUDE`）で `TCP-LISTEN:<cport>,fork,reuseaddr` → `TCP:<name>:<cport>` を中継。SSH トンネルコマンド例を表示。

### `unforward <container-port> [NAME]`
`fwd-<name>-<port>` を `rm -f`。

### `ports [NAME]`
`fwd-<name>-*` コンテナを列挙し `host:<hport> → <name>:<cport>` を表示。noVNC URL も表示。

### `list`
全 Claude コンテナ（`ancestor` フィルタ）を列挙し NAME / STATUS / WORKSPACE / noVNC URL / 各フォワードを表示。最後にプロキシコンテナの稼働状態を表示。

### `ssh-keys [reset]`
対象は**カレントプロジェクト**（`NAME=container_name`、設定は `$(pwd)/.claude-dev.yaml`）。
- 引数なし / `select`: `select_ssh_keys_interactive` を実行し、`~/.ssh/id_*` を対話選択して**カレントの `.claude-dev.yaml`** に保存（手書きでも同形式で可）。
- `reset`: カレントの `.claude-dev.yaml` から `ssh_keys` セクションを除去（`grep -vE` で `ssh_keys:` 行・リスト項目・管理用コメントを削除。`ssh_keys` だけのファイルは残らず削除、他の記述があれば残す）し、**このプロジェクト（`<NAME>`）の専用 agent** を停止・削除（`${DEV_AGENT_DIR}/<NAME>.pid` を kill し `.sock`/`.pid` を削除＝登録済み鍵をクリア）。再設定は `ssh-keys` で選択するか `.claude-dev.yaml` を作成する（`start` 自体は対話選択しない）。
- その他の引数: 使い方を表示して `exit 1`。

macOS 版（[11_cli-mac.md](11_cli-mac.md) D1）も同名・同挙動。差分は reset がブリッジ socat も停止する点のみ（Linux にブリッジは無い）。

### `upgrade`
`IMG_CLAUDE`（base）・`IMG_CLAUDE_VNC`（vnc）・`IMG_DOCKER_PROXY` を `--no-cache` で再ビルド。反映は `stop`→`start`。

### `firewall`
稼働中コンテナで `iptables -L OUTPUT -n --line-numbers` を表示。

### `reset`
確認プロンプト後、全 Claude コンテナ・全 `fwd-*`・プロキシコンテナを削除、4 ボリューム・ネットワーク・3 イメージを削除。

### `help` / その他
ヒアドキュメントで全コマンドの使用法を表示。

## 不変条件・注意点

- コンテナ名 = プロジェクトディレクトリ名のため、同名ディレクトリは同一セッションとして扱われる。
- 認証ファイルは「コピー方式」で受け渡し、symlink は使わない（Claude Code のアトミック書き込みで symlink が壊れるため。書き戻しは entrypoint のバックグラウンド同期が担当）。
- Docker ソケットも SSH 鍵ファイルもコンテナへ直接渡さない（[00_overview.md](00_overview.md) の不変条件と一致）。

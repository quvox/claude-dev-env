---
id: cli
layer: impl
title: cli 実装説明書
version: 1.3.0
updated: 2026-07-19
verified:
  at: 2026-07-19
  version: 1.3.0
  against:
    - doc: docs/02-design/system.md
      version: 1.2
summary: >
  ホスト Linux 用 `claude-dev`（単一 bash スクリプト）の実装。case ディスパッチで
  start/stop/list/attach/forward/orchestrate/login 等のサブコマンドを提供し、Docker
  コンテナのライフサイクル・認証コピー・SSH 専用 agent・ポート転送・docker-proxy 連携を担う。
keywords: [cli, claude-dev, bash, container, ssh-agent, port-forward, orchestrate, docker-proxy]
depends_on: [container-tools, hooks, portsync, devcontainer]
source:
  - docs/02-design/system.md
---

# 実装説明書:cli（ホスト CLI）

## 概要

ホスト Linux で日常操作を担う単一 bash スクリプト `claude-dev` の実装。任意のプロジェクト
ディレクトリで `claude-dev start` するだけで、隔離 Docker コンテナ上の Claude Code 環境を
起動・再接続・停止できる。`set -e` で動作し、先頭で `.env` 読込・定数定義・ヘルパー関数群を
用意し、末尾の `case "${1:-help}"` でサブコマンドへディスパッチする。責務は、コンテナ
ライフサイクル、認証ファイルのコピー受け渡し、プロジェクト単位 SSH 鍵の限定転送、動的ポート
フォワード、docker-proxy 経由の Docker アクセス、VM モード連携、AI オーケストレーターの
起動/再接続。OS 依存はこの CLI に閉じる（macOS 差分は cli-mac、上流: [全体設計](../02-design/system.md)）。

## ファイル構成

| パス | 役割 |
|---|---|
| `claude-dev` | 本モジュールの実体（単一 bash スクリプト、全ロジックを内包） |
| `.env` / `.env.example` | `BASE_DIR/.env`。`setup` が example から生成し、起動時に `set -a; source` で環境変数化 |
| `.claude-dev.yaml`（各プロジェクト直下） | そのプロジェクトで転送する SSH 鍵（`ssh_keys:`）。`cli` が所有・生成 |
| `~/.claude-dev/agents/<name>.{sock,pid}` | プロジェクト専用 ssh-agent のソケット/PID 置き場 |
| `.devcontainer/Dockerfile.claude` 他 | `require_setup`/`setup`/`upgrade` がビルドする（実体は devcontainer モジュール） |
| `scripts/tmux.conf` / `CLAUDE.md` | `start` が RO マウントする資産（container-tools / プロジェクト） |

## モジュール別実装詳細

### 初期化・定数（claude-dev L1〜48）

- `SCRIPT_PATH` を `readlink -f`／`realpath` で解決（symlink 経由起動に対応）、`BASE_DIR` はその親。
- `BASE_DIR/.env` があれば `set -a; source; set +a` でエクスポート。
- `DOCKER_CLI_HINTS` を既定 `false` で export（docker の「What's next:」抑制、利用者設定は尊重）。
- `CUSER`/`CHOME`: **イメージ `IMG_CLAUDE` に焼かれた `CONTAINER_USER` env を優先**して解決
  （`docker image inspect ... | sed -n 's/^CONTAINER_USER=//p'`）、無ければ `whoami`。GHCR の
  generic user イメージ（`CONTAINER_USER=dev`）を pull すると `CUSER=dev`・`/home/dev` が自動追従。
  この初期値は**新規コンテナ作成（create パス）用**（＝これから作るコンテナのユーザー）。
- `resolve_container_user <container>`: **起動中のコンテナへ exec する際のユーザー解決**。イメージの
  タグではなく **そのコンテナ自身の `CONTAINER_USER` env**（`docker inspect <container> ...`）から解決し、
  無ければ `CUSER` にフォールバック。`start`（再接続パス）/`code`/`orchestrate`/`attach` の各分岐で
  `is_running` 確認後に `CUSER="$(resolve_container_user "$NAME")"` と上書きしてから `docker exec -u` する。
  **狙い**: `make build` 等でローカルイメージのユーザーが変わっても（例: GHCR=`dev` とローカルビルド=
  `whoami` の混在）、別イメージ由来で稼働中のコンテナへ正しい `-u` で attach できる（イメージ由来の
  `CUSER` を使うと `unable to find user ...: no matching entries in passwd file` になる回帰を防ぐ）。
  create パス・firewall（`-u` 無し）は本上書きの対象外。
- 主要定数: `NETWORK=claude-dev-net`、`NOVNC_BASE_PORT=6080`、`FWD_PORT_BASE=8100`、共有ボリューム
  `VOL_AUTH/VOL_HISTORY/VOL_CONFIG`、コンテナ別 Chrome ボリューム接頭辞 `VOL_CHROME_PREFIX=claude-dev-chrome`、
  イメージ名 `IMG_CLAUDE`/`IMG_CLAUDE_VNC`/`IMG_DOCKER_PROXY`、`DOCKER_PROXY_CONTAINER`、
  `DEV_DIR=~/.claude-dev`・`DEV_AGENT_DIR`、`PROJECT_CONFIG_NAME=.claude-dev.yaml`。

### ヘルパー関数群（L54〜406）

- **SSH 鍵解決**: `_parse_ssh_keys_yaml`（`ssh_keys:` セクションの `- path` を簡易パース、`~`→`$HOME`
  展開・コメント除去）／`load_ssh_keys_from_config`（`<project_dir>/.claude-dev.yaml` の `ssh_keys:`
  **のみ**を読み `SSH_KEY_LIST` に格納。グローバルへのフォールバックや自動生成はしない。採用元を
  `SSH_CONFIG_SOURCE` に記録）／`discover_ssh_keys`（`~/.ssh/id_*`、`.pub` 除く）／
  `write_project_ssh_keys`（選択鍵を `.claude-dev.yaml` に書き出す）／`select_ssh_keys_interactive`
  （番号付き提示→カンマ/空白区切り番号・`a`=全部・`n`/空=なし で選択し保存）。
- **`ensure_ssh_agent <project_dir> <name>`**: 鍵を解決し、**プロジェクト専用 ssh-agent**
  （`${DEV_AGENT_DIR}/<name>.sock`）を起動/再利用して解決鍵だけ登録。ホストの `$SSH_AUTH_SOCK` は
  使わない（見える鍵をディレクトリごとに隔離）。`ssh-add -l` の指紋と `ssh-keygen -lf` を突き合わせ
  既登録はスキップ→未登録はまずパスフレーズなし（`SSH_ASKPASS=/bin/false SSH_ASKPASS_REQUIRE=force`）で
  一括 `ssh-add`→失敗分のみ対話追加。鍵 0 件なら `SSH_AUTH_SOCK=""`（転送しない）。最後に
  `SSH_AUTH_SOCK` を専用ソケットに固定。
- **命名/存在判定**: `project_name`/`container_name`（cwd 名を小文字化し `[^a-z0-9._-]`→`-`。両者同値）、
  `image_exists`、`is_running`（`docker ps -q -f name=^<n>$`）、`container_exists`（停止含む）。
- **ポート探索**: `find_available_novnc_port`（6080〜+100 で `docker ps` の公開ポートに無い空きを返す。
  選定〜`docker run` が非アトミックなため競合し得るが `start` のリトライで吸収）、
  `find_available_host_port`（8100〜+900）。
- **セットアップ/前提**: `require_setup`（`IMG_CLAUDE`/`IMG_CLAUDE_VNC` 未存在なら `--target base/vnc`・
  `USERNAME/USER_UID/USER_GID` build-arg で自動ビルド）、`check_host_deps`（`docker`・`jq` を確認、
  無ければ導入案内して `exit 1`）、`ensure_project_config`（`.claude-dev.yaml` 不在時のみ TTY は鍵選択、
  非 TTY は空 `ssh_keys:` で作成。既存は尊重）、`ensure_infrastructure`（ネットワーク＋共有 3 ボリュームを
  冪等作成。Chrome ボリュームは `docker run` 任せ）。
- **表示/プロキシ**: `get_novnc_url`（`docker port <n> 6080` から `http://localhost:<port>/vnc.html?autoconnect=true`）、
  `image_version`（`io.github.quvox.claude-dev.version` ラベル＝CI は `YYYYMMDDHHmm`／ローカルは `local`、
  無ければ `unknown`。短縮 ID・`Created` を付す）、`stop_proxy_if_idle`（Claude コンテナ 0 なら proxy を
  `rm -f`）、`ensure_docker_proxy_container`（`/var/run/docker.sock` がある場合のみ。未ビルドならビルド、
  未起動なら `claude-dev-net` 上に `--restart unless-stopped`・ソケット RO マウント・
  `-e CLAUDE_DEV_ALLOW_WORKSPACE_BINDS=${...:-1}` 付きで起動）。

### サブコマンド（case ディスパッチ、L411〜1354）

- **`setup`**: `.env` 生成（example から）、ネットワーク・共有 3 ボリューム作成、`IMG_CLAUDE`(base)・
  `IMG_CLAUDE_VNC`(vnc)・`IMG_DOCKER_PROXY` を順にビルド、次手順と PATH 用 symlink コマンドを案内。
- **`login`**: `require_setup`→`ensure_infrastructure` 後、一時コンテナ（`--rm -it`、`--entrypoint bash`、
  `VOL_AUTH` を `~/.claude-shared` へ）を起動。root が `settings.json` 未存在時に
  `{"permissions":{"defaultMode":"bypassPermissions"},"model":"sonnet"}` を生成し `chown`（共有しない）→
  `su` でユーザーに切替→共有ボリュームの認証（`.credentials.json`/`.claude.json`）を `~/.claude/` にコピー→
  `~/.claude.json` リンク→`claude` 対話起動→終了後 `~/.claude-shared/` へ書き戻す。**クォート制約**:
  `-c '...'` はホスト側でシングルクォートに括られるため内部でシングルクォートを使えず、JSON は root 部で
  `\"` エスケープの二重引用符で生成する。
- **`logout`**: 全 Claude コンテナ＋proxy を `rm -f` し、`VOL_AUTH` の中身を空にする（`rm -rf /auth/* /auth/.*`）。
- **`pull [TAG]`**: `.env` の `CLAUDE_DEV_REGISTRY`（既定 `ghcr.io/quvox`）と `CLAUDE_DEV_IMAGE_TAG`
  （既定 `latest`、引数 `TAG` で上書き）から 3 イメージを `docker pull` し、**`${name}:latest` へ retag**。
  以降 `start`/`require_setup` は retag 済みを使いビルドしない。1 つでも成功で完了、全失敗なら
  `docker login ghcr.io` を案内し `exit 1`。manifest はアーキで自動選択。
- **`start [--no-vnc] [--kvm] [--vm] [--vm-fresh]`**: 中核。`check_host_deps`→`require_setup`→`NAME`/
  `PROJECT_DIR` 確定→`ensure_project_config`→フラグ解析（`--vm`/`--vm-fresh` は `--kvm` 含意。`--vm` は
  `/dev/kvm` 必須で無ければ `exit 1`）。処理:
  1. 稼働中なら attach（使用中イメージバージョンと noVNC URL 表示、`tmux has-session -t main` 無ければ作成、
     `CLAUDE_DEV_NO_ATTACH!=1` のとき `tmux attach`）。`--vm-fresh` は稼働中無効の警告。
  2. 停止中コンテナ削除→`ensure_infrastructure`→イメージ選択（VNC 有無）。
  3. **認証コピー**: 一時コンテナで `VOL_AUTH`(RO) から `${PROJECT_DIR}/.claude/` へコピーしホスト UID/GID に chown。
  4. **ホスト設定抽出**: `~/.claude/settings.json` から `jq` で `{hooks, env}`（null 除外）を
     `host-hooks.json` へ（entrypoint がマージ。名は歴史的経緯で hooks だが env も含む）。
  5. **ユーザー hook**: `~/.local/bin/` が非空なら `.claude/host-local-bin/` へコピー（組込み hook は
     イメージ焼込み済みで対象外）。
  6. **.gitignore 追記**: `.claude` 未記載なら追記（`.git` あり `.gitignore` 無しは新規作成）。
  7. **マウント/オプション組立**: `GITCONFIG_OPT`（`~/.gitconfig` RO）、`GH_CONFIG_OPT`（`~/.config/gh` RO=
     `gh` 認証共有）、`DOCKER_OPTS`（ソケットあれば `ensure_docker_proxy_container` 後
     `DOCKER_HOST=tcp://<proxy>:2375`）、`COMPOSE_OPTS`（`NAME` を compose 互換名〈小文字・
     `[a-z0-9_-]` のみ〉へ正規化した `COMPOSE_PROJECT_NAME` を `-e` で付与。全プロジェクトが
     `/workspace` にマウントされ compose 既定名が `workspace` に衝突するのを防ぐ。`-e` なので
     対話・非対話シェル〈`bash -c` 実行〉と `docker exec` の全てで有効）、`SSH_OPTS`（`ensure_ssh_agent` の専用 agent ソケットを
     `/tmp/ssh-agent.sock` RO 転送＋`SSH_AUTH_SOCK`、`known_hosts` RO、`~/.ssh/config` は
     `IdentityFile/IdentitiesOnly/IdentityAgent` 行を `sed` 除去した一時コピーを RO）、`NOVNC_PORT_OPT`
     （VNC 時のみ空きポート `-p <port>:6080`＋コンテナ別 Chrome ボリューム）、`KVM_OPTS`（`--kvm` 時のみ
     `/dev/kvm`・`/dev/vhost-net`・`/dev/net/tun` を存在すれば `--device`）、`VM_OPTS`（`--vm` 時
     `CLAUDE_DEV_VM=1`＋`claude-dev-vm-<name>` ボリューム＋`VM_PORTS/VM_MEM/VM_SMP/VM_DISK/VM_SWAP` を
     設定時のみ渡す。`--vm-fresh` は先に該当ボリューム破棄）。
  8. **起動**: 使用イメージ名・バージョン表示（VM 時は所要時間注意も）→`docker run -d --cap-add NET_ADMIN,NET_RAW
     --restart unless-stopped`、`/workspace`・各ボリューム・`tmux.conf`/`CLAUDE.md` RO マウント、上記
     オプション、`NODE_OPTIONS=--max-old-space-size=4096`、`-t`。**ポート競合リトライ**: 失敗時は作成途中を
     `docker rm -f` し、エラーがポート競合かつ VNC 有効なら別ポートを取り直して最大 20 回再試行。他失敗/上限は
     stderr 表示し `exit 1`。
  9. tmux 起動待ち（通常 30 秒／VM 420 秒、VM は 15 秒ごと進捗表示）→noVNC URL 表示→
     `CLAUDE_DEV_NO_ATTACH!=1` なら `tmux attach -t main`。上限超過でも終了せず状況案内して `exit 0`
     （コンテナは `--restart unless-stopped` で稼働継続、次回 start の attach 経路で接続可能）。
- **`code`**: 稼働確認後 `tmux new-window -t main "<claude cmd>"` して attach。**VM モード時**
  （`CLAUDE_DEV_VM=1`）は `claude --append-system-prompt "..."` で VM 導線（docker はゲスト daemon 指定・
  bind source は `/workspace` 配下のみ・`/workspace/VM_DEV.md` 参照）を注入。未起動はエラー。
- **`orchestrate [<ゴール>] [--fresh]`**: `require_setup` 後、**未起動なら
  `CLAUDE_DEV_NO_ATTACH=1 "$SCRIPT_PATH" start`** で start 全ロジックを再利用して起動（attach 抑止）。
  引数走査で `--fresh` を除いた残りを `<ゴール>` に。tmux 常駐方式。手順: (1) メインセッション名を
  `claude-orchestrator --print-main-session` から取得（fallback `orch-main`）、(2) **コントローラプロセス
  生存判定**（`has-session` ではなく `pgrep -f "claude-orchestrator --workspace"` の cmdline が
  `claude-orchestrator` で始まるものだけ＝空き殻セッション誤検出回避）、生存なら `tmux attach -t <sess>`、
  (3) 不在なら空き殻を `kill-session` 後、`tmux new-session -d -s <sess> -n dashboard -c /workspace "<cmd>"`
  で新規起動→`tmux set-option mouse on`→attach。`<cmd>` は
  `[ -f /etc/claude-dev/vm.env ] && . /etc/claude-dev/vm.env; claude-orchestrator --workspace /workspace [--fresh] [\"<goal>\"]`
  （VM モードでゲスト `DOCKER_HOST` を非対話起動へ引継ぐ）。
- **`attach [NAME]`**: 稼働中なら `tmux attach -t main`、未起動はエラー。
- **`stop [NAME]`**: `fwd-<name>-*` とコンテナを `rm -f`→当該コンテナ内から起動された compose コンテナ群（ラベル `com.docker.compose.project=<正規化NAME>` で特定）を `rm -f` し、当該プロジェクトの compose デフォルトネットワーク（`<正規化NAME>_default`）が残れば `docker network rm`（`docker compose down` 相当。名前付きボリューム・共有 `claude-dev-net`・docker-proxy は残す）→`stop_proxy_if_idle`。正規化 NAME は start と同じく `NAME` を compose 互換名へ変換した値。VM モードは compose がゲスト内 Docker で完結するため対象外。
- **`forward <cport> [NAME]`**: 稼働確認→`fwd-<name>-<cport>` 既存なら現ポート表示。空きホストポート確保→
  `socat` を `--entrypoint` にした使い捨てコンテナ（`-d --rm`、`IMG_CLAUDE`）で
  `TCP-LISTEN:<cport>,fork,reuseaddr`→`TCP:<name>:<cport>` を中継。SSH トンネル例を表示。
- **`unforward <cport> [NAME]`**: `fwd-<name>-<cport>` を `rm -f`。
- **`ports [NAME]`**: `fwd-<name>-*` を列挙し `host:<h>→<name>:<c>` と noVNC URL 表示。
- **`list`**: 全 Claude コンテナ（`ancestor` フィルタ）を NAME/STATUS/WORKSPACE/noVNC/各フォワードで列挙し、
  最後に proxy 稼働状態を表示。
- **`ssh-keys [reset|select]`**: 対象はカレントプロジェクト。引数なし/`select` は `select_ssh_keys_interactive`。
  `reset` は `.claude-dev.yaml` から `ssh_keys` 関連行を `grep -vE` 除去（他記述なしなら削除）し、専用 agent
  （`<NAME>.sock`/`.pid`）を kill・削除。その他は使い方表示し `exit 1`。
- **`upgrade`**: 3 イメージを `--no-cache` 再ビルド（反映は stop→start）。
- **`firewall`**: 稼働中コンテナで `iptables -L OUTPUT -n --line-numbers`。
- **`reset`**: 確認プロンプト後、全 Claude コンテナ・全 `fwd-*`・proxy を削除、共有 3 ボリューム・全
  `claude-dev-chrome-*`・ネットワーク・3 イメージを削除。
- **`help|*`**: ヒアドキュメントで全コマンド使用法を表示。

## 設定・環境変数

| 名前 | 用途 | デフォルト | 必須 |
|---|---|---|---|
| `CLAUDE_DEV_REGISTRY` | `pull` の取得元レジストリ | `ghcr.io/quvox` | 否 |
| `CLAUDE_DEV_IMAGE_TAG` | `pull` の取得タグ（引数 TAG が優先） | `latest` | 否 |
| `CLAUDE_DEV_ALLOW_WORKSPACE_BINDS` | proxy に渡す `/workspace` bind 許可（proxy 起動時に env として付与） | `1` | 否 |
| `CLAUDE_DEV_NO_ATTACH` | `start` の最終 attach を抑止（`orchestrate` が内部設定） | `0` | 否 |
| `CLAUDE_DEV_VM` | コンテナへ渡す VM モードフラグ（`--vm` 時 CLI が設定） | 未設定 | 否 |
| `VM_PORTS`/`VM_MEM`/`VM_SMP`/`VM_DISK`/`VM_SWAP` | VM モード時に設定されていればコンテナへ渡す | 未設定 | 否 |
| `DOCKER_CLI_HINTS` | docker のヒント表示抑制（export） | `false` | 否 |
| `NODE_OPTIONS` | コンテナへ `--max-old-space-size=4096` を設定 | （固定） | — |
| `TERM`/`LANG` | `login` の一時コンテナへ渡す | `xterm-256color`/`en_US.UTF-8` | 否 |

- コンテナへ渡す契約（環境変数・マウント）は system.md「cli → コンテナ/entrypoint」に一致。
  `DOCKER_HOST=tcp://claude-dev-docker-proxy:2375` は `DOCKER_OPTS` で付与。

## エラーハンドリング実装

| 異常系 | 実装箇所 | 実際の振る舞い | 対応する要件 |
|---|---|---|---|
| ホストコマンド不足（docker/jq） | `check_host_deps` | 不足を列挙し導入案内、`exit 1` | core/1 |
| イメージ未ビルド | `require_setup`/`ensure_docker_proxy_container` | 自動ビルド（build-arg 付き） | core/1,9 |
| `.claude-dev.yaml` 不在 | `ensure_project_config` | TTY は鍵選択、非 TTY は空作成。停止しない | core/4 |
| SSH 鍵 0 件/存在しない鍵 | `ensure_ssh_agent` | 転送なしで続行し `ssh_keys:` 記述を案内、欠落鍵は警告スキップ | core/4 |
| noVNC ポート競合 | `start` の `docker run` リトライ | 途中コンテナ掃除→別ポートで最大 20 回再試行 | core/1,6 |
| tmux 起動タイムアウト | `start` L864〜 | 終了せず状況案内し `exit 0`（コンテナは稼働継続） | core/1 |
| コンテナ未起動での操作 | `code`/`attach`/`forward`/`ports`/`firewall` | 日本語エラーで `exit 1` | core/1,6 |
| pull 全失敗 | `pull` | `docker login ghcr.io` 案内し `exit 1` | core/9 |
| VM モードで `/dev/kvm` 不在 | `start` L632 | `exit 1`（`--kvm` のみの場合は警告のみで続行） | core/8 |

- 前提不足は停止せず日本語で案内する方針（system.md エラーハンドリング方針「cli」）に一致。

## テスト

bash スクリプトのため**自動テストランナーは存在しない**（tech steering）。検証はすべて実機確認
（`claude-dev` 実操作）。system.md テスト戦略でも「シェル系は自動テストなし＝実機確認」とされ、E2E-1/E2E-2
は本 CLI を含むが対応表は `docs/03-impl/e2e.md` が持つ。結合テスト契約 `cli(orchestrate)→orchestrator` の
**担当モジュールは orchestrator**（本モジュールではない）。

| テスト | レベル | 検証内容 | 対応する受け入れ基準/契約 |
|---|---|---|---|
| （自動テストなし） | — | `start`→マウント/認証/再接続、`list`/`stop`（proxy 連動） | core/要件1-1〜6 未検証(自動テストなし) |
| （自動テストなし） | — | `login`→認証ボリューム保存、`logout`→削除 | core/要件3-1,2,5 未検証(自動テストなし) |
| （自動テストなし） | — | `ssh-keys` 対話選択→`.claude-dev.yaml` 生成、専用 agent 限定転送 | core/要件4-4 ほか 未検証(自動テストなし) |
| （自動テストなし） | — | `forward`/`unforward`/`ports`（8100〜割当） | core/要件6-2,3,4 未検証(自動テストなし) |
| （自動テストなし） | — | `orchestrate`→未起動自動起動・生存判定 attach/resume | orchestration/要件13-2 未検証(自動テストなし) |

実行方法: 自動テストなし。実機で `claude-dev <subcommand>` を実行して確認する。

## 既知の制限・技術的負債

- `find_available_novnc_port` の選定〜`docker run` は非アトミック。同時 `start` のポート競合は
  リトライで吸収するが根本解決ではない。
- `host-hooks.json` はファイル名が実態（hooks＋env）と乖離（歴史的経緯、変更コスト回避で据置き）。
- 認証は「コピー方式」で symlink を使わない（Claude Code のアトミック書込みで symlink が壊れるため。
  書き戻しは entrypoint のバックグラウンド同期）。
- コンテナ名＝ディレクトリ名のため、別パスでも同名ディレクトリは同一セッション扱いになる。
- `.claude-dev.yaml` の SSH 鍵はローカル設定のみ参照し、グローバルへのフォールバックや鍵推測はしない
  （意図的な安全側設計）。

## 運用メモ

- PATH 登録: `sudo ln -sf ${BASE_DIR}/claude-dev /usr/local/bin/claude-dev`（`setup` が未登録時に案内）。
- proxy 設定変更（`CLAUDE_DEV_ALLOW_WORKSPACE_BINDS` 等）は共有・常駐のため proxy を作り直す必要がある。
- VM モード（`--vm`）は初回 provision に数分。tmux 未起動でも終了せずコンテナは稼働継続するので、
  再 `start` か（コンテナ内）`vm logs`/`vm status` で確認する。
- 生 Docker ソケット・SSH 秘密鍵ファイルはコンテナへ直接渡さない（不変条件）。

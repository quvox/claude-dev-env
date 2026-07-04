---
summary: macOS 版ホスト側 CLI（claude-dev-mac）の実装仕様。Linux 版 claude-dev（10_cli.md）との差分＝macOS 固有部分（SSH agent 魔法ソケット・Docker ソケット検出・VM/KVM 拒否・ポート直結・ネイティブアーキ）を成果物仕様として記述する。
keywords: [ CLI, claude-dev-mac, macOS, bash, SSHエージェント, Dockerソケット, ポートフォワード ]
---

# 実装仕様: claude-dev-mac CLI（macOS 版）

> **この文書の役割**: macOS（Docker Desktop）上でホスト側の日常操作を担う `claude-dev-mac` シェルスクリプトの実装仕様。設計意図は [docs/09_macos-support.md](../09_macos-support.md)、利用者向けコマンド使用法は [docs/04_cli-reference.md](../04_cli-reference.md) を参照。本書は Linux 版 [10_cli.md](10_cli.md) との**差分**を中心に、成果物仕様を記述する。

## 要件（なぜ必要か）

Linux 前提の `claude-dev` を macOS で使えるようにするため、ホスト側 CLI の OS 依存箇所を macOS 向けに置き換えた独立スクリプトを提供する。コンテナ内資産は Linux 版と共有し、CLI だけを分岐させる（設計原則は [09_macos-support.md](../09_macos-support.md)）。

## カバーするコード

```
claude-dev-mac      （単一の bash スクリプト。macOS 版ホスト CLI）
```

## Linux 版との関係

`claude-dev-mac` は `claude-dev`（[10_cli.md](10_cli.md)）の macOS 適応版であり、**以下に列挙する差分以外は Linux 版と同一の成果物仕様**に従う。定数・ヘルパー関数・サブコマンド体系（`setup`/`login`/`logout`/`start`/`code`/`orchestrate`/`attach`/`stop`/`forward`/`unforward`/`ports`/`list`/`upgrade`/`firewall`/`reset`/`help`）とその挙動は 10_cli.md を正本とする。

## macOS 固有の差分（成果物仕様）

### D1. SSH agent ソケットの転送

`start` のマウント組み立てにおいて、`ensure_ssh_agent` でホスト側 ssh-agent に鍵を読み込んだ後、`SSH_OPTS` を次のように構成する。

- ホストに ssh-agent が有効（`SSH_AUTH_SOCK` が非空）な場合、Docker Desktop の魔法ソケットをコンテナへマウントする:
  - `-v /run/host-services/ssh-auth.sock:/tmp/ssh-agent.sock -e SSH_AUTH_SOCK=/tmp/ssh-agent.sock`
  - マウント元 `/run/host-services/ssh-auth.sock` は Docker Desktop の Linux VM 内にのみ存在するため、**macOS ホスト上での存在確認（`[ -S ... ]`）は行わない**。
  - マウント先を `/tmp/ssh-agent.sock` に固定することで、entrypoint の既存処理（`/tmp/ssh-agent.sock` を検出して各シェルの `SSH_AUTH_SOCK` に書き出す）と整合する。
- `~/.ssh/known_hosts`（存在時 RO マウント）と `~/.ssh/config`（`IdentityFile`/`IdentitiesOnly` 行を `sed -E` で除去した一時ファイルを RO マウント）は Linux 版と同じ。
- Linux 版の「`$SSH_AUTH_SOCK` を直接 bind mount する」処理は macOS 版には**存在しない**。

### D2. Docker ソケットの検出

- ソケット検出用ヘルパー `detect_docker_sock` を持ち、次の優先順で最初に存在する Unix ソケットを標準出力に返す（無ければ空文字）:
  1. `/var/run/docker.sock`
  2. `$HOME/.docker/run/docker.sock`
- `ensure_docker_proxy_container`: `detect_docker_sock` の結果（ローカル変数 `sock`）が非空のときのみ動作。イメージ未ビルドならビルドし、未起動ならプロキシコンテナを `claude-dev-net` 上に `--restart unless-stopped`・`-e CLAUDE_DEV_ALLOW_WORKSPACE_BINDS=${CLAUDE_DEV_ALLOW_WORKSPACE_BINDS:-1}` 付きで起動する。ソケットは検出したパスを `-v "${sock}:/var/run/docker.sock:ro"` でマウントする。
- `start` の Docker オプション組み立ては `detect_docker_sock` をインラインで呼んで判定し（`if [ -n "$(detect_docker_sock)" ]`）、非空なら `ensure_docker_proxy_container` 後に `DOCKER_HOST=tcp://<proxy>:2375` を付与する。

### D3. VM モード / KVM の拒否

- `start` のフラグ解析で `--kvm` / `--vm` / `--vm-fresh` のいずれかを検出したら、macOS では利用できない旨（`/dev/kvm` 非対応・ネスト仮想化不可）を表示して `exit 1` する。この判定は `require_setup`（イメージ自動ビルド）**より前**に行い、無駄なビルドを避ける。
- Linux 版に存在する以下のロジックは macOS 版には**存在しない**:
  - `KVM_OPTS`（`/dev/kvm` 等の `--device` 受け渡し）
  - `VM_OPTS`（`CLAUDE_DEV_VM`・ゲスト用ボリューム・`VM_PORTS` 等の受け渡し）
  - VM モード用の長時間待機（tmux 起動待ちは常に 30 秒上限）・VM 起動進捗表示・provision 継続案内
- `code`: VM モード判定（`CLAUDE_DEV_VM` の printenv・`--append-system-prompt` 注入）は行わず、常に `tmux new-window -t main "claude"` を実行して attach する。
- `orchestrate`: `vm.env` の読み込み（`[ -f /etc/claude-dev/vm.env ] && . /etc/claude-dev/vm.env`）は挟まない。それ以外（`--fresh`・ゴール引数の扱い・`-c /workspace` での新規ウィンドウ起動）は Linux 版と同じ。

### D4. ポートフォワードの到達経路

- `forward`: フォワード確立後の案内を、SSH トンネル手順ではなく「ブラウザで `http://localhost:<host-port>` にアクセス」に変更する。socat プロキシコンテナの作成（`fwd-<name>-<port>`、`-p <hport>:<cport>`、`IMG_CLAUDE` を `--entrypoint socat`）は Linux 版と同じ。
- `help`: Web アプリアクセスの節を、SSH トンネル前提から「`claude-dev forward <port>` 後に `http://localhost:<host-port>`」の直結案内に変更する。`--kvm`/`--vm` の記載は含めない。

### D5. プラットフォーム（ネイティブアーキ）

- macOS 版はネイティブアーキでビルド/実行する（Apple Silicon=arm64 / Intel Mac=amd64）。`DOCKER_DEFAULT_PLATFORM` は**固定しない**（利用者が明示している場合のみ尊重）。共有 `Dockerfile.claude` がアーキ別に対応しているため、arm64 でもネイティブにビルドできる（gcloud はアーキ名写像、VNC ブラウザは arm64=Playwright Chromium／amd64=Google Chrome、共通ランチャー `claude-dev-chrome`。設計 [../09_macos-support.md](../09_macos-support.md) §5、Dockerfile 仕様 [40_devcontainer.md](40_devcontainer.md)）。
- Makefile（`Darwin` 判定時）も `DOCKER_DEFAULT_PLATFORM` を設定せず、`make build*`/`setup`/`upgrade` をネイティブアーキでビルドする（[20_makefile.md](20_makefile.md)）。

### D6. その他の差分

- スクリプト冒頭コメントに macOS 版である旨を記載する。
- `start` の起動メッセージから VM モード関連の分岐（「VM モードで起動します…」等）を除く。
- `find_available_novnc_port` / `find_available_host_port` の空きポート判定（`docker ps --format '{{.Ports}}' | grep '0.0.0.0:<port>->'`）は Docker Desktop の公開ポート表記と一致するため Linux 版と共通。
- `CUSER=$(whoami)`、`id -u`/`id -g` を用いたビルド、パス解決（`readlink -f "$0"`→失敗時 `realpath "$0"` で実体パスを得て `dirname` で `BASE_DIR`）は macOS でもそのまま機能するため Linux 版と共通。`make install` は `/usr/local/bin/claude-dev` を本スクリプトへの symlink にするため、`readlink -f` が repo の実体パスへ解決し、repo 内資産を参照できる。

## 不変条件・注意点

- コンテナ内資産（firewall・docker-proxy・tmux.conf）は Linux 版と完全共有し不変。`Dockerfile.claude` と `entrypoint-claude.sh` は arm64 ネイティブ対応のためアーキ別分岐を持つが、**amd64 では従来と同一**の後方互換（[../09_macos-support.md](../09_macos-support.md) §5）。
- SSH 鍵ファイル・Docker 生ソケットをコンテナへ直接渡さない不変条件は Linux 版と同じ（[00_overview.md](00_overview.md)）。macOS では SSH agent 転送を Docker Desktop 魔法ソケット経由で行う点のみ異なる。
- `make install` は OS を判定し、macOS では `sudo ln -sf` により `/usr/local/bin/claude-dev` を `claude-dev-mac` への symlink にする（Linux 版も symlink。[20_makefile.md](20_makefile.md)）。利用者コマンド名はどの OS でも `claude-dev`。

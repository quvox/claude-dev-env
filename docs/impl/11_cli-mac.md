---
summary: macOS 版ホスト側 CLI（claude-dev-mac）の実装仕様。Linux 版 claude-dev（10_cli.md）との差分＝macOS 固有部分（SSH agent は専用 agent＋socat TCP ブリッジ＝鍵は対話選択して config 保存・ssh-keys サブコマンド・Docker ソケット検出・VM/KVM 拒否・ポート直結・ネイティブアーキ）を成果物仕様として記述する。
keywords: [ CLI, claude-dev-mac, macOS, bash, SSHブリッジ, Dockerソケット, ポートフォワード ]
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

`claude-dev-mac` は `claude-dev`（[10_cli.md](10_cli.md)）の macOS 適応版であり、**以下に列挙する差分以外は Linux 版と同一の成果物仕様**に従う。定数・ヘルパー関数・サブコマンド体系（`setup`/`pull`/`login`/`logout`/`start`/`code`/`orchestrate`/`attach`/`stop`/`forward`/`unforward`/`ports`/`list`/`upgrade`/`firewall`/`reset`/`help`）とその挙動は 10_cli.md を正本とする。macOS 版はこれに加えて **`ssh-keys` サブコマンド**（SSH 鍵の対話選択・リセット。D1）を持つ。**GHCR 対応（`pull` サブコマンド・`CONTAINER_USER` によるコンテナユーザー解決）は両 OS 共通**で 10_cli.md／設計 [../10_ghcr-images.md](../10_ghcr-images.md) を正本とし、macOS 版も同一実装を持つ（macOS 固有差分ではない）。

## macOS 固有の差分（成果物仕様）

### D1. SSH agent の転送（方式 D: claude-dev 専用 agent＋socat TCP ブリッジ）

魔法ソケット方式・Linux 版の `$SSH_AUTH_SOCK` 直 bind mount・`ensure_ssh_agent` は macOS 版では**使わない**。代わりに claude-dev が自前の ssh-agent を鍵ファイルから構築し、127.0.0.1 の socat TCP ブリッジでコンテナへ転送する（設計 [../09_macos-support.md](../09_macos-support.md) §1）。

**パス/設定（成果物）**
- 専用 agent ソケット: `${HOME}/.claude-dev/ssh-agent.sock`、その PID: `${HOME}/.claude-dev/ssh-agent.pid`（`reset` の agent 停止に使う）。
- ブリッジ状態: `${HOME}/.claude-dev/ssh-bridge.pid`・`${HOME}/.claude-dev/ssh-bridge.port`。
- ブリッジポート: 既存ブリッジが `kill -0` で生存していれば `ssh-bridge.port` の値を再利用。無い場合は `.env` の `CLAUDE_DEV_SSH_BRIDGE_PORT` があればそれ、無ければ `find_free_local_port` で空き 127.0.0.1 ポートを確保して `ssh-bridge.port` に記録（全 claude コンテナで 1 つ共有）。
- 鍵設定: `~/.config/claude-dev.yaml` の `ssh_keys`（下記スキーマ）。

**ヘルパー（成果物）**
| 関数 | 責務 |
|------|------|
| `discover_ssh_keys` | `~/.ssh/id_*`（`.pub` 除く）を `DISCOVERED_KEYS` に列挙 |
| `config_has_ssh_selection` | config に `ssh_keys:` 行があるか（選択済み判定。`grep -qE '^ssh_keys:'`） |
| `load_config_ssh_keys` | config の `ssh_keys` を `SSH_KEY_LIST` に読み込む（YAML 簡易パース、`~`→`$HOME` 展開） |
| `write_config_ssh_keys <keys...>` | 選択鍵を config に書き出す（claude-dev 所有ファイルとして全体を再生成） |
| `select_ssh_keys_interactive` | `discover_ssh_keys` を番号付きで提示し、カンマ/空白区切り番号 / `a`=全部 / `n`(または空)=なし で選択→`write_config_ssh_keys` で保存し `SSH_KEY_LIST` に反映 |
| `ensure_dedicated_agent` | `SSH_AUTH_SOCK=<sock> ssh-add -l` の終了コードが 2（接続不可）または sock 非存在なら `ssh-agent -a <sock>` で（再）起動し、出力から PID を `ssh-agent.pid` に記録。選択鍵を `SSH_AUTH_SOCK=<sock> ssh-add`（重複 add は無害、パスフレーズ付きは対話で一度だけ） |
| `find_free_local_port` | 9700〜9799 を走査し空き 127.0.0.1 ポートを返す（forward の 8100〜・noVNC の 6080〜 と重ならない範囲。全滅時は 9700） |
| `ensure_ssh_bridge` | `socat` の有無を確認（無ければ `brew install socat` を案内して非0で戻り SSH 転送をスキップ）。既存ブリッジが `kill -0` で生存なら記録済み port を再利用。無ければポートを決定し `socat TCP-LISTEN:<port>,bind=127.0.0.1,fork,reuseaddr UNIX-CONNECT:<sock>` を `nohup ... &` でバックグラウンド起動、pid/port を記録。使用中の `<port>` を標準出力に返す |
| `stop_ssh_bridge_if_idle` | 稼働 claude コンテナ数（`ancestor` フィルタ）が 0 なら socat を停止（pid を kill、`ssh-bridge.pid`/`ssh-bridge.port` 削除）。専用 agent は残す（鍵保持・TCP 露出なし） |

**`start` の SSH 部分**
1. `config_has_ssh_selection` が偽なら `select_ssh_keys_interactive`（＝初回対話選択）。真なら `load_config_ssh_keys`。
2. 選択鍵が 1 つ以上あり `socat` が使えるなら、`ensure_dedicated_agent` → `ensure_ssh_bridge` で `<port>` を得て、`docker run` に `-e CLAUDE_DEV_SSH_BRIDGE_PORT=<port>` を付与する。鍵なし/`socat` なしなら SSH 転送を付けずに継続（警告）。
3. `~/.ssh/known_hosts`（存在時 RO マウント）・`~/.ssh/config`（`IdentityFile`/`IdentitiesOnly` 行を `sed -E` で除去した一時ファイルを RO マウント）は Linux 版と同じ。
4. コンテナ内で `/tmp/ssh-agent.sock` を立てて `SSH_AUTH_SOCK` に設定するのは entrypoint（[31_entrypoint.md](31_entrypoint.md)）。CLI 側は port を渡すだけ。

**`ssh-keys` サブコマンド**
- `claude-dev ssh-keys`: `select_ssh_keys_interactive` を実行し config を上書き保存（再選択）。
- `claude-dev ssh-keys reset`: config の `ssh_keys` セクションを削除（`grep -vE '^ssh_keys:|^[[:space:]]*-[[:space:]]'`）し、専用 agent の鍵をフラッシュ（`SSH_AUTH_SOCK=<sock> ssh-add -D`）、**ブリッジ socat と専用 agent を停止**して `ssh-bridge.pid`/`ssh-bridge.port`/`ssh-agent.pid`/`ssh-agent.sock` を削除する。次回 `start` で再度対話選択。

**`stop`**: 対象コンテナ削除後、`stop_ssh_bridge_if_idle` と `stop_proxy_if_idle` を呼ぶ。

**config スキーマ（`~/.config/claude-dev.yaml`）**
```yaml
ssh_keys:
  - ~/.ssh/id_ed25519_github
```
`ssh_keys` セクションの有無で「選択済み/未選択」を判定する。鍵ゼロを選んだ場合も「選択済み（空）」として再プロンプトしない。Linux 版の自動生成（`~/.ssh/id_*` を列挙して書き込む）とはフィールド互換（どちらも `ssh_keys` を読む）。

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
- `start` 時に使用イメージのバージョン（`image_version`：`io.github.quvox.claude-dev.version` ラベル→無ければ `unknown`＋作成日時）を表示するのは 10_cli.md 共通で、macOS 版も同一実装。
- `find_available_novnc_port` / `find_available_host_port` の空きポート判定（`docker ps --format '{{.Ports}}' | grep '0.0.0.0:<port>->'`）は Docker Desktop の公開ポート表記と一致するため Linux 版と共通。
- `CUSER` 解決（実行イメージの `CONTAINER_USER` env を優先、無ければ `whoami`。GHCR generic user 対応。10_cli.md 共通）、`id -u`/`id -g` を用いたビルド、パス解決（`readlink -f "$0"`→失敗時 `realpath "$0"` で実体パスを得て `dirname` で `BASE_DIR`）は macOS でもそのまま機能するため Linux 版と共通。`make install` は `/usr/local/bin/claude-dev` を本スクリプトへの symlink にするため、`readlink -f` が repo の実体パスへ解決し、repo 内資産を参照できる。

## 不変条件・注意点

- コンテナ内資産（firewall・docker-proxy・tmux.conf）は Linux 版と完全共有し不変。`Dockerfile.claude` は arm64 ネイティブ対応のためアーキ別分岐を持ち（§5）、`entrypoint-claude.sh` は arm64 ブラウザ分岐（§5）と **SSH TCP ブリッジ分岐（`CLAUDE_DEV_SSH_BRIDGE_PORT` 指定時のみ。D1）** を持つ。いずれも**該当条件が無い環境（Linux/amd64・ブリッジ port 未指定）では従来と同一**の後方互換（[../09_macos-support.md](../09_macos-support.md) §1・§5 / [31_entrypoint.md](31_entrypoint.md)）。
- SSH 鍵ファイル・Docker 生ソケットをコンテナへ直接渡さない不変条件は Linux 版と同じ（[00_overview.md](00_overview.md)）。macOS では SSH agent 転送を **claude-dev 専用 agent＋127.0.0.1 socat TCP ブリッジ**で行う（鍵ファイルはコンテナに渡らず、agent プロトコルのみ。露出は選択鍵のみ・稼働中のみ・127.0.0.1 限定）点が Linux 版（`$SSH_AUTH_SOCK` 直 bind mount）と異なる。
- `make install` は OS を判定し、macOS では `sudo ln -sf` により `/usr/local/bin/claude-dev` を `claude-dev-mac` への symlink にする（Linux 版も symlink。[20_makefile.md](20_makefile.md)）。利用者コマンド名はどの OS でも `claude-dev`。

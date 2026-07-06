---
summary: macOS 版ホスト側 CLI（claude-dev-mac）の実装仕様。Linux 版 claude-dev（10_cli.md）との差分＝macOS 固有部分（SSH agent はプロジェクト（ディレクトリ）ごとの専用 agent＋socat TCP ブリッジ＝鍵はプロジェクト設定 .claude-dev.yaml の ssh_keys のみ＝グローバルへのフォールバックなし・Docker ソケット検出・VM/KVM 拒否・ポート直結・ネイティブアーキ）を成果物仕様として記述する。鍵の解決方針や ssh-keys サブコマンドは両 OS 共通（10_cli.md 正本）で、mac 差分は転送手段（socat TCP ブリッジ）のみ。
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

`claude-dev-mac` は `claude-dev`（[10_cli.md](10_cli.md)）の macOS 適応版であり、**以下に列挙する差分以外は Linux 版と同一の成果物仕様**に従う。定数・ヘルパー関数・サブコマンド体系（`setup`/`pull`/`login`/`logout`/`start`/`code`/`orchestrate`/`attach`/`stop`/`forward`/`unforward`/`ports`/`list`/`ssh-keys`/`upgrade`/`firewall`/`reset`/`help`）とその挙動は 10_cli.md を正本とする。**`ssh-keys` サブコマンド**（SSH 鍵の対話選択・リセット）は両 OS 共通で 10_cli.md を正本とし、macOS 版の差分は `reset` がブリッジ socat も停止する点のみ（D1）。**GHCR 対応（`pull` サブコマンド・`CONTAINER_USER` によるコンテナユーザー解決）は両 OS 共通**で 10_cli.md／設計 [../10_ghcr-images.md](../10_ghcr-images.md) を正本とし、macOS 版も同一実装を持つ（macOS 固有差分ではない）。

## macOS 固有の差分（成果物仕様）

### D1. SSH agent の転送（方式 D: claude-dev 専用 agent＋socat TCP ブリッジ。プロジェクト単位で鍵を隔離）

魔法ソケット方式・Linux 版の `$SSH_AUTH_SOCK` 直 bind mount・`ensure_ssh_agent` は macOS 版では**使わない**。代わりに claude-dev が自前の ssh-agent を鍵ファイルから構築し、127.0.0.1 の socat TCP ブリッジでコンテナへ転送する（設計 [../09_macos-support.md](../09_macos-support.md) §1）。

専用 agent・ブリッジは**プロジェクト（= `NAME`＝ディレクトリ名）ごと**に持ち、使う鍵をディレクトリ単位で切り替える（Linux 版 [10_cli.md](10_cli.md) と同じ「プロジェクト設定優先＋専用 agent 隔離」方針。macOS は転送手段が socat TCP ブリッジである点のみ異なる）。

**パス/設定（成果物）**
- 専用 agent/ブリッジの置き場: `${HOME}/.claude-dev/agents/`（`DEV_AGENT_DIR`、`chmod 700`）。プロジェクトごとに `<name>.sock`（agent ソケット）・`<name>.pid`（agent PID）・`<name>.bridge.pid`・`<name>.bridge.port`。パスは `dev_agent_path <name> sock|pid|bpid|bport` が返す。
- ブリッジポート: そのプロジェクトの既存ブリッジが `kill -0` で生存していれば `<name>.bridge.port` の値を再利用。無い場合は `.env` の `CLAUDE_DEV_SSH_BRIDGE_PORT` があればそれ、無ければ `find_free_local_port` で空き 127.0.0.1 ポートを確保して `<name>.bridge.port` に記録（**プロジェクトごとに 1 つ**。稼働中の別プロジェクトのブリッジはポートを占有するので衝突しない）。
- 鍵設定: **`<PROJECT_DIR>/.claude-dev.yaml`（`PROJECT_CONFIG_NAME`）の `ssh_keys:` のみ**を見る（グローバル `~/.config/claude-dev.yaml` へのフォールバックはしない）。**`.claude-dev.yaml` が無い初回 `start` は両 OS 共通で `ensure_project_config` が作成する**（TTY は `select_ssh_keys_interactive` で鍵選択を促し、非 TTY は空 `ssh_keys:`。10_cli.md 正本）。鍵解決自体はローカル設定のみで、鍵の推測・グローバル流用はしない。
- **起動時の依存チェック（macOS 差分）**: `start` 冒頭の `check_host_deps` は Linux 版の `docker`・`jq` に加え **`socat`** を必須とする（方式 D の SSH ブリッジに host socat が要るため）。不足時は `brew install <cmd>`（docker は Docker Desktop 導入 URL）を案内して `exit 1`。
- 後方互換: 旧・単一 agent/ブリッジのファイル（`ssh-agent.sock`/`ssh-agent.pid`/`ssh-bridge.pid`/`ssh-bridge.port`）は生成しなくなったが、`reset` が残骸を掃除する（`LEGACY_*`）。

**ヘルパー（成果物）**
| 関数 | 責務 |
|------|------|
| `dev_agent_path <name> <kind>` | プロジェクト `<name>` の `sock`/`pid`/`bpid`/`bport` パスを stdout に返す |
| `discover_ssh_keys` | `~/.ssh/id_*`（`.pub` 除く）を `DISCOVERED_KEYS` に列挙（`ssh-keys` の対話選択で使う） |
| `_parse_ssh_keys_yaml <file>` | 指定 YAML の `ssh_keys:` を `SSH_KEY_LIST` に追記（簡易パース、`~`→`$HOME` 展開、コメント除去） |
| `resolve_ssh_keys_for_start <project_dir>` | 使う鍵を **`<project_dir>/.claude-dev.yaml` の `ssh_keys:` からのみ**解決して `SSH_KEY_LIST`／採用元 `SSH_CONFIG_SOURCE`（＝そのプロジェクトの `.claude-dev.yaml` パス）を設定。グローバルへのフォールバック・対話選択・自動生成はしない |
| `write_project_ssh_keys <file> <keys...>` | 選択鍵をプロジェクト直下の `.claude-dev.yaml` に書き出す（claude-dev 所有ファイルとして再生成） |
| `select_ssh_keys_interactive` | `discover_ssh_keys` を番号付きで提示し、カンマ/空白区切り番号 / `a`=全部 / `n`(または空)=なし で選択→`write_project_ssh_keys "$(pwd)/.claude-dev.yaml"` で**カレントプロジェクトの `.claude-dev.yaml`** に保存し `SSH_KEY_LIST` に反映 |
| `ensure_dedicated_agent <name>` | `${DEV_AGENT_DIR}/<name>.sock` に対し `ssh-add -l` の終了コードが 2（接続不可）または sock 非存在なら `ssh-agent -a <sock>` で（再）起動し PID を `<name>.pid` に記録。登録前に `ssh-add -l` の指紋と各鍵の指紋（`ssh-keygen -lf`、パスフレーズ不要）を突き合わせ**既登録の鍵はスキップ**、未登録分をパスフレーズなし一括→残りを対話追加。存在しない鍵は警告してスキップ |
| `find_free_local_port` | 9700〜9799 を走査し空き 127.0.0.1 ポートを返す（forward の 8100〜・noVNC の 6080〜 と重ならない範囲。全滅時は 9700） |
| `ensure_ssh_bridge <name>` | `socat` の有無を確認（無ければ `brew install socat` を案内して非0で戻り SSH 転送をスキップ）。そのプロジェクトの既存ブリッジが `kill -0` で生存なら記録済み port を再利用。無ければポートを決定し `socat TCP-LISTEN:<port>,bind=127.0.0.1,fork,reuseaddr UNIX-CONNECT:<name>.sock` を `nohup ... &` で起動、`<name>.bridge.pid`/`.port` を記録。使用中の `<port>` を標準出力に返す |
| `stop_ssh_bridge <name>` | 指定プロジェクトのブリッジ socat を停止（`<name>.bridge.pid` を kill、`.bridge.pid`/`.bridge.port` 削除）。専用 agent は残す（鍵保持・TCP 露出なし） |

**`start` の SSH 部分**
1. `resolve_ssh_keys_for_start "$PROJECT_DIR"` で使う鍵を解決（`<PROJECT_DIR>/.claude-dev.yaml` の `ssh_keys:` のみ。無ければ 0 件）。
2. 有効鍵（実在する鍵ファイル）が 1 つ以上あれば `ensure_dedicated_agent "$NAME"`（socat の有無に関わらず専用 agent を構築し鍵を登録。パスフレーズ入力が走り得る）を実行し、成功後に `ensure_ssh_bridge "$NAME"` で `<port>` を得る。`socat` が無い場合は `ensure_ssh_bridge` が `brew install socat` を案内して非0を返し、`<port>` が空になるため SSH 転送を付けずに継続する。`<port>` が得られたときのみ `docker run` に `-e CLAUDE_DEV_SSH_BRIDGE_PORT=<port>` を付与する。有効鍵が 1 つも無い場合は SSH 転送なしで継続し、`ssh-keys` での選択またはプロジェクト直下に `.claude-dev.yaml` を作る案内を出す（この案内は鍵なし分岐のみ。`socat` 不在時の警告は `brew install socat` の案内）。
3. `~/.ssh/known_hosts`（存在時 RO マウント）・`~/.ssh/config`（`IdentityFile`/`IdentitiesOnly`/**`IdentityAgent`** 行を `sed -E '/^[[:space:]]*(IdentityFile|IdentitiesOnly|IdentityAgent)/d'` で除去した**一時コピー**を RO マウント。ホストの config は変更しない）。`IdentityAgent` を除くのはホスト固有 agent パスが `SSH_AUTH_SOCK`（ブリッジ）を上書きし agent 不通になるのを防ぐため。Linux 版も同じ sed を使う。
4. コンテナ内で `/tmp/ssh-agent.sock` を立てて `SSH_AUTH_SOCK` に設定するのは entrypoint（[31_entrypoint.md](31_entrypoint.md)）。CLI 側は port を渡すだけ。

**`ssh-keys` サブコマンド**（対象は**カレントプロジェクト**）
- `claude-dev ssh-keys`: `select_ssh_keys_interactive` を実行し、**カレントディレクトリの `.claude-dev.yaml`** に選択鍵を保存（再選択）。手書きでも同じ `ssh_keys:` 形式で設定できる。
- `claude-dev ssh-keys reset`: カレントプロジェクトの `.claude-dev.yaml` から `ssh_keys` セクションを除去（`grep -vE` で ssh_keys 行・リスト項目・管理用コメントを削除。ssh_keys だけのファイルは残らず削除、他の記述があれば残す）し、**このプロジェクト（`container_name`）の専用 agent／ブリッジ**（`<name>.sock`/`<name>.pid`/`<name>.bridge.pid`/`<name>.bridge.port`）を停止・削除する。加えて後方互換で旧・単一 agent/ブリッジの残骸（`LEGACY_*`）も掃除する。再設定は `claude-dev ssh-keys` で選択するか `.claude-dev.yaml` を作成する（`start` 自体は対話選択しない）。

**`stop`**: 対象コンテナ削除後、`stop_ssh_bridge "$NAME"`（そのプロジェクトのブリッジのみ停止。専用 agent は残す）と `stop_proxy_if_idle` を呼ぶ。

**config スキーマ（プロジェクト `<PROJECT_DIR>/.claude-dev.yaml`）**
```yaml
ssh_keys:
  - ~/.ssh/id_ed25519_github
```
`.claude-dev.yaml` が無い、または `ssh_keys:` が空なら SSH 転送なしで起動する（グローバル config へのフォールバック・自動生成はしない）。Linux 版（[10_cli.md](10_cli.md)）と完全に同じスキーマ・同じ「ローカルのみ」方針で、`ssh_keys` を読む点も共通。

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

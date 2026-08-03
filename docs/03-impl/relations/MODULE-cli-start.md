---
id: MODULE-cli-start
module: MOD-cli-start
kind: tool
sync: sync
impl: claude-dev::main#start, claude-dev-mac::main#start
callers: MODULE-cli-orchestrate
callees: MODULE-entrypoint-claude, MODULE-cli-common-container-exists, MODULE-cli-common-container-name, MODULE-cli-common-dev-agent-path, MODULE-cli-common-ensure-infrastructure, MODULE-cli-common-get-novnc-url, MODULE-cli-common-image-exists, MODULE-cli-common-is-running, MODULE-cli-common-require-setup, MODULE-cli-common-resolve-container-user, MODULE-cli-common-select-ssh-keys, MODULE-cli-common-write-project-ssh-keys
contracts: CTR-cli-container
design: DSN-mod-01, DSN-mod-02, DSN-arch-01, DSN-auth-01, DSN-dist-02
requirements: FR-env-01, FR-env-02, FR-env-03, FR-env-04, FR-env-05, FR-env-06, FR-env-07, FR-env-08, FR-env-11, FR-env-12
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: カレントディレクトリで開発コンテナを起動する(VNC+Chrome が既定)
---

# MODULE-cli-start 開発コンテナの起動

## 目的

「任意のプロジェクトで `claude-dev start` するだけで隔離環境が立ち上がる」という本システムの
中核体験を実現する(FR-env-01)。UID/GID 追従(FR-env-02)、認証の受け渡し(FR-env-03)、
SSH 鍵の限定転送(FR-env-04)、ネットワーク隔離(FR-env-05)、noVNC ポート公開(FR-env-11)、
docker-proxy 経由の Docker アクセス(FR-env-07)、VM モード(FR-env-08)は、すべてこの機能が
`docker run` の引数として組み立てる。渡す内容の正は契約 `CTR-cli-container`。

## 処理の流れ

1. `check_host_deps`(本機能に畳み込み)で `docker` / `jq`(macOS はさらに `socat`)を確認し、
   不足があれば導入案内を出して `exit 1`。
2. `MODULE-cli-common-require-setup` でイメージをそろえる。
3. `MODULE-cli-common-container-name` で `NAME` を、`pwd` で `PROJECT_DIR` を確定する。
4. `ensure_project_config`(畳み込み)で `.claude-dev.yaml` が無ければ用意する。TTY なら
   `MODULE-cli-common-select-ssh-keys` を呼び、非 TTY なら
   `MODULE-cli-common-write-project-ssh-keys` で空の `ssh_keys:` を書く。
5. フラグを解析する(`--no-vnc` / `--kvm` / `--vm` / `--vm-fresh`。`--vm` 系は `--kvm` を含意し、
   `/dev/kvm` が無ければ `exit 1`)。**macOS 版は `--kvm` / `--vm` / `--vm-fresh` を
   `require_setup` より前に早期拒否して `exit 1` する**。
6. `MODULE-cli-common-is-running` が真なら再接続経路へ入る: 使用中イメージのバージョンと
   `MODULE-cli-common-get-novnc-url` の URL を表示し、`tmux has-session -t main` が無ければ作成し、
   `CLAUDE_DEV_NO_ATTACH != 1` のとき `tmux attach` する(`--vm-fresh` は稼働中は無効と警告)。
7. `MODULE-cli-common-container-exists` が真(停止中の残骸)なら削除し、
   `MODULE-cli-common-ensure-infrastructure` を呼び、VNC 有無でイメージを選ぶ。
8. **認証コピー**: 一時コンテナで `claude-dev-auth`(RO)から `${PROJECT_DIR}/.claude/` へコピーし、
   ホストの UID/GID に `chown` する。同じ一時コンテナに `${PROJECT_DIR}/.codex` を
   `/target-codex` としてマウントし、`/auth/codex/auth.json` があれば `/target-codex/auth.json`
   へコピーして同じ `chown -R` に含める(無ければ何もしない = 未ログインのまま起動できる)。
9. **ホスト設定抽出**: `~/.claude/settings.json` から `jq` で `{hooks, env}`(null 除外)を
   `.claude/host-hooks.json` へ書き出す(entrypoint がマージする)。
10. **ユーザー hook**: `~/.local/bin/` が非空なら `.claude/host-local-bin/` へコピーする。
11. **.gitignore 追記**: `.claude` と `.codex` について、`<name>` も `<name>/` も未記載のものだけ
    追記する(冪等)。`.git` があり `.gitignore` が無ければ2行で新規作成する。
12. **マウント/オプション組立**: `GITCONFIG_OPT`(`~/.gitconfig` RO)、`GH_CONFIG_OPT`
    (`~/.config/gh` RO)、`DOCKER_OPTS`(ソケットがあれば `ensure_docker_proxy_container` を
    呼んだうえで `DOCKER_HOST=tcp://claude-dev-docker-proxy:2375`。この過程で
    `MODULE-cli-common-container-exists` / `MODULE-cli-common-image-exists` /
    `MODULE-cli-common-is-running` を使う)、`COMPOSE_OPTS`(`NAME` を compose 互換名へ正規化した
    `COMPOSE_PROJECT_NAME` を `-e` で付与)、`SSH_OPTS`(Linux: `ensure_ssh_agent` の専用 agent
    ソケットを `/tmp/ssh-agent.sock` へ RO 転送し `SSH_AUTH_SOCK` を設定 / macOS:
    `ensure_dedicated_agent` と `ensure_ssh_bridge` で socat TCP ブリッジを立て
    `-e CLAUDE_DEV_SSH_BRIDGE_PORT=<port>` を付与。いずれも `known_hosts` RO、`~/.ssh/config` は
    `IdentityFile` / `IdentitiesOnly` / `IdentityAgent` 行を `sed` 除去した一時コピーを RO)、
    `NOVNC_PORT_OPT`(VNC 時のみ空きポートで `-p <port>:6080` とコンテナ別 Chrome ボリューム)、
    `KVM_OPTS` / `VM_OPTS`(Linux の `--kvm` / `--vm` 時のみ)。
13. **起動**: イメージ名とバージョンを表示し、`docker run -d --cap-add NET_ADMIN,NET_RAW
    --restart unless-stopped` に `/workspace`・各ボリューム・`tmux.conf` / `CLAUDE.md` の RO マウント・
    上記オプション・`NODE_OPTIONS=--max-old-space-size=4096`・`-t` を付けて実行する。
    **`--security-opt` は付けない**(Docker 既定の seccomp と `docker-default` AppArmor を有効なまま使う)。
14. **ポート競合リトライ**: 失敗時は作成途中のコンテナを `docker rm -f` し、エラーがポート競合かつ
    VNC 有効なら別ポートを取り直して最大20回再試行する。他の失敗または上限超過は stderr へ出して `exit 1`。
15. tmux の起動を待ち(通常30秒 / VM は420秒で15秒ごとに進捗表示)、noVNC URL を表示し、
    `CLAUDE_DEV_NO_ATTACH != 1` なら `tmux attach -t main` する。上限を超えても終了せず状況を案内して
    `exit 0`(コンテナは `--restart unless-stopped` で稼働を続ける)。

## 呼び出され方

- 契機: 利用者が `claude-dev start [--no-vnc] [--kvm] [--vm] [--vm-fresh]` を実行したとき。
  `MODULE-cli-orchestrate` も未起動時に `CLAUDE_DEV_NO_ATTACH=1` を付けて本機能を再帰的に呼ぶ。
- 前提条件: カレントディレクトリが対象プロジェクトであること。`docker` / `jq`(macOS は `socat` も)が
  導入済みであること。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `--no-vnc` | フラグ | 任意 | VNC/Chrome 無しの軽量イメージで起動する |
| `--kvm` | フラグ | 任意 | `/dev/kvm` 等を `--device` で渡す。macOS は拒否 |
| `--vm` | フラグ | 任意 | VM モード。`--kvm` を含意し `/dev/kvm` 必須。macOS は拒否 |
| `--vm-fresh` | フラグ | 任意 | ゲストを再 provision する。`--vm` を含意。稼働中は無効 |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容
### MODULE-entrypoint-claude

- 何のために呼ぶか: コンテナ内の初期化(UID/GID 追従・認証コピー・ファイアウォール適用・
  VNC/Chrome・tmux・同期ループ・ポート同期)を行わせるため。`docker run` でコンテナを作ると
  イメージの `ENTRYPOINT` として起動する(`claude-dev:419` / `claude-dev-mac:486` の `docker run -d`)。
- 何を渡すか: 契約 `CTR-cli-container` が定める環境変数一式とマウント、`NET_ADMIN` / `NET_RAW`。
- 何を受け取るか: 直接の戻り値は無い。tmux が立ち上がった状態のコンテナ。
- **失敗したときどうなるか**: `docker run` が非0なら起動失敗として扱う。entrypoint 内部の
  補助処理(ファイアウォール等)の失敗は `|| true` で握られ、起動は継続する。
- **注記**: これは関数呼び出しではなく**プロセス境界をまたぐ起動**である。コールグラフには
  現れないため `callgraph-check.py` は CG3「低」として出すが、実在する連携である。

### MODULE-cli-common-require-setup

- 何のために呼ぶか: 起動に使うイメージを保証するため。 / 何を渡すか: なし。 / 何を受け取るか: なし。
- **失敗したときどうなるか**: `set -e` で非0終了し、コンテナは作られない。

### MODULE-cli-common-container-name

- 何のために呼ぶか: コンテナ名・compose プロジェクト名・各種ボリューム名の基準を決めるため。
- 何を渡すか: なし。 / 何を受け取るか: コンテナ名。
- **失敗したときどうなるか**: 想定されない。

### MODULE-cli-common-is-running

- 何のために呼ぶか: 再接続経路と新規作成経路の分岐、および docker-proxy の起動要否判定。
- 何を渡すか: コンテナ名 / docker-proxy 名。 / 何を受け取るか: 終了ステータス。
- **失敗したときどうなるか**: 非稼働と判定され新規作成へ進む。既存コンテナがあれば名前衝突で
  `docker run` が失敗し、リトライ経路で `rm -f` される。

### MODULE-cli-common-container-exists

- 何のために呼ぶか: 停止中の残骸を消してから作り直すため、および docker-proxy の残骸削除。
- 何を渡すか: コンテナ名。 / 何を受け取るか: 終了ステータス。
- **失敗したときどうなるか**: 残骸が残り、`docker run` が名前衝突で失敗する。

### MODULE-cli-common-image-exists

- 何のために呼ぶか: `ensure_docker_proxy_container` が docker-proxy イメージのビルド要否を決めるため。
- 何を渡すか: `claude-dev-docker-proxy`。 / 何を受け取るか: 終了ステータス。
- **失敗したときどうなるか**: ビルドが走る(既存なら即座に完了する)。

### MODULE-cli-common-ensure-infrastructure

- 何のために呼ぶか: ネットワークと共有ボリュームを用意するため。 / 何を渡すか: なし。 / 何を受け取るか: なし。
- **失敗したときどうなるか**: 握りつぶされ、`docker run` のボリューム自動作成で吸収される。

### MODULE-cli-common-resolve-container-user

- 何のために呼ぶか: 再接続経路で `docker exec -u` に渡すユーザを解決するため。
- 何を渡すか: コンテナ名。 / 何を受け取るか: ユーザ名。
- **失敗したときどうなるか**: `CUSER` へフォールバックし、合わなければ exec が失敗する。

### MODULE-cli-common-get-novnc-url

- 何のために呼ぶか: 起動後/再接続時に利用者へ接続 URL を提示するため。
- 何を渡すか: コンテナ名。 / 何を受け取るか: URL 文字列(未公開なら空)。
- **失敗したときどうなるか**: 空が返り、URL 行を表示しないだけで起動は続く。

### MODULE-cli-common-select-ssh-keys

- 何のために呼ぶか: `.claude-dev.yaml` が無く TTY のとき、転送する鍵を選ばせるため。
- 何を渡すか: なし。 / 何を受け取るか: `SSH_KEY_LIST` と `.claude-dev.yaml`。
- **失敗したときどうなるか**: 鍵0件として扱われ、SSH 転送なしで起動が続く。

### MODULE-cli-common-write-project-ssh-keys

- 何のために呼ぶか: 非 TTY で `.claude-dev.yaml` を空作成するため。
- 何を渡すか: 書き出し先パス(鍵は0件)。 / 何を受け取るか: なし。
- **失敗したときどうなるか**: `set -e` で非0終了し、起動しない。

### MODULE-cli-common-dev-agent-path

- 何のために呼ぶか: macOS で専用 agent ソケットと socat ブリッジの PID / ポートの位置を決めるため。
- 何を渡すか: コンテナ名と種別(`sock` / `pid` / `bpid` / `bport`)。 / 何を受け取るか: パス。
- **失敗したときどうなるか**: 空パスになりブリッジが立たず、SSH 転送なしで起動が続く。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 0(tmux 待ちタイムアウトでも 0)。前提不足・KVM 不在・リトライ上限超過は 1 |
| 永続化 | コンテナ `<name>`。`${PROJECT_DIR}/.claude/`(認証・`host-hooks.json`・`host-local-bin/`)、`${PROJECT_DIR}/.codex/auth.json`、`${PROJECT_DIR}/.gitignore` への追記、`${PROJECT_DIR}/.claude-dev.yaml`。docker volume `claude-dev-auth` / `claude-dev-history` / `claude-dev-config` / `claude-dev-chrome-<name>` / (VM 時)`claude-dev-vm-<name>`。macOS では `~/.claude-dev/agents/<name>.{sock,pid,bridge.pid,bridge.port}` |
| 発火するイベント | なし |
| ログ | 標準出力へイメージ名・バージョン・noVNC URL・進捗。失敗は stderr |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| `docker` / `jq`(macOS は `socat`)が無い | 不足を列挙して導入案内を出し `exit 1` | 起動しない |
| `.claude-dev.yaml` が無い | TTY なら鍵選択、非 TTY なら空作成。停止しない | SSH 転送なしで起動しうる |
| SSH 鍵が0件、または指定鍵が存在しない | 転送なしで続行し、`ssh_keys:` の記述方法を案内する。欠落鍵は警告してスキップ | コンテナ内で SSH が使えない |
| agent ソケットのパスがソケットでない残骸 | `rm -rf` で自己修復。消せなければ**停止せず** `sudo rm -rf` を案内し SSH 転送なしで続行する | 起動は成功する |
| noVNC ポート競合 | 作成途中のコンテナを掃除し、別ポートで最大20回再試行する | 割り当てポートが 6080 以外になる |
| リトライ上限を超えた/ポート競合以外の失敗 | stderr にエラーを出して `exit 1` | 起動しない |
| tmux 起動タイムアウト(通常30秒 / VM 420秒) | 終了せず状況を案内して `exit 0`。コンテナは稼働を続ける | 再 `start` の attach 経路で接続できる |
| `--vm` 指定で `/dev/kvm` が無い(Linux) | `exit 1`(`--kvm` のみなら警告して続行) | 起動しない |
| `--kvm` / `--vm` / `--vm-fresh` 指定(macOS) | 非対応の理由を表示して `exit 1`(イメージビルドより前) | 起動しない |
| Docker ソケットが無い(macOS の `detect_docker_sock` が空) | docker-proxy を起動せず `DOCKER_HOST` を付けずに続行する | コンテナ内から Docker が使えない |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | `--security-opt` を付けない(Docker 既定の confinement を維持する)。この下では codex の bubblewrap サンドボックスが動かないが、対処はコンテナ側を緩めるのではなく codex 側の無効化で行う | D0-sec-01 |
| 2 | 認証は symlink ではなくコピーで渡し、書き戻しは entrypoint のバックグラウンド同期に任せる | D0-auth-02 |
| 3 | `COMPOSE_PROJECT_NAME` を `-e` で渡す(全プロジェクトが `/workspace` にマウントされ compose 既定名 `workspace` が衝突するのを防ぐ。`-e` なら対話・非対話シェルと `docker exec` の全てで有効) | D0-scope-02 |
| 4 | ホストの `~/.ssh/config` はそのまま渡さず、`IdentityFile` / `IdentitiesOnly` / `IdentityAgent` を除去した一時コピーを RO マウントする | D0-sec-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 空きポート選定から `docker run` までが非アトミック | 同時 `start` でポート競合が起きうる(リトライで吸収するが根本解決ではない) | なし |
| `host-hooks.json` の名前が実態(hooks + env)と乖離 | 読み手が誤解しうる。歴史的経緯で据え置き | なし |
| コンテナ名がディレクトリ名だけで決まる | 別パスの同名ディレクトリが同一セッション扱いになる | なし |
| `~/.claude-dev/agents/<name>.sock` に root 所有の残骸が残ることがある | 自動では消せない場合があり、案内を出して SSH 転送なしで続行する | なし |

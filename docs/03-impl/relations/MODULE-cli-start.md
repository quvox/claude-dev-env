---
id: MODULE-cli-start
module: MOD-cli-start
kind: tool
sync: sync
impl: claude-dev::main#start, claude-dev-mac::main#start
callers: MODULE-cli-orchestrate
callees: MODULE-entrypoint-claude, MODULE-cli-common-container-exists, MODULE-cli-common-container-name, MODULE-cli-common-dev-agent-path, MODULE-cli-common-ensure-infrastructure, MODULE-cli-common-get-novnc-url, MODULE-cli-common-image-exists, MODULE-cli-common-is-running, MODULE-cli-common-lock, MODULE-cli-common-require-setup, MODULE-cli-common-resolve-container-user, MODULE-cli-common-select-ssh-keys, MODULE-cli-common-write-project-ssh-keys
contracts: CTR-cli-container
design: DSN-mod-01, DSN-mod-02, DSN-arch-01, DSN-auth-01, DSN-dist-02, DSN-env-01, DSN-env-02
requirements: FR-env-01, FR-env-02, FR-env-03, FR-env-04, FR-env-05, FR-env-06, FR-env-07, FR-env-08, FR-env-11, FR-env-12
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-04
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
2. (欠番。旧「`require_setup` でイメージをそろえる」は**ロック取得の後**へ移した = 手順4。
   取得の前に置くと、同一プロジェクトの2つ目の `start` が数分のイメージビルドを終えてから
   「ロックが取れない」と言うことになり、**もともとロックの後で呼ぶ macOS 版と成否の
   タイミングと出力が食い違う**(`D0-scope-03`)。)
3. `MODULE-cli-common-container-name` で `NAME` を、`pwd` で `PROJECT_DIR` を確定する。
4. `MODULE-cli-common-lock` で**プロジェクト単位**のロック(キー = `NAME`、操作名 `start`)を取り、
   取れたら `MODULE-cli-common-require-setup` でイメージをそろえる。
   取得できなければ、**手順5 以降の生成物(`.claude-dev.yaml`・`${PROJECT_DIR}/.claude`・
   `.codex`・`.gitignore` の追記)と Docker コンテナを一切作らずに**非0で終わる
   (`FR-env-01` 受入基準16)。以降のすべての手順はこのロックの中で行う。
   **`require_setup` によるイメージのビルドはロックの保護対象外**である(契約の「排他(ロックキー)」。
   イメージは冪等に作られる共有資源で、どの操作から作っても結果が同じであるため)。
   **ただし実装ではロック取得の後に置く**: 保護対象外であることと「取得の前に呼ばなければ
   ならない」ことは別であり、後ろに置くほうが受入基準16 に対して安全側で、かつ両 OS で
   同じタイミングになる。
5. `ensure_project_config`(畳み込み)で `.claude-dev.yaml` が無ければ用意する。TTY なら
   `MODULE-cli-common-select-ssh-keys` を呼び、非 TTY なら
   `MODULE-cli-common-write-project-ssh-keys` で空の `ssh_keys:` を書く。
6. フラグを解析する(`--no-vnc` / `--kvm` / `--vm` / `--vm-fresh`。`--vm` 系は `--kvm` を含意し、
   `/dev/kvm` が無ければ `exit 1`)。**macOS 版は `--kvm` / `--vm` / `--vm-fresh` を
   `require_setup` より前に早期拒否して `exit 1` する**。
7. `MODULE-cli-common-is-running` が真なら再接続経路へ入る: 使用中イメージのバージョンと
   `MODULE-cli-common-get-novnc-url` の URL を表示し、`tmux has-session -t main` が無ければ作成し、
   `CLAUDE_DEV_NO_ATTACH != 1` のとき `tmux attach` する(`--vm-fresh` は稼働中は無効と警告)。
8. `MODULE-cli-common-container-exists` が真で、**かつ `MODULE-cli-common-is-running` が偽**のとき
   だけ、その停止中の残骸を削除する(手順7 の判定から本手順までの間に他プロセスが同名コンテナを
   起動していた場合に、稼働中のものを消さないための再確認である。**手順4 のロックは同じ CLI
   同士の競合しか防げず、利用者が直接 `docker run` する経路は防げない**ため、この再確認は残す)。
   そのうえで `MODULE-cli-common-ensure-infrastructure` を呼び、VNC 有無でイメージを選ぶ。
9. **認証コピー**: `MODULE-cli-common-lock` で**共有資源単位**のロック(キー `shared`、操作名
   `start`)を取り、その中で一時コンテナにより `claude-dev-auth`(RO)から
   `${PROJECT_DIR}/.claude/` へコピーし、ホストの UID/GID に `chown` する。同じ一時コンテナに
   `${PROJECT_DIR}/.codex` を `/target-codex` としてマウントし、`/auth/codex/auth.json` があれば
   `/target-codex/auth.json` へコピーして同じ `chown -R` に含める(無ければ何もしない = 未ログインの
   まま起動できる)。**共有資源単位のロックは手順15(コンテナ作成の確定)まで保持する**(プロジェクト単位も保持する)。
   認証コピーの直後に離すと、起動したコンテナの entrypoint が 30 秒ごとに認証を共有ボリュームへ
   書き戻すため(`FR-env-03` 受入基準3・8)、**`logout` が完走した直後に作られたコンテナが認証を
   書き戻して `logout` が静かに巻き戻る**。あわせて手順13 の `ensure_docker_proxy_container` も
   この区間に入るので、`stop` の遊休判定との競合も同じロックで防げる(契約の「排他(ロックキー)」)。
   ロックが取れなければ、`logout` / `reset` が同時に走っていることを表示して非0で終わる
   (**認証が空のまま起動することを防ぐ**。`docs/issues/020`)。
10. **ホスト設定抽出**: `~/.claude/settings.json` から `jq` で `{hooks, env}`(null 除外)を
    `.claude/host-hooks.json` へ書き出す(entrypoint がマージする)。
11. **ユーザー hook**: `~/.local/bin/` が非空なら `.claude/host-local-bin/` へコピーする。
12. **.gitignore 追記**: `.claude` と `.codex` について、`<name>` も `<name>/` も未記載のものだけ
    追記する(冪等)。`.git` があり `.gitignore` が無ければ2行で新規作成する。
13. **マウント/オプション組立**: `GITCONFIG_OPT`(`~/.gitconfig` RO)、`GH_CONFIG_OPT`
    (`~/.config/gh` RO)、`DOCKER_OPTS`(ソケットがあれば `ensure_docker_proxy_container` を
    呼んだうえで `DOCKER_HOST=tcp://claude-dev-docker-proxy:2375`。この過程で
    `MODULE-cli-common-container-exists` / `MODULE-cli-common-image-exists` /
    `MODULE-cli-common-is-running` を使う)、`COMPOSE_OPTS`(**`COMPOSE_PROJECT_NAME` を
    「`NAME` を compose 互換名へ正規化した値」+ `-` + 「`PROJECT_DIR` の SHA-256 先頭6桁」** にして
    `-e` で付与。契約 `CTR-cli-container` の「compose 資源の識別」。`stop` が同じ関数で再計算する)、**管理ラベル3つ**(契約 `CTR-cli-container` が定める
    `claude-dev.managed=1` / `claude-dev.role=claude` / `claude-dev.project-dir=${PROJECT_DIR}`。
    **他のオプションと違い変数にまとめず、`docker run` の引数として引用付きで直接渡す** —
    `project-dir` の値は利用者のパスでありスペースを含みうるので、`$VAR` で展開すると
    語分割されてラベルが壊れるため)、`SSH_OPTS`(Linux: `ensure_ssh_agent` の専用 agent
    ソケットを `/tmp/ssh-agent.sock` へ RO 転送し `SSH_AUTH_SOCK` を設定 / macOS:
    `ensure_dedicated_agent` と `ensure_ssh_bridge` で socat TCP ブリッジを立て
    `-e CLAUDE_DEV_SSH_BRIDGE_PORT=<port>` を付与。いずれも `known_hosts` RO、`~/.ssh/config` は
    `IdentityFile` / `IdentitiesOnly` / `IdentityAgent` 行を `sed` 除去した一時コピーを RO)、
    `NOVNC_PORT_OPT`(VNC 時のみ空きポートで `-p <port>:6080` とコンテナ別 Chrome ボリューム)、
    `KVM_OPTS` / `VM_OPTS`(Linux の `--kvm` / `--vm` 時のみ)。
14. **起動**: イメージ名とバージョンを表示し、`docker run -d --cap-add NET_ADMIN,NET_RAW
    --restart unless-stopped` に `/workspace`・各ボリューム・`tmux.conf` / `CLAUDE.md` の RO マウント・
    **管理ラベル3つ**・上記オプション・`NODE_OPTIONS=--max-old-space-size=4096`・`-t` を付けて実行する。
    **`--security-opt` は付けない**(Docker 既定の seccomp と `docker-default` AppArmor を有効なまま使う)。
    **`ensure_docker_proxy_container` が docker-proxy を作るときはラベルを付けない**
    (固定名 `claude-dev-docker-proxy` で識別できるため。契約の「識別の手段は資源ごとに違う」)。
    **共有資源単位のロックは手順15 の再試行ループを抜けたところ**(コンテナが作られた、または
    失敗が確定した時点)**で解放する**(プロジェクト単位は手順17 まで保持する)。
    再試行の途中で離すと、次の試行で作られるコンテナが保護の外に出る。
15. **失敗時の後片付けとリトライ**: `docker run` が失敗したとき、後片付けは次の2条件を**両方**
    満たすときだけ行う。
    - エラーが**名前衝突ではない**(`docker run` の出力が同名コンテナの使用中を示していない)
    - 対象コンテナが**稼働中でない**(`MODULE-cli-common-is-running` が偽)

    判定の順序は「**名前衝突か** → 稼働中か」である。**名前衝突のときは何も削除せず**、
    対象が稼働中かで文面を分けて stderr へ出し、再試行せずに `exit 1` する。
    - 稼働中: 同名コンテナが稼働中である旨 / **管理ラベル `claude-dev.project-dir` があれば
      その値(そのコンテナがどのホスト側ディレクトリで起動されたか)を表示し、無ければ
      別ディレクトリの同名プロジェクトである可能性を表示** / **既存のコンテナに手を触れていないこと** /
      そのプロジェクトのディレクトリで `start` すれば再接続できること / このディレクトリで
      起動したいなら先に `stop <name>` すること
    - 停止中(判定の窓の中で他プロセスが作りかけた場合): 同名コンテナが停止状態で存在する旨と
      `stop <name>` で削除してから再実行すること

    名前衝突でなく、かつ対象が稼働中でないときだけ作りかけのコンテナを `docker rm -f` し、
    エラーがポート競合かつ VNC 有効なら別ポートを取り直して最大20回再試行する。
    他の失敗または上限超過も stderr へ出して `exit 1`。
16. tmux の起動を待ち(通常30秒 / VM は420秒で15秒ごとに進捗表示)、noVNC URL を表示し、
    `CLAUDE_DEV_NO_ATTACH != 1` なら `tmux attach -t main` する。上限を超えても終了せず状況を案内して
    `exit 0`(コンテナは `--restart unless-stopped` で稼働を続ける)。
17. **`tmux attach` の前にプロジェクト単位のロックを解放する**(アタッチは利用者の対話であり、
    その間ロックを保持すると `stop` が実行できなくなる。`trap` で解放されるが、アタッチは
    プロセスが生きたまま長時間続くため明示的に解放する)。

## 呼び出され方

- 契機: 利用者が `claude-dev start [--no-vnc] [--kvm] [--vm] [--vm-fresh]` を実行したとき。
  `MODULE-cli-orchestrate` も未起動時に `CLAUDE_DEV_NO_ATTACH=1` を付けて本機能を再帰的に呼ぶ。
- 前提条件: カレントディレクトリが対象プロジェクトであること。`docker` / `jq`(macOS は `socat` も)が
  導入済みであること。
- 引数(**フラグは `case` の1回走査で解釈し、順序は結果に影響しない**):

| 引数 | 型 | 必須 | 実装が行う検証 | 受理/拒否と結果 |
|---|---|---|---|---|
| `--no-vnc` | フラグ | 任意 | なし | VNC/Chrome 無しの軽量イメージで起動する |
| `--kvm` | フラグ | 任意 | `/dev/kvm` の存在 | 実在するデバイスだけを渡す。`/dev/kvm` が無ければ**警告して続行** |
| `--vm` | フラグ | 任意 | `/dev/kvm` の存在 | `--kvm` を含意する。`/dev/kvm` が無ければ**中止して終了コード 1**(TCG では実用にならないため) |
| `--vm-fresh` | フラグ | 任意 | 同上 | `--vm` を含意し、ゲスト用ボリュームを破棄してから作成する。**稼働中コンテナには効かず警告のみ** |
| **未知の引数**(`--foo` / 位置引数) | — | — | **検証しない** | **黙って無視する**(エラーにも警告にもならない) |
| **同じフラグの重複**(`--vm --vm`) | — | — | — | 同じ変数へ再代入するだけで**結果は1回指定と同じ** |
| **`--no-vnc` と `--vm` の併用** | — | — | — | **両方効く**(VNC 無しの VM モード。排他ではない) |
| macOS で `--kvm` / `--vm` / `--vm-fresh` | — | — | 早期に拒否 | 非対応の理由を表示して**終了コード 1**(イメージビルドより前) |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

### MODULE-cli-common-lock

- 何のために呼ぶか: `stop` との競合(起動直後のコンテナが消される)を防ぐためにプロジェクト単位を
  手順4 で、`logout` / `reset` との競合(**認証が空のまま起動する**。`docs/issues/020`)を防ぐために
  共有資源単位を手順9〜15(認証コピーの開始からコンテナ作成の確定まで。再試行を含む)で取る。
- 何を渡すか: キー(`NAME` / `shared`)と操作名 `start`。
- 何を受け取るか: 終了ステータス。
- **失敗したときどうなるか**: **プロジェクト単位が取れなければ手順5 以降の生成物と Docker コンテナを
  一切作らずに非0で終わる**(手順2 の `require_setup` によるイメージのビルドはロックの保護対象外で、
  既に済んでいることがある)。共有資源単位が取れなければ、`logout` / `reset` が同時に走っていることを
  表示して非0で終わる(認証が空のコンテナを作らないため、ここでは続行しない)。

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
  `docker run` が失敗するが、**名前衝突では既存コンテナを削除しない**(手順15 の判定順が
  「名前衝突か → 稼働中か」であり、名前衝突なら何も削除せず再試行もせずに `exit 1`。
  `FR-env-01` 受入基準12・13)。**判定が失敗しても稼働中のコンテナが消される経路は無い。**

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
| 戻り値 | 0(tmux 待ちタイムアウトでも 0)。前提不足・KVM 不在・リトライ上限超過・**同名コンテナとの衝突**・**ロックを取得できない**場合は 1 |
| 永続化 | コンテナ `<name>`(**管理ラベル `claude-dev.managed=1` / `claude-dev.role=claude` / `claude-dev.project-dir=<起動ディレクトリの絶対パス>` 付き**)。`${PROJECT_DIR}/.claude/`(認証・`host-hooks.json`・`host-local-bin/`)、`${PROJECT_DIR}/.codex/auth.json`、`${PROJECT_DIR}/.gitignore` への追記、`${PROJECT_DIR}/.claude-dev.yaml`。docker volume `claude-dev-auth` / `claude-dev-history` / `claude-dev-config` / `claude-dev-chrome-<name>` / (VM 時)`claude-dev-vm-<name>`。**ロックのシンボリックリンク `${HOME}/.claude-dev/locks/<name>.lock` と `shared.lock` を作成・削除する**。macOS では `~/.claude-dev/agents/<name>.{sock,pid,bridge.pid,bridge.port}`。**docker-proxy にはラベルを付けない** |
| 発火するイベント | なし |
| ログ | 標準出力へイメージ名・バージョン・noVNC URL・進捗。失敗とロックの取得失敗・残骸の引き継ぎは stderr |

### 副作用の順序と、途中で失敗したときに残るもの

**トランザクションは無い。** スクリプトは `set -e`(`claude-dev:8`)で走るため、下表のいずれかで
失敗するとその時点で終了し、**それまでの副作用は残ったまま**になる。取り消し処理は無い。
**ただしロックだけは `trap` が必ず解放する。**

| # | 副作用 | 失敗したときに残るもの | 再実行での回復 |
|---|---|---|---|
| 1 | **プロジェクト単位のロックの取得**(手順3) | シンボリックリンク1本。`trap` が解放する | 取れなければ以降の副作用は1つも起きない |
| 2 | `require_setup` によるイメージのビルド(手順4) | ビルド済みのイメージ(冪等に作られる共有資源) | 既にあれば何も起きない |
| 3 | `.claude-dev.yaml` の作成(無いときだけ) | 作られたファイル | 既にあれば作り直さない |
| 4 | 停止中の同名コンテナの削除(**稼働中なら削除しない**) | 削除済みの状態。稼働中だった場合は何も変わらない | 影響なし |
| 5 | ネットワーク・共有ボリュームの作成 | 作られた資源(他プロジェクトと共有) | すべて `\|\| true` で握られ、再実行しても増えない |
| 6 | **共有資源単位のロックの取得**(手順9) | シンボリックリンク1本。`trap` が解放する | 取れなければ認証コピー以降は1つも起きない |
| 7 | `${PROJECT_DIR}/.claude` と `.codex` の作成 + 認証コピー(一時コンテナ) | 空または部分的な作業用ディレクトリ | `mkdir -p` と `cp` なので**再実行で上書きされる** |
| 8 | `host-hooks.json` の書き出し | 書き出されたファイル | 毎回書き直す |
| 9 | `host-local-bin/` へのコピー | コピー済みのファイル | 毎回 `cp -a` で上書きする。**ホスト側で消したファイルは残り続ける**(同期ではない) |
| 10 | `.gitignore` への追記 | 追記済みの行 | 既に記載があれば追記しない(冪等) |
| 11 | `~/.ssh/config` の一時コピー作成(`mktemp`) | `/tmp/claude-dev-ssh-config.XXXXXX` が残る | **削除しない。実行のたびに1つ増える** |
| 12 | macOS の専用 agent / TCP ブリッジ起動 | プロセスと `~/.claude-dev/agents/<name>.*` | 既存を再利用する |
| 13 | `docker run`(コンテナ作成。**管理ラベル3つ付き**) | 失敗時は作りかけを `docker rm -f` する。**名前衝突のときは何も削除せず、稼働中のコンテナも削除しない** | 再試行またはやり直しで作られる。残った停止中コンテナは次回の手順8 が消す |
| 14 | コンテナ内の初期化(entrypoint) | 起動済みのコンテナ | `--restart unless-stopped` で残る。再実行は再接続経路に入る |

**回復点は「もう一度 `claude-dev start` を実行すること」**である。手順はいずれも再入可能で、
稼働中なら再接続経路(手順7)に入るため二重にコンテナを作らない。

### 並行性

**2段のロックで直列化する**(`CTR-cli-container` の「排他(ロックキー)」)。プロジェクト単位は
全区間、共有資源単位は認証コピーからコンテナ作成の確定まで。**待たない**ので、取得できなければ
理由を表示して終了コード 1 で終わる。**別プロジェクトの `start` 同士は直列化しない**
(プロジェクト単位のキーが異なるため。`NFR-scale-01`)。

| 同時に起きること | 実際の結果 |
|---|---|
| **同じ**ディレクトリで `start` を2つ(または basename が同じ別ディレクトリ) | **後発はプロジェクト単位のロックを取得できず、`.claude-dev.yaml` すら作らずに終了コード 1 で終わる**。ロックを取れた側だけが進む |
| **別**のディレクトリで `start` を2つ | コンテナ名・compose プロジェクト名・Chrome ボリュームが別で、**ロックのキーも別**なので独立に成功する。**直列化されるのは共有資源単位のキーを取る区間(認証コピー〜コンテナ作成の確定)だけ**。もう一つの競合点は noVNC の空きポート選定で、これはポート競合の再試行(最大20回)で吸収する |
| `start` と `stop` が同時 | **同じキーのロックで直列化される**。後発は取得できずに終了コード 1。**起動直後のコンテナが消える経路は閉じた** |
| `start` と `reset` / `logout` / `login` が同時 | **共有資源単位のキーで直列化される**。`start` は認証コピーの手前で取得を試み、取れなければ**認証が空のコンテナを作らずに**終了コード 1 で終わる(`docs/issues/020`) |
| 別プロジェクトの `start` と共有インフラの作成が同時 | ネットワーク・ボリュームの作成はすべて `\|\| true` で握るため、どちらが作っても問題にならない(**ロックの保護対象外**) |
| 利用者が直接 `docker run` / `docker start` する | **保護されない**。そのため手順8 の「稼働中でないことの再確認」を二重の防護として残している |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| `docker` / `jq`(macOS は `socat`)が無い | 不足を列挙して導入案内を出し `exit 1` | 起動しない |
| **プロジェクト単位のロックを取得できない** | 保持している操作名と PID、再実行の方法を stderr へ出し、**`.claude-dev.yaml` の生成を含む一切の生成物を作らずに** `exit 1`。**`require_setup` によるイメージのビルドだけはロックの保護対象外**なので、既に済んでいることがある | 二重 `start` と `stop` との競合を防ぐ(`FR-env-01` 受入基準16) |
| **共有資源単位のロックを取得できない**(認証コピーの直前) | `logout` / `reset` / `login` が同時に走っていることを stderr へ出して `exit 1`。**認証コピーもコンテナ作成も行わない** | **認証が空のままコンテナが起動することを防ぐ**(`docs/issues/020`) |
| **ロックが存在しないプロセスに保持されたまま残っている** | 引き継いだ旨を stderr へ出して処理を続行する | 永久に取得できない状態にならない(受入基準17) |
| `.claude-dev.yaml` が無い | TTY なら鍵選択、非 TTY なら空作成。停止しない | SSH 転送なしで起動しうる |
| SSH 鍵が0件、または指定鍵が存在しない | 転送なしで続行し、`ssh_keys:` の記述方法を案内する。欠落鍵は警告してスキップ | コンテナ内で SSH が使えない |
| agent ソケットのパスがソケットでない残骸 | `rm -rf` で自己修復。消せなければ**停止せず** `sudo rm -rf` を案内し SSH 転送なしで続行する | 起動は成功する |
| **認証コピーの一時コンテナが失敗した** | `set -e` によりその場で非0終了する。`${PROJECT_DIR}/.claude` と `.codex` は作られたまま残る。**`trap` がロックを解放する** | 起動しない。再実行で回復する |
| 共有ボリュームに認証が無い | 何もコピーせず先へ進む(`[ -f ... ] &&` で分岐) | 未ログインのまま起動する |
| `~/.claude/settings.json` が無い / `jq` の解析に失敗 | `host-hooks.json` を書かずに続行する(`2>/dev/null` と非空判定で握る) | hooks / env の引き継ぎだけが行われない |
| noVNC ポート競合 | **稼働中でない**作成途中のコンテナだけを掃除し、別ポートで最大20回再試行する。**共有資源単位のロックは再試行ループを抜けるまで保持する**(途中で離すと次の試行で作られるコンテナが保護の外に出る) | 割り当てポートが 6080 以外になる |
| **同名コンテナが競合で作られた(手順7 の判定後に他プロセスが作った)** | エラー文言が `Conflict.` / `already in use by container` に一致するので**再試行せず**、**既存コンテナを削除せずに** `exit 1`。文面は対象が稼働中か停止中かで分ける。**稼働中で管理ラベル `claude-dev.project-dir` を持つ場合は、可能性ではなく「どのディレクトリで起動されたか」という事実を表示する** | **一方の `start` だけが成功し、そのコンテナは失われない** |
| リトライ上限を超えた/ポート競合以外の失敗 | stderr にエラーを出して `exit 1` | 起動しない |
| tmux 起動タイムアウト(通常30秒 / VM 420秒) | 終了せず状況を案内して `exit 0`。コンテナは稼働を続ける | 再 `start` の attach 経路で接続できる |
| `--vm` 指定で `/dev/kvm` が無い(Linux) | `exit 1`(`--kvm` のみなら警告して続行)。**ロックを取った直後だが `trap` が即座に解放する** | 起動しない |
| **`--kvm` / `--vm` / `--vm-fresh` を macOS で指定した** | 早期に拒否して `exit 1`。**ロックは取得済みだが副作用は何も起きておらず `trap` が解放する** | 起動しない |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | `--security-opt` を付けない(Docker 既定の confinement を維持する)。この下では codex の bubblewrap サンドボックスが動かないが、対処はコンテナ側を緩めるのではなく codex 側の無効化で行う | D0-sec-01 |
| 2 | 認証は symlink ではなくコピーで渡し、書き戻しは entrypoint のバックグラウンド同期に任せる | D0-auth-02 |
| 3 | `COMPOSE_PROJECT_NAME` を `-e` で渡す(全プロジェクトが `/workspace` にマウントされ compose 既定名 `workspace` が衝突するのを防ぐ。`-e` なら対話・非対話シェルと `docker exec` の全てで有効)。**値に起動ディレクトリの絶対パスのハッシュ短縮値を足して一意化する**(`DSN-env-03`)。ハッシュの計算は Linux が `sha256sum`、macOS が `shasum -a 256` で同じ値になることを確かめる。**一意化名を作る関数を1つに集約し、`stop` と共有する**(その関数は正規化の前に小文字化も行う。`MODULE-cli-stop` 判断13) | D0-scope-02 / `DSN-env-03` / D0-scope-03 |
| 4 | ホストの `~/.ssh/config` はそのまま渡さず、`IdentityFile` / `IdentitiesOnly` / `IdentityAgent` を除去した一時コピーを RO マウントする | D0-sec-02 |
| 5 | **後片付けの対象を絞る手段として管理ラベルを導入する**(`D0-env-08` の決定に従う)。付けるのは **Claude コンテナだけ**で、docker-proxy と `fwd-*` には付けない(固定名・固定接頭辞で識別できるため)。**この判断は 2026-08-04 より前の「ラベルを導入しない」という判断を撤回したものである**(当時は `FR-env-01` 受入基準12・13 を満たすのにラベルが要らなかったが、`docs/issues/024` / `029` / `045` を閉じるには所有権の印が要る) | D0-env-10 |
| 6 | 手順8(停止中の残骸の削除)の稼働中判定は、ロックを入れても**残す**。ロックはホスト CLI のプロセス間だけで有効で、利用者が直接 `docker run` / `docker start` する経路は防げないため、二重の防護として維持する | D0-scope-02 |
| 7 | 名前衝突の判定と後片付けの限定を Linux 版・macOS 版の**両方に同じ形で**入れる(同じサブコマンドの成否・出力を OS で変えないため) | D0-scope-03 |
| 8 | 名前衝突時のメッセージを**対象が稼働中か停止中かで分ける**。稼働中の場合は、管理ラベル `claude-dev.project-dir` があれば**推測ではなく事実**(どのディレクトリで起動されたか)を示す。ラベルが無い既存コンテナには従来どおり可能性として示す | D0-scope-02 / D0-env-10(表示内容の要件は `FR-env-01` 受入基準12 と `02-design/logging.md` が定める) |
| 9 | **共有資源単位のロックを「認証コピーの開始からコンテナ作成の確定まで」保持する**(手順9〜15。**手順15 の再試行ループを含む** — 途中で離すと次の試行で作られるコンテナが保護の外に出る)。認証コピーの直後に離すと、(a) `logout` の完走直後に作られたコンテナの同期ループが認証を書き戻して **`logout` が静かに巻き戻る**、(b) 手順13 の `ensure_docker_proxy_container` が `stop` の遊休判定と競合する。守るべきものは「共有ボリュームの内容」だけでなく**「それを読んで作られたコンテナ」**まで含む。**`start` の全区間で保持はしない**(手順1〜8 と手順16 以降を含めると別プロジェクトの `start` が互いに待ち `NFR-scale-01` を損なう) | D0-env-09 / 契約「排他(ロックキー)」 |
| 10 | **プロジェクト単位のロックは `tmux attach` の前に解放する**(手順17)。アタッチ中は利用者が端末を占有しており、その間 `stop` が「ロックが取れない」で失敗すると、利用者は自分のセッションを止められなくなる | D0-env-09(制約「ロック待ちで固まらない」の趣旨) |
| 11 | ロックの取得を**コンテナ名が確定した直後・最初の副作用より前**(手順4)に置く。キーがコンテナ名なので名前の確定より前には取れず、`.claude-dev.yaml` の生成(手順5)が最初の副作用であるため、その間が唯一の位置である。**`--vm` 指定かつ `/dev/kvm` 不在の失敗経路(手順6)はロックを取った直後に終わるが、`trap` が即座に解放する**。**macOS 版の `--kvm` / `--vm` 早期拒否も同じ扱いになる**: macOS 版はフラグ解析が `ensure_project_config` より後にあるため、ロックは早期拒否より前に取られる。副作用は何も起きておらず `trap` が解放するので害は無く、むしろロックが取れないときに `require_setup` のイメージビルドも走らない分だけ受入基準16 に対して安全側である | D0-env-09 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| **コンテナ名が起動ディレクトリ名から決まるため一意でない** | 別ディレクトリの同名プロジェクトと衝突する。**管理ラベル `claude-dev.project-dir` により、衝突時にどのディレクトリのものかを事実として示せるようになった**が、名前の一意性自体は未解決 | `docs/issues/028` |
| **compose 一意化名のハッシュ衝突を検出しない** | 異なる絶対パスの先頭6桁が一致すると、一方の `stop` が他方の compose 資源を削除しうる | `docs/pendings.md` **P-005** |
| **ロックはホスト CLI のプロセス間でしか有効でない** | 利用者が直接 `docker run` / `docker start` する経路は防げない。そのため手順8 の「稼働中でないことの再確認」を二重の防護として残している | なし(契約 `CTR-cli-container`「ロックが守れない範囲」が明示) |
| **プロジェクト単位のロックを `tmux attach` の前に解放する** | アタッチ中は排他が効かないので、別プロセスの `stop` が走りうる | なし(閾値の外: アタッチ中も保持すると利用者が自分のセッションを止められなくなる。`MODULE-cli-start` 判断10) |
| **共有資源単位のロックは `start` の全区間では保持しない** | 手順1〜8 と手順16 以降は保護されない | なし(閾値の外: 全区間で保持すると別プロジェクトの `start` が互いに待ち `NFR-scale-01`(5プロジェクト同時起動)を損なう。判断9) |
| **`MODULE-cli-common-lock` を含めた呼び出し先が 13 件になった** | `relations-query.py --health` の「呼び出し先が多い機能(> 7)」に載る | なし(閾値の外: 分割は 02 の分割定義の見直し事項であり、本タスクでは行わない) |

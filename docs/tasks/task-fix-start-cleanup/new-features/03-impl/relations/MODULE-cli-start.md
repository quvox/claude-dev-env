---
target: docs/03-impl/relations/MODULE-cli-start.md
change: replace
sections:
  - "## 処理の流れ"
  - "## 戻り値・副作用"
  - "## 異常系"
  - "## 実装上の判断"
  - "## 既知の制限"
deletes: []
reason: FR-env-01 受入基準12・13(docs/issues/036)。後片付けの条件が変わるため、処理の流れ 手順7・14、副作用の順序 #2・#10、並行性の1行目、異常系2行、既知の制限の排他行を修正後の事実へ更新する
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
updated: 2026-08-04
summary: カレントディレクトリで開発コンテナを起動する(VNC+Chrome が既定)
---

<!-- 変更指示(relations は frontmatter を持つ例外形。.claude/directions/change-set.md 例外2)。
     frontmatter の relations フィールドは**現行から変わらない**(新しい関数を作らず、
     既存の is_running と docker run のエラー文言で判定するため callees も増えない)。
     /task-close はコードから再生成して照合する。 -->

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
7. `MODULE-cli-common-container-exists` が真で、**かつ `MODULE-cli-common-is-running` が偽**のとき
   だけ、その停止中の残骸を削除する(手順6 の判定から本手順までの間に他プロセスが同名コンテナを
   起動していた場合に、稼働中のものを消さないための再確認である)。
   そのうえで `MODULE-cli-common-ensure-infrastructure` を呼び、VNC 有無でイメージを選ぶ。
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
14. **失敗時の後片付けとリトライ**: `docker run` が失敗したとき、後片付けは次の2条件を**両方**
    満たすときだけ行う。
    - エラーが**名前衝突ではない**(`docker run` の出力が同名コンテナの使用中を示していない)
    - 対象コンテナが**稼働中でない**(`MODULE-cli-common-is-running` が偽)

    判定の順序は「**名前衝突か** → 稼働中か」である。**名前衝突のときは何も削除せず**、
    対象が稼働中かで文面を分けて stderr へ出し、再試行せずに `exit 1` する。
    - 稼働中: 同名コンテナが稼働中である旨 / **別ディレクトリの同名プロジェクトである可能性** /
      **既存のコンテナに手を触れていないこと** / そのプロジェクトのディレクトリで `start` すれば
      再接続できること / このディレクトリで起動したいなら先に `stop <name>` すること
    - 停止中(判定の窓の中で他プロセスが作りかけた場合): 同名コンテナが停止状態で存在する旨と
      `stop <name>` で削除してから再実行すること

    名前衝突でなく、かつ対象が稼働中でないときだけ作りかけのコンテナを `docker rm -f` し、
    エラーがポート競合かつ VNC 有効なら別ポートを取り直して最大20回再試行する。
    他の失敗または上限超過も stderr へ出して `exit 1`。
15. tmux の起動を待ち(通常30秒 / VM は420秒で15秒ごとに進捗表示)、noVNC URL を表示し、
    `CLAUDE_DEV_NO_ATTACH != 1` なら `tmux attach -t main` する。上限を超えても終了せず状況を案内して
    `exit 0`(コンテナは `--restart unless-stopped` で稼働を続ける)。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 0(tmux 待ちタイムアウトでも 0)。前提不足・KVM 不在・リトライ上限超過・**同名コンテナとの衝突**は 1 |
| 永続化 | コンテナ `<name>`。`${PROJECT_DIR}/.claude/`(認証・`host-hooks.json`・`host-local-bin/`)、`${PROJECT_DIR}/.codex/auth.json`、`${PROJECT_DIR}/.gitignore` への追記、`${PROJECT_DIR}/.claude-dev.yaml`。docker volume `claude-dev-auth` / `claude-dev-history` / `claude-dev-config` / `claude-dev-chrome-<name>` / (VM 時)`claude-dev-vm-<name>`。macOS では `~/.claude-dev/agents/<name>.{sock,pid,bridge.pid,bridge.port}` |
| 発火するイベント | なし |
| ログ | 標準出力へイメージ名・バージョン・noVNC URL・進捗。失敗は stderr |

### 副作用の順序と、途中で失敗したときに残るもの

**トランザクションは無い。** スクリプトは `set -e`(`claude-dev:8`)で走るため、下表のいずれかで
失敗するとその時点で終了し、**それまでの副作用は残ったまま**になる。取り消し処理は無い。

| # | 副作用 | 失敗したときに残るもの | 再実行での回復 |
|---|---|---|---|
| 1 | `.claude-dev.yaml` の作成(無いときだけ) | 作られたファイル | 既にあれば作り直さない |
| 2 | 停止中の同名コンテナの削除(**稼働中なら削除しない**) | 削除済みの状態。稼働中だった場合は何も変わらない | 影響なし |
| 3 | ネットワーク・共有ボリュームの作成 | 作られた資源(他プロジェクトと共有) | すべて `\|\| true` で握られ、再実行しても増えない |
| 4 | `${PROJECT_DIR}/.claude` と `.codex` の作成 + 認証コピー(一時コンテナ) | 空または部分的な作業用ディレクトリ | `mkdir -p` と `cp` なので**再実行で上書きされる** |
| 5 | `host-hooks.json` の書き出し | 書き出されたファイル | 毎回書き直す |
| 6 | `host-local-bin/` へのコピー | コピー済みのファイル | 毎回 `cp -a` で上書きする。**ホスト側で消したファイルは残り続ける**(同期ではない) |
| 7 | `.gitignore` への追記 | 追記済みの行 | 既に記載があれば追記しない(冪等) |
| 8 | `~/.ssh/config` の一時コピー作成(`mktemp`) | `/tmp/claude-dev-ssh-config.XXXXXX` が残る | **削除しない。実行のたびに1つ増える** |
| 9 | macOS の専用 agent / TCP ブリッジ起動 | プロセスと `~/.claude-dev/agents/<name>.*` | 既存を再利用する |
| 10 | `docker run`(コンテナ作成) | 失敗時は作りかけを `docker rm -f` する。**名前衝突のときは何も削除せず、稼働中のコンテナも削除しない**(その場合は作りかけの停止中コンテナが残りうる) | 再試行またはやり直しで作られる。残った停止中コンテナは次回の手順7 が消す |
| 11 | コンテナ内の初期化(entrypoint) | 起動済みのコンテナ | `--restart unless-stopped` で残る。再実行は再接続経路に入る |

**回復点は「もう一度 `claude-dev start` を実行すること」**である。手順 1〜9 はいずれも再入可能で、
稼働中なら再接続経路(手順 6)に入るため二重にコンテナを作らない。**手動での後片付けが要るのは
手順 8 の一時ファイルだけ**である。

### 並行性

**排他機構(ロックファイル等)を一切持たない。** 同時実行の結果は次のとおり。

| 同時に起きること | 実際の結果 |
|---|---|
| **同じ**ディレクトリで `start` を2つ(または basename が同じ別ディレクトリ) | どちらも同じコンテナ名を使う。**後から始めた側が手順6 の稼働判定に達した時点で相手のコンテナが既に稼働していれば、再接続経路に入って `exit 0` する**(衝突しない。別ディレクトリでも同じコンテナへ繋がる = `docs/issues/028`)。**両者が手順6 を通り抜けたあと**(手順7〜12 の数秒の窓)に一方が先に `docker run` を終えた場合だけ、もう一方が名前衝突で失敗する(ポート競合の文言に当たらないので再試行しない)。**失敗した側は何も削除せず**、同名のコンテナが稼働中である旨を表示して `exit 1` するので、**先に成功した側の稼働中コンテナはそのまま残る**。手順 4〜9 のファイル操作は両者が同じパスへ書くため、内容は後勝ちになる |
| **別**のディレクトリで `start` を2つ | コンテナ名・compose プロジェクト名・Chrome ボリュームが別なので独立に成功する。**唯一の競合点は noVNC の空きポート選定**で、これはポート競合の再試行(最大20回)で吸収する |
| `start` と `stop` が同時 | 保護は無い。`stop` が先に走ると起動直後のコンテナが消える。逆順ならコンテナは残る |
| `start` と `reset` / `logout` が同時 | 保護は無い。`reset` / `logout` は稼働中コンテナを問答無用で削除し、共有ボリュームを空にする。`start` の手順 4(認証コピー)と重なると**認証が空のまま起動する** |
| 別プロジェクトの `start` と共有インフラの作成が同時 | ネットワーク・ボリュームの作成はすべて `\|\| true` で握るため、どちらが作っても問題にならない |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| `docker` / `jq`(macOS は `socat`)が無い | 不足を列挙して導入案内を出し `exit 1` | 起動しない |
| `.claude-dev.yaml` が無い | TTY なら鍵選択、非 TTY なら空作成。停止しない | SSH 転送なしで起動しうる |
| SSH 鍵が0件、または指定鍵が存在しない | 転送なしで続行し、`ssh_keys:` の記述方法を案内する。欠落鍵は警告してスキップ | コンテナ内で SSH が使えない |
| agent ソケットのパスがソケットでない残骸 | `rm -rf` で自己修復。消せなければ**停止せず** `sudo rm -rf` を案内し SSH 転送なしで続行する | 起動は成功する |
| **認証コピーの一時コンテナが失敗した** | `set -e` によりその場で非0終了する。`${PROJECT_DIR}/.claude` と `.codex` は作られたまま残る | 起動しない。再実行で回復する |
| 共有ボリュームに認証が無い | 何もコピーせず先へ進む(`[ -f ... ] &&` で分岐) | 未ログインのまま起動する |
| `~/.claude/settings.json` が無い / `jq` の解析に失敗 | `host-hooks.json` を書かずに続行する(`2>/dev/null` と非空判定で握る) | hooks / env の引き継ぎだけが行われない |
| noVNC ポート競合 | **稼働中でない**作成途中のコンテナだけを掃除し、別ポートで最大20回再試行する | 割り当てポートが 6080 以外になる |
| **同名コンテナが競合で作られた(手順6 の判定後に他プロセスが作った)** | エラー文言が `Conflict.` / `already in use by container` に一致するので**再試行せず**、**既存コンテナを削除せずに** `exit 1`。文面は対象が稼働中か停止中かで分ける(稼働中なら別ディレクトリの同名プロジェクトである可能性と、既存に手を触れていないことを明示する) | **一方の `start` だけが成功し、そのコンテナは失われない** |
| リトライ上限を超えた/ポート競合以外の失敗 | stderr にエラーを出して `exit 1` | 起動しない |
| tmux 起動タイムアウト(通常30秒 / VM 420秒) | 終了せず状況を案内して `exit 0`。コンテナは稼働を続ける | 再 `start` の attach 経路で接続できる |
| `--vm` 指定で `/dev/kvm` が無い(Linux) | `exit 1`(`--kvm` のみなら警告して続行) | 起動しない |
| `--kvm` / `--vm` / `--vm-fresh` 指定(macOS) | 非対応の理由を表示して `exit 1`(イメージビルドより前) | 起動しない |
| Docker ソケットが無い(macOS の `detect_docker_sock` が空) | docker-proxy を起動せず `DOCKER_HOST` を付けずに続行する | コンテナ内から Docker が使えない |
| VM モードでゲスト VM の起動に失敗した | entrypoint が警告を出し**VM 無しで続行する**(コンテナ起動は成功扱い) | `docker` は既定の proxy 経路のまま |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | `--security-opt` を付けない(Docker 既定の confinement を維持する)。この下では codex の bubblewrap サンドボックスが動かないが、対処はコンテナ側を緩めるのではなく codex 側の無効化で行う | D0-sec-01 |
| 2 | 認証は symlink ではなくコピーで渡し、書き戻しは entrypoint のバックグラウンド同期に任せる | D0-auth-02 |
| 3 | `COMPOSE_PROJECT_NAME` を `-e` で渡す(全プロジェクトが `/workspace` にマウントされ compose 既定名 `workspace` が衝突するのを防ぐ。`-e` なら対話・非対話シェルと `docker exec` の全てで有効) | D0-scope-02 |
| 4 | ホストの `~/.ssh/config` はそのまま渡さず、`IdentityFile` / `IdentitiesOnly` / `IdentityAgent` を除去した一時コピーを RO マウントする | D0-sec-02 |
| 5 | 後片付けの対象を絞る手段として、**コンテナへの所有者ラベル付与は導入せず**、既存の `MODULE-cli-common-is-running` と `docker run` のエラー文言だけで判定する(`FR-env-01` 受入基準12・13 を満たすのに新しい契約項目もラベルも要らないため。ラベル方式は `NFR-scale-01` を満たす命名の一意化=`docs/issues/028` と併せて検討する) | D0-scope-02 |
| 6 | 手順7(停止中の残骸の削除)にも同じ稼働中判定を入れる(手順6 の判定から手順7 までの TOCTOU で稼働中になっていた場合に削除しないため。停止中コンテナを削除する観測可能な振る舞いは従来どおり) | D0-scope-02 |
| 7 | 名前衝突の判定と後片付けの限定を Linux 版・macOS 版の**両方に同じ形で**入れる(同じサブコマンドの成否・出力を OS で変えないため) | D0-scope-03 |
| 8 | 名前衝突時のメッセージを**対象が稼働中か停止中かで分ける**(「稼働しています」と書くのは実際に稼働しているときだけにする。停止中は `stop` での削除を案内する)。文面は既存の表示スタイル(絵文字 + 日本語1行)に合わせ、終了コードは 1 | D0-scope-02(表示内容の要件は `FR-env-01` 受入基準12 と `02-design/logging.md` が定める) |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 空きポート選定から `docker run` までが非アトミック | 同時 `start` でポート競合が起きうる(リトライで吸収するが根本解決ではない) | なし(閾値の外: **`find_available_novnc_port`(`claude-dev:270`。6080 番台)は `forward` の `find_available_host_port`(8100 番台)とは別関数**なので `docs/issues/010` の事象には含まれない。競合は最大20回の再試行で吸収し、吸収できなければ非0終了で**その場で気づける**) |
| **排他機構が無い** | 同じディレクトリでの同時 `start` は一方が名前衝突で失敗する(**失敗した側は何も削除しないので、稼働中のコンテナと作業中の tmux セッションは失われない**)。ただし `reset` / `logout` と重なると認証が空のまま起動しうる(**利用者が失敗に気づけない**) | `docs/issues/020-modify-cli-destructive-commands-have-no-mutual-exclusion.md`(排他の欠如そのもの) |
| `host-hooks.json` の名前が実態(hooks + env)と乖離 | 読み手が誤解しうる。歴史的経緯で据え置き | なし(閾値の外: 観測可能な被害が無い。名前だけの問題) |
| コンテナ名がディレクトリ名だけで決まる | 別パスの同名ディレクトリが同一セッション扱いになる(`start` は既存コンテナへ再接続する) | `docs/issues/028-modify-name-uniqueness-does-not-satisfy-nfr-scale-01.md`(**`NFR-scale-01` との不一致**) |
| `~/.claude-dev/agents/<name>.sock` に root 所有の残骸が残ることがある | 自動では消せない場合があり、案内を出して SSH 転送なしで続行する | なし(閾値の外: 案内が表示される=**その場で気づける**) |
| `~/.ssh/config` の一時コピーを削除しない | `start` のたびに `/tmp/claude-dev-ssh-config.*` が1つ増える(OS の一時領域の掃除に任せている) | なし(起票の閾値の外: 観測可能な被害が無い) |
| `host-local-bin/` がコピーであって同期ではない | ホスト側で削除したスクリプトがコンテナ側に残り続ける | なし(閾値の外: コンテナ内で `ls` すれば確認できる。被害は古いスクリプトの残存のみ) |
| 名前衝突で失敗したときに、**作りかけの停止中コンテナが残りうる** | 次回の `start` の手順7 が削除するので自動回復する。手動の後片付けは要らない | なし(閾値の外: 自動回復し、観測可能な被害が無い) |
| 名前衝突の判定が **`docker` のエラー文言に依存する**(ポート競合の判定と同じ方式) | Docker 側の文言が変わると名前衝突を見分けられなくなる。その場合でも**稼働中コンテナは稼働中判定で守られる**ため、起きるのは「停止中の同名コンテナを消してしまう」ことと「専用のエラー文を出せずに汎用の失敗表示になる」ことに留まる | なし(閾値の外: データの破壊には至らず、稼働中判定が二重の防護になっている) |
| 稼働中判定から `docker rm -f` までが**原子的でない** | 排他機構が無いため、判定の直後に他プロセスが同名コンテナを起動した場合は依然として削除しうる(窓は数ミリ秒)。根本解決には排他が要る | `docs/issues/020-modify-cli-destructive-commands-have-no-mutual-exclusion.md`(排他の欠如) |

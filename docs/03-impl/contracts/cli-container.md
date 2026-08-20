---
id: cli-container
version: 1.13.0
updated: 2026-08-20
source:
  - docs/02-design/contracts/cli-container.md
kind: other
impl: claude-dev::main#start, claude-dev-mac::main#start, scripts/entrypoint-claude.sh::main
summary: ホスト CLI がコンテナへ渡す環境変数・マウント・起動オプションの取り決め(実装側)
keywords: [契約, CTR, 実装]
verified:
  at: 2026-08-19
  version: 1.11.0
  against:
    - {doc: docs/02-design/contracts/cli-container.md, version: 1.14.0}
---

# CTR-cli-container ホスト CLI → コンテナ/entrypoint(実装)

- 実装: `claude-dev::main#start` / `claude-dev-mac::main#start`(発行側)、
  `scripts/entrypoint-claude.sh::main`(受け側)
- 当事者: MOD-cli-start → MOD-entrypoint
- 対応する設計: `docs/02-design/contracts/cli-container.md`

## 実装上の事実

| 項目 | 実際の値 | 定義箇所 |
|---|---|---|
| 起動コマンド | `docker run -d --name <NAME> --hostname <NAME> --network claude-dev-net --cap-add NET_ADMIN --cap-add NET_RAW --restart unless-stopped -t` | `claude-dev:1501`〜`:1529` |
| `--security-opt` | **付けていない**(Docker 既定の seccomp と `docker-default` AppArmor が有効なまま) | `claude-dev:1501`〜(不在であることが実装) |
| **管理ラベル** | Claude コンテナにだけ `--label claude-dev.managed=1 --label claude-dev.role=claude --label "claude-dev.project-dir=${PROJECT_DIR}"` の3つを付ける。**他のオプションと違い変数にまとめず、引用付きの引数として直接渡す**(`project-dir` の値は利用者のパスでスペースを含みうるため)。**docker-proxy と `fwd-*` には付けない**。**セッション由来の資源には docker-proxy が `claude-dev.role=spawned` と `claude-dev.owner-project-dir` の2つを付ける**(付与側は `CTR-docker-api` が持つ) | `claude-dev:1508`〜`:1510`(付与), `claude-dev:728`〜`:735`(docker-proxy は付けない) |
| **セッション由来の資源の削除対象を引く** | 共有関数 `spawned_resources <container|network> <ラベルフィルタ式>` で名前だけを取る。**`stop` は `claude-dev.owner-project-dir=<起動ディレクトリの絶対パス>`**(値は手順4 で読んだ `claude-dev.project-dir` と同じ)、**`reset` は `claude-dev.role=spawned`**(所有者を問わない)。削除はコンテナ → ネットワークの順。`stop` は失敗を握って続行し、`reset` は握らない。**`logout` も同じ共有関数を `container` + `claude-dev.role=spawned` で呼ぶが、削除には使わない** — 「管理ラベルを持たないコンテナ」の表示集合から除くためだけである(規則 D は `logout` に掛からない。引けなかったときは除外せずに表示し、混じっている可能性を出す) | `claude-dev:586`(共有関数の定義), `:1741`・`:1751`(`stop` の呼び出し), `:2079`・`:2084`(`reset` の呼び出し) / `claude-dev-mac:651`(定義), `:1750`・`:1760`(`stop`), `:2103`・`:2108`(`reset`) |
| `DOCKER_HOST` | `tcp://claude-dev-docker-proxy:2375`。**ホストに Docker ソケットがあるときだけ**付与する(`[ -S ... ]`)。**探す場所は OS で違う**: Linux 版は `/var/run/docker.sock` だけを見る。macOS 版は `detect_docker_sock` が `/var/run/docker.sock` → `${HOME}/.docker/run/docker.sock`(Docker Desktop のユーザソケット)の順に見て、**どちらかがあれば付与する**。VM モードでは entrypoint がゲスト VM 側の値へ上書きする(**`vm-up.sh` が成功したときだけ**。あわせて `/etc/claude-dev/runtime.env` へも記録し、外から tmux サーバを作り直す経路へ届ける) | `claude-dev:1407`〜`:1412`(Linux), `claude-dev-mac:310`〜`:316`(`detect_docker_sock`), `scripts/entrypoint-claude.sh:501`〜 |
| `COMPOSE_PROJECT_NAME` | **`<正規化名>-<起動ディレクトリの絶対パスの SHA-256 先頭6桁>`**。正規化は `tr '[:upper:]' '[:lower:]'` → `sed 's/[^a-z0-9_-]/-/g'`、ハッシュは Linux が `sha256sum` / macOS が `shasum -a 256`(入力は `printf '%s'` で改行を付けない)。**`start` と `stop` が同じ関数 `compose_project_name` を通す**。**常に付与する** | `claude-dev:539`〜`:559`(関数), `:1420`(`start` の付与), `:1810`(`stop` の再計算) |
| `CLAUDE_DEV_VM` | CLI は `--vm` / `--vm-fresh` のときだけ `1` を付与する。entrypoint は **`= "1"` の厳密一致**で判定する | `claude-dev:1696`(`VM_OPTS` で `-e CLAUDE_DEV_VM=1` を付与), `scripts/entrypoint-claude.sh:501` |
| `VM_PORTS` / `VM_MEM` / `VM_SMP` / `VM_DISK` / `VM_SWAP` | VM モードで、かつホスト側の同名変数が**非空のときだけ**そのまま転送する(値の検証なし) | `claude-dev:1481`〜`:1484` |
| `CLAUDE_DEV_VNC` | **イメージの `ENV`** で `1`(ブラウザ確認資産入りイメージのみ)。CLI は付与しない。entrypoint は `= "1"` の厳密一致で判定する | `.devcontainer/Dockerfile.claude:473`, `scripts/entrypoint-claude.sh:565`, `:622`, `:687` |
| `CLAUDE_DEV_DOOD_PORTSYNC` | CLI は付与しない。entrypoint は **`!= "0"`(未設定を含む)** かつ VM モードでない かつ `DOCKER_HOST` が `docker-proxy` を含む かつ同期スクリプトが実行可能、の4条件が揃ったときだけ同期を起動する | `scripts/entrypoint-claude.sh:518`〜`:524` |
| `CLAUDE_DEV_SSH_BRIDGE_PORT` | macOS のみ付与。entrypoint は**非空かつ `socat` があるとき**に `TCP:host.docker.internal:<値>` へのブリッジを起動し、`/tmp/ssh-agent.sock`(所有者 `$USERNAME`・`mode=600`)を用意する。**値の形式・範囲を検証しない**。ソケットの出現を **0.2 秒 × 最大 20 回(= 最大 4 秒)** 待ち、現れなくても起動を続ける | `claude-dev-mac:1495`(CLI の付与), `:274`(ブリッジ起動側が値を読む), `scripts/entrypoint-claude.sh:96`〜`:103` |
| `SSH_AUTH_SOCK` | Linux は `-e SSH_AUTH_SOCK=/tmp/ssh-agent.sock` を付け、同じパスへ agent ソケットを読み取り専用でマウントする。**macOS 経路では CLI が付けず、entrypoint が socat ブリッジでソケットを作ってから自分の環境へ `export` する**(そうしないと tmux サーバへ引き継がれない)。**あわせて `/etc/claude-dev/runtime.env` へも記録する**(外から tmux サーバを作り直す経路にはこれが唯一の入手先)。あわせて `/etc/zsh/zshrc` と `/etc/bash.bashrc` へ `export` を追記するが、**それが効くのは対話シェルだけである**(2026-08-19 より前はこの追記だけで「全シェルで有効」と書いていたが偽であった。現に届いていたのは `tmux` の `update-environment` の既定値に `SSH_AUTH_SOCK` が入っているという別の理由による) | `claude-dev:1615`, `scripts/entrypoint-claude.sh` の SSH_AUTH_SOCK 節 |
| `NODE_OPTIONS` | `--max-old-space-size=4096`。常に付与する | `claude-dev:1525`(`claude-dev-mac` の同一箇所) |
| `container` | `docker`。**起動時ではなくイメージの `ENV` で付与** | `.devcontainer/Dockerfile.claude:307` |
| コンテナ内ホーム `CHOME` | `/home/<CUSER>`。`CUSER` は**実行するイメージに焼き込まれた `CONTAINER_USER`** を優先し、取れなければホストの `whoami`。稼働中コンテナへ `exec` するときは**そのコンテナ自身**の `CONTAINER_USER` から解決し直す。以下のマウント先はすべてこの `CHOME` を基準にする | `claude-dev:46`〜`:48`(既定), `:54`〜`:59`(`resolve_container_user`) |
| マウント(常に。**マウント先の絶対パス**) | `<カレントディレクトリ>` → `/workspace`(rw)/ `claude-dev-history` → `${CHOME}/.command_history`(rw)/ `claude-dev-auth` → `${CHOME}/.claude-shared`(rw)/ `claude-dev-config` → `${CHOME}/.config-shared`(rw)/ キット同梱の `scripts/tmux.conf` → `${CHOME}/.tmux.conf`(ro)/ キット同梱の `CLAUDE.md` → `${CHOME}/CLAUDE.md`(ro) | `claude-dev:1511`〜`:1516` |
| マウント(条件付き。**マウント先の絶対パス**) | `~/.gitconfig` → `${CHOME}/.gitconfig`(ro。**ファイルとして存在するとき**)/ `~/.config/gh` → `${CHOME}/.config/gh`(ro。**ディレクトリとして存在するとき**)/ agent ソケット → `/tmp/ssh-agent.sock`(ro。`${CHOME}` 配下ではない)/ `~/.ssh/known_hosts` → `${CHOME}/.ssh/known_hosts`(ro)/ 加工済み `~/.ssh/config` の一時コピー → `${CHOME}/.ssh/config`(ro)/ ブラウザ確認時のプロファイル用ボリューム `claude-dev-chrome-<NAME>` → `${CHOME}/.chrome-profile`/ VM モードの `claude-dev-vm-<NAME>` → `${CHOME}/.claude-dev-vm` | `claude-dev:1397`〜`:1406`, `:1428`, `:1432`, `:1438`〜`:1441`, `:1448`, `:1480`, `:1511`〜`:1521` |
| `~/.ssh/config` の加工 | `sed -E '/^[[:space:]]*(IdentityFile\|IdentitiesOnly\|IdentityAgent)/d'` で3種の行を落とした一時コピーを作り、それを ro マウントする(**ホストの設定は変更しない**)。**`mktemp` と `sed` を `if` の条件に並べて両方の失敗を握る**: 作れなければ**加工前の config を代わりに渡さず**マウント自体を省き、渡さなかったことを表示して起動を続ける。`mktemp` だけ成功していた場合の作りかけは消す(`FR-env-04-9`) | `claude-dev:1648`〜`:1658`, `claude-dev-mac:1739`〜`:1749` |
| **ホスト資産の取り込みは失敗しても起動を止めない** | `~/.local/bin/` の `cp -a` は `if !` で握り、`cp` 自身のエラー(どのファイルが読めなかったか)と「取り込めなかったこと」を表示して続ける。**読めたファイルはコピー済みで残る**(`FR-env-02-7` / `NFR-avail-03`) | `claude-dev:1553`, `claude-dev-mac:1628` |
| **実行時に決まる環境変数の受け渡し(`/etc/claude-dev/runtime.env`)** | entrypoint が実行の最初にこのファイルを空へ戻し `0644` にし(`RUNTIME_ENV_FILE` / `record_runtime_env`)、**値を実際に採用した地点でだけ** `export <名前>='<値>'` の1行を追記する。対象は2つ: `/tmp/ssh-agent.sock` が**ソケットとして在るときの** `SSH_AUTH_SOCK`(`:128` の `[ -S ... ]` が条件で、中継ポート方式に限らず Linux の ro マウント経路でも記録される。値は同じなので害は無い)と、**`vm-up.sh` が成功したときだけ**の `DOCKER_HOST=tcp://127.0.0.1:2375`。ホスト CLI の再接続経路は `docker exec … sh -c '[ -f … ] && . …; exec tmux new-session -d -s main'` の形で読んでから tmux サーバを起こす。**行が1本も無ければ何も読み込まず起こす**(VM モードでも中継ポート方式でもないコンテナでは空のまま)。**ファイル自体は `:27` の `: > "$RUNTIME_ENV_FILE"` が条件節の外で必ず作る**ので存在しない状態は無く、CLI 側の `[ -f ]` は受け渡しファイルを持たない古いイメージに対する防御である。**entrypoint 自身は読まない**(自分の環境に `export` 済み) | `scripts/entrypoint-claude.sh:25`〜`:33`(初期化と記録関数), `:131`(`SSH_AUTH_SOCK`), `:516`(VM の `DOCKER_HOST`), `claude-dev:1474`〜`:1476`, `claude-dev-mac:1551`〜`:1553` |
| 公開ポート | ブラウザ確認資産を使うときだけ `-p <空きポート>:6080`。空きポートは専用の探索関数が選ぶ | `claude-dev:1445`〜`:1449` |
| デバイス | `--kvm` / `--vm` / `--vm-fresh` 指定時に `/dev/kvm` `/dev/vhost-net` `/dev/net/tun` のうち**実在するものだけ**を渡す。`/dev/kvm` が**無いとき**の扱いは指定の仕方で分かれる: **`--kvm` だけなら警告して続行**、**`--vm` または `--vm-fresh`(どちらも `USE_VM=1` にする)なら中止して終了コード 1**(TCG では実用にならないため)。`--vm` 系はデバイス判定より前、フラグ解析の直後に判定する | `claude-dev:1284`〜`:1292`(フラグ解析), `:1293`〜`:1297`(中止), `:1456`〜`:1471`(警告と付与) |
| 起動の再試行 | `docker run` が失敗したときの後片付けは、**エラー文言が名前衝突(`Conflict.` / `already in use by container`)でなく、かつ対象コンテナが稼働中でない**ときだけ `docker rm -f` する。そのうえで、**ブラウザ確認資産あり かつ 20 回以内 かつ エラー文言がポート競合(`port is already allocated` / `address already in use` / `bind for … failed`)** のときだけ、別のポートを取り直して再試行する。**エラー文言が名前衝突のときは何も削除せず、再試行もせず**、同名のコンテナが稼働中である旨を stderr へ出して**終了コード 1**。**管理ラベル `claude-dev.project-dir` が読めた場合は、可能性ではなく「どのディレクトリで起動されたか」という事実を出す**。それ以外の失敗と上限超過もエラーを表示して**終了コード 1** | `claude-dev:1499`〜`:1569`(Linux), `claude-dev-mac` の同一箇所 |
| **tmux サーバがコンテナの環境を引き継ぐこと** | **tmux サーバを起こす経路は2つあり、義務は両方に掛かる。** (2) **稼働中コンテナで `main` が失われたときにホスト CLI が `docker exec` で作り直す経路**は、`docker exec` がコンテナ作成時の env しか引き継がないため、上の受け渡しファイルを読んでから起こす。(1) entrypoint は tmux セッションを `su "$USERNAME" -s /bin/zsh -c "…"` で起こす。**`-l` を付けない** — 付けるとホストの `-e` で渡された変数もイメージの `ENV` で付いた変数も利用者のプロジェクト環境ファイルの組も**まとめて捨てられ**、**tmux サーバの環境をその配下の全ウィンドウ・全プロセスが継承する**ため、tmux の中から1つも見えなくなる。**`-l` の有無で `PATH` と `HOME` は変わらない**(2026-08-19 に実機で両方を並べて測定。違うのは `PWD` だけで、コマンドが `cd /workspace` するので影響しない)。**`tmux` の `update-environment` の既定値(`DISPLAY` / `SSH_AUTH_SOCK` ほか8個)だけはクライアント接続時にセッション環境へ写されるが、それ以外は1つも含まれない**ので当てにしない | `scripts/entrypoint-claude.sh` の tmux セッション開始 |
| 常駐セッションの待ち | `tmux has-session -t main` を 1 秒間隔で最大 **30 回**(VM モードは **420 回**)試す。時間内に上がらなければ状況を案内して**終了コード 0** で戻る(コンテナは残す) | `claude-dev:1573`〜`:1599` |
| 認証の受け渡し | 一時コンテナで共有ボリューム(ro)から `${PROJECT_DIR}/.claude/`(`.credentials.json` / `.claude.json`)と `${PROJECT_DIR}/.codex/auth.json` へコピーし、ホストの UID/GID へ `chown` する。**無い鍵は黙って飛ばす**(未ログインでも起動できる)。**この区間は共有資源単位のロックの中にある**(取得は `:1342`、解放はコンテナ作成の確定後 `:1570`) | `claude-dev:1349`〜`:1362` |
| 認証の書き戻し | コンテナ内で 30 秒間隔のバックグラウンドループ | `scripts/entrypoint-claude.sh:454` |
| **排他ロックの実体** | `${HOME}/.claude-dev/locks/` 配下の**シンボリックリンク**。向き先の文字列 `<PID> <操作名>` が保持者の記録を兼ねる(`ln -s` は同名パスがあると失敗するので、生成と所有者の記録が1回の原子的操作で成立する)。**ファイル名は種別で名前空間を分ける**: プロジェクト単位 `proj-<キー>.lock` / 共有資源単位 `shared.lock`(分けないとプロジェクト名が `shared` のとき2つのキーが同じファイルを指す)。ディレクトリは `mkdir -p` + `chmod 700` | `claude-dev:388`(置き場所), `:396`〜`:404`(パス), `:407`〜`:409`(生成), `:434`〜`:510`(取得), `:514`〜`:532`(解放) |
| **ロックを取る操作と区間** | `start`(プロジェクト単位 = 全区間 `:1270`〜`:1604` / 共有資源単位 = 認証コピー〜コンテナ作成の確定 `:1342`〜`:1570`)、`stop`(プロジェクト単位 = 全区間 `:1767`〜`:1901` / 共有資源単位 = 遊休判定〜proxy 削除 `:1895`〜`:1897`)、`logout`(`:960`)、`reset`(`:2136`)、`login`(`:826`)、`login-codex`(`:902`)。**取得順はプロジェクト単位 → 共有資源単位で固定**。**待たない** | `claude-dev` の各分岐 |
| **ロック残骸の回収** | 向き先の PID を `kill -0` で見て、存在しなければ `mv` で引き取る。**引き取った中身を `readlink` で検証し、観測した残骸と違ってその PID が生きているなら `ln -s` で元に戻して取得失敗にする**(`mv` は「そのパスの rename に成功するのは1プロセスだけ」を保証するだけで、中身が観測時と同じであることは保証しないため)。**時間による判定は一切しない** | `claude-dev:472`〜`:509` |
| **ロックの解放** | `trap '_release_all_locks' EXIT` と `trap '_release_all_locks; exit 130' INT TERM`。**取得より前に仕掛ける**。**向き先の PID が自分と一致するときだけ**削除し、明示解放したパスは trap 用の配列から外す | `claude-dev:424`〜`:430`(一括解放), `:451`〜`:452`(仕掛け), `:514`〜`:527`(所有者確認) |
| **遊休判定** | `docker network inspect claude-dev-net` の接続コンテナと `docker ps` の稼働集合の**積**から、固定名 `claude-dev-docker-proxy` と接頭辞 `fwd-` を除いた集合。**空のときだけ** docker-proxy(と `reset` では `claude-dev-net` も)を削除する。**`--filter ancestor` も管理ラベルも使わない**。問い合わせに失敗したら非0を返し、呼び出し元は「遊休でない」と判定する | `claude-dev:600`〜`:612`(集合), `:614`〜`:630`(`stop` の削除) |
| **破壊的操作の削除結果の記録** | 削除予定・削除済み・削除失敗の3つの配列で1件ずつ記録する。**同じ資源を削除済みと削除失敗の両方に記録しない**(記録関数は素の追記なので、排他は呼び出し側が担保する。`logout` は消去を確認できなかった共有ボリュームを削除失敗にだけ記録する)。**結果に記録する表示名は `destructive_plan` に渡した名前と一致させる** — 記録関数は**名前が一致した予定行だけ**を予定一覧から外すので、違う名前で記録すると予定側が「(未着手)」として残り、同じ資源が結果表示に2行出る。**引けなかった問い合わせも「消えなかった資源」として記録する**(`reset` のセッション由来の資源の列挙と、`logout` の管理ラベル付きコンテナの列挙)。**削除コマンドは `( trap '' INT TERM; ... )` のサブシェルで起動する**(非対話シェルでは子プロセスがシェルと同じプロセスグループに入り、端末の `Ctrl-C` が `docker` にも直接届くため。`SIG_IGN` は `exec` した子へ継承される) | `claude-dev:635`〜`:653`(記録), `:661`〜`:669`(サブシェル) |
| **共有ボリュームの中身の列挙(2箇所とも印を使い、位置で判定する)** | `logout` は `/auth` の中身を2回列挙し、**どちらも列挙の直前に印 `__CLAUDE_DEV_AUTH_LISTED__` を出す**。**印は標準出力の1行目に現れ**(列挙の直前に1回だけ出す。`docker` 自身の警告は標準エラーへ出る)、**中身の判定は「1行目が印であること」と「2行目以降」という位置で行い、行の内容では行わない**(内容で除くと `/auth/__CLAUDE_DEV_AUTH_LISTED__` という名前のファイルやディレクトリを印と区別できず、中身があるのに「空」と判定する)。(a) **手順6 の0件判定**: **印が出ている・一時コンテナの終了ステータスが 0・印以外の行が無い**の3つがそろったときだけ「空」とする(消去を伴わないので終了ステータスが「列挙できたか」をそのまま表す)。**1つでも欠ければ「空」と判定せず**、削除対象0件の経路に入らずに確認へ進む。(b) **手順10 の消去後の判定**: 印が無ければ一時コンテナが起動できていないので失敗に数える。**`rm -rf` の終了コードはどちらでも見ない**(`.` と `..` に当たって非0を返しうるため「消えたか」を表さない)。**列挙の終了ステータスは2箇所とも見る**: 一時コンテナに渡すコマンドの**最後が列挙**(`… ; echo 印; ls -A /auth`)なので、コンテナの終了ステータスは列挙の状態であり `rm -rf` の状態ではない。**手順10 でも、印が出た直後に列挙が失敗すると出力が印だけになって「消去に成功して空になった」場合と区別できない**ので、終了ステータスを条件に入れる。**印を使う箇所を1つにしないのは、判定の対象が「消す前の中身」と「消した後の中身」で別だからである**(判定手段は同じなので、位置で読む形も2箇所で揃える) | `claude-dev` の `logout` 分岐(手順6 の判定と手順10 の判定), `claude-dev-mac` の同一箇所 |
| ファイアウォールの起動 | `/usr/local/bin/init-firewall.sh 2>/dev/null \|\| true` | `scripts/entrypoint-claude.sh:476` |

**環境変数の判定はすべて厳密一致**だが、比較する値は変数ごとに違う: `CLAUDE_DEV_VM` と
`CLAUDE_DEV_VNC` は **`= "1"`**(それ以外はすべて無効)、`CLAUDE_DEV_DOOD_PORTSYNC` は
**`!= "0"`**(`0` 以外の任意の値 — `abc` や `false` を含む — は有効)。したがって `true` / `yes` は
前者では無効、後者では有効になる。**受け側が値の不正を理由に起動を止めることはない。**

## 設計との差異

| 種別 | 設計(02)の期待 | 実装 | 対処 |
|---|---|---|---|
| 名前の一意性 | 「名前・ポート・プロファイルの**一意化で衝突を避ける**」(`02-design/contracts/cli-container.md` の「順序性・冪等性・並行性の背景」/ `NFR-scale-01`「衝突 0 件」) | **compose プロジェクト名は起動ディレクトリの絶対パスのハッシュを含めて一意化した**(`DSN-env-03`)。**コンテナ名は依然ディレクトリ名だけから決まり一意でない** | **設計が正**と裁定済み(2026-08-04)。**compose 側は解消**(経緯は `docs/histories/2026-08-04-fix-destructive-scope.md`)。**コンテナ名の一意化は未解決**で、`docs/issues/028-modify-name-uniqueness-does-not-satisfy-nfr-scale-01.md` で追跡する。ただし管理ラベル `claude-dev.project-dir` により、衝突時にどのディレクトリのものかを事実として示せるようになった |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 空きポートの選定から `docker run` までが原子的でない | 同時起動でポート競合が起きうる(ブラウザ確認資産ありのときだけ最大20回の再試行で吸収する。**再試行はポート競合の文言判定に依存する**ため、文言が変わると吸収できない) | なし(閾値の外: 競合は最大20回の再試行で吸収し、吸収できなければ非0終了で**その場で気づける**。`forward` 側の選定(`docs/issues/010`)とは別関数) |
| `.claude/host-hooks.json` の名前が実態(hooks と env)と乖離している | 読み手が誤解しうる。歴史的経緯で据え置き | なし(閾値の外: 観測可能な被害が無い。名前だけの問題) |
| コンテナ名がディレクトリ名だけで決まる | 別パスの同名ディレクトリが同一セッション扱いになる | `docs/issues/028-modify-name-uniqueness-does-not-satisfy-nfr-scale-01.md`(**`NFR-scale-01` との不一致**) |
| `COMPOSE_PROJECT_NAME` の**ハッシュ短縮値が 6 桁(24 ビット)** | 異なる絶対パスが同じ先頭6桁になると、一方の `stop` が他方の compose 資源を削除しうる。**衝突は検出しない** | `docs/pendings.md` **P-005**(2026-08-04 に人間が受容。**正規化が非可逆だったことによる確実な衝突は解消した**。経緯は `docs/histories/2026-08-04-fix-destructive-scope.md`) |
| **管理ラベルも一意化された compose 名も持たない資源が既存環境に残っている**(それらを作った時点の実装がラベルを付けていなかった) | `logout` / `reset` はそのコンテナを削除せず名前を表示して残し、`stop` は旧い名前の compose 資源を削除せず手動手順を案内する | なし(閾値の外: どちらも**表示する**ので気づけ、表示が空になれば移行の完了を判別できる) |
| **遊休判定の集合に利用者の compose コンテナが入る** | Claude コンテナ内から `docker compose` で起動した資源も `claude-dev-net` に接続するため「稼働中」に数える。docker-proxy が回収されにくく、`reset` が「完全な初期化になっていない」になりやすい。**過剰に数える=消さない側**なので `FR-env-01` 受入基準9 は破らない | なし(2026-08-04 の決定シート #1 で人間が「現状のまま」と裁定) |
| **排他ロックはホスト CLI のプロセス間・同一ユーザのみ** | 利用者が直接 `docker rm -f` する経路、別ユーザ、別ホストからの操作は保護されない。**コンテナ内の認証書き戻しループ(30 秒周期)にも効かない**ため、ラベルを持たないコンテナを残したまま `logout` すると最大 30 秒で認証が復活する(警告を出す) | なし(契約の「ロックが守れない範囲」が明示) |
| **残骸の引き取りに2システムコール分の窓が残る** | 引き取りで生きているロックを奪い元に戻すまでの2システムコールの間に第三のプロセスが取得すると、2つが同時に臨界区間に入る。**この場合は「ロックを元に戻せませんでした」を出して知らせる** | なし(閾値の外: 成立に3プロセスの同時競合が要る。黙って進まない) |
| 起動途中の失敗で `${PROJECT_DIR}/.claude` / `.codex` が残る | 認証コピー以降の失敗ではコンテナが無いのに作業用ディレクトリだけが残る。**再実行で回復する**(いずれの手順も再入可能) | なし(閾値の外: 失敗は非0終了で**その場で気づける**。再実行で回復する) |

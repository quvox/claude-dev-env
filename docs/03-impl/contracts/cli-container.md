---
id: cli-container
version: 1.5.1
updated: 2026-08-05
source:
  - docs/02-design/contracts/cli-container.md
kind: other
impl: claude-dev::main#start, claude-dev-mac::main#start
summary: ホスト CLI がコンテナへ渡す環境変数・マウント・起動オプションの取り決め(実装側)
keywords: [契約, CTR, 実装]
verified:
  at: 2026-08-06
  version: 1.5.1
  against:
    - doc: docs/02-design/contracts/cli-container.md
      version: 1.4.2
---

# CTR-cli-container ホスト CLI → コンテナ/entrypoint(実装)

- 実装: `claude-dev::main#start` / `claude-dev-mac::main#start`(発行側)、
  `scripts/entrypoint-claude.sh::main`(受け側)
- 当事者: MOD-cli-start → MOD-entrypoint
- 対応する設計: `docs/02-design/contracts/cli-container.md`

## 実装上の事実

| 項目 | 実際の値 | 定義箇所 |
|---|---|---|
| 起動コマンド | `docker run -d --name <NAME> --hostname <NAME> --network claude-dev-net --cap-add NET_ADMIN --cap-add NET_RAW --restart unless-stopped -t` | `claude-dev:1381`〜`:1409` |
| `--security-opt` | **付けていない**(Docker 既定の seccomp と `docker-default` AppArmor が有効なまま) | `claude-dev:1381`〜(不在であることが実装) |
| **管理ラベル** | Claude コンテナにだけ `--label claude-dev.managed=1 --label claude-dev.role=claude --label "claude-dev.project-dir=${PROJECT_DIR}"` の3つを付ける。**他のオプションと違い変数にまとめず、引用付きの引数として直接渡す**(`project-dir` の値は利用者のパスでスペースを含みうるため)。**docker-proxy と `fwd-*` には付けない** | `claude-dev:1388`〜`:1390`(付与), `claude-dev:710`〜`:717`(docker-proxy は付けない) |
| `DOCKER_HOST` | `tcp://claude-dev-docker-proxy:2375`。**ホストに Docker ソケットがあるときだけ**付与する(`[ -S ... ]`)。**探す場所は OS で違う**: Linux 版は `/var/run/docker.sock` だけを見る。macOS 版は `detect_docker_sock` が `/var/run/docker.sock` → `${HOME}/.docker/run/docker.sock`(Docker Desktop のユーザソケット)の順に見て、**どちらかがあれば付与する**。VM モードでは entrypoint がゲスト VM 側の値へ上書きする | `claude-dev:1291`〜`:1294`(Linux), `claude-dev-mac:310`〜`:316`(`detect_docker_sock`), `scripts/entrypoint-claude.sh:476`〜 |
| `COMPOSE_PROJECT_NAME` | **`<正規化名>-<起動ディレクトリの絶対パスの SHA-256 先頭6桁>`**。正規化は `tr '[:upper:]' '[:lower:]'` → `sed 's/[^a-z0-9_-]/-/g'`、ハッシュは Linux が `sha256sum` / macOS が `shasum -a 256`(入力は `printf '%s'` で改行を付けない)。**`start` と `stop` が同じ関数 `compose_project_name` を通す**。**常に付与する** | `claude-dev:539`〜`:559`(関数), `:1300`(`start` の付与), `:1684`(`stop` の再計算) |
| `CLAUDE_DEV_VM` | CLI は `--vm` / `--vm-fresh` のときだけ `1` を付与する。entrypoint は **`= "1"` の厳密一致**で判定する | `claude-dev:1354`〜`:1360`, `scripts/entrypoint-claude.sh:476` |
| `VM_PORTS` / `VM_MEM` / `VM_SMP` / `VM_DISK` / `VM_SWAP` | VM モードで、かつホスト側の同名変数が**非空のときだけ**そのまま転送する(値の検証なし) | `claude-dev:1361`〜`:1364` |
| `CLAUDE_DEV_VNC` | **イメージの `ENV`** で `1`(ブラウザ確認資産入りイメージのみ)。CLI は付与しない。entrypoint は `= "1"` の厳密一致で判定する | `.devcontainer/Dockerfile.claude:473`, `scripts/entrypoint-claude.sh:556`, `:613`, `:678` |
| `CLAUDE_DEV_DOOD_PORTSYNC` | CLI は付与しない。entrypoint は **`!= "0"`(未設定を含む)** かつ VM モードでない かつ `DOCKER_HOST` が `docker-proxy` を含む かつ同期スクリプトが実行可能、の4条件が揃ったときだけ同期を起動する | `scripts/entrypoint-claude.sh:509`〜`:515` |
| `CLAUDE_DEV_SSH_BRIDGE_PORT` | macOS のみ付与。entrypoint は**非空かつ `socat` があるとき**に `TCP:host.docker.internal:<値>` へのブリッジを起動し、`/tmp/ssh-agent.sock`(所有者 `$USERNAME`・`mode=600`)を用意する。**値の形式・範囲を検証しない**。ソケットの出現を **0.2 秒 × 最大 20 回(= 最大 4 秒)** 待ち、現れなくても起動を続ける | `claude-dev-mac:1375`(CLI の付与), `:274`(ブリッジ起動側が値を読む), `scripts/entrypoint-claude.sh:96`〜`:103` |
| `SSH_AUTH_SOCK` | Linux は `-e SSH_AUTH_SOCK=/tmp/ssh-agent.sock` を付け、同じパスへ agent ソケットを読み取り専用でマウントする。`su -l` で失われるため、entrypoint が `/etc/zsh/zshrc` と `/etc/bash.bashrc` へ `export` を追記して全シェルで有効にする | `claude-dev:1306`〜`:1309`, `scripts/entrypoint-claude.sh:105`〜`:116` |
| `NODE_OPTIONS` | `--max-old-space-size=4096`。常に付与する | `claude-dev` の `docker run` 引数 |
| `container` | `docker`。**起動時ではなくイメージの `ENV` で付与** | `.devcontainer/Dockerfile.claude:307` |
| コンテナ内ホーム `CHOME` | `/home/<CUSER>`。`CUSER` は**実行するイメージに焼き込まれた `CONTAINER_USER`** を優先し、取れなければホストの `whoami`。稼働中コンテナへ `exec` するときは**そのコンテナ自身**の `CONTAINER_USER` から解決し直す。以下のマウント先はすべてこの `CHOME` を基準にする | `claude-dev:46`〜`:48`(既定), `:54`〜`:59`(`resolve_container_user`) |
| マウント(常に。**マウント先の絶対パス**) | `<カレントディレクトリ>` → `/workspace`(rw)/ `claude-dev-history` → `${CHOME}/.command_history`(rw)/ `claude-dev-auth` → `${CHOME}/.claude-shared`(rw)/ `claude-dev-config` → `${CHOME}/.config-shared`(rw)/ キット同梱の `scripts/tmux.conf` → `${CHOME}/.tmux.conf`(ro)/ キット同梱の `CLAUDE.md` → `${CHOME}/CLAUDE.md`(ro) | `claude-dev:1391`〜`:1396` |
| マウント(条件付き。**マウント先の絶対パス**) | `~/.gitconfig` → `${CHOME}/.gitconfig`(ro。**ファイルとして存在するとき**)/ `~/.config/gh` → `${CHOME}/.config/gh`(ro。**ディレクトリとして存在するとき**)/ agent ソケット → `/tmp/ssh-agent.sock`(ro。`${CHOME}` 配下ではない)/ `~/.ssh/known_hosts` → `${CHOME}/.ssh/known_hosts`(ro)/ 加工済み `~/.ssh/config` の一時コピー → `${CHOME}/.ssh/config`(ro)/ ブラウザ確認時のプロファイル用ボリューム `claude-dev-chrome-<NAME>` → `${CHOME}/.chrome-profile`/ VM モードの `claude-dev-vm-<NAME>` → `${CHOME}/.claude-dev-vm` | `claude-dev:1277`〜`:1286`, `:1308`, `:1312`, `:1318`〜`:1321`, `:1328`, `:1360`, `:1391`〜`:1401` |
| `~/.ssh/config` の加工 | `sed -E '/^[[:space:]]*(IdentityFile\|IdentitiesOnly\|IdentityAgent)/d'` で3種の行を落とした一時コピーを作り、それを ro マウントする(**ホストの設定は変更しない**) | `claude-dev:1314`〜`:1323` |
| 公開ポート | ブラウザ確認資産を使うときだけ `-p <空きポート>:6080`。空きポートは専用の探索関数が選ぶ | `claude-dev:1325`〜`:1329` |
| デバイス | `--kvm` / `--vm` / `--vm-fresh` 指定時に `/dev/kvm` `/dev/vhost-net` `/dev/net/tun` のうち**実在するものだけ**を渡す。`/dev/kvm` が**無いとき**の扱いは指定の仕方で分かれる: **`--kvm` だけなら警告して続行**、**`--vm` または `--vm-fresh`(どちらも `USE_VM=1` にする)なら中止して終了コード 1**(TCG では実用にならないため)。`--vm` 系はデバイス判定より前、フラグ解析の直後に判定する | `claude-dev:1163`〜`:1164`(フラグ), `:1168`〜`:1171`(中止), `:1336`〜`:1351`(警告と付与) |
| 起動の再試行 | `docker run` が失敗したときの後片付けは、**エラー文言が名前衝突(`Conflict.` / `already in use by container`)でなく、かつ対象コンテナが稼働中でない**ときだけ `docker rm -f` する。そのうえで、**ブラウザ確認資産あり かつ 20 回以内 かつ エラー文言がポート競合(`port is already allocated` / `address already in use` / `bind for … failed`)** のときだけ、別のポートを取り直して再試行する。**エラー文言が名前衝突のときは何も削除せず、再試行もせず**、同名のコンテナが稼働中である旨を stderr へ出して**終了コード 1**。**管理ラベル `claude-dev.project-dir` が読めた場合は、可能性ではなく「どのディレクトリで起動されたか」という事実を出す**。それ以外の失敗と上限超過もエラーを表示して**終了コード 1** | `claude-dev:1379`〜`:1449`(Linux), `claude-dev-mac` の同一箇所 |
| 常駐セッションの待ち | `tmux has-session -t main` を 1 秒間隔で最大 **30 回**(VM モードは **420 回**)試す。時間内に上がらなければ状況を案内して**終了コード 0** で戻る(コンテナは残す) | `claude-dev:1453`〜`:1479` |
| 認証の受け渡し | 一時コンテナで共有ボリューム(ro)から `${PROJECT_DIR}/.claude/`(`.credentials.json` / `.claude.json`)と `${PROJECT_DIR}/.codex/auth.json` へコピーし、ホストの UID/GID へ `chown` する。**無い鍵は黙って飛ばす**(未ログインでも起動できる)。**この区間は共有資源単位のロックの中にある**(取得は `:1222`、解放はコンテナ作成の確定後 `:1450`) | `claude-dev:1229`〜`:1242` |
| 認証の書き戻し | コンテナ内で 30 秒間隔のバックグラウンドループ | `scripts/entrypoint-claude.sh:449` |
| **排他ロックの実体** | `${HOME}/.claude-dev/locks/` 配下の**シンボリックリンク**。向き先の文字列 `<PID> <操作名>` が保持者の記録を兼ねる(`ln -s` は同名パスがあると失敗するので、生成と所有者の記録が1回の原子的操作で成立する)。**ファイル名は種別で名前空間を分ける**: プロジェクト単位 `proj-<キー>.lock` / 共有資源単位 `shared.lock`(分けないとプロジェクト名が `shared` のとき2つのキーが同じファイルを指す)。ディレクトリは `mkdir -p` + `chmod 700` | `claude-dev:388`(置き場所), `:396`〜`:404`(パス), `:407`〜`:409`(生成), `:434`〜`:510`(取得), `:514`〜`:532`(解放) |
| **ロックを取る操作と区間** | `start`(プロジェクト単位 = 全区間 `:1150`〜`:1484` / 共有資源単位 = 認証コピー〜コンテナ作成の確定 `:1222`〜`:1450`)、`stop`(プロジェクト単位 = 全区間 `:1647`〜`:1717` / 共有資源単位 = 遊休判定〜proxy 削除 `:1711`〜`:1713`)、`logout`(`:942`)、`reset`(`:1952`)、`login`(`:808`)、`login-codex`(`:884`)。**取得順はプロジェクト単位 → 共有資源単位で固定**。**待たない** | `claude-dev` の各分岐 |
| **ロック残骸の回収** | 向き先の PID を `kill -0` で見て、存在しなければ `mv` で引き取る。**引き取った中身を `readlink` で検証し、観測した残骸と違ってその PID が生きているなら `ln -s` で元に戻して取得失敗にする**(`mv` は「そのパスの rename に成功するのは1プロセスだけ」を保証するだけで、中身が観測時と同じであることは保証しないため)。**時間による判定は一切しない** | `claude-dev:472`〜`:509` |
| **ロックの解放** | `trap '_release_all_locks' EXIT` と `trap '_release_all_locks; exit 130' INT TERM`。**取得より前に仕掛ける**。**向き先の PID が自分と一致するときだけ**削除し、明示解放したパスは trap 用の配列から外す | `claude-dev:424`〜`:430`(一括解放), `:451`〜`:452`(仕掛け), `:514`〜`:527`(所有者確認) |
| **遊休判定** | `docker network inspect claude-dev-net` の接続コンテナと `docker ps` の稼働集合の**積**から、固定名 `claude-dev-docker-proxy` と接頭辞 `fwd-` を除いた集合。**空のときだけ** docker-proxy(と `reset` では `claude-dev-net` も)を削除する。**`--filter ancestor` も管理ラベルも使わない**。問い合わせに失敗したら非0を返し、呼び出し元は「遊休でない」と判定する | `claude-dev:582`〜`:594`(集合), `:596`〜`:612`(`stop` の削除) |
| **破壊的操作の削除結果の記録** | 削除予定・削除済み・削除失敗の3つの配列で1件ずつ記録する。**削除コマンドは `( trap '' INT TERM; ... )` のサブシェルで起動する**(非対話シェルでは子プロセスがシェルと同じプロセスグループに入り、端末の `Ctrl-C` が `docker` にも直接届くため。`SIG_IGN` は `exec` した子へ継承される) | `claude-dev:617`〜`:635`(記録), `:643`〜`:651`(サブシェル) |
| **共有ボリュームの消去の成否判定** | 一時コンテナで `rm -rf /auth/* /auth/.*` した後、**印 `__CLAUDE_DEV_AUTH_LISTED__` を出してから** `/auth` を列挙する。**印が無ければ一時コンテナが起動できていない**ので失敗に数える。**`rm -rf` の終了コードは見ない** | `claude-dev:1058`〜`:1070` |
| ファイアウォールの起動 | `/usr/local/bin/init-firewall.sh 2>/dev/null \|\| true` | `scripts/entrypoint-claude.sh:471` |

**環境変数の判定はすべて厳密一致**だが、比較する値は変数ごとに違う: `CLAUDE_DEV_VM` と
`CLAUDE_DEV_VNC` は **`= "1"`**(それ以外はすべて無効)、`CLAUDE_DEV_DOOD_PORTSYNC` は
**`!= "0"`**(`0` 以外の任意の値 — `abc` や `false` を含む — は有効)。したがって `true` / `yes` は
前者では無効、後者では有効になる。**受け側が値の不正を理由に起動を止めることはない。**

## 設計との差異

| 種別 | 設計(02)の期待 | 実装 | 対処 |
|---|---|---|---|
| 名前の一意性 | 「名前・ポート・プロファイルの**一意化で衝突を避ける**」(`02-design/contracts/cli-container.md` の「順序性・冪等性・並行性の背景」/ `NFR-scale-01`「衝突 0 件」) | **compose プロジェクト名は起動ディレクトリの絶対パスのハッシュを含めて一意化した**(`DSN-env-03`)。**コンテナ名は依然ディレクトリ名だけから決まり一意でない** | **設計が正**と裁定済み(2026-08-04)。**compose 側は解消**(`docs/issues/024` を閉じた)。**コンテナ名の一意化は未解決**で、`docs/issues/028-modify-name-uniqueness-does-not-satisfy-nfr-scale-01.md` で追跡する。ただし管理ラベル `claude-dev.project-dir` により、衝突時にどのディレクトリのものかを事実として示せるようになった |

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
| **残骸の引き取りに極小の窓が残る** | 引き取りで生きているロックを奪い元に戻すまでの2システムコールの間に第三のプロセスが取得すると、2つが同時に臨界区間に入る。**この場合は「ロックを元に戻せませんでした」を出して知らせる** | なし(閾値の外: 成立に3プロセスの同時競合が要る。黙って進まない) |
| `CLAUDE_DEV_SSH_BRIDGE_PORT` を検証しない | **ホストの環境変数から読むため利用者が任意の値を与えられる**(`claude-dev-mac:274` の `${CLAUDE_DEV_SSH_BRIDGE_PORT:-}`)。不正な値でも socat の起動を試み、失敗しても成功時と同じ表示で起動が続く | `docs/issues/023-bug-ssh-bridge-port-accepts-unvalidated-host-env.md` |
| 起動途中の失敗で `${PROJECT_DIR}/.claude` / `.codex` が残る | 認証コピー以降の失敗ではコンテナが無いのに作業用ディレクトリだけが残る。**再実行で回復する**(いずれの手順も再入可能) | なし(閾値の外: 失敗は非0終了で**その場で気づける**。再実行で回復する) |

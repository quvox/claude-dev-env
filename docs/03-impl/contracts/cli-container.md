---
id: cli-container
version: 1.3.0
updated: 2026-08-04
source:
  - docs/02-design/contracts/cli-container.md
kind: other
impl: claude-dev::main#start
summary: ホスト CLI がコンテナへ渡す環境変数・マウント・起動オプションの取り決め(実装側)
keywords: [契約, CTR, 実装]
verified:
  at: 2026-08-04
  version: 1.3.0
  against:
    - doc: docs/02-design/contracts/cli-container.md
      version: 1.3.0
---

# CTR-cli-container ホスト CLI → コンテナ/entrypoint(実装)

- 実装: `claude-dev::main#start` / `claude-dev-mac::main#start`(発行側)、
  `scripts/entrypoint-claude.sh::main`(受け側)
- 当事者: MOD-cli-start → MOD-entrypoint
- 対応する設計: `docs/02-design/contracts/cli-container.md`

## 実装上の事実

| 項目 | 実際の値 | 定義箇所 |
|---|---|---|
| 起動コマンド | `docker run -d --name <NAME> --hostname <NAME> --network claude-dev-net --cap-add NET_ADMIN --cap-add NET_RAW --restart unless-stopped -t` | `claude-dev:901`〜`:924` |
| `--security-opt` | **付けていない**(Docker 既定の seccomp と `docker-default` AppArmor が有効なまま) | `claude-dev:901`〜(不在であることが実装) |
| `DOCKER_HOST` | `tcp://claude-dev-docker-proxy:2375`。**ホストの `/var/run/docker.sock` がソケットとして存在するときだけ**付与する(`[ -S ... ]`)。VM モードでは entrypoint がゲスト VM 側の値へ上書きする | `claude-dev:811`〜`:814`, `scripts/entrypoint-claude.sh:476`〜 |
| `COMPOSE_PROJECT_NAME` | コンテナ名を `sed 's/[^a-z0-9_-]/-/g'` で正規化した値。**常に付与する** | `claude-dev:820`〜`:821` |
| `CLAUDE_DEV_VM` | CLI は `--vm` / `--vm-fresh` のときだけ `1` を付与する。entrypoint は **`= "1"` の厳密一致**で判定する | `claude-dev:874`〜`:880`, `scripts/entrypoint-claude.sh:476` |
| `VM_PORTS` / `VM_MEM` / `VM_SMP` / `VM_DISK` / `VM_SWAP` | VM モードで、かつホスト側の同名変数が**非空のときだけ**そのまま転送する(値の検証なし) | `claude-dev:881`〜`:884` |
| `CLAUDE_DEV_VNC` | **イメージの `ENV`** で `1`(ブラウザ確認資産入りイメージのみ)。CLI は付与しない。entrypoint は `= "1"` の厳密一致で判定する | `.devcontainer/Dockerfile.claude:473`, `scripts/entrypoint-claude.sh:556`, `:613`, `:678` |
| `CLAUDE_DEV_DOOD_PORTSYNC` | CLI は付与しない。entrypoint は **`!= "0"`(未設定を含む)** かつ VM モードでない かつ `DOCKER_HOST` が `docker-proxy` を含む かつ同期スクリプトが実行可能、の4条件が揃ったときだけ同期を起動する | `scripts/entrypoint-claude.sh:509`〜`:515` |
| `CLAUDE_DEV_SSH_BRIDGE_PORT` | macOS のみ付与。entrypoint は**非空かつ `socat` があるとき**に `TCP:host.docker.internal:<値>` へのブリッジを起動し、`/tmp/ssh-agent.sock`(所有者 `$USERNAME`・`mode=600`)を用意する。**値の形式・範囲を検証しない**。ソケットの出現を **0.2 秒 × 最大 20 回(= 最大 4 秒)** 待ち、現れなくても起動を続ける | `claude-dev-mac:274`, `:899`, `scripts/entrypoint-claude.sh:96`〜`:103` |
| `SSH_AUTH_SOCK` | Linux は `-e SSH_AUTH_SOCK=/tmp/ssh-agent.sock` を付け、同じパスへ agent ソケットを読み取り専用でマウントする。`su -l` で失われるため、entrypoint が `/etc/zsh/zshrc` と `/etc/bash.bashrc` へ `export` を追記して全シェルで有効にする | `claude-dev:826`〜`:829`, `scripts/entrypoint-claude.sh:105`〜`:116` |
| `NODE_OPTIONS` | `--max-old-space-size=4096`。常に付与する | `claude-dev` の `docker run` 引数 |
| `container` | `docker`。**起動時ではなくイメージの `ENV` で付与** | `.devcontainer/Dockerfile.claude:307` |
| コンテナ内ホーム `CHOME` | `/home/<CUSER>`。`CUSER` は**実行するイメージに焼き込まれた `CONTAINER_USER`** を優先し、取れなければホストの `whoami`。稼働中コンテナへ `exec` するときは**そのコンテナ自身**の `CONTAINER_USER` から解決し直す。以下のマウント先はすべてこの `CHOME` を基準にする | `claude-dev:46`〜`:48`(既定), `:54`〜`:59`(`resolve_container_user`) |
| マウント(常に。**マウント先の絶対パス**) | `<カレントディレクトリ>` → `/workspace`(rw)/ `claude-dev-history` → `${CHOME}/.command_history`(rw)/ `claude-dev-auth` → `${CHOME}/.claude-shared`(rw)/ `claude-dev-config` → `${CHOME}/.config-shared`(rw)/ キット同梱の `scripts/tmux.conf` → `${CHOME}/.tmux.conf`(ro)/ キット同梱の `CLAUDE.md` → `${CHOME}/CLAUDE.md`(ro) | `claude-dev:908`〜`:913` |
| マウント(条件付き。**マウント先の絶対パス**) | `~/.gitconfig` → `${CHOME}/.gitconfig`(ro。**ファイルとして存在するとき**)/ `~/.config/gh` → `${CHOME}/.config/gh`(ro。**ディレクトリとして存在するとき**)/ agent ソケット → `/tmp/ssh-agent.sock`(ro。`${CHOME}` 配下ではない)/ `~/.ssh/known_hosts` → `${CHOME}/.ssh/known_hosts`(ro)/ 加工済み `~/.ssh/config` の一時コピー → `${CHOME}/.ssh/config`(ro)/ ブラウザ確認時のプロファイル用ボリューム `claude-dev-chrome-<NAME>` → `${CHOME}/.chrome-profile`/ VM モードの `claude-dev-vm-<NAME>` → `${CHOME}/.claude-dev-vm` | `claude-dev:797`〜`:806`, `:828`, `:832`, `:838`〜`:841`, `:848`, `:880`, `:908`〜`:921` |
| `~/.ssh/config` の加工 | `sed -E '/^[[:space:]]*(IdentityFile\|IdentitiesOnly\|IdentityAgent)/d'` で3種の行を落とした一時コピーを作り、それを ro マウントする(**ホストの設定は変更しない**) | `claude-dev:834`〜`:843` |
| 公開ポート | ブラウザ確認資産を使うときだけ `-p <空きポート>:6080`。空きポートは専用の探索関数が選ぶ | `claude-dev:845`〜`:849` |
| デバイス | `--kvm` / `--vm` / `--vm-fresh` 指定時に `/dev/kvm` `/dev/vhost-net` `/dev/net/tun` のうち**実在するものだけ**を渡す。`/dev/kvm` が**無いとき**の扱いは指定の仕方で分かれる: **`--kvm` だけなら警告して続行**、**`--vm` または `--vm-fresh`(どちらも `USE_VM=1` にする)なら中止して終了コード 1**(TCG では実用にならないため)。`--vm` 系はデバイス判定より前、フラグ解析の直後に判定する | `claude-dev:703`〜`:704`(フラグ), `:708`〜`:711`(中止), `:856`〜`:871`(警告と付与) |
| 起動の再試行 | `docker run` が失敗したときの後片付けは、**エラー文言が名前衝突(`Conflict.` / `already in use by container`)でなく、かつ対象コンテナが稼働中でない**ときだけ `docker rm -f` する。そのうえで、**ブラウザ確認資産あり かつ 20 回以内 かつ エラー文言がポート競合(`port is already allocated` / `address already in use` / `bind for … failed`)** のときだけ、別のポートを取り直して再試行する。**エラー文言が名前衝突のときは何も削除せず、再試行もせず**、同名のコンテナが稼働中である旨と別ディレクトリの同名プロジェクトである可能性を stderr へ出して**終了コード 1**。それ以外の失敗と上限超過もエラーを表示して**終了コード 1** | `claude-dev:899`〜`:939`(Linux), `claude-dev-mac` の同一箇所 |
| 常駐セッションの待ち | `tmux has-session -t main` を 1 秒間隔で最大 **30 回**(VM モードは **420 回**)試す。時間内に上がらなければ状況を案内して**終了コード 0** で戻る(コンテナは残す) | `claude-dev:941`〜`:967` |
| 認証の受け渡し | 一時コンテナで共有ボリューム(ro)から `${PROJECT_DIR}/.claude/`(`.credentials.json` / `.claude.json`)と `${PROJECT_DIR}/.codex/auth.json` へコピーし、ホストの UID/GID へ `chown` する。**無い鍵は黙って飛ばす**(未ログインでも起動できる) | `claude-dev:749`〜`:766` |
| 認証の書き戻し | コンテナ内で 30 秒間隔のバックグラウンドループ | `scripts/entrypoint-claude.sh:449` |
| ファイアウォールの起動 | `/usr/local/bin/init-firewall.sh 2>/dev/null \|\| true` | `scripts/entrypoint-claude.sh:471` |

**環境変数の判定はすべて厳密一致**だが、比較する値は変数ごとに違う: `CLAUDE_DEV_VM` と
`CLAUDE_DEV_VNC` は **`= "1"`**(それ以外はすべて無効)、`CLAUDE_DEV_DOOD_PORTSYNC` は
**`!= "0"`**(`0` 以外の任意の値 — `abc` や `false` を含む — は有効)。したがって `true` / `yes` は
前者では無効、後者では有効になる。**受け側が値の不正を理由に起動を止めることはない。**

## 設計との差異

| 種別 | 設計(02)の期待 | 実装 | 対処 |
|---|---|---|---|
| 名前の一意性 | 「名前・ポート・プロファイルの**一意化で衝突を避ける**」(`02-design/contracts/cli-container.md` の「順序性・冪等性・並行性の背景」/ `NFR-scale-01`「衝突 0 件」) | **別パスの同名ディレクトリを同一セッションとして扱う**(コンテナ名・compose プロジェクト名をディレクトリ名だけから導くため)。`NFR-scale-01` の「衝突 0 件」を満たさない | **設計が正**と裁定済み(2026-08-04)。コード修正は別タスク。`docs/issues/028-modify-name-uniqueness-does-not-satisfy-nfr-scale-01.md` で追跡 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 空きポートの選定から `docker run` までが原子的でない | 同時起動でポート競合が起きうる(ブラウザ確認資産ありのときだけ最大20回の再試行で吸収する。**再試行はポート競合の文言判定に依存する**ため、文言が変わると吸収できない) | なし(閾値の外: 競合は最大20回の再試行で吸収し、吸収できなければ非0終了で**その場で気づける**。`forward` 側の選定(`docs/issues/010`)とは別関数) |
| `.claude/host-hooks.json` の名前が実態(hooks と env)と乖離している | 読み手が誤解しうる。歴史的経緯で据え置き | なし(閾値の外: 観測可能な被害が無い。名前だけの問題) |
| コンテナ名がディレクトリ名だけで決まる | 別パスの同名ディレクトリが同一セッション扱いになる | `docs/issues/028-modify-name-uniqueness-does-not-satisfy-nfr-scale-01.md`(**`NFR-scale-01` との不一致**) |
| `COMPOSE_PROJECT_NAME` の正規化が非可逆 | `[a-z0-9_-]` 以外を一律 `-` に置換するため、大文字違い・記号違いのディレクトリ名が同じ compose プロジェクト名に落ちる。`stop` の後片付けが**別プロジェクトのコンテナを巻き込みうる** | `docs/issues/024-modify-stop-can-delete-other-projects-compose-resources.md` |
| `CLAUDE_DEV_SSH_BRIDGE_PORT` を検証しない | **ホストの環境変数から読むため利用者が任意の値を与えられる**(`claude-dev-mac:274` の `${CLAUDE_DEV_SSH_BRIDGE_PORT:-}`)。不正な値でも socat の起動を試み、失敗しても成功時と同じ表示で起動が続く | `docs/issues/023-bug-ssh-bridge-port-accepts-unvalidated-host-env.md` |
| 起動途中の失敗で `${PROJECT_DIR}/.claude` / `.codex` が残る | 認証コピー以降の失敗ではコンテナが無いのに作業用ディレクトリだけが残る。**再実行で回復する**(いずれの手順も再入可能) | なし(閾値の外: 失敗は非0終了で**その場で気づける**。再実行で回復する) |

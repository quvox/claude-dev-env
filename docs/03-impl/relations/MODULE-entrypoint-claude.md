---
id: MODULE-entrypoint-claude
updated: 2026-08-19
module: MOD-entrypoint
kind: tool
sync: sync
impl: scripts/entrypoint-claude.sh::main
callers: MODULE-cli-start
callees: MODULE-firewall-init, MODULE-portsync-dood, MODULE-vm-mode-up
contracts: CTR-cli-container, CTR-entrypoint-firewall
design: DSN-mod-01, DSN-arch-01, DSN-auth-01, DSN-dist-02
requirements: FR-env-02, FR-env-03, FR-env-05, FR-env-06, FR-env-07, FR-env-08, FR-env-11, FR-env-12, FR-env-14
tests: なし(未実装。シェル実装のため自動テストランナーが無い。codex 経路は `scripts/e2e6-codex.sh` の実機検証で確認する)
summary: コンテナ起動時に UID/GID・認証共有・VNC・firewall・portsync を整える
---

# MODULE-entrypoint-claude コンテナ初期化

## 目的

コンテナの ENTRYPOINT として **root で1プロセス**起動し、内部の初期化を上から順に実行する。
UID/GID 追従(FR-env-02)、認証共有(FR-env-03)、firewall の適用(FR-env-05)、ポート同期
(FR-env-06・FR-env-07)、VM モードの起動(FR-env-08)、VNC/Chrome/noVNC(FR-env-11)、
エージェント CLI の既定設定(FR-env-12)を、この順序で成立させる。契約
`CTR-cli-container` の受け手であり、`CTR-entrypoint-firewall` の呼び出し側である。

## 処理の流れ

**起動シーケンスそのものが成果物である**(この順序に意味がある)。`set -e` の下で動くが、
失敗を許容してよい箇所には個別に `|| true` を付けて継続する。

1. **UID/GID 追従**: `/workspace` の所有者 UID/GID を `stat` で取り、コンテナユーザ(`$USERNAME`)と
   違えば `groupmod` / `usermod` で合わせる。他のエントリと衝突する場合は一時 GID/UID(9900〜の空き)へ
   退避してから割り当てる。変更が起きたときだけ、旧 UID または旧 GID を持つファイルに限って
   `find ... -exec chown` する(全走査を避ける)。`HOST_UID=0`(root 所有)なら変更しない。
2. **`~/.ssh` 整備**: 存在すれば所有権を設定し `chmod 700` する。`config` は CLI 側が
   `IdentityFile` / `IdentitiesOnly` / `IdentityAgent` を除去した加工版を RO マウントしている前提。
3. **KVM デバイスのグループ権限**: `/dev/kvm` / `/dev/vhost-net` があれば、その GID に一致する
   グループを用意し(無ければ `kvm-host-<gid>` を `groupadd`)、`$USERNAME` を追加する。
4. **SSH agent の受け口(macOS の TCP ブリッジ)**: `CLAUDE_DEV_SSH_BRIDGE_PORT` が渡され `socat` が
   あれば、既存の `/tmp/ssh-agent.sock` を消してから
   `socat UNIX-LISTEN:/tmp/ssh-agent.sock,fork,mode=600 TCP:host.docker.internal:<port>` を
   ユーザ権限で起動し、ソケットの出現を最大20回×0.2秒待つ。Linux 版はホストの `$SSH_AUTH_SOCK` を
   直接 bind してあるのでこの分岐を通らない。
5. **`SSH_AUTH_SOCK` を確定させる**: `/tmp/ssh-agent.sock` があれば
   `export SSH_AUTH_SOCK=/tmp/ssh-agent.sock` を `/etc/zsh/zshrc` と `/etc/bash.bashrc` へ追記し、
   **同じ値を entrypoint 自身の環境にも `export` する**(macOS 経路では手順4 が作ったソケットであり、
   ホストの `-e` では渡ってきていないため、ここで載せないと手順20 が引き継げない)。
   **これが効くのは対話シェルだけである** — 初期化ファイルを読むのは対話シェルだけなので、
   非対話シェルにも、tmux の窓の中で起動したプロセスにも届かない。**それらへ届けるのは手順20 である。**
6. **`DOCKER_HOST` を対話シェル向けに書き出す**: 設定されていれば同様に両 rc へ追記する。
   届く範囲は手順5 と同じで、**tmux の窓の中へ届けるのは手順20 である**。
7. **`COMPOSE_PROJECT_NAME` は rc へ書き出さない**: 値はホスト CLI が `docker run -e` で渡す
   (`MODULE-cli-start` の責務)。entrypoint がこの変数について負う仕事は、
   **手順20 で tmux サーバへ引き継ぐこと**である。
8. **`.zshrc` 共有**: `~/.config-shared/` に `.zshrc` が無ければ、`~/.zshrc.default` → 実体 `~/.zshrc` →
   空ファイル の順にコピー元を決めて作る。以後 `~/.zshrc` を共有ファイルへの symlink にする。
9. **`~/.claude` / `~/.codex` の構成と認証共有**: `/workspace/.claude` を確保し、`~/.claude` が実
   ディレクトリなら中身を `cp -an` で退避して削除し、`~/.claude → /workspace/.claude` の symlink を張る。
   認証ファイル(`.credentials.json` / `.claude.json`。CLI がコピー済み)の所有権と `chmod 600` を整え、
   `~/.claude.json` → `/workspace/.claude/.claude.json` の symlink を張る。
   codex も同じ形にする(`~/.codex → /workspace/.codex`、`auth.json` を `chmod 600`)。
   `config.toml` とセッション履歴は共有せずプロジェクトに残す。**イメージにはビルド時の
   `codex --version` が作った実 `~/.codex` があるため、この退避は初回起動で必ず通る**。
   共有側(`~/.claude-shared/codex`)はこの段より前に `mkdir -p` + `chown` で用意する
   (`login-codex` を一度も実行していなくても同期ループが書き戻せるように)。
10. **既定設定の生成**: `settings.json` が無ければ
    `{"permissions":{"defaultMode":"bypassPermissions"},"model":"sonnet"}` を作る(共有しない)。
    codex 側は `config.toml` に既定3鍵 —
    `sandbox_mode = "danger-full-access"` / `approval_policy = "never"` /
    `[features]` の `use_legacy_landlock = true` — を保証する。
    **既にある鍵とその値は一切書き換えず、不足している鍵だけを足す**(冪等)。
    判定・生成・検証は `/usr/bin/python3` の `tomllib` で行い、
    **「候補を作る → 意味的に検証する → 通ったときだけ原子的に置き換える」**手順を取る:
    - 判定は正規表現ではなく `tomllib` のパース結果のキーパス有無で行う。したがって `"sandbox_mode"`
      のような引用符付きキー、`features.use_legacy_landlock` のドット記法、行コメントの中の
      同名文字列を、いずれも TOML の文法どおりに解釈する(誤検出・見落としが起きない)。
      パースできないファイルは**何も書かず警告だけ**出す。
    - 追記位置は、トップレベル2鍵がファイル先頭、`use_legacy_landlock` は
      ①`[features]` 見出しの直後 → ②末尾に見出しごと追記 の順に試す。
    - `features` が配列テーブル(`[[features]]`)やインラインテーブルの場合は、既存値を変えずに
      鍵を足す書き方が TOML に無いので landlock だけ諦めて警告する。
    - **検証**: 書く前に候補を再パースし、既存の全キーパスの値が1つも変わっていないことと、
      増えた鍵が意図したものだけであることを確かめる。外れたら書かない。
    - 置き換えは同ディレクトリに `mkstemp`(`O_EXCL` / 0600)で作り、uid/gid を写してから mode を写し
      (この順でないと Linux が setuid/setgid を落とす)、`os.replace` で原子的に差し替える。
      リダイレクトによる truncate は使わない。所有者を復元できない場合は差し替えを中止する。
    - `python3` / `tomllib` が使えない環境では**既存ファイルに一切触れず**警告だけ出す。
11. **ホスト設定のマージ**: `host-hooks.json`(名称は歴史的経緯。`hooks` と `env` の両方を運ぶ)があり
    `.hooks` か `.env` を含むなら、`jq '. * $overlay[0]'` で `settings.json` へ深くマージして元を消す。
    失敗したら警告して続行する。
12. **ユーザ hook スクリプトの配置**: `host-local-bin/` があれば `~/.local/bin/` へ
    `cp -a --update=none` でコピーし(イメージ焼き込み済みを上書きしない)、実行権を付けて元を消す。
13. **認証のバックグラウンド同期**: 30秒ごとに `/workspace/.claude` の認証ファイルを共有ボリュームと
    `cmp` し、差分があれば書き戻すループを背後で回す(トークンリフレッシュの伝播)。同じループで
    `/workspace/.codex/auth.json` を `~/.claude-shared/codex/auth.json` と比べ、差分があれば
    `mkdir -p` → `cp` → `chmod 600` する。**ループは root で走るため共有側は root 所有になる**
    (そのため `MODULE-cli-login-codex` が書き込み前に `chown -R` する)。
14. **firewall の起動**: `/usr/local/bin/init-firewall.sh` を実行する(失敗は無視する)。
15. **VM モードの起動**(`CLAUDE_DEV_VM=1` のとき): root のうちに `install -d -o $USERNAME` で
    `~/.claude-dev-vm` と `/run/vm` を用意し、`su "$USERNAME" -c /usr/local/bin/vm-up.sh` を実行する。
    成功したときだけ `/etc/claude-dev/vm.env` に `DOCKER_HOST=tcp://127.0.0.1:2375` を書き、両 rc へ
    source フックを追記し、**同じ値を entrypoint 自身の環境にも `export` して**、`VM_DEV.md` を生成して
    バナーを出す。失敗したら proxy 既定のまま続行する。
    **自身の環境にも載せるのは、手順20 が引き継ぐ値を「その時点で有効な値」に一致させるためである** —
    載せないと、対話シェルはゲスト VM を指し、tmux の窓の中のプロセスは docker-proxy を指す、という
    2つの値が同居する(02 の契約は「VM モードでは entrypoint が上書きする」と1つの値しか認めていない)。
16. **portsync の起動**: `CLAUDE_DEV_VM != 1` かつ `CLAUDE_DEV_DOOD_PORTSYNC != 0` かつ `DOCKER_HOST` が
    `docker-proxy` を含み、`dood-portsync.sh` が実行可能なとき、`setsid ... --loop &` で常駐起動する。
17. **CLAUDE.md への環境情報の書き込み**: マーカー `<!-- claude-dev-auto-start -->` 〜
    `<!-- claude-dev-auto-end -->` の範囲を毎回 `sed` で消してから再生成する。常に「注意事項」と
    「Docker ネットワーク(重要)」を書き、`CLAUDE_DEV_VNC=1` なら「Web アプリの動作確認(重要)」、
    `/dev/kvm` があり `CLAUDE_DEV_VM != 1` なら「KVM / 仮想化(重要)」を足す。VM モードでは KVM/VM の
    情報を CLAUDE.md に書かず `VM_DEV.md` に集約する。`/workspace/CLAUDE.md` が無ければ作る。
18. **MCP 設定**(`CLAUDE_DEV_VNC=1` のときのみ): `/workspace/.mcp.json` に `chrome-devtools`
    (`npx -y chrome-devtools-mcp@latest --browserUrl http://localhost:9222`)を確保する。
    `rmcp-xdotool` があるときだけ `computer-use` を未定義時に足す(**`enabledMcpjsonServers` には
    追加しない** = 既定で無効。強権限のため利用時に明示有効化させる)。
    `/workspace/.claude/.claude.json` の `projects["/workspace"].enabledMcpjsonServers` へ
    `chrome-devtools` を追加する(未登録時のみ。ファイルが無ければ `{}` を作り `chmod 600`)。
19. **VNC / Chrome / noVNC の起動**(`CLAUDE_DEV_VNC=1` のときのみ): システム D-Bus 起動・GTK
    immodules キャッシュ更新・`~/.vnc/xstartup` 用意の後、`/tmp/start-user-desktop.sh` を生成して
    ユーザ権限で背後起動する。中身は順に `Xvnc :99 -geometry 1280x800 -depth 24 -SecurityTypes None
    -rfbport 5999`、`setxkbmap -layout us,jp`、D-Bus セッションバス、`openbox`、
    `ibus-daemon -xrR` と Mozc のプリロード/ホットキー、
    `websockify --heartbeat 30 --web /usr/share/novnc 6080 localhost:5999`、
    Chrome の残存ロック(`SingletonLock` 等)削除の後に
    `claude-dev-chrome ... --remote-debugging-port=9222 --user-data-dir=~/.chrome-profile`。
20. **tmux セッションの開始**: `su "$USERNAME" -s /bin/zsh -c "cd /workspace &&
    tmux -f ~/.tmux.conf new-session -d -s main 'exec zsh -l'"`。
    **`-l` を付けない。** 付けると、ホストの `-e` で渡された変数もイメージの `ENV` で付いた変数も
    利用者のプロジェクト環境ファイルの組も**まとめて捨てられる**。
    **tmux サーバの環境はその配下の全ウィンドウ・全プロセスが継承する**ので、
    捨てられた変数は tmux の中のどこからも見えなくなる(`FR-env-07-13` / `FR-env-14-11` /
    `CTR-cli-container`「渡す環境変数」)。
    **`-l` の有無で `PATH` と `HOME` は変わらない** — 2026-08-19 に実機で
    `su <user> -s /bin/zsh -l -c` と `su <user> -s /bin/zsh -c` を並べて測り、どちらも
    `PATH` は同一、`HOME` は同一だった。違うのは `PWD` だけで(`~` → `/workspace`)、
    このコマンドは自分で `cd /workspace` するので影響しない。
    **`exec zsh -l` が掛かるのは `new-session` が同時に作る最初の窓だけ**で、以後の窓は
    `scripts/tmux.conf:15` の `default-command /bin/zsh`(`-l` 無し)で起こる。それでも
    手順5・手順6 が書き出した `export` は効く — `/etc/zsh/zshrc` と `/etc/bash.bashrc` を
    読むのはログインシェルかどうかではなく**対話シェルかどうか**だからである。
    **`tmux` の `update-environment` を当てにしない**: 既定値の8個(`DISPLAY` / `SSH_AUTH_SOCK` ほか)は
    クライアント接続時にセッション環境へ写されるが、それ以外は1つも含まれず、
    しかも**最初の接続より前に作られた窓には効かない**。
21. **常駐**: `✅ Ready (...)` を表示して `exec tail -f /dev/null` で待つ。

## 呼び出され方

- 契機: `docker run` によるコンテナ起動(Dockerfile の `ENTRYPOINT`)。起動するのは
  `MODULE-cli-start`。
- 前提条件: 契約 `CTR-cli-container` が定める環境変数とマウントが渡っていること
  (`/workspace`・共有3ボリューム・`tmux.conf` / `CLAUDE.md` の RO マウント・`DOCKER_HOST` 等)。
  `NET_ADMIN` / `NET_RAW` が付与されていること。
- 引数: なし(コマンドライン引数・関数 API を持たない)。

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `CLAUDE_DEV_VNC` | 環境変数 | 任意 | `1` で VNC/Chrome/noVNC と MCP 設定を有効化 |
| `CLAUDE_DEV_VM` | 環境変数 | 任意 | `1` で VM モードを起動する |
| `CLAUDE_DEV_DOOD_PORTSYNC` | 環境変数 | 任意 | `0` で portsync を起動しない(既定 1) |
| `CLAUDE_DEV_SSH_BRIDGE_PORT` | 環境変数 | 任意 | macOS の socat ブリッジの接続先ポート |
| `DOCKER_HOST` | 環境変数 | 任意 | docker-proxy を指していれば DooD とみなす |

- 認可: root(コンテナ内)。ユーザ権限が要る処理は `su "$USERNAME"` で降りて実行する。

## 連携先と連携内容

### MODULE-firewall-init

- 何のために呼ぶか: 起動シーケンス中に1度だけ egress のブラックリストを適用するため
  (契約 `CTR-entrypoint-firewall`)。
- 何を渡すか: なし(`/usr/local/bin/init-firewall.sh` を引数なしで実行する)。
- 何を受け取るか: 終了ステータス(参照しない)。
- **失敗したときどうなるか**: **無視して起動を続ける**(適用の成否に関わらず entrypoint は継続する。
  これが契約の定めである)。成否はスクリプトのサマリと `⚠️ WARNING` 行で判別する。

### MODULE-portsync-dood

- 何のために呼ぶか: DooD でホストに公開されたポートへ、コンテナ内の `127.0.0.1:PORT` から
  到達できるようにするため。
- 何を渡すか: `DOCKER_HOST` を引き継いだ環境で `--loop` を付けて `setsid` 起動する。
- 何を受け取るか: なし(常駐プロセスとして切り離す)。
- **失敗したときどうなるか**: `socat` 不在やデフォルトゲートウェイ不明で相手が `exit 1` しても、
  entrypoint は起動を続ける。ポート転送が張られないだけになる。

### MODULE-vm-mode-up

- 何のために呼ぶか: `CLAUDE_DEV_VM=1` のときにゲスト VM を起動し、ネイティブ Docker を使えるように
  するため。
- 何を渡すか: `su "$USERNAME" -c /usr/local/bin/vm-up.sh`(制御は `VM_*` 環境変数)。
- 何を受け取るか: **終了コードだけ**(0 = ゲスト dockerd 準備完了)。
- **失敗したときどうなるか**: 失敗バナーを出し、`/etc/claude-dev/vm.env` を書かず
  `DOCKER_HOST` も上書きしない。**既定の DooD 経路を維持して起動を続ける**(docker が全面不通に
  なるのを避けるため)。

<!-- 上の3件はいずれも `/usr/local/bin/...` に配置された絶対パスで起動するため、
     shell 抽出器はソースファイルへ解決できず、コールグラフに辺が現れない。
     契約と実コードに基づいて宣言しており、`callgraph-check.py` の CG3 に
     「機械が出した辺に対応するものが無い」として出るのは想定内である。 -->

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 終了しない(`exec tail -f /dev/null` で常駐する) |
| 永続化 | `/workspace/.claude/`(`settings.json`・`.claude.json`・認証)、`/workspace/.codex/`(`auth.json`・`config.toml`)、`/workspace/CLAUDE.md`(マーカー範囲)、`/workspace/.mcp.json`、`/workspace/VM_DEV.md`(VM 時)、共有ボリューム `claude-dev-auth`(30秒ごとの書き戻し)と `claude-dev-config`(`.zshrc`)、`/etc/zsh/zshrc` と `/etc/bash.bashrc`、`/etc/claude-dev/vm.env`(VM 時)、`/tmp/start-user-desktop.sh` |
| 発火するイベント | 認証同期ループ、firewall 適用、portsync 常駐、VM 起動、VNC/Chrome/noVNC、tmux セッション `main` |
| ログ | 標準出力へ各段の進捗と `✅ Ready (...)` |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| UID/GID が他のエントリと衝突する | 一時 GID/UID(9900〜の空き)へ退避してから割り当てる | 起動は成功する |
| `/workspace` が root 所有(`HOST_UID=0`) | UID/GID を変更しない | ホストと所有者がずれる可能性がある |
| `config.toml` がパースできない | **何も書かず警告だけ出す**(既存ファイルを温存する) | codex の既定設定が入らない |
| `config.toml` の挿入候補が検証に落ちた | 書き込まない | 同上。要件違反の書き換えは検証で必ず止まる |
| `python3` / `tomllib` が使えない | 既存ファイルに一切触れず警告のみ(新規生成は行う) | 同上 |
| `config.toml` の所有者を復元できない | 差し替えを中止する(黙って所有者を変えない) | 同上 |
| `ensure_codex_config` が失敗 | `|| true` で握りつぶす(`set -e` の下でも起動を止めない) | codex を使わない利用者の起動を止めない |
| firewall の適用に失敗 | 無視して続行する | ネットワーク制限がかからないまま起動する |
| `vm-up.sh` が失敗 | 失敗バナーを出し `DOCKER_HOST` を上書きせず DooD 経路を維持する | VM は使えないが docker は使える |
| `host-hooks.json` のマージに失敗 | 警告して続行する | ホストの hooks / env が反映されない |
| Chrome のプロファイルロックが残っている | `SingletonLock` 等を消してから起動する | 起動できる |
| ホストが `DOCKER_HOST` を渡していない(ホストに Docker ソケットが無い) | 変数が無いまま tmux が起動する(引き継ぎは「在るものを継ぐ」だけなので分岐しない) | tmux は立つが、その窓から `docker` は使えない(`CTR-cli-container` が「到達できなければコンテナ内から Docker が使えないだけで、起動は続く」と定める範囲) |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 認証は symlink ではなく「起動時コピー + 30秒書き戻し」にする(Claude Code のアトミック書き込みで symlink が壊れるため) | D0-auth-02 |
| 2 | codex も claude と同じ形(`~/.codex → /workspace/.codex` の symlink、`auth.json` はコピーと書き戻し)に揃える。`auth.json` はその場書き換えで symlink でも壊れないが、同期ループと片付け経路を2方式に分けないため | D0-auth-01 |
| 3 | codex の既定3鍵を置く。既定のサンドボックス(bubblewrap)はコンテナ内で起動できない(Docker 既定 seccomp が `CLONE_NEWUSER` を拒否し、外しても `docker-default` AppArmor が `mount --make-rslave /` を拒否する)。`--sandbox read-only` のようにサンドボックスを明示要求する呼び出しは config の既定を上書きして bwrap 経路に戻るため、ユーザー名前空間を必要としない landlock バックエンドを有効にする。**コンテナ側の `--security-opt` を緩める対処は取らない** | D0-sec-01 |
| 4 | `config.toml` の不足鍵補完を行単位の正規表現ではなく `tomllib` のパース + 検証方式で行う(当初の awk 実装は「複数行文字列内の `[features]` を見出しと誤認する」「quoted key を見落として同一鍵を二重定義する」という反例が独立レビューで出たため作り直した) | D0-scope-05 |
| 5 | CLAUDE.md への書き込みをマーカー範囲の削除 + 再生成にする(`--kvm` の付け外しに追従でき、利用者の記述を壊さない) | D0-scope-02 |
| 6 | `computer-use` MCP を `enabledMcpjsonServers` に入れない(強権限のため利用時に明示有効化させる) | D0-sec-01 |

- [DS-05] tmux セッションを起こす `su` から **`-l` を外す**(名前を列挙して載せ直す形にも、`tmux.conf` の `update-environment` に足す形にもしない) — 理由: **列挙しないので、コンテナに渡っている変数がそのまま全部引き継がれる** — 利用者がプロジェクト環境ファイルに書いた組(`AC-08`)も、時刻帯や文字の並び順も同時に届く。列挙する形は、変数が増えるたびに列挙も増やす必要があり、増やし忘れが `AC-08` の不合格として現れた経路そのものである。`update-environment` はクライアント接続時にしか働かないので、**接続より前に作られる窓**(この手順は `new-session -d` で接続なしに作る)に効かない。同じ entrypoint の中で `su` を使うもう1箇所(`start-user-desktop.sh` の起動)が既に `-l` を付けておらず、この形の前例である / 見直す条件: `-l` の有無で `PATH` か `HOME` が変わる環境が現れたとき、またはコンテナに渡る変数の中に tmux の窓へ渡してはならないものが現れたとき

<!-- 2026-08-19 更新(`.claude/directions/delegation.md` §3.1)。前の版はこの判断の逆(`-l` を残して
     予約名を列挙して載せ直す)を採っており、理由に「`-l` を外すと `PATH` / `HOME` / 作業ディレクトリまで
     変わる」と書いていた。**実機で両方を並べて測ったところ `PATH` も `HOME` も同一**で、この理由は
     事実として誤りだった(原則2)。あわせて、列挙する形では `AC-08` を満たせないことが分かった。 -->

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| `host-hooks.json` の名前が実態(`hooks` と `env` の両方を運ぶ)と乖離 | 読み手が誤解しうる。歴史的経緯で据え置き | なし |
| `use_legacy_landlock` は codex 0.146.0 時点で deprecated(起動時に警告が出る) | 版更新で撤去された場合は監査を添付方式へ退避する必要がある(検知は E2E-06 の疎通確認) | なし |
| 認証同期ループが root で走るため共有側が root 所有になる | `login-codex` 側で `chown -R` して補っている | なし |
| **稼働中の tmux サーバの環境は後から変えられない** | コンテナを起動した後に環境変数を足しても、既に立っている tmux サーバとその配下には入らない | なし(閾値の外: `claude-dev start` でコンテナを作り直せば揃う。稼働中に足すことは `tmux set-environment -g` で人手でできるが、それは製品の経路ではない) |
| 起動シーケンスが1本の長いスクリプト | 段階ごとの単体テストができず、検証は実機確認に依存する | なし |

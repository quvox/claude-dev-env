---
id: entrypoint
layer: impl
title: entrypoint 実装説明書
version: 1.8.0
updated: 2026-07-31
verified:
  at: 2026-07-31
  version: 1.8.0
  against:
    - doc: docs/02-design/system.md
      version: 1.9
summary: >
  Claude コンテナの ENTRYPOINT として root で起動し、UID/GID 追従・認証共有（claude/codex）・
  既定設定生成（claude settings.json / codex config.toml）・MCP 生成・firewall/portsync 起動・
  VNC/Chrome 起動・tmux セッション開始までを行う初期化シェルスクリプトの実装。
keywords: [entrypoint, UID/GID, 認証共有, codex, Codexサンドボックス, config.toml, MCP, VNC, Chrome, tmux, firewall, portsync]
depends_on: [firewall, portsync]
source:
  - docs/02-design/system.md
---

# 実装説明書:entrypoint

## 概要

`scripts/entrypoint-claude.sh` は Claude コンテナの ENTRYPOINT として **root で 1 プロセス**起動し、
コンテナ内部の初期化を上から順に実行する初期化スクリプトである（上流: [全体設計](../02-design/system.md)、
契約「cli → コンテナ/entrypoint」「entrypoint → firewall」）。主な責務は、(1) `/workspace` 所有者に合わせた
UID/GID 追従、(2) 共有ボリューム経由の認証共有（claude / codex）と `~/.claude`・`~/.codex` の symlink 化、
(3) 既定設定生成（claude `settings.json`／codex `config.toml`＝既定でのサンドボックス無効化と読み取り専用用途の landlock 有効化）と MCP 設定生成、
(4) `firewall` 起動、(5) `portsync`（DooD ポート転送）起動、(6) VNC/Chrome/noVNC 起動（VNC イメージ時のみ）、
(7) `tmux` セッション開始。最後に `exec tail -f /dev/null` で常駐する。
要件 core/2,3,5,11,12(12-4〜12-6,12-9) を担う。

## ファイル構成

| パス | 役割 |
|---|---|
| scripts/entrypoint-claude.sh | ENTRYPOINT 本体（ビルド時に `/usr/local/bin/entrypoint.sh` へ配置）。本モジュールの全実装 |
| /usr/local/bin/init-firewall.sh | 起動時に呼び出す firewall 適用スクリプト（[firewall](firewall.md) が提供） |
| /usr/local/bin/dood-portsync.sh | DooD ポート転送常駐ヘルパ（[portsync](portsync.md) が提供、entrypoint が起動） |
| /tmp/start-user-desktop.sh | entrypoint が実行時生成する VNC/Chrome 起動スクリプト（VNC イメージ時のみ） |

## モジュール別実装詳細

### entrypoint 本体(scripts/entrypoint-claude.sh)

- **責務:** コンテナ起動時初期化（設計書のコンポーネント: entrypoint）。root で起動し、上から順の逐次処理で
  ユーザー環境・認証・設定・ネットワーク・GUI・tmux を用意する。`set -e` 有効だが、失敗を許容すべき箇所は
  各コマンドに `|| true` を付けて継続する。
- **公開インターフェース:** コマンドライン引数・関数 API は持たない。Dockerfile の `ENTRYPOINT` として起動され、
  環境変数（後述「設定・環境変数」）と `/workspace` 等のマウントを入力に取る。
- **処理の要点（起動シーケンス。この順序が成果物）:**
  1. **UID/GID 追従:** `/workspace` の所有者 UID/GID を `stat` で取得し、コンテナユーザー（`$USERNAME`）の
     現 UID/GID と異なれば `groupmod`/`usermod` で合わせる。GID/UID が他エントリと衝突する場合は一時
     GID/UID（9900〜、空きを探索）へ退避してから割り当てる。変更が起きた場合のみ、旧 UID または旧 GID を
     持つファイルだけを `find ... -exec chown` で更新（全走査回避）。`HOST_UID=0`（root 所有）なら変更しない。
  2. **~/.ssh 整備:** `$USER_HOME/.ssh` が存在すれば所有権を設定し `chmod 700`。`config` は CLI 側で
     `IdentityFile`/`IdentitiesOnly` 等を除去した加工版が RO マウントされる前提（正本は cli/cli-mac）。
  3. **KVM デバイスのグループ権限:** `/dev/kvm`・`/dev/vhost-net` が存在すれば、そのデバイスの GID に一致する
     グループをコンテナ内に用意（無ければ `kvm-host-<gid>` を `groupadd`）し、`$USERNAME` を `usermod -aG` で追加。
  4. **SSH agent の受け口（macOS TCP ブリッジ）:** `CLAUDE_DEV_SSH_BRIDGE_PORT` が渡され `socat` があれば、
     既存 `/tmp/ssh-agent.sock` を削除後、`su "$USERNAME" -c "nohup socat UNIX-LISTEN:/tmp/ssh-agent.sock,fork,mode=600 TCP:host.docker.internal:<port> ... &"`
     でユーザー権限のブリッジを起動し、ソケット出現まで最大 20 回×0.2 秒待機。Linux 版は `$SSH_AUTH_SOCK` を
     `/tmp/ssh-agent.sock` へ直接 bind mount 済みで本分岐を通らない。
  5. **SSH_AUTH_SOCK 永続化:** `/tmp/ssh-agent.sock` が存在すれば `export SSH_AUTH_SOCK=/tmp/ssh-agent.sock`
     を `/etc/zsh/zshrc`・`/etc/bash.bashrc` に追記（`su -l` でのリセット対策）。
  6. **DOCKER_HOST 永続化:** `DOCKER_HOST` があれば同様に両 rc へ追記（Docker CLI `default` コンテキストが
     環境変数を参照するためカスタム context は不要）。
  7. **COMPOSE_PROJECT_NAME はここでは設定しない:** docker compose の既定名衝突（全プロジェクトが
     `/workspace` にマウントされ既定名が `workspace` に衝突する）の一意化は、rc 追記だと非対話シェル
     （`bash -c` 実行）に効かないため、ホスト CLI が `docker run` の `-e COMPOSE_PROJECT_NAME` で渡す
     （正本は cli/cli-mac。`DOCKER_HOST` と同様に全シェル・`docker exec` で有効）。entrypoint は関与しない。
  8. **.zshrc 共有:** `~/.config-shared/`（ボリューム）に `.zshrc` が無ければ、`~/.zshrc.default`→実体 `~/.zshrc`→
     空ファイルの順でコピー元を決めて作成。以後 `~/.zshrc` を共有ファイルへの symlink にする（コンテナ間共有）。
  9. **~/.claude・~/.codex 構成と認証共有:** `LOCAL_CLAUDE=/workspace/.claude` を確保。`~/.claude` が実ディレクトリなら
     中身を `cp -an` で退避して削除し、`~/.claude → /workspace/.claude` の symlink（`ln -sfn`）を張る。認証ファイル
     （`.credentials.json`・`.claude.json`。CLI がコピー済み）は所有権と `chmod 600` を整える。`~/.claude.json`
     （ホーム直下）→ `/workspace/.claude/.claude.json` の symlink を張る。
     続けて codex 側も同形に整える——`LOCAL_CODEX=/workspace/.codex` を確保し、`~/.codex` が実ディレクトリなら
     中身を `cp -an` で退避して削除して `~/.codex → /workspace/.codex` の symlink を張り、認証ファイル
     `auth.json`（CLI がコピー済み）の所有権と `chmod 600` を整える。`config.toml`・セッション履歴は共有せず
     このディレクトリ（＝プロジェクト）に残す（要件 core/3-7,3-9）。**イメージには実 `~/.codex` が存在する**
     （ビルド時の `codex --version` が作る）ため、この退避処理は初回起動で必ず通る経路である。
     共有側（`$SHARED_CLAUDE/codex`）はこの段より前に `mkdir -p`＋`chown` で用意する（`login-codex` を
     一度も実行していない場合でも同期ループが書き戻せるようにするため）。
  10. **settings.json 生成:** `$LOCAL_CLAUDE/settings.json` が無ければ
      `{"permissions":{"defaultMode":"bypassPermissions"},"model":"sonnet"}` を生成（共有しない）。
      **同じ考え方で codex 側も既定設定を置く**——`$LOCAL_CODEX/config.toml` に対し、既定 3 鍵
      `sandbox_mode = "danger-full-access"` / `approval_policy = "never"` /
      `[features]` テーブルの `use_legacy_landlock = true` を保証し、所有権を `$USERNAME` に整える
      （共有しない）。ファイルが無ければ 3 鍵を生成する。既に存在する場合は**書かれている鍵とその値を
      一切書き換えず、不足している鍵だけを追記する**。同じ設定で何度起動しても結果は変わらない（冪等）。
      要件 core/12-5,12-6・D-27 ⑥。
      **不足鍵の判定と追記（TOML の構造を壊さないこと）:** 行単位の正規表現では TOML の構文状態を
      追えないため、判定・生成・検証は `/usr/bin/python3` の `tomllib` で行う（ubuntu 24.04 標準。
      root の素の PATH で到達でき、pyenv 初期化を必要としない）。手順は
      **「候補を作る → 意味的に検証する → 通ったときだけ原子的に置き換える」**:
      - **判定**: ファイルを `tomllib` でパースし、キーパス（`sandbox_mode` /`approval_policy` /
        `features.use_legacy_landlock`）の有無で判断する。パーサが正規化するので、quoted key
        （`"sandbox_mode" = ...`）・ドット記法（`features.use_legacy_landlock = ...`）・
        コメント行が自動的に正しく扱われる。**パースできないファイルは何も書かず警告のみ**。
      - **追記位置**: トップレベル 2 鍵は**ファイルの先頭**へ入れる（先頭は常にトップレベルなので、
        「最初のテーブル見出しより前」を満たす最も安全な位置）。`use_legacy_landlock` は
        **①`[features]` 見出し行の直後 → ②末尾に見出しごと追記** の 2 戦略を、下の検証を通った
        最初の候補が採られる形で順に試す。見出しの検出は正規表現で行い、行末コメント
        （`[features] # ...`）・quoted key（`["features"]`）・空白（`[ features ]`）を許容する。
        暗黙の親テーブルしか無い場合（`[features.child]` だけがある等）は ① が空振りして ② が通る。
      - **追記できない場合**: `features` が配列テーブル（`[[features]]`）で定義されている、または
        インラインテーブル（`features = { ... }`）に当該鍵が無い場合は、既存値を変えずに鍵を足す
        書き方が TOML に無いので landlock だけ諦めて理由を警告する（トップレベル鍵の補完は行う）。
      - **検証（この方式の要）**: 書き込む前に候補を再度パースし、**既存の全キーパスの値が
        1 つも変わっていないこと**と**増えたキーが意図した鍵だけであること**を確かめる。
        外れたら書き込まない。挿入位置のヒューリスティックが想定外の入力で外れても、
        要件 core/12-6 違反はこの検証で必ず止まる。
      - **置き換え**: 同じディレクトリに `mkstemp`（`O_EXCL`・0600）で一時ファイルを作り、元ファイルの
        uid/gid を写してから mode を写し（この順序でないと Linux が setuid/setgid を落とす）、
        `os.replace` で原子的に差し替える。リダイレクトによる truncate は使わない（途中で失敗すると
        元ファイルを壊し、「失敗時は元ファイルを温存」の契約を破るため）。所有者を復元できない場合は
        差し替えを中止する（黙って利用者のファイルの所有者を変えないため）。
      - `python3`／`tomllib` が使えない環境では、**既存ファイルには一切触れず**警告のみ出す
        （新規生成は影響を受けない）。
      （配置規則は 2026-07-31 の人間判断。feedback/log.md [17]。tomllib 方式への作り直しは
      同日の独立レビュー指摘による。feedback/log.md [19]）
      前 2 鍵が必要な理由は、codex の既定サンドボックス（bubblewrap 実装）がコンテナ内で起動できないこと
      ——Docker 既定 seccomp が `CLONE_NEWUSER` を拒否し、それを外しても `docker-default` AppArmor が
      `mount --make-rslave /` を拒否するため、既定の `sandbox_mode` では codex のシェルコマンドが例外なく
      `exited 1` になる。3 鍵目が必要な理由は、`--sandbox read-only` のようにサンドボックスを**明示要求
      する呼び出し**（コードレビューや文書監査を codex に依頼する経路）が config の既定を上書きして
      bwrap 経路に戻ってしまうこと——landlock バックエンドはユーザー名前空間を必要としないため、
      confinement を緩めずに読み取り専用を成立させられる（要件 core/12-9、設計判断は 02-design 判断5）。
      コンテナ側の `--security-opt` を緩める対処は取らない（要件 core/12-7）。
      なお `use_legacy_landlock` は codex 0.146.0 時点で deprecated（起動時に警告が出る）であり、
      版更新で撤去された場合は監査を添付方式へ退避する（検知は E2E-6 の疎通確認）。
  11. **ホスト設定マージ:** `host-hooks.json`（名称は歴史的経緯で `hooks`/`env` 両方を運ぶ）があり `.hooks` か
      `.env` を含むなら `jq '. * $overlay[0]'` で `settings.json` へ深いマージし、元ファイル削除。失敗時は警告し継続。
  12. **ユーザー hook スクリプト配置:** `host-local-bin/` があれば `~/.local/bin/` へ `cp -a --update=none`
      （イメージ焼き込み済みを上書きしない）し、実行権付与後に元を削除。
  13. **認証バックグラウンド同期:** 30 秒ごとに `LOCAL_CLAUDE` の認証ファイルを共有ボリュームと `cmp` し、
      差分があれば書き戻すループを `( while true; ... ) &` でバックグラウンド起動（トークンリフレッシュ伝播）。
      同じループで codex の `LOCAL_CODEX/auth.json` を `~/.claude-shared/codex/auth.json` と `cmp` し、
      差分があれば `mkdir -p`→`cp`→`chmod 600` で書き戻す（対象ファイルが増えるだけで、ループ・間隔・
      比較方法は claude と共通。要件 core/3-8）。ループは root で走るため共有側のファイルは root 所有に
      なる（claude 側と同じ既存挙動）。そのため `login-codex` は書き込み前に `chown -R` する（cli 側の責務）。
  14. **firewall 起動:** `/usr/local/bin/init-firewall.sh` を実行（失敗は無視）。契約「entrypoint → firewall」。
  15. **VM モード起動（`CLAUDE_DEV_VM=1` 時）:** root のうちに `install -d -o $USERNAME` でマウント点
      `~/.claude-dev-vm`・`/run/vm` を用意し、`su "$USERNAME" -c /usr/local/bin/vm-up.sh` で起動。成功時のみ
      `/etc/claude-dev/vm.env` に `DOCKER_HOST=tcp://127.0.0.1:2375` を書き、両 rc に source フック追記・
      `VM_DEV.md` 生成・バナー表示。失敗時は proxy 既定を維持して継続（詳細正本は vm-mode）。
  16. **portsync 起動（DooD ポート転送）:** `CLAUDE_DEV_VM != 1` かつ `CLAUDE_DEV_DOOD_PORTSYNC != 0` かつ
      `DOCKER_HOST` が `docker-proxy` を含み、`dood-portsync.sh` が実行可能なとき、
      `su "$USERNAME" -c "DOCKER_HOST=... setsid /usr/local/bin/dood-portsync.sh --loop &"` で常駐起動。
      依存モジュール [portsync](portsync.md)。
  17. **CLAUDE.md 環境情報書き込み:** マーカー `<!-- claude-dev-auto-start -->`〜`<!-- claude-dev-auto-end -->`
      で囲んだ範囲を毎回 `sed` で削除（旧形式セクションも除去）→再生成する。常に「注意事項」「Docker
      ネットワーク（重要）」（自コンテナ名でのアクセス指示）を書き込み、`CLAUDE_DEV_VNC=1` なら「Web アプリの
      動作確認（重要）」、`/dev/kvm` が存在しかつ `CLAUDE_DEV_VM != 1` なら「KVM / 仮想化（重要）」を追記する。
      VM モードでは KVM/VM 情報を CLAUDE.md に書かず `VM_DEV.md` へ集約（CLAUDE.md 不可侵方針）。
      `/workspace/CLAUDE.md` が無ければ作成する。マーカー方式により `--kvm` の付け外しにも追従する。
  18. **MCP 設定（`CLAUDE_DEV_VNC=1` 時のみ）:**
      - `/workspace/.mcp.json` に `chrome-devtools`（`npx -y chrome-devtools-mcp@latest --browserUrl http://localhost:9222`）
        エントリを確保（無ければ新規、既存に未定義なら `jq` で追加）。
      - `rmcp-xdotool` バイナリがある場合のみ `computer-use`（`{"command":"rmcp-xdotool","args":[],"env":{"DISPLAY":":99"}}`）
        を未定義時のみ追加。**`enabledMcpjsonServers` には追加しない**（既定で無効。強権限のため利用時に明示有効化）。
      - `$LOCAL_CLAUDE/.claude.json` の `projects["/workspace"].enabledMcpjsonServers` に `chrome-devtools` を
        追加（未登録時のみ。ファイルが無ければ `{}` を作成、`chmod 600`）。
  19. **VNC/Chrome/noVNC 起動（`CLAUDE_DEV_VNC=1` 時のみ）:** システム D-Bus 起動・GTK immodules キャッシュ更新・
      `~/.vnc/xstartup` 用意の後、`/tmp/start-user-desktop.sh` を生成しユーザー権限でバックグラウンド起動する。
      内容は順に、`Xvnc :99 -geometry 1280x800 -depth 24 -SecurityTypes None -rfbport 5999 ...`（X+VNC 一体型）、
      `setxkbmap -layout us,jp`、D-Bus セッションバス、`openbox`、`ibus-daemon -xrR`＋Mozc プリロード/ホットキー
      （`<Control><Shift>space` / `<Super>space`）、`websockify --heartbeat 30 --web /usr/share/novnc 6080 localhost:5999`、
      Chrome プロファイルの残存ロック（`SingletonLock` 等）削除後に `claude-dev-chrome ... --remote-debugging-port=9222
      --user-data-dir=~/.chrome-profile`（アーキ別ランチャー: amd64=Google Chrome / arm64=Playwright Chromium）。
  20. **tmux セッション開始:** `su "$USERNAME" -s /bin/zsh -l -c "cd /workspace && tmux -f ~/.tmux.conf new-session -d -s main 'exec zsh -l'"`。
  21. **常駐:** `✅ Ready (...)` を表示し `exec tail -f /dev/null` で待機。
- **実装上の判断:** 認証共有は symlink でなく「起動時コピー＋30 秒書き戻し」（Claude Code のアトミック書き込みで
  symlink が壊れるため。設計判断3/D-3）。`~/.claude` 自体は `/workspace/.claude` への symlink とし、
  `settings.json`/`projects/`/`sessions/` はプロジェクトに永続化する。codex も同じ形（`~/.codex` →
  `/workspace/.codex` の symlink、`auth.json` はコピー＋書き戻し）に揃える——codex の `auth.json` は
  その場書き換えで symlink でも壊れないが、同期ループと片付け経路を 2 方式に分けない判断（設計判断3/D-27）。
  共有ボリューム内の codex 認証パスが `~/.claude-shared/codex/auth.json` になるのは、認証ボリュームを
  claude と共用する決定（D-27 ③）によるもので、名称は claude 由来のまま据え置く。
  `config.toml` の不足鍵補完は `ensure_codex_config()` に閉じる。**当初は awk による行単位の実装だったが、
  独立レビューで「複数行文字列内の `[features]` を見出しと誤認して文字列の値を書き換える」「quoted key を
  見落として同一鍵を二重定義し TOML を壊す」という要件違反の反例が出たため、`tomllib` による
  パース＋検証方式へ作り直した**（feedback/log.md [19]）。教訓は
  `docs/knowledge/append-missing-defaults-must-respect-file-structure.md`。
  補完に失敗した場合は元ファイルを温存し、警告のみ出して起動を続ける（`ensure_codex_config || true`
  で `set -e` 下でも起動を止めない）——codex を使わない利用者のコンテナ起動を、codex の設定補完で
  止めてはならないため。

## データアクセス

| データ | 操作 | 実施モジュール | 備考 |
|---|---|---|---|
| 認証ファイル（.credentials.json / .claude.json） | 起動時 chmod 600・30秒ごと共有ボリュームへ書き戻し | entrypoint | 共有元コピーは cli 側。symlink 不使用（D-3） |
| codex 認証ファイル（/workspace/.codex/auth.json） | 起動時 chmod 600・30秒ごと `~/.claude-shared/codex/auth.json` へ書き戻し | entrypoint | 共有元コピーは cli 側（`login-codex`/`start`）。`config.toml`・セッション履歴は共有しない（D-27） |
| /workspace/.claude/settings.json | 生成（無い時）・host-hooks.json を jq で深いマージ | entrypoint | コンテナローカル（共有しない） |
| /workspace/.codex/config.toml | 既定 3 鍵（`sandbox_mode`/`approval_policy`/`features.use_legacy_landlock`）を保証。無い時は生成、存在時は不足鍵のみ追記（既存の鍵と値は不変・冪等） | entrypoint | コンテナローカル（共有しない）。既定でのサンドボックス無効化＋読み取り専用用途の landlock 有効化（D-27 ⑥・core/12-5,12-6,12-9） |
| /workspace/.mcp.json | chrome-devtools / computer-use エントリを jq で追加 | entrypoint | VNC 時のみ |
| /workspace/.claude/.claude.json | enabledMcpjsonServers に chrome-devtools を追加 | entrypoint | VNC 時のみ |
| /workspace/CLAUDE.md | マーカー範囲を毎回削除→再生成 | entrypoint | KVM/VNC/Docker ネットワーク情報 |

## API実装詳細

外部公開 API なし（コンテナ内初期化スクリプトのため）。

## 設定・環境変数

| 名前 | 用途 | デフォルト | 必須 |
|---|---|---|---|
| CONTAINER_USER | コンテナユーザー名（`$USERNAME`/`$USER_HOME` の元） | devuser | いいえ（Dockerfile ENV） |
| DOCKER_HOST | Docker 接続先（docker-proxy 経由）。両 rc へ永続化。portsync 起動条件の判定にも使用 | （proxy 経由を CLI が付与） | いいえ |
| CLAUDE_DEV_DOOD_PORTSYNC | DooD ポート転送（portsync）の有効/無効。`!= 0` で起動 | 1 | いいえ |
| CLAUDE_DEV_VM | VM モード連携フラグ。`1` で VM 起動、portsync/CLAUDE.md の KVM 追記を抑止 | （未設定=非VM） | いいえ |
| CLAUDE_DEV_VNC | VNC イメージ判定。`1` で MCP 設定・VNC/Chrome/noVNC 起動・CLAUDE.md へブラウザ節追記 | （vnc ステージのみ 1） | いいえ |
| CLAUDE_DEV_SSH_BRIDGE_PORT | macOS 版 SSH agent TCP ブリッジ用ポート（socat で host.docker.internal へ） | （Linux では未設定） | いいえ |
| SSH_AUTH_SOCK | SSH agent ソケット。`/tmp/ssh-agent.sock` を両 rc へ永続化 | — | いいえ |
| VNC_DISPLAY | X ディスプレイ番号 | 99 | いいえ |
| VNC_RESOLUTION | Xvnc の解像度 | 1280x800 | いいえ |
| VM_PORTS | VM_DEV.md テンプレートのポート表記 | （Docker API のみ） | いいえ |

固定ポート（コンテナ内のみ）: VNC 5999・noVNC 6080・Chrome DevTools 9222。ホストへは noVNC 6080 のみ
CLI が動的割り当てで公開する。

## エラーハンドリング実装

| 異常系 | 実装箇所 | 実際の振る舞い | 対応する要件 |
|---|---|---|---|
| UID/GID 衝突 | UID/GID 追従ブロック | 競合エントリを一時 ID（9900〜）へ退避してから割当。`|| true` で継続 | core/2 |
| firewall 適用失敗 | `init-firewall.sh` 呼び出し | `2>/dev/null || true` で起動は中止せず継続（警告は firewall スクリプト自身が標準出力へ出す） | core/5-3 |
| host-hooks.json マージ失敗 | jq マージブロック | `.tmp` を削除し「⚠️ ホスト設定のマージに失敗」を出力、元 settings 維持 | core/3 |
| .mcp.json / .claude.json 更新失敗 | MCP 設定ブロック | `.tmp` 削除・警告出力し当該追加をスキップ、以降継続 | core/11 |
| VM 起動失敗 | VM モードブロック | 「⚠️ VM の起動に失敗」を出力、`DOCKER_HOST` を変えず proxy 既定で継続 | core/8（vm-mode） |
| Chrome プロファイルの残存ロック | start-user-desktop.sh | `SingletonLock`/`SingletonSocket`/`SingletonCookie` を削除後に起動 | core/11 |

## テスト

シェルスクリプトのため自動テストは無い（[テスト戦略](../02-design/system.md) の方針「シェル系は自動テスト
なし＝実機確認」）。以下の受け入れ基準・契約は **実機確認**で検証する（`claude-dev start` 実操作。E2E-1）。
自動テストランナーが無いため、**下表はいずれも「未検証(テスト未実装)」の状態にある**（自動化された
回帰検出手段が無い、という意味）。その上で各行の左欄に実機確認の実施状況を記録する——
**「実施済み」と書かれた行は、その日付時点で実際に観測した内容を示す**（回帰時は同じ観測を繰り返す）。
記載の無い行は実機確認そのものが未実施である。とくに `codex` に実際の作業を依頼する観点
（core/12-4 のシェル実行成功、core/12-9 の `codex exec -s read-only` での読み取り成功）は、
codex のデバイス認証を要するため本モジュール単体では実施できず、**E2E-6 が担う**。

**本モジュールは 02-design のテスト戦略「結合テスト対象」で 2 契約の担当である**——`entrypoint → firewall`
（呼び出し元担当の原則どおり）と `cli → コンテナ/entrypoint`（呼び出し元 cli が bash で自動テストを持たないため
観測側の本モジュールへ寄せたもの）。いずれも手段は実機確認であり、下表で対応関係を示す。

| テスト(ファイル::ケース名) | レベル | 検証内容 | 対応する受け入れ基準/契約 |
|---|---|---|---|
| （自動テストなし・実機確認） | 結合 | 起動時に firewall が適用される | 契約: entrypoint→firewall／要件 core/5 |
| （自動テストなし・実機確認） | 結合 | cli が `docker run` で渡した環境変数（`DOCKER_HOST`／`CLAUDE_DEV_DOOD_PORTSYNC`／`CLAUDE_DEV_VM`／`COMPOSE_PROJECT_NAME`）とマウント（`<cwd>`→`/workspace`、`claude-dev-auth`→`~/.claude-shared`、`claude-dev-config`→`~/.config-shared`、`$SSH_AUTH_SOCK`→`/tmp/ssh-agent.sock`）を受け取り、`SSH_AUTH_SOCK`/`DOCKER_HOST` の export 行が `/etc/zsh/zshrc`・`/etc/bash.bashrc` の両方に追記され、`CLAUDE_DEV_VM != 1` かつ `CLAUDE_DEV_DOOD_PORTSYNC != 0` かつ `DOCKER_HOST` が `docker-proxy` を含むときに限り portsync が常駐起動する | 契約: cli→コンテナ/entrypoint |
| （自動テストなし・実機確認） | 結合 | `/workspace` 所有者に UID/GID が追従しファイル所有権齟齬が無い | 契約: cli→コンテナ/entrypoint／要件 core/2 |
| （自動テストなし・実機確認） | 結合 | 認証が共有ボリューム経由でコピー・30秒書き戻しされ再接続できる | 契約: cli→コンテナ/entrypoint／要件 core/3 |
| （自動テストなし・実機確認。ローカル検証済み: symlink 化・`chmod 600`・共有 `codex/` 作成・書き戻し伝播） | 結合 | codex 認証（auth.json）がコピーされ `codex` が再ログイン不要で動き、更新が 30 秒で共有ボリュームへ書き戻る | 契約: cli→コンテナ/entrypoint／要件 core/3-7,8,9（E2E-6） |
| （自動テストなし・実機確認。**2026-07-31 実施済み**: `claude-dev-claude:latest` に更新後の entrypoint をマウントした使い捨てコンテナで、3 鍵を含む `config.toml` が生成され所有者が `dev:dev`・パーミッション 644 になることを確認。生成物は `python3 -m tomllib` でパースでき、`sandbox_mode`/`approval_policy`/`features.use_legacy_landlock` の 3 鍵が読み取れる。codex のシェル実行成功は E2E-6 が担う） | 単体 | `config.toml` が無いコンテナで起動すると既定 3 鍵（`sandbox_mode`・`approval_policy`・`features.use_legacy_landlock`）を含む `config.toml` が生成され、codex のシェルコマンドが成功する | 要件 core/12-4,12-5（E2E-6） |
| （自動テストなし・実機確認。**2026-07-31 実施済み**: `model`・`approval_policy = "on-request"`・`[tui]`・**複数行文字列の中に `[features]` を含む** `config.toml` を置いて `docker restart` → 利用者の鍵は値ごと不変（`note` が `'[features]\ntext\n'` のまま）、不足していた `sandbox_mode` と `[features] use_legacy_landlock` だけが追記され、再起動しても md5 不変＝冪等。ホスト側の関数単体ハーネス 15 ケースを `tomllib` でパース検証済み〈トップレベルのみ／`[features]` がファイル途中／ドット記法／インラインテーブル（鍵あり・鍵なし）／配列テーブル／quoted key／複数行文字列／コメントアウト／3 鍵とも既存／空ファイル／壊れた TOML／CRLF／末尾改行なし〉） | 単体 | 利用者が書き換えた `config.toml` を持つコンテナを再起動しても既存の鍵と値は変わらず、不足していた既定鍵だけが追記される（2 回目の再起動で内容が変化しない＝冪等） | 要件 core/12-6 |
| （自動テストなし・実機確認。**2026-07-31 実施済み**: entrypoint が生成した 3 鍵の `config.toml` を持つコンテナで、**フラグを付けずに** `codex sandbox -- /bin/true` が exit 0（＝config 経由で landlock が起動する）、同経路の `touch /tmp/e2e-deny` は `Permission denied` でファイル未生成、`cat` による読み取りは成功。`--enable use_legacy_landlock` を明示した形でも exit 0。`codex exec -s read-only` を伴う実依頼は認証が要るため E2E-6 が担う） | 単体 | `--sandbox read-only` を明示指定した呼び出しでも codex の読み取りが成功し、書き込みは拒否される | 要件 core/12-9（E2E-6） |
| （自動テストなし・実機確認） | 結合 | VNC イメージで Chrome/noVNC が起動し chrome-devtools MCP で操作できる | 要件 core/11 |

実行方法: 自動テストコマンドなし。`claude-dev start`（VNC あり/`--no-vnc`）でコンテナを起動し、
`docker exec` 等で UID/GID・認証・firewall・tmux・（VNC 時）noVNC 表示を目視確認する（E2E-1 に集約）。

## 既知の制限・技術的負債

- 自動テストが無く、回帰検出は実機確認に依存する。
- `config.toml` の差し替えは inode を作り直すため、**POSIX ACL・拡張属性は引き継がれない**
  （復元するのは uid/gid と mode のみ）。設定ファイルに ACL を付ける運用は想定していない。
- 既存 `config.toml` の `features` がインラインテーブルで、その中に `use_legacy_landlock` が
  無い場合、TOML の仕様上インラインテーブルへ後から要素を足せないため landlock を補完できない
  （警告のみ・無変更）。その環境で読み取り専用の依頼を使うには、利用者が `[features]` テーブル形式へ
  書き換えるか、呼び出し側で `--enable use_legacy_landlock` を明示する必要がある。
- `host-hooks.json` の名称は歴史的経緯で、実際には `hooks` と `env` の両方を運ぶ（改名していない）。
- VNC 関連ポート（VNC 5999・Chrome DevTools 9222）はコンテナ内限定。ホスト公開は noVNC 6080 のみ。
- `docker compose` の host 公開ポート（`ports:`）衝突は `COMPOSE_PROJECT_NAME` 一意化では解決せず、
  `claude-dev forward` の利用で回避する。

## 運用メモ

- `CLAUDE.md` はマーカー範囲だけを毎回再生成するため、マーカー外にユーザーが書いた内容は保持される。
- codex の `config.toml` はプロジェクト配下（`/workspace/.codex/config.toml`）の実体である。既定へ
  戻したいときは削除して再起動すれば 3 鍵が再生成される。ファイルが存在する場合に entrypoint が行うのは
  **不足している既定鍵の追記だけ**で、既に書かれている鍵とその値は変更しない（要件 core/12-6）。
- `--kvm`/`--vm` の切り替えは再起動で追従する（KVM 追記の有無・VM_DEV.md 生成が変わる）。
- VM モード時、`vm-up.sh` は `$USERNAME` 権限で走るため、root 所有のマウント点を entrypoint が事前に
  `install -d -o $USERNAME` で用意している（これが無いと `mkdir` が Permission denied で失敗する）。

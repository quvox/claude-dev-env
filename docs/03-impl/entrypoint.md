---
id: entrypoint
layer: impl
title: entrypoint 実装説明書
version: 1.0.0
updated: 2026-07-18
verified:
  at: 2026-07-18
  version: 1.0.0
  against:
    - doc: docs/02-design/system.md
      version: 1.0
summary: >
  Claude コンテナの ENTRYPOINT として root で起動し、UID/GID 追従・認証共有・settings/MCP 生成・
  firewall/portsync 起動・VNC/Chrome 起動・tmux セッション開始までを行う初期化シェルスクリプトの実装。
keywords: [entrypoint, UID/GID, 認証共有, MCP, VNC, Chrome, tmux, firewall, portsync]
depends_on: [firewall, portsync]
source:
  - docs/02-design/system.md
---

# 実装説明書:entrypoint

## 概要

`scripts/entrypoint-claude.sh` は Claude コンテナの ENTRYPOINT として **root で 1 プロセス**起動し、
コンテナ内部の初期化を上から順に実行する初期化スクリプトである（上流: [全体設計](../02-design/system.md)、
契約「cli → コンテナ/entrypoint」「entrypoint → firewall」）。主な責務は、(1) `/workspace` 所有者に合わせた
UID/GID 追従、(2) 共有ボリューム経由の認証共有と `~/.claude` の symlink 化、(3) `settings.json`・MCP 設定生成、
(4) `firewall` 起動、(5) `portsync`（DooD ポート転送）起動、(6) VNC/Chrome/noVNC 起動（VNC イメージ時のみ）、
(7) `tmux` セッション開始。最後に `exec tail -f /dev/null` で常駐する。要件 core/2,3,5,11 を担う。

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
  7. **COMPOSE_PROJECT_NAME 一意化:** ホスト名（=プロジェクトディレクトリ名で一意）を小文字化し
     `[a-z0-9_-]` 以外を `-` に置換した名前を `export COMPOSE_PROJECT_NAME` として両 rc へ追記。全プロジェクトが
     `/workspace` にマウントされ既定名が `workspace` に衝突するのを防ぐ。
  8. **.zshrc 共有:** `~/.config-shared/`（ボリューム）に `.zshrc` が無ければ、`~/.zshrc.default`→実体 `~/.zshrc`→
     空ファイルの順でコピー元を決めて作成。以後 `~/.zshrc` を共有ファイルへの symlink にする（コンテナ間共有）。
  9. **~/.claude 構成と認証共有:** `LOCAL_CLAUDE=/workspace/.claude` を確保。`~/.claude` が実ディレクトリなら
     中身を `cp -an` で退避して削除し、`~/.claude → /workspace/.claude` の symlink（`ln -sfn`）を張る。認証ファイル
     （`.credentials.json`・`.claude.json`。CLI がコピー済み）は所有権と `chmod 600` を整える。`~/.claude.json`
     （ホーム直下）→ `/workspace/.claude/.claude.json` の symlink を張る。
  10. **settings.json 生成:** `$LOCAL_CLAUDE/settings.json` が無ければ
      `{"permissions":{"defaultMode":"bypassPermissions"},"model":"sonnet"}` を生成（共有しない）。
  11. **ホスト設定マージ:** `host-hooks.json`（名称は歴史的経緯で `hooks`/`env` 両方を運ぶ）があり `.hooks` か
      `.env` を含むなら `jq '. * $overlay[0]'` で `settings.json` へ深いマージし、元ファイル削除。失敗時は警告し継続。
  12. **ユーザー hook スクリプト配置:** `host-local-bin/` があれば `~/.local/bin/` へ `cp -a --update=none`
      （イメージ焼き込み済みを上書きしない）し、実行権付与後に元を削除。
  13. **認証バックグラウンド同期:** 30 秒ごとに `LOCAL_CLAUDE` の認証ファイルを共有ボリュームと `cmp` し、
      差分があれば書き戻すループを `( while true; ... ) &` でバックグラウンド起動（トークンリフレッシュ伝播）。
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
  `settings.json`/`projects/`/`sessions/` はプロジェクトに永続化する。

## データアクセス

| データ | 操作 | 実施モジュール | 備考 |
|---|---|---|---|
| 認証ファイル（.credentials.json / .claude.json） | 起動時 chmod 600・30秒ごと共有ボリュームへ書き戻し | entrypoint | 共有元コピーは cli 側。symlink 不使用（D-3） |
| /workspace/.claude/settings.json | 生成（無い時）・host-hooks.json を jq で深いマージ | entrypoint | コンテナローカル（共有しない） |
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
| firewall 適用失敗 | `init-firewall.sh` 呼び出し | `2>/dev/null || true` で無視し継続 | core/5 |
| host-hooks.json マージ失敗 | jq マージブロック | `.tmp` を削除し「⚠️ ホスト設定のマージに失敗」を出力、元 settings 維持 | core/3 |
| .mcp.json / .claude.json 更新失敗 | MCP 設定ブロック | `.tmp` 削除・警告出力し当該追加をスキップ、以降継続 | core/11 |
| VM 起動失敗 | VM モードブロック | 「⚠️ VM の起動に失敗」を出力、`DOCKER_HOST` を変えず proxy 既定で継続 | core/8（vm-mode） |
| Chrome プロファイルの残存ロック | start-user-desktop.sh | `SingletonLock`/`SingletonSocket`/`SingletonCookie` を削除後に起動 | core/11 |

## テスト

シェルスクリプトのため自動テストは無い（[テスト戦略](../02-design/system.md) の方針「シェル系は自動テスト
なし＝実機確認」）。以下の受け入れ基準・契約は **実機確認**で検証する（`claude-dev start` 実操作。E2E-1）。
自動テストが存在しないため、下表はいずれも**未検証（自動テストなし）**であり、実機確認の対応関係を示す。

| テスト(ファイル::ケース名) | レベル | 検証内容 | 対応する受け入れ基準/契約 |
|---|---|---|---|
| （自動テストなし・実機確認） | 結合 | 起動時に firewall が適用される | 契約: entrypoint→firewall／要件 core/5 |
| （自動テストなし・実機確認） | 結合 | `/workspace` 所有者に UID/GID が追従しファイル所有権齟齬が無い | 要件 core/2 |
| （自動テストなし・実機確認） | 結合 | 認証が共有ボリューム経由でコピー・30秒書き戻しされ再接続できる | 要件 core/3 |
| （自動テストなし・実機確認） | 結合 | VNC イメージで Chrome/noVNC が起動し chrome-devtools MCP で操作できる | 要件 core/11 |

実行方法: 自動テストコマンドなし。`claude-dev start`（VNC あり/`--no-vnc`）でコンテナを起動し、
`docker exec` 等で UID/GID・認証・firewall・tmux・（VNC 時）noVNC 表示を目視確認する（E2E-1 に集約）。

## 既知の制限・技術的負債

- 自動テストが無く、回帰検出は実機確認に依存する。
- `host-hooks.json` の名称は歴史的経緯で、実際には `hooks` と `env` の両方を運ぶ（改名していない）。
- VNC 関連ポート（VNC 5999・Chrome DevTools 9222）はコンテナ内限定。ホスト公開は noVNC 6080 のみ。
- `docker compose` の host 公開ポート（`ports:`）衝突は `COMPOSE_PROJECT_NAME` 一意化では解決せず、
  `claude-dev forward` の利用で回避する。

## 運用メモ

- `CLAUDE.md` はマーカー範囲だけを毎回再生成するため、マーカー外にユーザーが書いた内容は保持される。
- `--kvm`/`--vm` の切り替えは再起動で追従する（KVM 追記の有無・VM_DEV.md 生成が変わる）。
- VM モード時、`vm-up.sh` は `$USERNAME` 権限で走るため、root 所有のマウント点を entrypoint が事前に
  `install -d -o $USERNAME` で用意している（これが無いと `mkdir` が Permission denied で失敗する）。

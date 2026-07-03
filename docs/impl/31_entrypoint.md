---
summary: Claude コンテナのENTRYPOINTとして起動し、UID/GID追従・認証共有・MCP設定・VNC/Chrome起動・tmuxセッション開始までを行う初期化スクリプトの実装仕様。
keywords: [ entrypoint, UID/GID, 認証, MCP, VNC, Chrome, tmux ]
---

# 実装仕様: scripts/entrypoint-claude.sh

> **この文書の役割**: Claude コンテナの ENTRYPOINT として root で起動し、UID/GID 追従・認証共有・設定生成・VNC/Chrome 起動・tmux セッション開始までを行う初期化スクリプトの実装仕様。

## 要件（なぜ必要か）

`claude-dev start` が `docker run` でコンテナを起動した後、コンテナ内部では以下を解決する必要がある。

- ホストの `/workspace` 所有者と一致する UID/GID でユーザーを動作させ、ファイル所有権の齟齬を防ぐ。
- 認証ファイルを共有ボリュームと往復させつつ、セッション・設定はプロジェクトローカルに保つ。
- ホスト由来の hooks/env 設定とユーザー独自スクリプトを取り込む。
- ファイアウォール・MCP・VNC/Chrome・tmux を起動する。

## カバーするコード

```
scripts/entrypoint-claude.sh   （ビルド時に /usr/local/bin/entrypoint.sh へ配置）
```

## 前提環境変数

- `CONTAINER_USER`（Dockerfile の `ENV`、既定 `devuser`）→ `USERNAME`。`USER_HOME=/home/$USERNAME`。
- `CLAUDE_DEV_VNC=1`（vnc ステージのみ設定）で VNC 経路を有効化。
- `DOCKER_HOST` / `SSH_AUTH_SOCK`（`docker run -e` 由来）。

## 処理シーケンス（成果物としての順序）

1. **UID/GID 追従**: `/workspace` の所有者 UID/GID を `stat` で取得。コンテナユーザーの現 UID/GID と異なれば `groupmod`/`usermod` で変更する。競合するグループ/ユーザーがいれば一時 GID/UID（9900〜）へ退避してから割り当てる。UID/GID を変更した場合のみ、旧 UID/GID を持つファイルだけを対象に `chown`（全走査回避）。`HOST_UID=0`（root 所有）の場合は変更しない。
2. **~/.ssh 整備**: ディレクトリの所有権を設定し `chmod 700`。`~/.ssh/config` は CLI 側で IdentityFile 等を除去済みのものがマウントされる前提。
3. **KVM デバイスのグループ権限**: `/dev/kvm` `/dev/vhost-net` が存在すれば、そのデバイスの GID に一致するグループをコンテナ内に用意（無ければ `kvm-host-<gid>` を作成）し、`$USERNAME` を追加する。
4. **SSH_AUTH_SOCK の永続化**: `/tmp/ssh-agent.sock` があれば `export SSH_AUTH_SOCK=/tmp/ssh-agent.sock` を `/etc/zsh/zshrc` と `/etc/bash.bashrc` に追記（`su -l` でのリセット対策）。
5. **DOCKER_HOST の永続化**: `DOCKER_HOST` があれば同様に両 rc へ追記。Docker CLI の `default` コンテキストが環境変数を参照するためカスタム context は不要。
6. **COMPOSE_PROJECT_NAME の一意化**: コンテナのホスト名（= プロジェクトディレクトリ名で一意）を compose 互換名（小文字化し `[a-z0-9_-]` 以外を `-` に置換）へ正規化し、`export COMPOSE_PROJECT_NAME=<正規化名>` を両 rc へ追記する。どのプロジェクトもコンテナ内では `/workspace` にマウントされ、`docker compose` の既定プロジェクト名が全コンテナで `workspace` になってしまうため、複数プロジェクトを同時に起動するとコンテナ名・ネットワーク名が衝突する。これを防ぎ、プロジェクトごとに一意のプロジェクト名・コンテナ名・ネットワーク名になるようにする（`DOCKER_HOST` の有無に関わらず設定する）。
7. **.zshrc 共有**: `~/.config-shared/`（`VOL_CONFIG`）に `.zshrc` が無ければ、`~/.zshrc.default`（イメージ既定）→ 実体 `~/.zshrc` → 空ファイルの順でコピー元を決めて作成。以後 `~/.zshrc` を共有ファイルへの symlink にする（コンテナ間共有）。
8. **~/.claude の構成と認証共有**:
   - `LOCAL_CLAUDE=/workspace/.claude` を確保。`~/.claude` が実ディレクトリなら中身を退避して削除し、`~/.claude → /workspace/.claude` の symlink を張る。
   - 認証ファイル（`.credentials.json`, `.claude.json`）は CLI が既にコピー済み。ここでは所有権と `chmod 600` を整える。
   - `~/.claude.json`（ホーム直下）→ `/workspace/.claude/.claude.json` の symlink。
   - `settings.json` が無ければ `{"permissions":{"defaultMode":"bypassPermissions"},"model":"sonnet"}` を生成（共有しない）。
9. **ホスト設定のマージ**: `/workspace/.claude/host-hooks.json` があり `.hooks` か `.env` を含むなら、`jq '. * $overlay[0]'` で `settings.json` に深いマージを行い、元ファイルを削除。失敗時は警告。
10. **ユーザー hook スクリプト配置**: `/workspace/.claude/host-local-bin/` があれば `~/.local/bin/` へ `cp -a --update=none`（イメージ焼き込み済みファイルを上書きしない）し、実行権限を付与して元を削除。
11. **認証バックグラウンド同期**: 30 秒ごとに `/workspace/.claude/` の認証ファイルを共有ボリュームと `cmp` し、差分があれば書き戻すループをバックグラウンド起動（トークンリフレッシュ伝播）。
12. **ファイアウォール**: `/usr/local/bin/init-firewall.sh` を実行（失敗は無視、[32_firewall.md](32_firewall.md)）。
13. **CLAUDE.md への環境情報追記**: マーカー `<!-- claude-dev-auto-start -->`〜`<!-- claude-dev-auto-end -->` で囲んだ範囲を毎回削除→再生成（旧形式セクションも除去）。「注意事項」、VNC 時は「Web アプリの動作確認」、**`/dev/kvm` が存在する時（`--kvm` 起動時）は「KVM / 仮想化（重要）」**（KVM 加速の有効化方法・QEMU 起動例・GUI VM を `:99` に表示する方法・computer-use/scrot での操作・ネットワーク・ディスクイメージ配置の注意）、常に「Docker ネットワーク（重要）」（コンテナ名でのアクセス指示）を書き込む。`/workspace/CLAUDE.md` が無ければ作成。これらはすべてマーカー範囲内に書かれるため、次回起動時に範囲ごと削除・再生成され、KVM の有無の変化（`--kvm` の付け外し）にも追従する。
    - **VM モード時の例外（実装済み・要イメージ再ビルド反映。正本 [80_vm-mode.md](80_vm-mode.md) / [docs/08_vm-mode.md](../08_vm-mode.md)）**: `--vm`（`CLAUDE_DEV_VM=1`）で起動した場合、上記の「KVM / 仮想化（重要）」の **CLAUDE.md への追記は抑止**し、KVM/VM 情報は代わりに `/workspace/VM_DEV.md` へ集約する（CLAUDE.md 不可侵の方針。VM モードでは `--kvm` が含意され `/dev/kvm` が存在するが、CLAUDE.md には書かない）。
14. **VM モードの起動（実装済み・要イメージ再ビルド反映。正本 [80_vm-mode.md](80_vm-mode.md)）**: `CLAUDE_DEV_VM=1` のとき、まず **root のうちに** `vm-up.sh` が書き込む root 所有ディレクトリを `$USERNAME` 所有で用意する（`install -d -o $USERNAME`：docker ボリュームのマウント点 `$USER_HOME/.claude-dev-vm` と実行時ディレクトリ `/run/vm` はいずれも既定で `root:root` のため、これを直さないと後続の `su $USERNAME -c vm-up.sh` 内の `mkdir` が Permission denied で失敗する）。その後 `su "$USERNAME" -c /usr/local/bin/vm-up.sh` で `scripts/vm-up.sh` を起動し（virtiofsd＋QEMU 常駐＋ゲスト dockerd 同期待ち）、成功時のみ `DOCKER_HOST` env スニペット（`/etc/claude-dev/vm.env`）出力・両 rc への source フック追記・`/workspace/VM_DEV.md` 生成・バナー表示を行う。失敗時は `DOCKER_HOST` を設定せず（proxy 既定維持）継続する。
14. **MCP 設定（VNC 時のみ）**:
    - `/workspace/.mcp.json` に `chrome-devtools`（`npx -y chrome-devtools-mcp@latest --browserUrl http://localhost:9222`）エントリを確保（無ければ新規、既存に未定義なら追加）。
    - `rmcp-xdotool` バイナリが存在する場合のみ、`/workspace/.mcp.json` に `computer-use`（`{"command":"rmcp-xdotool","env":{"DISPLAY":":99"}}`）エントリを定義する（未定義時のみ追加）。デスクトップ操作用の MCP（[40_devcontainer.md](40_devcontainer.md) で VNC イメージに焼き込み）。`chrome-devtools` と異なり **`enabledMcpjsonServers` には追加しない**（既定では無効。デスクトップ全体を操作できる強い権限のため、利用時に明示的に有効化する想定。画面取得は `scrot` を併用）。
    - `/workspace/.claude/.claude.json` の `projects["/workspace"].enabledMcpjsonServers` に `chrome-devtools` を追加（未登録時のみ。ファイルが無ければ `{}` を作成）。
15. **VNC / Chrome 起動（VNC 時のみ）**: `/tmp/start-user-desktop.sh` を生成し、ユーザー権限でバックグラウンド起動。内容は順に:
    - `Xvnc :99 -geometry 1280x800 -depth 24 -SecurityTypes None -rfbport 5999`（X + VNC 一体型、ディスプレイ `:99` / VNC ポート 5999）
    - `setxkbmap -layout us,jp`、D-Bus セッションバス、`openbox`
    - `ibus-daemon -xrR` + IBus/Mozc プリロード・ホットキー（`<Control><Shift>space` / `<Super>space`）設定
    - `websockify --heartbeat 30 --web /usr/share/novnc 6080 localhost:5999`（HTTP 6080 → VNC 5999）
    - Chrome プロファイルの残存ロック（`SingletonLock` 等）を削除後、`google-chrome-stable ... --remote-debugging-port=9222 --user-data-dir=~/.chrome-profile` を起動
    - システム D-Bus デーモン起動・GTK immodules キャッシュ更新も事前に実施
16. **tmux セッション開始**: ユーザー権限で `cd /workspace && tmux -f ~/.tmux.conf new-session -d -s main 'exec zsh -l'`。
17. `✅ Ready ...` を表示し、`exec tail -f /dev/null` で常駐。

## 不変条件・注意点

- 認証は「起動時コピー + 30 秒ごとの書き戻し」で共有する（symlink を使わない理由は [10_cli.md](10_cli.md) と同じ）。
- `~/.claude` は `/workspace/.claude` への symlink であり、`settings.json`/`projects/`/`sessions/` はプロジェクトディレクトリに永続化される。
- `host-hooks.json` という名称は歴史的経緯で、実際には `hooks` と `env` の両方を運ぶ。
- VNC 関連ポート（VNC 5999・Chrome DevTools 9222）はコンテナ内のみ。ホストへは noVNC の 6080（CLI が動的にホストポートへ割り当て）だけが公開される。
- `COMPOSE_PROJECT_NAME` をコンテナごとに一意化するのは、プロジェクトが `docker compose` で複数コンテナを起動する際、`/workspace` 由来の既定名 `workspace` が全プロジェクトで重複しコンテナ名・ネットワーク名が衝突するのを防ぐため。なお host 公開ポート（compose の `ports:`）の衝突は別問題であり、ホスト公開を避けて `claude-dev forward` を使うことで回避する。

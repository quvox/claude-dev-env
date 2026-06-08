#!/bin/bash
# =============================================================================
# Claude コンテナ エントリポイント
# =============================================================================
# 1. /workspace の所有者 UID/GID にコンテナユーザーを合わせる
# 2. ~/.claude → /workspace/.claude にシンボリックリンク
#    認証ファイルを共有ボリューム（~/.claude-shared/）から /workspace/.claude/ にコピー
# 3. ファイアウォール設定
# 4. tmux 起動
# =============================================================================
set -e

# CONTAINER_USER は Dockerfile の ENV で設定される（デフォルト: devuser）
USERNAME="${CONTAINER_USER:-devuser}"
USER_HOME="/home/$USERNAME"

# --- /workspace の所有者に UID/GID を合わせる ---
if [ -d /workspace ]; then
    HOST_UID=$(stat -c '%u' /workspace 2>/dev/null || echo "1500")
    HOST_GID=$(stat -c '%g' /workspace 2>/dev/null || echo "1500")
    CURRENT_UID=$(id -u "$USERNAME" 2>/dev/null || echo "1500")
    CURRENT_GID=$(id -g "$USERNAME" 2>/dev/null || echo "1500")

    if [ "$HOST_UID" != "0" ]; then
        CHANGED=0
        # GID 変更
        if [ "$HOST_GID" != "$CURRENT_GID" ]; then
            CONFLICT_GROUP=$(getent group "$HOST_GID" 2>/dev/null | cut -d: -f1)
            if [ -n "$CONFLICT_GROUP" ] && [ "$CONFLICT_GROUP" != "$USERNAME" ]; then
                TEMP_GID=9900
                while getent group "$TEMP_GID" >/dev/null 2>&1; do
                    TEMP_GID=$((TEMP_GID + 1))
                done
                groupmod -g "$TEMP_GID" "$CONFLICT_GROUP" 2>/dev/null || true
            fi
            groupmod -g "$HOST_GID" "$USERNAME" 2>/dev/null || true
            CHANGED=1
        fi
        # UID 変更
        if [ "$HOST_UID" != "$CURRENT_UID" ]; then
            CONFLICT_USER=$(getent passwd "$HOST_UID" 2>/dev/null | cut -d: -f1)
            if [ -n "$CONFLICT_USER" ] && [ "$CONFLICT_USER" != "$USERNAME" ]; then
                TEMP_UID=9900
                while getent passwd "$TEMP_UID" >/dev/null 2>&1; do
                    TEMP_UID=$((TEMP_UID + 1))
                done
                usermod -u "$TEMP_UID" "$CONFLICT_USER" 2>/dev/null || true
            fi
            usermod -u "$HOST_UID" "$USERNAME" 2>/dev/null || true
            CHANGED=1
        fi
        # UID/GID が変更された場合のみ、ホームディレクトリの所有権を更新
        if [ "$CHANGED" = "1" ]; then
            # 旧 UID/GID のファイルだけを対象にする（全ファイル走査を避ける）
            find "$USER_HOME" \
                \( -uid "$CURRENT_UID" -o -gid "$CURRENT_GID" \) \
                -exec chown "$USERNAME":"$USERNAME" {} + 2>/dev/null || true
        fi
    fi
fi

# --- ~/.ssh ディレクトリの所有権・パーミッション ---
if [ -d "$USER_HOME/.ssh" ]; then
    chown "$USERNAME":"$USERNAME" "$USER_HOME/.ssh" 2>/dev/null || true
    chmod 700 "$USER_HOME/.ssh" 2>/dev/null || true

    # ~/.ssh/config は claude-dev スクリプト側でエージェント転送用に加工済みのものがマウントされる
    # （IdentityFile / IdentitiesOnly 行は除去済み）
fi

# --- KVM デバイスへのアクセス権 ---
# claude-dev が --device=/dev/kvm /dev/vhost-net /dev/net/tun を渡している場合、
# ホスト側のグループ ID（多くは "kvm"）に合わせたグループをコンテナ内に作り、
# $USERNAME を所属させる。GID はホストごとに違うため実行時に検出する。
for dev in /dev/kvm /dev/vhost-net; do
    [ -c "$dev" ] || continue
    DEV_GID=$(stat -c '%g' "$dev" 2>/dev/null || echo "")
    [ -z "$DEV_GID" ] && continue
    # 既に同じ GID のグループがあればそれを利用、なければ作成
    GRP_NAME=$(getent group "$DEV_GID" | cut -d: -f1)
    if [ -z "$GRP_NAME" ]; then
        GRP_NAME="kvm-host-${DEV_GID}"
        groupadd -g "$DEV_GID" "$GRP_NAME" 2>/dev/null || true
    fi
    # $USERNAME をそのグループに追加
    if [ -n "$GRP_NAME" ] && ! id -nG "$USERNAME" 2>/dev/null | tr ' ' '\n' | grep -qx "$GRP_NAME"; then
        usermod -aG "$GRP_NAME" "$USERNAME" 2>/dev/null || true
    fi
done

# --- SSH_AUTH_SOCK をシェル初期化ファイルに設定 ---
# Docker の -e で渡された SSH_AUTH_SOCK は su -l でリセットされるため、
# シェル初期化ファイルに書き出して全シェルで利用可能にする
if [ -S "/tmp/ssh-agent.sock" ]; then
    for rc in /etc/zsh/zshrc /etc/bash.bashrc; do
        if [ -f "$rc" ]; then
            echo "" >> "$rc"
            echo "# --- claude-dev: SSH agent forwarding ---" >> "$rc"
            echo 'export SSH_AUTH_SOCK=/tmp/ssh-agent.sock' >> "$rc"
        fi
    done
fi

# --- Docker Socket Proxy の設定 ---
# docker run -e で渡された DOCKER_HOST は su -l でリセットされるため、
# シェル初期化ファイルに書き出して全シェルで利用可能にする。
# Docker CLI の "default" コンテキストは DOCKER_HOST 環境変数を参照するため、
# 環境変数の設定だけで十分（カスタム context は不要）。
if [ -n "${DOCKER_HOST:-}" ]; then
    for rc in /etc/zsh/zshrc /etc/bash.bashrc; do
        if [ -f "$rc" ]; then
            echo "" >> "$rc"
            echo "# --- claude-dev: Docker Socket Proxy ---" >> "$rc"
            echo "export DOCKER_HOST='${DOCKER_HOST}'" >> "$rc"
        fi
    done
fi

# --- Docker Compose プロジェクト名の一意化 ---
# どのプロジェクトもコンテナ内では /workspace にマウントされるため、
# docker compose の既定プロジェクト名が全コンテナで "workspace" になり、
# 複数プロジェクトを同時に起動するとコンテナ名・ネットワーク名が衝突する。
# コンテナのホスト名（= プロジェクトディレクトリ名で一意）を compose 互換名
# （小文字・[a-z0-9_-] のみ）に正規化し、COMPOSE_PROJECT_NAME として全シェルに設定する。
COMPOSE_NAME=$(hostname | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9_-]/-/g')
if [ -n "$COMPOSE_NAME" ]; then
    for rc in /etc/zsh/zshrc /etc/bash.bashrc; do
        if [ -f "$rc" ]; then
            echo "" >> "$rc"
            echo "# --- claude-dev: Docker Compose project name ---" >> "$rc"
            echo "export COMPOSE_PROJECT_NAME='${COMPOSE_NAME}'" >> "$rc"
        fi
    done
fi

# --- .zshrc の共有（ボリューム経由でコンテナ間共有）---
# ~/.config-shared/ はボリュームとしてマウントされている
SHARED_DIR="$USER_HOME/.config-shared"
if [ -d "$SHARED_DIR" ]; then
    chown "$USERNAME":"$USERNAME" "$SHARED_DIR" 2>/dev/null || true
    # 初回: ボリュームに .zshrc がなければデフォルトをコピー
    if [ ! -f "$SHARED_DIR/.zshrc" ]; then
        if [ -f "$USER_HOME/.zshrc.default" ]; then
            cp "$USER_HOME/.zshrc.default" "$SHARED_DIR/.zshrc"
        elif [ -f "$USER_HOME/.zshrc" ] && [ ! -L "$USER_HOME/.zshrc" ]; then
            cp "$USER_HOME/.zshrc" "$SHARED_DIR/.zshrc"
        else
            touch "$SHARED_DIR/.zshrc"
        fi
        chown "$USERNAME":"$USERNAME" "$SHARED_DIR/.zshrc"
    fi
    # ~/.zshrc をボリューム内のファイルに symlink
    ln -sf "$SHARED_DIR/.zshrc" "$USER_HOME/.zshrc"
    chown -h "$USERNAME":"$USERNAME" "$USER_HOME/.zshrc"
fi

# =============================================================================
# ~/.claude → /workspace/.claude + 認証ファイルの共有
# =============================================================================
# 設計:
#   ~/.claude/ は /workspace/.claude/ へのシンボリックリンク。
#   settings.json, projects/, sessions/, memory/ 等はプロジェクトディレクトリに永続化。
#   認証ファイルだけは共有ボリューム (~/.claude-shared/) から起動時にコピーし、
#   バックグラウンドで書き戻す（トークンリフレッシュ等の伝播用）。
#
# 共有対象: .credentials.json, .claude.json のみ
# =============================================================================
SHARED_CLAUDE="$USER_HOME/.claude-shared"
LOCAL_CLAUDE="/workspace/.claude"
AUTH_FILES=".credentials.json .claude.json"

# 共有ボリュームの所有権
chown "$USERNAME":"$USERNAME" "$SHARED_CLAUDE" 2>/dev/null || true

# /workspace/.claude/ ディレクトリを確保
mkdir -p "$LOCAL_CLAUDE"
chown "$USERNAME":"$USERNAME" "$LOCAL_CLAUDE"

# ~/.claude が実ディレクトリの場合は中身を /workspace/.claude/ に退避してから削除
# （ln -sfn は実ディレクトリを置き換えられないため）
if [ -d "$USER_HOME/.claude" ] && [ ! -L "$USER_HOME/.claude" ]; then
    cp -an "$USER_HOME/.claude/." "$LOCAL_CLAUDE/" 2>/dev/null || true
    rm -rf "$USER_HOME/.claude"
fi

# ~/.claude → /workspace/.claude へのシンボリックリンク
ln -sfn "$LOCAL_CLAUDE" "$USER_HOME/.claude"
chown -h "$USERNAME":"$USERNAME" "$USER_HOME/.claude"

# --- 認証ファイルのパーミッション修正（claude-dev start でコピー済み）---
for f in $AUTH_FILES; do
    if [ -f "$LOCAL_CLAUDE/$f" ]; then
        chown "$USERNAME":"$USERNAME" "$LOCAL_CLAUDE/$f"
        chmod 600 "$LOCAL_CLAUDE/$f"
    fi
done

# ~/.claude.json（ホーム直下）— Claude Code が参照するためリンク
if [ -f "$LOCAL_CLAUDE/.claude.json" ]; then
    ln -sf "$LOCAL_CLAUDE/.claude.json" "$USER_HOME/.claude.json"
    chown -h "$USERNAME":"$USERNAME" "$USER_HOME/.claude.json"
fi

# --- settings.json はコンテナローカル（共有しない）---
if [ ! -f "$LOCAL_CLAUDE/settings.json" ]; then
    echo '{"permissions":{"defaultMode":"bypassPermissions"},"model":"sonnet"}' > "$LOCAL_CLAUDE/settings.json"
    chown "$USERNAME":"$USERNAME" "$LOCAL_CLAUDE/settings.json"
fi

# --- ホストの hooks / env 設定をマージ ---
# claude-dev start 時にコピーされた host-hooks.json があれば settings.json にマージ
# （ファイル名は歴史的経緯で host-hooks.json のままだが env も含む）
HOST_HOOKS="$LOCAL_CLAUDE/host-hooks.json"
if [ -f "$HOST_HOOKS" ]; then
    if jq -e '.hooks // .env' "$HOST_HOOKS" >/dev/null 2>&1; then
        SETTINGS="$LOCAL_CLAUDE/settings.json"
        if jq --slurpfile overlay "$HOST_HOOKS" '. * $overlay[0]' "$SETTINGS" > "${SETTINGS}.tmp" 2>/dev/null; then
            mv "${SETTINGS}.tmp" "$SETTINGS"
            chown "$USERNAME":"$USERNAME" "$SETTINGS"
        else
            rm -f "${SETTINGS}.tmp"
            echo "⚠️  ホスト設定のマージに失敗しました"
        fi
    fi
    rm -f "$HOST_HOOKS"
fi

# --- ホストの ~/.local/bin スクリプトを配置 ---
# claude-dev start 時にコピーされたスクリプトをユーザーの ~/.local/bin/ に配置
# --update=none: イメージに焼き込まれているファイル（claude バイナリの symlink 等）を
# ホスト側のもので上書きしない。ホスト/イメージ間で claude のバージョンが食い違うと
# symlink target がコンテナ内に存在せず「claude: command not found」になるため。
HOST_LOCAL_BIN="$LOCAL_CLAUDE/host-local-bin"
if [ -d "$HOST_LOCAL_BIN" ] && [ -n "$(ls -A "$HOST_LOCAL_BIN" 2>/dev/null)" ]; then
    mkdir -p "$USER_HOME/.local/bin"
    cp -a --update=none "$HOST_LOCAL_BIN/." "$USER_HOME/.local/bin/"
    chown -R "$USERNAME":"$USERNAME" "$USER_HOME/.local/bin"
    chmod -R +x "$USER_HOME/.local/bin"
    rm -rf "$HOST_LOCAL_BIN"
fi

# --- バックグラウンド: 認証ファイルの変更を共有ボリュームに書き戻し ---
# トークンリフレッシュ等で認証ファイルが更新された場合に他コンテナへ伝播する
(
    while true; do
        sleep 30
        for f in $AUTH_FILES; do
            if [ -f "$LOCAL_CLAUDE/$f" ]; then
                # ファイル内容が異なる場合のみコピー
                if ! cmp -s "$LOCAL_CLAUDE/$f" "$SHARED_CLAUDE/$f" 2>/dev/null; then
                    cp "$LOCAL_CLAUDE/$f" "$SHARED_CLAUDE/$f" 2>/dev/null || true
                fi
            fi
        done
    done
) &

# --- ファイアウォール設定 ---
/usr/local/bin/init-firewall.sh 2>/dev/null || true

# --- CLAUDE.md にコンテナ環境情報を書き込み ---
# マーカー（<!-- claude-dev-auto-start/end -->）で囲んだ範囲を毎回削除→再書き込みする。
# これにより entrypoint の更新が次回起動時に必ず反映される。
MARKER_START="<!-- claude-dev-auto-start -->"
MARKER_END="<!-- claude-dev-auto-end -->"
# CLAUDE.md がなければ作成
if [ ! -f /workspace/CLAUDE.md ]; then
    cat > /workspace/CLAUDE.md << 'CLAUDE_INIT_EOF'
# CLAUDE.md
CLAUDE_INIT_EOF
    chown "$USERNAME":"$USERNAME" /workspace/CLAUDE.md 2>/dev/null || true
fi

if [ -f /workspace/CLAUDE.md ]; then
    CONTAINER_NAME=$(hostname)

    # 既存のマーカー範囲を削除（旧形式のセクションも削除）
    TMP_CLAUDE=$(mktemp)
    sed "/${MARKER_START}/,/${MARKER_END}/d" /workspace/CLAUDE.md \
        | sed '/^## noVNC Chrome ブラウザ$/,/^## /{ /^## noVNC Chrome/d; /^## /!d; }' \
        | sed '/^## Web アプリの動作確認（重要）$/,/^## /{ /^## Web アプリ/d; /^## /!d; }' \
        | sed '/^## Docker ネットワーク（重要）$/,/^## /{ /^## Docker ネットワーク/d; /^## /!d; }' \
        > "$TMP_CLAUDE"
    # 末尾の空行を整理
    sed -i -e :a -e '/^\n*$/{$d;N;ba' -e '}' "$TMP_CLAUDE"
    mv "$TMP_CLAUDE" /workspace/CLAUDE.md

    # マーカーで囲んだ新しい内容を追記
    cat >> /workspace/CLAUDE.md << CLAUDE_AUTO_EOF

${MARKER_START}

## 注意事項

- 必ず公式の最新情報、最新仕様を調べて、それを適用すること

CLAUDE_AUTO_EOF

    # VNC ありの場合はブラウザ関連の情報を追加
    if [ "${CLAUDE_DEV_VNC:-}" = "1" ]; then
        cat >> /workspace/CLAUDE.md << 'CLAUDE_VNC_EOF'
## Web アプリの動作確認（重要）

- コンテナ内で Google Chrome が動作している。ユーザーは noVNC 経由でブラウザ画面をリアルタイムに確認できる
- chrome-devtools MCP サーバー経由で Chrome を操作すること
- **ヘッドレスブラウザを別途起動しないこと**（`chromium.launch()` 等は禁止）

### 動作確認の手順

1. 開発サーバーを起動する（`0.0.0.0` にバインドすること）
2. chrome-devtools MCP で Chrome を操作する（ページ遷移、クリック、入力、スクリーンショット等）
3. ユーザーは noVNC 画面で操作をリアルタイムに確認できる

### 注意事項
- 開発サーバーは `0.0.0.0` にバインドする（`--host 0.0.0.0` 等）
- コンテナ内の Chrome からは `localhost` で開発サーバーにアクセスできる

CLAUDE_VNC_EOF
    fi

    cat >> /workspace/CLAUDE.md << CLAUDE_DOCKER_EOF
## Docker ネットワーク（重要）

- このシェルは Docker コンテナ \`${CONTAINER_NAME}\` 内で動作している
- \`localhost\` / \`127.0.0.1\` では他のコンテナにアクセスできない。必ず**コンテナ名**を使うこと
  - 例: \`curl http://localhost:8000\` → \`curl http://${CONTAINER_NAME}:8000\`
- 自コンテナ内のサーバーへのアクセスは \`localhost\` で可
- \`docker ps\` でコンテナ名を確認できる
- 全コンテナは Docker ネットワーク \`claude-dev-net\` に接続されている

${MARKER_END}
CLAUDE_DOCKER_EOF
    chown "$USERNAME":"$USERNAME" /workspace/CLAUDE.md 2>/dev/null || true
fi

# --- MCP 設定（VNC ありの場合のみ）---
# chrome-devtools MCP サーバーで Chrome を操作するための設定
if [ "${CLAUDE_DEV_VNC:-}" = "1" ]; then
    # .mcp.json: chrome-devtools エントリを確保
    MCP_JSON="/workspace/.mcp.json"
    CHROME_DEVTOOLS_ENTRY='{"command":"npx","args":["-y","chrome-devtools-mcp@latest","--browserUrl","http://localhost:9222"]}'

    if [ ! -f "$MCP_JSON" ]; then
        # 新規作成
        echo "{\"mcpServers\":{\"chrome-devtools\":${CHROME_DEVTOOLS_ENTRY}}}" | jq . > "$MCP_JSON"
    else
        # 既存ファイルに chrome-devtools がなければ追加
        if ! jq -e '.mcpServers["chrome-devtools"]' "$MCP_JSON" >/dev/null 2>&1; then
            if jq --argjson entry "$CHROME_DEVTOOLS_ENTRY" '.mcpServers["chrome-devtools"] = $entry' "$MCP_JSON" > "${MCP_JSON}.tmp" 2>/dev/null; then
                mv "${MCP_JSON}.tmp" "$MCP_JSON"
            else
                rm -f "${MCP_JSON}.tmp"
                echo "⚠️  .mcp.json の更新に失敗しました（不正な JSON？）。chrome-devtools 追加をスキップします"
            fi
        fi
    fi
    chown "$USERNAME":"$USERNAME" "$MCP_JSON"

    # .claude.json: chrome-devtools MCP を有効化
    # .claude.json が存在しない場合は新規作成する
    CLAUDE_JSON="$LOCAL_CLAUDE/.claude.json"
    if [ ! -f "$CLAUDE_JSON" ]; then
        echo '{}' > "$CLAUDE_JSON"
        chown "$USERNAME":"$USERNAME" "$CLAUDE_JSON"
        chmod 600 "$CLAUDE_JSON"
    fi
    if ! jq -e '(.projects["/workspace"].enabledMcpjsonServers // []) | index("chrome-devtools")' "$CLAUDE_JSON" >/dev/null 2>&1; then
        if jq '
            .projects //= {} |
            .projects["/workspace"] //= {} |
            .projects["/workspace"].enabledMcpjsonServers = (
                (.projects["/workspace"].enabledMcpjsonServers // []) + ["chrome-devtools"] | unique
            )
        ' "$CLAUDE_JSON" > "${CLAUDE_JSON}.tmp" 2>/dev/null; then
            mv "${CLAUDE_JSON}.tmp" "$CLAUDE_JSON"
            chown "$USERNAME":"$USERNAME" "$CLAUDE_JSON"
            chmod 600 "$CLAUDE_JSON"
        else
            rm -f "${CLAUDE_JSON}.tmp"
            echo "⚠️  .claude.json の更新に失敗しました（不正な JSON？）。MCP 有効化をスキップします"
        fi
    fi
fi

# --- VNC / Chrome 起動（VNC ありイメージの場合のみ）---
if [ "${CLAUDE_DEV_VNC:-}" = "1" ]; then
    VNC_DISPLAY="${VNC_DISPLAY:-99}"
    VNC_RESOLUTION="${VNC_RESOLUTION:-1280x800}"
    VNC_PORT=5999
    NOVNC_PORT=6080

    # システム D-Bus デーモン
    mkdir -p /run/dbus
    dbus-daemon --system --fork 2>/dev/null || true

    # GTK immodules キャッシュ更新
    find /usr/lib -name "gtk-query-immodules-2.0" -exec {} --update-cache \; 2>/dev/null || true
    find /usr/lib -name "gtk-query-immodules-3.0" -exec {} --update-cache \; 2>/dev/null || true

    # VNC パスワードなし設定
    mkdir -p "$USER_HOME/.vnc"
    cat > "$USER_HOME/.vnc/xstartup" << 'XSTARTUP_EOF'
#!/bin/bash
XSTARTUP_EOF
    chmod +x "$USER_HOME/.vnc/xstartup"
    chown -R "$USERNAME":"$USERNAME" "$USER_HOME/.vnc"

    # Chrome プロファイルディレクトリの所有権
    if [ -d "$USER_HOME/.chrome-profile" ]; then
        chown "$USERNAME":"$USERNAME" "$USER_HOME/.chrome-profile" 2>/dev/null || true
    fi

    # デスクトッププロセスをユーザー権限で起動
    cat > /tmp/start-user-desktop.sh << DESKEOF
#!/bin/bash
export DISPLAY=:${VNC_DISPLAY}
export GTK_IM_MODULE=ibus
export QT_IM_MODULE=ibus
export XMODIFIERS=@im=ibus
export LANG=ja_JP.UTF-8
export LC_ALL=ja_JP.UTF-8
export IBUS_ENABLE_SYNC_MODE=1

# Xvnc（X サーバー + VNC サーバー一体型）
Xvnc :${VNC_DISPLAY} -geometry ${VNC_RESOLUTION} -depth 24 \
    -SecurityTypes None -rfbport ${VNC_PORT} \
    -AlwaysShared -AcceptKeyEvents -AcceptPointerEvents &
sleep 2

# キーボードレイアウト設定
setxkbmap -layout us,jp -model pc105 2>/dev/null || setxkbmap -layout us 2>/dev/null || true

# D-Bus セッションバス
eval "\$(dbus-launch --sh-syntax)"
export DBUS_SESSION_BUS_ADDRESS

# openbox
openbox &
sleep 0.5

# IBus デーモン
ibus-daemon -xrR &
for i in \$(seq 1 30); do
    ibus list-engine >/dev/null 2>&1 && break
    sleep 1
done

# IBus 設定
gsettings set org.freedesktop.ibus.general preload-engines "['xkb:us::eng', 'mozc-jp']" 2>/dev/null || true
gsettings set org.freedesktop.ibus.general.hotkey triggers "['<Control><Shift>space', '<Super>space']" 2>/dev/null || true
gsettings set org.freedesktop.ibus.general use-global-engine true 2>/dev/null || true

# noVNC（websockify: HTTP port ${NOVNC_PORT} → VNC port ${VNC_PORT}）
websockify --heartbeat 30 --web /usr/share/novnc ${NOVNC_PORT} localhost:${VNC_PORT} &
sleep 0.5

# Chrome プロファイルのロックファイルを削除（前回コンテナの残骸）
# Docker ボリュームに永続化されたプロファイルには前回コンテナの SingletonLock が残るため、
# 新コンテナで Chrome が「別プロセスが使用中」と判定し --remote-debugging-port を無視する
rm -f \$HOME/.chrome-profile/SingletonLock \$HOME/.chrome-profile/SingletonSocket \$HOME/.chrome-profile/SingletonCookie

# Chrome
sleep 2
google-chrome-stable --no-sandbox --disable-gpu --disable-software-rasterizer \
    --disable-dev-shm-usage --disable-background-networking \
    --no-first-run --no-default-browser-check --start-maximized \
    --remote-debugging-port=9222 \
    --gtk-version=4 \
    --user-data-dir=\$HOME/.chrome-profile &

wait
DESKEOF

    chmod +x /tmp/start-user-desktop.sh
    chown "$USERNAME":"$USERNAME" /tmp/start-user-desktop.sh
    su "$USERNAME" -s /bin/bash -c "/tmp/start-user-desktop.sh" &
    # VNC 起動完了メッセージはバックグラウンドで（tmux 起動をブロックしない）
    (sleep 12 && echo "🖥️  VNC 起動完了 (noVNC: port ${NOVNC_PORT})" && echo "   日本語入力: Ctrl+Shift+Space で切り替え (IBus-Mozc)") &
fi

# --- tmux セッション開始 ---
su "$USERNAME" -s /bin/zsh -l -c \
    "cd /workspace && tmux -f ~/.tmux.conf new-session -d -s main 'exec zsh -l'" \
    2>/dev/null || true

echo "✅ Ready (user: $USERNAME, uid: $(id -u $USERNAME), gid: $(id -g $USERNAME))"

# --- 待機 ---
exec tail -f /dev/null

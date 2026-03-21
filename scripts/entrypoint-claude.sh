#!/bin/bash
# =============================================================================
# Claude コンテナ エントリポイント
# =============================================================================
# 1. /workspace の所有者 UID/GID にコンテナユーザーを合わせる
# 2. ~/.claude/.claude.json → ~/.claude.json の symlink 作成
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
        # GID 変更
        if [ "$HOST_GID" != "$CURRENT_GID" ]; then
            CONFLICT_GROUP=$(getent group "$HOST_GID" 2>/dev/null | cut -d: -f1)
            if [ -n "$CONFLICT_GROUP" ] && [ "$CONFLICT_GROUP" != "$USERNAME" ]; then
                # 競合するグループの GID を退避（99xx 番台の空き番号へ）
                TEMP_GID=9900
                while getent group "$TEMP_GID" >/dev/null 2>&1; do
                    TEMP_GID=$((TEMP_GID + 1))
                done
                groupmod -g "$TEMP_GID" "$CONFLICT_GROUP" 2>/dev/null || true
            fi
            groupmod -g "$HOST_GID" "$USERNAME" 2>/dev/null || true
        fi
        # UID 変更
        if [ "$HOST_UID" != "$CURRENT_UID" ]; then
            CONFLICT_USER=$(getent passwd "$HOST_UID" 2>/dev/null | cut -d: -f1)
            if [ -n "$CONFLICT_USER" ] && [ "$CONFLICT_USER" != "$USERNAME" ]; then
                # 競合するユーザーの UID を退避（99xx 番台の空き番号へ）
                TEMP_UID=9900
                while getent passwd "$TEMP_UID" >/dev/null 2>&1; do
                    TEMP_UID=$((TEMP_UID + 1))
                done
                usermod -u "$TEMP_UID" "$CONFLICT_USER" 2>/dev/null || true
            fi
            usermod -u "$HOST_UID" "$USERNAME" 2>/dev/null || true
        fi
        # ホームディレクトリの所有権を更新
        chown -R "$USERNAME":"$USERNAME" "$USER_HOME" 2>/dev/null || true
    fi
fi

# --- ~/.ssh ディレクトリの所有権・パーミッション ---
if [ -d "$USER_HOME/.ssh" ]; then
    chown "$USERNAME":"$USERNAME" "$USER_HOME/.ssh" 2>/dev/null || true
    chmod 700 "$USER_HOME/.ssh" 2>/dev/null || true
    # known_hosts, config は読み取り専用マウントなので chown/chmod しない
fi

# --- .zshrc の共有（ボリューム経由でコンテナ間共有）---
# ~/.config-shared/ はボリュームとしてマウントされている
SHARED_DIR="$USER_HOME/.config-shared"
if [ -d "$SHARED_DIR" ]; then
    chown "$USERNAME":"$USERNAME" "$SHARED_DIR" 2>/dev/null || true
    # 初回: ボリュームに .zshrc がなければイメージのデフォルトをコピー
    if [ ! -f "$SHARED_DIR/.zshrc" ]; then
        if [ -f "$USER_HOME/.zshrc" ] && [ ! -L "$USER_HOME/.zshrc" ]; then
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

# --- 認証情報の symlink ---
# ~/.claude/ はボリュームとして直接マウントされている
# ~/.claude.json は Claude Code が参照するので、ボリューム内のファイルに symlink する
if [ -f "$USER_HOME/.claude/.claude.json" ]; then
    ln -sf "$USER_HOME/.claude/.claude.json" "$USER_HOME/.claude.json"
    chown -h "$USERNAME":"$USERNAME" "$USER_HOME/.claude.json"
fi

# --- ~/.claude/ ディレクトリの所有権 ---
chown -R "$USERNAME":"$USERNAME" "$USER_HOME/.claude" 2>/dev/null || true

# --- settings.json の確保 ---
# bypassPermissions 設定が消えていたら再作成
SETTINGS="$USER_HOME/.claude/settings.json"
if [ ! -f "$SETTINGS" ]; then
    echo '{"permissions":{"defaultMode":"bypassPermissions"}}' > "$SETTINGS"
    chown "$USERNAME":"$USERNAME" "$SETTINGS"
fi

# --- ファイアウォール設定 ---
/usr/local/bin/init-firewall.sh 2>/dev/null || true

# --- VNC 環境起動（ENABLE_VNC=1 の場合） ---
if [ "${ENABLE_VNC:-0}" = "1" ]; then
    VNC_DISPLAY="${VNC_DISPLAY:-99}"
    VNC_RESOLUTION="${VNC_RESOLUTION:-1920x1080x24}"
    VNC_PORT=5900
    NOVNC_PORT=6080

    # Xvfb（仮想ディスプレイ）
    su "$USERNAME" -c "Xvfb :${VNC_DISPLAY} -screen 0 ${VNC_RESOLUTION} &"
    sleep 1

    # openbox（ウィンドウマネージャ）
    su "$USERNAME" -c "DISPLAY=:${VNC_DISPLAY} openbox &"
    sleep 0.5

    # x11vnc（VNC サーバー）
    su "$USERNAME" -c "x11vnc -display :${VNC_DISPLAY} -forever -nopw -rfbport ${VNC_PORT} -shared &"
    sleep 0.5

    # websockify + noVNC（Web ブラウザからアクセス）
    su "$USERNAME" -c "websockify --web /usr/share/novnc ${NOVNC_PORT} localhost:${VNC_PORT} &"
    sleep 0.5

    # DISPLAY 環境変数をシェル設定に追加（tmux 内で Chrome が使えるように）
    echo "export DISPLAY=:${VNC_DISPLAY}" >> "$USER_HOME/.zshrc"
    echo "export DISPLAY=:${VNC_DISPLAY}" >> "$USER_HOME/.bashrc"

    echo "🖥️  VNC 起動 (noVNC: port ${NOVNC_PORT}, VNC: port ${VNC_PORT})"
fi

# --- tmux セッション開始 ---
su "$USERNAME" -s /bin/zsh -l -c \
    "cd /workspace && tmux -f ~/.tmux.conf new-session -d -s main 'exec zsh -l'" \
    2>/dev/null || true

echo "✅ Ready (user: $USERNAME, uid: $(id -u $USERNAME), gid: $(id -g $USERNAME))"

# --- 待機 ---
exec tail -f /dev/null

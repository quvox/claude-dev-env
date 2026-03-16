#!/bin/bash
# =============================================================================
# Claude コンテナ エントリポイント
# =============================================================================
# 1. /workspace の所有者 UID/GID に devuser を合わせる
# 2. ~/.claude/.claude.json → ~/.claude.json の symlink 作成
# 3. ファイアウォール設定
# 4. tmux 起動
# =============================================================================
set -e

USERNAME="devuser"
USER_HOME="/home/$USERNAME"

# --- /workspace の所有者に UID/GID を合わせる ---
if [ -d /workspace ]; then
    HOST_UID=$(stat -c '%u' /workspace 2>/dev/null || echo "1500")
    HOST_GID=$(stat -c '%g' /workspace 2>/dev/null || echo "1500")
    CURRENT_UID=$(id -u "$USERNAME" 2>/dev/null || echo "1500")
    CURRENT_GID=$(id -g "$USERNAME" 2>/dev/null || echo "1500")

    if [ "$HOST_UID" != "0" ] && [ "$HOST_UID" != "$CURRENT_UID" ]; then
        # GID 変更（既存グループと被る場合はスキップ）
        if [ "$HOST_GID" != "$CURRENT_GID" ]; then
            if ! getent group "$HOST_GID" >/dev/null 2>&1; then
                groupmod -g "$HOST_GID" "$USERNAME" 2>/dev/null || true
            fi
        fi
        # UID 変更（既存ユーザーと被る場合はスキップ）
        if ! getent passwd "$HOST_UID" >/dev/null 2>&1; then
            usermod -u "$HOST_UID" "$USERNAME" 2>/dev/null || true
        fi
        # ホームディレクトリの所有権を更新
        chown -R "$USERNAME":"$USERNAME" "$USER_HOME" 2>/dev/null || true
    fi
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

# --- tmux セッション開始 ---
su "$USERNAME" -s /bin/zsh -l -c \
    "cd /workspace && tmux -f ~/.tmux.conf new-session -d -s main 'exec zsh -l'" \
    2>/dev/null || true

echo "✅ Ready (user: $USERNAME, uid: $(id -u $USERNAME), gid: $(id -g $USERNAME))"

# --- 待機 ---
exec tail -f /dev/null

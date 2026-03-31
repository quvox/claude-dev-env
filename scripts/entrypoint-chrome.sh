#!/bin/bash
# =============================================================================
# Chrome/VNC コンテナ エントリポイント
# =============================================================================
# TigerVNC (Xvnc) を X サーバーとして使用
# Xvnc は X サーバーと VNC サーバーが一体化しているため、
# キーイベントがネイティブ X11 イベントとして処理され、
# IBus のキーインターセプトが正常に動作する
# =============================================================================

USERNAME="${CONTAINER_USER:-devuser}"
USER_HOME="/home/$USERNAME"

# --- auth ボリュームの所有権 ---
chown -R "$USERNAME":"$USERNAME" "$USER_HOME/.claude-shared" 2>/dev/null || true
# 認証ファイルを共有ボリュームからコピー（symlink ではなく実体コピー）
mkdir -p "$USER_HOME/.claude"
chown "$USERNAME":"$USERNAME" "$USER_HOME/.claude"
for f in .credentials.json .claude.json; do
    if [ -f "$USER_HOME/.claude-shared/$f" ]; then
        cp "$USER_HOME/.claude-shared/$f" "$USER_HOME/.claude/$f"
        chown "$USERNAME":"$USERNAME" "$USER_HOME/.claude/$f"
    fi
done
if [ -f "$USER_HOME/.claude/.claude.json" ]; then
    ln -sf "$USER_HOME/.claude/.claude.json" "$USER_HOME/.claude.json"
    chown -h "$USERNAME":"$USERNAME" "$USER_HOME/.claude.json"
fi

# --- Chrome ユーザーデータの所有権（ボリュームマウント）---
if [ -d "$USER_HOME/.config/google-chrome" ]; then
    chown "$USERNAME":"$USERNAME" "$USER_HOME/.config/google-chrome" 2>/dev/null || true
fi

# --- GTK immodules キャッシュ更新 ---
find /usr/lib -name "gtk-query-immodules-2.0" -exec {} --update-cache \; 2>/dev/null || true
find /usr/lib -name "gtk-query-immodules-3.0" -exec {} --update-cache \; 2>/dev/null || true

# --- システム D-Bus デーモン ---
mkdir -p /run/dbus
dbus-daemon --system --fork 2>/dev/null || true

# --- 共通変数 ---
VNC_DISPLAY="${VNC_DISPLAY:-99}"
VNC_RESOLUTION="${VNC_RESOLUTION:-1280x800}"
VNC_PORT=5900
NOVNC_PORT=6080

# --- TigerVNC (Xvnc) パスワードなしで設定 ---
mkdir -p "$USER_HOME/.vnc"
# セキュリティなし（コンテナ内のローカルアクセスのみ）
cat > "$USER_HOME/.vnc/xstartup" << 'XSTARTUP_EOF'
#!/bin/bash
# This is started by Xvnc
XSTARTUP_EOF
chmod +x "$USER_HOME/.vnc/xstartup"
chown -R "$USERNAME":"$USERNAME" "$USER_HOME/.vnc"

# --- 全デスクトッププロセスをユーザーシェルから起動 ---
cat > /tmp/start-user-desktop.sh << EOF
#!/bin/bash
export DISPLAY=:${VNC_DISPLAY}
export GTK_IM_MODULE=ibus
export QT_IM_MODULE=ibus
export XMODIFIERS=@im=ibus
export LANG=ja_JP.UTF-8
export LC_ALL=ja_JP.UTF-8
export IBUS_ENABLE_SYNC_MODE=1

# --- Xvnc（X サーバー + VNC サーバー一体型）---
# 注意: -xkblayout us,jp -xkbmodel pc105 を指定すると Xvnc が起動に失敗する
# 代わりに起動後に setxkbmap で設定する
Xvnc :${VNC_DISPLAY} -geometry ${VNC_RESOLUTION} -depth 24 \
    -SecurityTypes None -rfbport ${VNC_PORT} \
    -AlwaysShared -AcceptKeyEvents -AcceptPointerEvents &
sleep 2

# キーボードレイアウト設定（Xvnc 起動後に適用）
setxkbmap -layout us,jp -model pc105 2>/dev/null || setxkbmap -layout us 2>/dev/null || true

# D-Bus セッションバス
eval "\$(dbus-launch --sh-syntax)"
export DBUS_SESSION_BUS_ADDRESS

echo "--- Environment ---"
echo "DISPLAY=\$DISPLAY"
echo "DBUS_SESSION_BUS_ADDRESS=\$DBUS_SESSION_BUS_ADDRESS"
echo "GTK_IM_MODULE=\$GTK_IM_MODULE"

# GTK immodules cache 確認
echo "--- GTK3 ibus in cache ---"
grep ibus /usr/lib/x86_64-linux-gnu/gtk-3.0/3.0.0/immodules.cache 2>/dev/null | head -2 || echo "NOT FOUND"

# openbox
openbox &
sleep 0.5

# IBus デーモン（フォアグラウンドでバックグラウンド実行、-d なし）
ibus-daemon -xrR &

# IBus デーモンの準備完了をポーリングで待つ
echo "Waiting for ibus-daemon to be ready..."
for i in \$(seq 1 30); do
    if ibus list-engine >/dev/null 2>&1; then
        echo "ibus-daemon ready (attempt \$i)"
        break
    fi
    sleep 1
done

# IBus 設定
gsettings set org.freedesktop.ibus.general preload-engines "['xkb:us::eng', 'mozc-jp']" || echo "WARN: preload-engines failed"
# IBus 内蔵ホットキーは無効化（openbox のキーバインドで toggle-ime を使う）
gsettings set org.freedesktop.ibus.general.hotkey triggers "[]" || echo "WARN: hotkey failed"
gsettings set org.freedesktop.ibus.general use-global-engine true || echo "WARN: use-global-engine failed"

# noVNC（--heartbeat で WebSocket 接続を維持）
websockify --heartbeat 30 --web /usr/share/novnc ${NOVNC_PORT} localhost:${VNC_PORT} &
sleep 0.5

# Chrome（--gtk-version=4 は Chrome 135+ の IBus バグ回避に必要）
sleep 2
google-chrome-stable --no-sandbox --disable-gpu --disable-software-rasterizer \
    --disable-dev-shm-usage --disable-background-networking \
    --no-first-run --no-default-browser-check --start-maximized \
    --gtk-version=4 \
    --remote-debugging-address=0.0.0.0 --remote-debugging-port=9222 &

# 初期エンジンは mozc-jp（preload-engines の設定による）
# ibus engine コマンドでの切り替えはフォーカスされた入力コンテキストが
# 必要なため起動時には実行不可。F2 キーで英語/日本語を切り替える。
echo "Engine: \$(ibus engine 2>/dev/null)"

echo "🖥️  Desktop ready (noVNC: port ${NOVNC_PORT})"

wait
EOF

chmod +x /tmp/start-user-desktop.sh
chown "$USERNAME":"$USERNAME" /tmp/start-user-desktop.sh

# --- ユーザー権限で一括起動 ---
su "$USERNAME" -c "/tmp/start-user-desktop.sh" &
sleep 12

echo "🖥️  Chrome/VNC 起動完了 (noVNC: port ${NOVNC_PORT})"
echo "   日本語入力: Ctrl+\\ または F3 で切り替え (IBus-Mozc)"
echo "   右クリック → Terminal でターミナル起動"

# --- 待機 ---
exec tail -f /dev/null

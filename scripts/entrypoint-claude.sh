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

# --- Chrome DevTools MCP 設定 ---
# claude mcp add で MCP サーバーを登録する。このコマンドは:
#   1. /workspace/.mcp.json に chrome-devtools エントリを作成/更新
#   2. .claude.json の enabledMcpjsonServers に自動追加（trust 承認含む）
# .mcp.json を直接編集すると trust ダイアログの承認が別途必要になるため、
# 必ず claude mcp add を使う。
# 注意: Claude Code は ~/.claude/mcp.json ではなく .mcp.json（プロジェクトルート直下）を読む。
# claude mcp add --scope project は /workspace/.mcp.json に書き込む
# su -l のログインシェルでは ~/.local/bin が PATH に入らない場合があるため、
# claude のフルパスを使用する
CLAUDE_BIN="$USER_HOME/.local/bin/claude"
MCP_JSON="/workspace/.mcp.json"
MCP_NEED_ADD=0
if [ ! -f "$MCP_JSON" ]; then
    MCP_NEED_ADD=1
elif ! grep -q '"chrome-devtools"' "$MCP_JSON" 2>/dev/null; then
    MCP_NEED_ADD=1
elif ! grep -q '127\.0\.0\.1:9222' "$MCP_JSON" 2>/dev/null; then
    # エントリはあるが接続先が古い場合は再登録
    su "$USERNAME" -s /bin/zsh -l -c "cd /workspace && $CLAUDE_BIN mcp remove chrome-devtools --scope project" 2>/dev/null || true
    MCP_NEED_ADD=1
fi
if [ "$MCP_NEED_ADD" = "1" ] && [ -x "$CLAUDE_BIN" ]; then
    # スクリプト経由で実行（su -l の cd $HOME 問題を回避）
    cat > /tmp/mcp-add.sh << 'MCP_SCRIPT'
#!/bin/zsh
cd /workspace
"$1" mcp add --transport stdio chrome-devtools --scope project -- chrome-devtools-mcp --browserUrl=http://127.0.0.1:9222
MCP_SCRIPT
    chmod +x /tmp/mcp-add.sh
    su "$USERNAME" -s /bin/zsh -c "/tmp/mcp-add.sh $CLAUDE_BIN" 2>/dev/null || true
    rm -f /tmp/mcp-add.sh
fi

# --- .claude.json の enabledMcpjsonServers に chrome-devtools を追加 ---
# claude mcp add は .mcp.json を作成するが、enabledMcpjsonServers への追加は
# Claude Code の trust ダイアログ経由でしか行われない。
# コンテナ環境では --dangerously-skip-permissions で動作する前提のため、
# entrypoint で直接追加する。
CLAUDE_JSON="$LOCAL_CLAUDE/.claude.json"
if command -v jq >/dev/null 2>&1; then
    # .claude.json がなければ最小限の内容で作成
    if [ ! -f "$CLAUDE_JSON" ]; then
        echo '{}' > "$CLAUDE_JSON"
        chown "$USERNAME":"$USERNAME" "$CLAUDE_JSON"
    fi
    if ! jq -e '.projects["/workspace"].enabledMcpjsonServers // [] | index("chrome-devtools")' "$CLAUDE_JSON" >/dev/null 2>&1; then
        TMP_CJ=$(mktemp)
        jq '
            .projects["/workspace"].enabledMcpjsonServers = (
                (.projects["/workspace"].enabledMcpjsonServers // []) + ["chrome-devtools"] | unique
            )
        ' "$CLAUDE_JSON" > "$TMP_CJ" \
            && mv "$TMP_CJ" "$CLAUDE_JSON" \
            && chown "$USERNAME":"$USERNAME" "$CLAUDE_JSON"
    fi
fi

# --- Chrome DevTools CDP リレー ---
# Chrome 146+ では CDP が 127.0.0.1 にのみバインドされ、Host ヘッダーが
# IP または localhost でないと拒否される。socat でローカルにリレーすることで
# MCP が http://127.0.0.1:9222 に接続できるようにする。
# Chrome コンテナ側でも socat が 0.0.0.0:9223 → 127.0.0.1:9222 にリレーしている。
if command -v socat >/dev/null 2>&1; then
    socat TCP-LISTEN:9222,fork,reuseaddr,bind=127.0.0.1 TCP:claude-dev-chrome:9223 &
fi

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

## Web アプリの動作確認（重要）

- **ヘッドレスブラウザを直接起動しないこと**（\`chromium.launch()\` 等は禁止）
- 別コンテナ \`claude-dev-chrome\` で Google Chrome が起動している。ユーザーは noVNC 経由でブラウザ画面をリアルタイムに確認できる
- Chrome DevTools MCP が設定済みで、MCP ツール経由で noVNC の Chrome を直接操作できる

### 動作確認の手順

1. 開発サーバーを起動する（\`0.0.0.0\` にバインドすること）
2. MCP ツールで Chrome を操作する（ページ遷移、クリック、入力、スクリーンショット等）
3. ユーザーは noVNC 画面で操作をリアルタイムに確認できる

### 利用可能な主要 MCP ツール

- \`navigate_page\` — URL に遷移する
- \`take_screenshot\` — スクリーンショットを撮る
- \`click\` — 要素をクリックする
- \`fill\` — 入力欄にテキストを入力する
- \`fill_form\` — 複数のフォーム要素を一括入力する
- \`press_key\` — キーボード操作を送信する
- \`evaluate_script\` — JavaScript を実行する
- \`list_console_messages\` — コンソール出力を取得する
- \`list_network_requests\` — ネットワークリクエストを確認する
- \`take_snapshot\` — DOM スナップショットを取得する

### 注意事項
- URL には \`localhost\` ではなく**コンテナ名**を使うこと（例: \`http://${CONTAINER_NAME}:3000\`）
- 開発サーバーは \`0.0.0.0\` にバインドする（\`--host 0.0.0.0\` 等）

## Docker ネットワーク（重要）

- このシェルは Docker コンテナ \`${CONTAINER_NAME}\` 内で動作している
- \`localhost\` / \`127.0.0.1\` では他のコンテナにアクセスできない。必ず**コンテナ名**を使うこと
  - 例: \`curl http://localhost:8000\` → \`curl http://${CONTAINER_NAME}:8000\`
- 自コンテナ内のサーバーへのアクセスは \`localhost\` で可
- \`docker ps\` でコンテナ名を確認できる
- 全コンテナは Docker ネットワーク \`claude-dev-net\` に接続されている

${MARKER_END}
CLAUDE_AUTO_EOF
    chown "$USERNAME":"$USERNAME" /workspace/CLAUDE.md 2>/dev/null || true
fi

# --- tmux セッション開始 ---
su "$USERNAME" -s /bin/zsh -l -c \
    "cd /workspace && tmux -f ~/.tmux.conf new-session -d -s main 'exec zsh -l'" \
    2>/dev/null || true

echo "✅ Ready (user: $USERNAME, uid: $(id -u $USERNAME), gid: $(id -g $USERNAME))"

# --- 待機 ---
exec tail -f /dev/null

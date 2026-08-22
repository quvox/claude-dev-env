#!/bin/bash
# =============================================================================
# Claude コンテナ エントリポイント
# =============================================================================
# 1. /workspace の所有者 UID/GID にコンテナユーザーを合わせる
# 2. ~/.claude → /workspace/.claude・~/.codex → /workspace/.codex にシンボリックリンク
#    認証ファイルを共有ボリューム（~/.claude-shared/、codex は同 codex/）からコピー
# 3. ファイアウォール設定
# 4. tmux 起動
# =============================================================================
set -e

# CONTAINER_USER は Dockerfile の ENV で設定される（デフォルト: devuser）
USERNAME="${CONTAINER_USER:-devuser}"
USER_HOME="/home/$USERNAME"

# --- 実行時に決まる環境変数の受け渡し先 ---
# コンテナ作成時には決まらず、この entrypoint が実行時に決める環境変数（VM モードの
# DOCKER_HOST / 中継ポート方式の SSH_AUTH_SOCK）を1本のファイルに記録する。docker exec が
# 引き継ぐのはコンテナ作成時の env だけなので、稼働中のコンテナへ外からプロセスの木を起こす側
# （ホスト CLI が tmux サーバを作り直す経路）はこれを読んでから起こす
# （CTR-cli-container「実行時に決まる環境変数の受け渡し」/ FR-env-07-13 / FR-env-14-11）。
# **自分の実行の最初に空へ戻す** — コンテナの再起動で前回の値が残ると、今回は採用しなかった
# 値を配ることになる。**秘密は書かない**（0644 で全ユーザーが読む）。
RUNTIME_ENV_FILE=/etc/claude-dev/runtime.env
mkdir -p /etc/claude-dev
: > "$RUNTIME_ENV_FILE"
chmod 0644 "$RUNTIME_ENV_FILE"

# 実行時に値を採用した時点で1行ずつ追記する（採用しなかった変数の行は書かない）
record_runtime_env() {
    printf "export %s='%s'\n" "$1" "$2" >> "$RUNTIME_ENV_FILE"
}

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

# --- SSH agent の受け口を用意（macOS 版の TCP ブリッジ）---
# CLAUDE_DEV_SSH_BRIDGE_PORT が渡された場合（macOS の方式D。設計 docs/09 §1）、
# ホストの claude-dev 専用 agent へ host.docker.internal:<port> 経由で接続する socat を
# $USERNAME 権限で起動し、/tmp/ssh-agent.sock（ユーザー所有・0600）を用意する。
# Linux 版は $SSH_AUTH_SOCK を /tmp/ssh-agent.sock に直接 bind mount しているため本分岐は通らない。
if [ -n "${CLAUDE_DEV_SSH_BRIDGE_PORT:-}" ] && command -v socat >/dev/null 2>&1; then
    rm -f /tmp/ssh-agent.sock
    su "$USERNAME" -c "nohup socat UNIX-LISTEN:/tmp/ssh-agent.sock,fork,mode=600 TCP:host.docker.internal:${CLAUDE_DEV_SSH_BRIDGE_PORT} >/dev/null 2>&1 &"
    for _i in $(seq 1 20); do
        [ -S /tmp/ssh-agent.sock ] && break
        sleep 0.2
    done
fi

# --- SSH_AUTH_SOCK を確定させる ---
# 対話シェル向けにはシェル初期化ファイルへ書き出す（初期化ファイルを読むのは対話シェルだけ）。
# tmux の窓の中のプロセスへは、下の tmux 起動が -l を付けずに環境をそのまま引き継ぐことで届く
# （FR-env-07-13）。macOS 経路ではこのソケットを上の socat が作っており、ホストの -e では
# 渡ってきていないので、ここで自分の環境にも export しないと tmux へ引き継がれない。
if [ -S "/tmp/ssh-agent.sock" ]; then
    export SSH_AUTH_SOCK=/tmp/ssh-agent.sock
    # 外から木を起こす側へも同じ値を届ける（中継ポート方式ではホストの -e で渡ってきていない）
    record_runtime_env SSH_AUTH_SOCK /tmp/ssh-agent.sock
    for rc in /etc/zsh/zshrc /etc/bash.bashrc; do
        if [ -f "$rc" ]; then
            echo "" >> "$rc"
            echo "# --- claude-dev: SSH agent forwarding ---" >> "$rc"
            echo 'export SSH_AUTH_SOCK=/tmp/ssh-agent.sock' >> "$rc"
        fi
    done
fi

# --- Docker Socket Proxy の設定 ---
# 対話シェル向けにシェル初期化ファイルへ書き出す。読むのは対話シェルだけなので、
# 非対話シェルには効かない。**tmux の窓の中のプロセスへは、下の tmux 起動が -l を付けずに
# 環境をそのまま引き継ぐことで届く**（この export は対話シェルの利便のためであって、
# 到達の義務を果たす手段ではない。CTR-cli-container「渡す環境変数」）。
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

# docker compose プロジェクト名の一意化（COMPOSE_PROJECT_NAME）は、ホスト CLI 側で docker run の
# -e として渡す（cli/cli-mac が正本）。ここで rc へ書き出さないのは、-e で渡った値が
# コンテナのプロセス環境に在り、下の tmux 起動が -l を付けずにそれを引き継ぐためである。

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
#   codex も同じ形にする。~/.codex/ は /workspace/.codex/ へのシンボリックリンクとし、
#   認証ファイル auth.json だけを共有ボリュームの codex/ サブディレクトリ経由で共有する
#   （config.toml・セッション履歴は共有せずコンテナ固有。D-27）。
#
# 共有対象: claude=.credentials.json, .claude.json / codex=auth.json のみ
# =============================================================================
SHARED_CLAUDE="$USER_HOME/.claude-shared"
LOCAL_CLAUDE="/workspace/.claude"
AUTH_FILES=".credentials.json .claude.json"
# codex 認証は claude と同じボリュームの codex/ に相乗りする（D-27。ボリュームを増やさず
# logout / reset の分岐も増やさないため。ディレクトリ名が claude 由来なのは歴史的経緯）
SHARED_CODEX="$SHARED_CLAUDE/codex"
LOCAL_CODEX="/workspace/.codex"
CODEX_AUTH_FILES="auth.json"

# 共有ボリュームの所有権
chown "$USERNAME":"$USERNAME" "$SHARED_CLAUDE" 2>/dev/null || true
mkdir -p "$SHARED_CODEX" 2>/dev/null || true
chown "$USERNAME":"$USERNAME" "$SHARED_CODEX" 2>/dev/null || true

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

# --- codex（~/.codex → /workspace/.codex）も同じ形に整える ---
mkdir -p "$LOCAL_CODEX"
chown "$USERNAME":"$USERNAME" "$LOCAL_CODEX"

# ~/.codex が実ディレクトリの場合は中身を退避してから削除（ln -sfn は実ディレクトリを置き換えられない）
if [ -d "$USER_HOME/.codex" ] && [ ! -L "$USER_HOME/.codex" ]; then
    cp -an "$USER_HOME/.codex/." "$LOCAL_CODEX/" 2>/dev/null || true
    rm -rf "$USER_HOME/.codex"
fi

ln -sfn "$LOCAL_CODEX" "$USER_HOME/.codex"
chown -h "$USERNAME":"$USERNAME" "$USER_HOME/.codex"

# 認証ファイルのパーミッション修正（claude-dev start でコピー済み）
for f in $CODEX_AUTH_FILES; do
    if [ -f "$LOCAL_CODEX/$f" ]; then
        chown "$USERNAME":"$USERNAME" "$LOCAL_CODEX/$f"
        chmod 600 "$LOCAL_CODEX/$f"
    fi
done

# --- settings.json はコンテナローカル（共有しない）---
if [ ! -f "$LOCAL_CLAUDE/settings.json" ]; then
    echo '{"permissions":{"defaultMode":"bypassPermissions"},"model":"sonnet"}' > "$LOCAL_CLAUDE/settings.json"
    chown "$USERNAME":"$USERNAME" "$LOCAL_CLAUDE/settings.json"
fi

# --- codex の config.toml もコンテナローカル（共有しない）---
# 既定 3 鍵を保証する（要件 core/12-5,12-6,12-9 / D-27 ⑥）:
#   sandbox_mode = "danger-full-access"   … 既定でサンドボックスを無効化
#   approval_policy = "never"
#   [features] use_legacy_landlock = true … --sandbox read-only を明示要求された場合の受け皿
# 前 2 鍵が必要な理由: codex 自前のサンドボックス（Linux では bubblewrap 実装）はこのコンテナ内では
# 起動できない。Docker 既定 seccomp が CLONE_NEWUSER を拒否し、それを外しても docker-default
# AppArmor が mount --make-rslave / を拒否する 2 段構えのため。既定の sandbox_mode のままでは
# codex が起こすシェルコマンドが例外なく exited 1 になるので、隔離はコンテナ境界に委ねる。
# 3 鍵目が必要な理由: --sandbox read-only のような明示指定は config の既定を上書きして bwrap 経路へ
# 戻ってしまう。landlock はユーザー名前空間を必要としないため confinement を緩めずに成立する。
# コンテナ側の --security-opt は緩めない（要件 core/12-7。ホスト CLI の責務）。
#
# 既存ファイルがある場合は「書かれている鍵とその値を一切書き換えず、不足している鍵だけを追記」する
# （要件 core/12-6・冪等）。TOML はテーブル見出し以降の鍵が当該テーブルに属するため、単純な末尾追記は
# トップレベル鍵の意味を変えてしまう。よって追記位置を次のとおり固定する:
#   - sandbox_mode / approval_policy … 最初のテーブル見出し（[...] 行）の直前
#   - use_legacy_landlock            … [features] 見出しの直後（無ければ末尾に見出しごと）
# 位置を特定できない（TOML として壊れている）場合は何も書かず警告のみ出して継続する。
ensure_codex_config() {
    _cfg="$LOCAL_CODEX/config.toml"

    if [ ! -f "$_cfg" ]; then
        printf '%s\n%s\n\n%s\n%s\n' \
            'sandbox_mode = "danger-full-access"' \
            'approval_policy = "never"' \
            '[features]' \
            'use_legacy_landlock = true' \
            > "$_cfg"
        chown "$USERNAME":"$USERNAME" "$_cfg"
        return 0
    fi

    # 既存ファイルの補完には TOML パーサが要る。行単位の正規表現では、複数行文字列の中の
    # `[features]` を見出しと誤認する・quoted key（`"sandbox_mode" = ...`）を見落として
    # 重複定義を作る・`[[features]]`（配列テーブル）を通常テーブルと混同する、といった形で
    # 「既存の鍵と値を変更しない」を破りうるため（2026-07-31 の独立レビュー指摘）。
    if ! command -v python3 >/dev/null 2>&1 || ! python3 -c 'import tomllib' >/dev/null 2>&1; then
        echo "⚠️  python3/tomllib が無いため codex config.toml の既定鍵補完をスキップします: $_cfg"
        return 0
    fi

    python3 - "$_cfg" <<'PYEOF'
import os, re, sys, tempfile, tomllib

path = sys.argv[1]
WANT = [(("sandbox_mode",),  'sandbox_mode = "danger-full-access"',  "danger-full-access"),
        (("approval_policy",), 'approval_policy = "never"',          "never"),
        (("features", "use_legacy_landlock"), "use_legacy_landlock = true", True)]

def flatten(d, prefix=()):
    out = {}
    for k, v in d.items():
        p = prefix + (k,)
        if isinstance(v, dict):
            out.update(flatten(v, p))
        else:
            out[p] = v
    return out

try:
    raw = open(path, "rb").read()
    orig = tomllib.loads(raw.decode("utf-8"))
except Exception as e:
    print(f"⚠️  codex config.toml を TOML として読めません。既定鍵の補完をスキップします: {path} ({e})")
    sys.exit(0)

oflat = flatten(orig)
missing = [w for w in WANT if w[0] not in oflat]
if not missing:
    sys.exit(0)                                   # 3 鍵とも揃っている（冪等）

text = raw.decode("utf-8")
nl = "\r\n" if "\r\n" in text else "\n"
lines = text.splitlines()

need_top = [m for m in missing if len(m[0]) == 1]
need_ll  = [m for m in missing if m[0] == ("features", "use_legacy_landlock")]

# features が配列テーブル（[[features]]）等で定義済みなら、既存値を変えずに鍵を足す方法が無い。
feat = orig.get("features")
ll_blocked = bool(need_ll) and feat is not None and not isinstance(feat, dict)
ll_reason = "既存の features が通常テーブルではない（配列テーブル等）"

# [features] 見出し行。空白・quoted key（["features"]）・行末コメントを許容する。
HDR = re.compile(r"""^\s*\[\s*(?:features|"features"|'features')\s*\]\s*(?:#.*)?\r?$""")
hdr_idx = next((i for i, l in enumerate(lines) if HDR.match(l)), None)

def build(strategy):
    """挿入位置の候補を 1 つ作る。作れない戦略には None を返す。"""
    out = list(lines)
    if need_ll and not ll_blocked:
        if strategy == "after_header":
            if hdr_idx is None:
                return None
            out.insert(hdr_idx + 1, "use_legacy_landlock = true")
        else:                       # "append": 末尾に [features] ごと足す
            out = out + ["", "[features]", "use_legacy_landlock = true"]
    # トップレベル鍵はファイル先頭へ。先頭は常にトップレベルなので最も安全。
    if need_top:
        out = [m[1] for m in need_top] + out
    return nl.join(out) + nl

def verify(cand, expect_ll):
    """既存の全キーパスの値が不変で、増分が意図した鍵だけかを意味的に確かめる。"""
    try:
        new = tomllib.loads(cand)
    except Exception:
        return None
    nflat = flatten(new)
    for kp, v in oflat.items():
        if kp not in nflat or nflat[kp] != v:
            return None
    want = {m[0]: m[2] for m in need_top}
    if expect_ll:
        want[("features", "use_legacy_landlock")] = True
    extra = set(nflat) - set(oflat)
    if extra != set(want) or any(nflat[kp] != want[kp] for kp in extra):
        return None
    return cand

cand = None
if not ll_blocked:
    # 見出しの直後 → 末尾に見出しごと、の順に試し、検証を通った最初の候補を採る。
    # 行単位の見出し検出が外れても（複数行文字列の中の [features] 等）、検証が弾いて次へ進む。
    for st in ("after_header", "append"):
        c = build(st)
        if c is not None and verify(c, bool(need_ll)):
            cand = c
            break
    if cand is None and need_ll:
        ll_blocked = True
        ll_reason = "既存の features 定義と両立する追記位置が見つからない"
if cand is None:
    if ll_blocked:
        print(f"⚠️  landlock を追記できません（{ll_reason}）: {path}")
        if not need_top:
            sys.exit(0)                      # 追記できるものが何も無い＝無変更
        cand = verify(build("none"), False)  # トップレベル鍵だけ補完する
    if cand is None:
        print(f"⚠️  既定鍵を安全に追記できないため書き込みません（無変更）: {path}")
        sys.exit(0)

# --- 置き換え: 一時ファイルを作って属性を移し、rename で原子的に差し替える ---
# リダイレクトによる truncate は使わない（途中で失敗すると元ファイルを壊すため）。
st = os.stat(path)
d = os.path.dirname(path) or "."
fd, tmp = tempfile.mkstemp(dir=d, prefix=".config.toml.")   # O_EXCL・0600
try:
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(cand)
    # chown を先、chmod を後にする（逆順だと Linux が setuid/setgid ビットを落とす）。
    # 所有者を復元できないなら差し替えない——利用者のファイルの所有者を変えてしまうため。
    os.chown(tmp, st.st_uid, st.st_gid)
    os.chmod(tmp, st.st_mode & 0o7777)
    os.replace(tmp, path)
except Exception as e:
    try:
        os.unlink(tmp)
    except OSError:
        pass
    print(f"⚠️  codex config.toml の書き換えに失敗しました（元ファイルは無変更）: {path} ({e})")
    sys.exit(0)
print("✓ codex config.toml に不足していた既定鍵を追記しました: " + path
      + ("（landlock を除く。上記の理由により）" if ll_blocked else ""))
PYEOF
}

# codex の設定へブラウザ操作用 MCP サーバーを登録する（FR-env-12-14 / D0-dist-06 項4）。
# ensure_codex_config と同じ流儀: **書かれていないときだけ追記し、既存の値は一切変えない**。
# 別関数にしてあるのは呼ぶ条件が違うためである — 既定3鍵はブラウザ確認の有無に関わらず要るが、
# この登録は接続先（コンテナ内 Chrome の :9222）が在るときだけ意味を持つので、
# VNC ありの初期化からだけ呼ぶ。
ensure_codex_mcp_entry() {
    _cfg="$LOCAL_CODEX/config.toml"
    [ -f "$_cfg" ] || return 0        # 既定鍵の生成に失敗した等。起動は止めない

    if ! command -v python3 >/dev/null 2>&1 || ! python3 -c 'import tomllib' >/dev/null 2>&1; then
        echo "⚠️  python3/tomllib が無いため codex への chrome-devtools 登録をスキップします: $_cfg"
        return 0
    fi

    python3 - "$_cfg" <<'PYEOF2'
import os, sys, tempfile, tomllib

path = sys.argv[1]
TABLE = ("mcp_servers", "chrome-devtools")
BLOCK = ['[mcp_servers.chrome-devtools]',
         'command = "chrome-devtools-mcp"',
         'args = ["--browserUrl", "http://localhost:9222"]']
WANT = {TABLE + ("command",): "chrome-devtools-mcp",
        TABLE + ("args",): ["--browserUrl", "http://localhost:9222"]}

def flatten(d, prefix=()):
    out = {}
    for k, v in d.items():
        p = prefix + (k,)
        if isinstance(v, dict):
            out.update(flatten(v, p))
        else:
            out[p] = v
    return out

try:
    raw = open(path, "rb").read()
    orig = tomllib.loads(raw.decode("utf-8"))
except Exception as e:
    print(f"⚠️  codex config.toml を TOML として読めません。chrome-devtools の登録をスキップします: {path} ({e})")
    sys.exit(0)

oflat = flatten(orig)
# 既に何らかの形で登録されているなら触らない（値の是非は利用者のものである）。
srv = orig.get("mcp_servers")
if isinstance(srv, dict) and "chrome-devtools" in srv:
    sys.exit(0)
if not isinstance(srv, (dict, type(None))):
    print(f"⚠️  codex config.toml の mcp_servers が通常テーブルではないため、chrome-devtools の登録をスキップします: {path}")
    sys.exit(0)

text = raw.decode("utf-8")
nl = "\r\n" if "\r\n" in text else "\n"
cand = text
if cand and not cand.endswith(("\n", "\r")):
    cand += nl
cand += nl.join([""] + BLOCK) + nl

# 意味で確かめる: 既存の全キーパスの値が不変で、増分がこの表の2鍵だけであること。
try:
    new = tomllib.loads(cand)
except Exception as e:
    print(f"⚠️  chrome-devtools の登録を追記すると TOML として読めなくなるため、元ファイルを変更しません: {path} ({e})")
    sys.exit(0)
nflat = flatten(new)
for kp, v in oflat.items():
    if kp not in nflat or nflat[kp] != v:
        print(f"⚠️  chrome-devtools の追記が既存の設定を変えるため、元ファイルを変更しません: {path}")
        sys.exit(0)
extra = set(nflat) - set(oflat)
if extra != set(WANT) or any(nflat[kp] != WANT[kp] for kp in extra):
    print(f"⚠️  chrome-devtools の追記の検証に通らないため、元ファイルを変更しません: {path}")
    sys.exit(0)

d = os.path.dirname(path) or "."
tmp = None
try:
    fd, tmp = tempfile.mkstemp(dir=d)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(cand)
    st = os.stat(path)
    os.chmod(tmp, st.st_mode & 0o7777)
    os.chown(tmp, st.st_uid, st.st_gid)
    os.replace(tmp, path)
except Exception as e:
    if tmp:
        try:
            os.unlink(tmp)
        except OSError:
            pass
    print(f"⚠️  codex config.toml の書き換えに失敗しました（元ファイルは無変更）: {path} ({e})")
    sys.exit(0)
print("✓ codex config.toml に chrome-devtools MCP を登録しました: " + path)
PYEOF2
}

ensure_codex_config || true

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
# （claude / codex 双方を同じループ・同じ間隔で見る。D-27）
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
        for f in $CODEX_AUTH_FILES; do
            if [ -f "$LOCAL_CODEX/$f" ]; then
                if ! cmp -s "$LOCAL_CODEX/$f" "$SHARED_CODEX/$f" 2>/dev/null; then
                    mkdir -p "$SHARED_CODEX" 2>/dev/null || true
                    cp "$LOCAL_CODEX/$f" "$SHARED_CODEX/$f" 2>/dev/null || true
                    chmod 600 "$SHARED_CODEX/$f" 2>/dev/null || true
                fi
            fi
        done
    done
) &

# --- ファイアウォール設定 ---
/usr/local/bin/init-firewall.sh 2>/dev/null || true

# --- VM モード起動（--vm / CLAUDE_DEV_VM=1）---
# ゲスト VM（QEMU+virtiofs）を起動し dockerd 準備完了を待つ（docs/impl/80 §5）。
# 成功時のみ DOCKER_HOST をゲストへ向け、VM_DEV.md を生成。失敗時は proxy 既定を維持。
if [ "${CLAUDE_DEV_VM:-}" = "1" ]; then
    echo "🖥️  VM モード: ゲスト VM を起動中（初回は provision に数分かかります）…"
    # vm-up.sh は $USERNAME 権限で走るため、root 所有のマウント点/実行時ディレクトリを
    # 事前に $USERNAME 所有で用意する（docker ボリューム `~/.claude-dev-vm` と /run/vm は
    # 既定で root:root。これを直さないと vm-up.sh の mkdir が Permission denied で失敗する）。
    install -d -o "$USERNAME" -g "$USERNAME" "$USER_HOME/.claude-dev-vm" /run/vm
    if su "$USERNAME" -c '/usr/local/bin/vm-up.sh'; then
        mkdir -p /etc/claude-dev
        echo "export DOCKER_HOST='tcp://127.0.0.1:2375'" > /etc/claude-dev/vm.env
        # 自分の環境にも載せる。載せないと、対話シェルはゲスト VM を、tmux の窓の中の
        # プロセスは docker-proxy を指すという 2 つの値が同居する（CTR-cli-container は
        # 「VM モードでは entrypoint が上書きする」と 1 つの値しか認めていない）。
        export DOCKER_HOST='tcp://127.0.0.1:2375'
        # 外から木を起こす側へも同じ値を届ける。**ゲスト VM の起動に成功したこの分岐でだけ
        # 記録する** — 失敗時は中継先のままが正なので、記録しなければ既定が使われる。
        record_runtime_env DOCKER_HOST 'tcp://127.0.0.1:2375'
        for rc in /etc/zsh/zshrc /etc/bash.bashrc; do
            if [ -f "$rc" ] && ! grep -q '/etc/claude-dev/vm.env' "$rc"; then
                {
                    echo ''
                    echo '# --- claude-dev: VM モード DOCKER_HOST（ゲストの dockerd） ---'
                    echo '[ -f /etc/claude-dev/vm.env ] && . /etc/claude-dev/vm.env'
                } >> "$rc"
            fi
        done
        if [ -f /usr/local/share/claude-dev/VM_DEV.md.tmpl ]; then
            sed -e 's#@DOCKER_HOST@#tcp://127.0.0.1:2375#g' \
                -e "s#@VM_PORTS@#${VM_PORTS:-（Docker API のみ）}#g" \
                /usr/local/share/claude-dev/VM_DEV.md.tmpl > /workspace/VM_DEV.md
            chown "$USERNAME":"$USERNAME" /workspace/VM_DEV.md 2>/dev/null || true
        fi
        echo "✅ VM モード有効。制御情報は /workspace/VM_DEV.md（docker はゲスト VM を指します）"
    else
        echo "⚠️  VM の起動に失敗。VM 無しで継続します（docker は既定の proxy 経路のまま）。'vm logs' で調査可。"
    fi
fi

# --- DooD モードのポート転送（非 VM かつ proxy 経由）---
# ホスト共有daemon に公開されたコンテナポートを claude コンテナの 127.0.0.1 へ socat 転送し、
# テスト等が叩く 127.0.0.1:PORT を到達可能にする（VM モードの vm-portsync 相当。docs/impl/30）。
if [ "${CLAUDE_DEV_VM:-}" != "1" ] \
   && [ "${CLAUDE_DEV_DOOD_PORTSYNC:-1}" != "0" ] \
   && printf '%s' "${DOCKER_HOST:-}" | grep -q 'docker-proxy' \
   && [ -x /usr/local/bin/dood-portsync.sh ]; then
    su "$USERNAME" -c "DOCKER_HOST='${DOCKER_HOST}' setsid /usr/local/bin/dood-portsync.sh --loop >/dev/null 2>&1 &" || true
    echo "🔌 DooD ポート転送を起動（ホスト公開ポートを 127.0.0.1 へ同期）"
fi

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

    # KVM が渡されている場合（--kvm 起動）は仮想化に関する指示を追加。
    # ただし VM モード（--vm / CLAUDE_DEV_VM=1）では CLAUDE.md への追記を抑止し、
    # KVM/VM 情報は /workspace/VM_DEV.md へ集約する（docs/impl/80 §5, docs/08 §3.6）。
    if [ -c /dev/kvm ] && [ "${CLAUDE_DEV_VM:-}" != "1" ]; then
        cat >> /workspace/CLAUDE.md << 'CLAUDE_KVM_EOF'
## KVM / 仮想化（重要）

- このコンテナには `/dev/kvm` が渡されており、**KVM ハードウェア仮想化が利用できる**（`qemu-system-x86_64` 同梱）。仮想マシン（別 OS・別カーネル・フルデスクトップ等）が必要な時に使う。通常の開発・テストは Docker コンテナや Chrome 操作で十分なので、必要な時だけ VM を使うこと。
- VM は KVM 加速で起動する。`-enable-kvm`（または `-accel kvm`）と `-cpu host` を付ける:
  - 例: `qemu-system-x86_64 -enable-kvm -cpu host -m 4096 -smp 2 -drive file=guest.qcow2,if=virtio -nographic`
- **GUI/デスクトップの VM** は QEMU の表示をコンテナの X ディスプレイ `:99` に出すと、ユーザーが noVNC で確認できる:
  - 例: `DISPLAY=:99 qemu-system-x86_64 -enable-kvm -cpu host -m 4096 -drive file=guest.qcow2,if=virtio -display gtk &`
- **ゲストのデスクトップ操作**は、`scrot`（`DISPLAY=:99 scrot /tmp/shot.png`）で画面を取得し、`xdotool`（`DISPLAY=:99 xdotool ...`）または computer-use MCP（`rmcp-xdotool`。`/mcp` で有効化）で QEMU ウィンドウを操作する。QEMU ウィンドウにフォーカスがある状態で入力するとゲストに渡る。
- **ネットワーク**: 手軽なのは user モード（`-netdev user,id=n0 -device virtio-net,netdev=n0`）。`/dev/net/tun` が渡っていれば tap も使える。
- **ディスクイメージ**は `/workspace` 配下に置けばホストと共有される。サイズが大きいので `.gitignore` に追加すること。メモリ/CPU はホスト資源を消費するため過大に確保しない。

CLAUDE_KVM_EOF
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
    # **同梱した実行ファイルを名前で起動する**（FR-env-12-13 / D0-dist-06）。起動のたびに
    # npx で取得する形はやめた — 取得先の可用性とコンテナ内ファイアウォールにブラウザ確認の
    # 成否が依存するため。ランチャーは Dockerfile が /usr/local/bin へ置いている。
    MCP_JSON="/workspace/.mcp.json"
    CHROME_DEVTOOLS_ENTRY='{"command":"chrome-devtools-mcp","args":["--browserUrl","http://localhost:9222"]}'
    # 以前このスクリプトが書いていた値。**これと完全一致するときだけ**同梱物へ向け直す
    # （FR-env-11-9）。利用者が自分で書き換えた設定を確認なく上書きしないため、部分一致では
    # 判定しない。
    CHROME_DEVTOOLS_LEGACY_ENTRY='{"command":"npx","args":["-y","chrome-devtools-mcp@latest","--browserUrl","http://localhost:9222"]}'

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
        # 旧値（実行時取得）がそのまま残っているときだけ、同梱物を指す値へ置き換える。
        elif jq -e --argjson legacy "$CHROME_DEVTOOLS_LEGACY_ENTRY" \
                '.mcpServers["chrome-devtools"] == $legacy' "$MCP_JSON" >/dev/null 2>&1; then
            if jq --argjson entry "$CHROME_DEVTOOLS_ENTRY" '.mcpServers["chrome-devtools"] = $entry' "$MCP_JSON" > "${MCP_JSON}.tmp" 2>/dev/null; then
                mv "${MCP_JSON}.tmp" "$MCP_JSON"
                echo "🔧 .mcp.json の chrome-devtools を同梱物に切り替えました（起動時の取得が不要になります）"
            else
                rm -f "${MCP_JSON}.tmp"
                echo "⚠️  .mcp.json の更新に失敗しました（不正な JSON？）。chrome-devtools の切り替えをスキップします"
            fi
        fi
    fi
    chown "$USERNAME":"$USERNAME" "$MCP_JSON"

    # codex 側にも同じ MCP サーバーを登録する（FR-env-12-14 / D0-dist-06 項4）。
    # 既定3鍵と同じ流儀で、**書かれていないときだけ追記**し、既存の値は変えない。
    ensure_codex_mcp_entry || true

    # computer-use MCP（デスクトップ操作）: rmcp-xdotool バイナリがある場合のみ
    # .mcp.json に定義を用意する。既定では有効化しない（enabledMcpjsonServers に追加しない）。
    # 利用時に Claude Code の /mcp で有効化するか、enabledMcpjsonServers に追加する。
    # 画面取得は scrot を併用する（rmcp-xdotool は入力専用）。
    if command -v rmcp-xdotool >/dev/null 2>&1; then
        COMPUTER_USE_ENTRY='{"command":"rmcp-xdotool","args":[],"env":{"DISPLAY":":99"}}'
        if ! jq -e '.mcpServers["computer-use"]' "$MCP_JSON" >/dev/null 2>&1; then
            if jq --argjson entry "$COMPUTER_USE_ENTRY" '.mcpServers["computer-use"] = $entry' "$MCP_JSON" > "${MCP_JSON}.tmp" 2>/dev/null; then
                mv "${MCP_JSON}.tmp" "$MCP_JSON"
                chown "$USERNAME":"$USERNAME" "$MCP_JSON"
            else
                rm -f "${MCP_JSON}.tmp"
                echo "⚠️  .mcp.json への computer-use 追加に失敗しました（不正な JSON？）。スキップします"
            fi
        fi
    fi

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

# Chrome / Chromium（GUI ブラウザ。amd64=Google Chrome / arm64=Playwright Chromium）
# claude-dev-chrome ランチャーがアーキに応じて適切なバイナリを起動する。
sleep 2
claude-dev-chrome --no-sandbox --disable-gpu --disable-software-rasterizer \
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
# **-l を付けない。** 付けると su がログイン用に環境を作り直し、docker run -e で渡された変数も
# イメージの ENV で付いた変数も、利用者のプロジェクト環境ファイルの組も、まとめて捨てられる。
# tmux サーバの環境はその配下の全ウィンドウ・全プロセスが継承するので、捨てられた変数は
# tmux の中のどこからも見えなくなる（FR-env-07-13 / FR-env-14-11 /
# CTR-cli-container「渡す環境変数」/ AC-08）。
# -l の有無で PATH と HOME は変わらない（2026-08-19 に実機で両方を並べて測定。違うのは PWD だけで、
# このコマンドは自分で cd /workspace するので影響しない）。各ウィンドウの対話シェルは
# 'exec zsh -l' で起こすので、対話シェル向けの初期化（上で両 rc へ書き出した export を含む）は効く。
su "$USERNAME" -s /bin/zsh -c \
    "cd /workspace && tmux -f ~/.tmux.conf new-session -d -s main 'exec zsh -l'" \
    2>/dev/null || true

echo "✅ Ready (user: $USERNAME, uid: $(id -u $USERNAME), gid: $(id -g $USERNAME))"

# --- 待機 ---
exec tail -f /dev/null

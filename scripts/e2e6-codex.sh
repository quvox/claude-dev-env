#!/usr/bin/env bash
# =============================================================================
# E2E-6（UC-6 / 要件 core/12-4, 12-5, 12-6, 12-9, 3-6〜3-9）実施スクリプト
# =============================================================================
# 使い方:
#   scripts/e2e6-codex.sh            # 全ステップ実行
#   scripts/e2e6-codex.sh --keep     # 後始末をせず残す（失敗調査用）
#   scripts/e2e6-codex.sh --cleanup  # 前回の残骸だけ片付けて終了
#
# 前提:
#   - make build 済み（イメージに今回の entrypoint が入っていること。本スクリプトが検査する）
#   - claude-dev login-codex 済み（共有ボリュームに codex/auth.json があること。本スクリプトが検査する）
#     デバイス認証はブラウザ操作を伴うため無人化できない。未実行なら中止して案内する。
#
# 合否判定の原則（重要）:
#   codex の応答を根拠にしない。`codex exec` はプロセスの終了コードが内部コマンド全滅でも 0 になり、
#   モデルが失敗を認識せず成功したかのように答える事象が観測されている（docs/03-impl/e2e.md 既知の制限）。
#   本スクリプトは【成果物】と【ファイルの不在】だけで自動判定する。
#   読み取り成功の判定だけは応答を見るが、これは自己申告ではなく
#   「依頼文に含めていないランダム値が応答に現れた」という観測である。
# =============================================================================
set -uo pipefail

P1="${HOME}/e2e6-p1"
P2="${HOME}/e2e6-p2"
N1="e2e6-p1"
N2="e2e6-p2"
KEEP=0
PASS=0
FAIL=0
SKIP=0

for a in "$@"; do
    case "$a" in
        --keep)    KEEP=1 ;;
        --cleanup) CLEANUP_ONLY=1 ;;
        *) echo "不明な引数: $a" >&2; exit 2 ;;
    esac
done

c_ok()   { printf '  \033[32m✓ PASS\033[0m  %s\n' "$1"; PASS=$((PASS+1)); }
c_ng()   { printf '  \033[31m✗ FAIL\033[0m  %s\n' "$1"; FAIL=$((FAIL+1)); }
c_skip() { printf '  \033[33m- SKIP\033[0m  %s\n' "$1"; SKIP=$((SKIP+1)); }
step()   { printf '\n\033[1m── %s\033[0m\n' "$1"; }
note()   { printf '        %s\n' "$1"; }

# 判定ヘルパ: 条件が真なら PASS
check() { if eval "$2" >/dev/null 2>&1; then c_ok "$1"; else c_ng "$1"; fi; }

# コンテナ内ユーザーはイメージの CONTAINER_USER で決まる（GHCR=dev / ローカルビルド=whoami）。
# 決め打ちすると docker exec が落ち、その失敗が「テスト失敗」や偽陽性に化けるため必ず解決する。
cuser() {
    docker inspect "$1" --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null \
        | sed -n 's/^CONTAINER_USER=//p' | head -1
}
# コンテナ内でユーザー権限のコマンドを実行する。docker exec 自体が失敗したら即座に落とす
# （インフラ由来の失敗をテスト結果と混同しないため）。
dx() {  # dx <container> <command...>
    local c="$1"; shift
    local u; u="$(cuser "$c")"
    [ -n "$u" ] || { echo "コンテナ ${c} の CONTAINER_USER を解決できません" >&2; return 99; }
    docker exec -u "$u" "$c" sh -lc "$*"
}
dxw() { # dxw <container> <workdir> <command...>
    local c="$1" w="$2"; shift 2
    local u; u="$(cuser "$c")"
    [ -n "$u" ] || { echo "コンテナ ${c} の CONTAINER_USER を解決できません" >&2; return 99; }
    docker exec -u "$u" -w "$w" "$c" sh -lc "$*"
}
die() { printf '  \033[31m致命的\033[0m %s\n' "$1" >&2; exit 1; }

cleanup() {
    step "後始末"
    for n in "$N1" "$N2"; do
        docker ps -a --format '{{.Names}}' | grep -qx "$n" && claude-dev stop "$n" >/dev/null 2>&1
    done
    rm -rf "$P1" "$P2"
    # 共有ボリュームの認証は消さない（claude-dev logout は claude 側も消えるため使わない）
    note "使い捨てプロジェクトとコンテナを削除しました（共有ボリュームの認証は保持）"
}

if [ "${CLEANUP_ONLY:-0}" = "1" ]; then cleanup; exit 0; fi

# =============================================================================
step "前提チェック"
# =============================================================================
command -v claude-dev >/dev/null 2>&1 || { echo "claude-dev が PATH にありません（make install）" >&2; exit 1; }

if ! docker image inspect claude-dev-claude:latest >/dev/null 2>&1; then
    echo "イメージ claude-dev-claude:latest がありません（make build）" >&2; exit 1
fi

# イメージに今回の実装（tomllib 方式の不足鍵補完）が入っているか
if docker run --rm --entrypoint sh claude-dev-claude:latest \
     -c 'grep -q "ensure_codex_config" /usr/local/bin/entrypoint.sh && grep -q tomllib /usr/local/bin/entrypoint.sh' 2>/dev/null; then
    c_ok "イメージに config.toml 補完の実装が入っている"
else
    c_ng "イメージが古い（make build をやり直してください）"
    exit 1
fi

# codex 認証の有無（デバイス認証は無人化できないので、無ければ中止）
if docker run --rm --entrypoint sh -v claude-dev-auth:/auth claude-dev-claude:latest \
     -c 'test -s /auth/codex/auth.json' 2>/dev/null; then
    c_ok "共有ボリュームに codex 認証がある"
else
    c_ng "共有ボリュームに codex/auth.json がありません"
    note "先に 'claude-dev login-codex' でデバイス認証を済ませてください（ブラウザ操作が要ります）"
    exit 1
fi

cleanup >/dev/null 2>&1 || true

# =============================================================================
step "準備: 使い捨てプロジェクト p1 を起動"
# =============================================================================
mkdir -p "$P1"; ( cd "$P1" && git init -q )   # codex exec は git リポジトリ外だと起動を拒む
( cd "$P1" && CLAUDE_DEV_NO_ATTACH=1 claude-dev start --no-vnc >/dev/null 2>&1 )
docker ps --format '{{.Names}}' | grep -qx "$N1" || { c_ng "p1 のコンテナが起動しませんでした"; exit 1; }

# 依頼文には絶対に含めないランダムマーカー（応答に現れたら「実際に読めた」証拠になる）
MARK=$(dx "$N1" 'M=MARKER_$(openssl rand -hex 4); printf "%s\n" "$M" > /workspace/e2e6-input.txt; printf "%s" "$M"')
[ -n "$MARK" ] || die "マーカーを作成できませんでした（コンテナ内でコマンドを実行できていません）"
note "MARK=${MARK}（依頼文には入れない）  コンテナユーザー=$(cuser "$N1")"

# =============================================================================
step "① 既定 config.toml が生成される（要件 12-5）"
# =============================================================================
docker exec -i "$N1" python3 - <<'PY' > /tmp/e2e6-cfg.txt 2>&1
import tomllib
d = tomllib.load(open("/workspace/.codex/config.toml", "rb"))
f = d.get("features") or {}
print(d.get("sandbox_mode"), d.get("approval_policy"), f.get("use_legacy_landlock"))
PY
SM=""; AP=""; LL=""
read -r SM AP LL < /tmp/e2e6-cfg.txt || true
[ -n "$SM$AP$LL" ] || die "config.toml を読み出せませんでした: $(cat /tmp/e2e6-cfg.txt)"
note "sandbox_mode=${SM} approval_policy=${AP} use_legacy_landlock=${LL}"
check "3 鍵が期待値で生成されている" '[ "$SM" = "danger-full-access" ] && [ "$AP" = "never" ] && [ "$LL" = "True" ]'

# =============================================================================
step "② codex のシェル実行と /workspace の読み書き（要件 12-4）"
# =============================================================================
note "codex に実際の作業を依頼します（数十秒かかります）"
dxw "$N1" /workspace 'codex exec "/workspace/e2e6-input.txt を読み、その内容を /workspace/e2e6-output.txt へ書き写してください"' \
  > /tmp/e2e6-run2.log 2>&1
check "成果物 e2e6-output.txt にマーカーが書き写されている" \
      "docker exec $N1 grep -qF '$MARK' /workspace/e2e6-output.txt"
if grep -qiE 'bwrap|No permissions to create new namespace' /tmp/e2e6-run2.log; then
    c_ng "codex のシェル実行が bwrap エラーで失敗している（サンドボックスが無効化できていない）"
else
    c_ok "bwrap エラーが出ていない"
fi
note "codex の出力: /tmp/e2e6-run2.log（exec 行の終了コードを目視確認できます）"

# =============================================================================
step "③ landlock 疎通 — config 経由・フラグなし（今回の変更の核心）"
# =============================================================================
RC=$(dx "$N1" 'codex sandbox -- /bin/true >/dev/null 2>&1; echo $?')
check "codex sandbox -- /bin/true が exit 0（landlock が起動する）" '[ "$RC" = "0" ]'
dx "$N1" 'rm -f /tmp/e2e6-deny; codex sandbox -- /bin/sh -c "touch /tmp/e2e6-deny"; echo RAN' > /tmp/e2e6-deny-run.log 2>&1
check "同じ経路での書き込みが拒否される（コマンドは走った上でファイルが作られない）" \
      "grep -q RAN /tmp/e2e6-deny-run.log && ! docker exec $N1 test -e /tmp/e2e6-deny"
RCF=$(dx "$N1" 'codex sandbox --enable use_legacy_landlock -- /bin/true >/dev/null 2>&1; echo $?')
check "--enable use_legacy_landlock 明示でも exit 0（フラグ経路の回帰確認）" '[ "$RCF" = "0" ]'

# =============================================================================
step "④ 読み取り専用の明示指定（要件 12-9）"
# =============================================================================
dxw "$N1" /workspace 'codex exec -s read-only "/workspace/e2e6-input.txt の内容をそのまま答えてください"' \
  > /tmp/e2e6-run4.log 2>&1
check "読み取り成功（依頼文に無いマーカーが応答に現れる）" "grep -qF '$MARK' /tmp/e2e6-run4.log"
dxw "$N1" /workspace 'codex exec -s read-only "/workspace/e2e6-deny.txt に denied と書いてください"' \
  > /tmp/e2e6-run4b.log 2>&1
check "書き込みは拒否される（e2e6-deny.txt が作られない）" \
      "! docker exec $N1 test -e /workspace/e2e6-deny.txt"

# =============================================================================
step "⑤ 認証の書き戻し（要件 3-8）"
# =============================================================================
# 同期は「ローカルと共有側の内容が異なるとき」だけコピーするため、通常起動では発火しない。
# 実トークンのリフレッシュは発生タイミングを制御できないので、無害な差分を作って経路を確認する。
dx "$N1" 'printf "\n" >> ~/.codex/auth.json' || die "認証ファイルに差分を作れませんでした"
note "同期を待ちます（間隔 30 秒。ループの位相があるので最大 90 秒までポーリング）"
SYNCED=0
for _i in $(seq 1 18); do
    if dx "$N1" 'cmp -s ~/.codex/auth.json ~/.claude-shared/codex/auth.json' >/dev/null 2>&1; then
        SYNCED=1; note "${_i}0 秒以内に同期されました"; break
    fi
    sleep 5
done
check "共有ボリュームへ書き戻された（ローカルと共有が一致）" '[ "$SYNCED" = "1" ]'
note "※ 他のコンテナが同時に走っていると、そちらの書き戻しが後勝ちして不一致に見えることがあります"

# =============================================================================
step "⑥ 別プロジェクトへの引継ぎ＝再ログイン不要（要件 3-7 / UC-6 事後条件）"
# =============================================================================
mkdir -p "$P2"; ( cd "$P2" && git init -q )
( cd "$P2" && CLAUDE_DEV_NO_ATTACH=1 claude-dev start --no-vnc >/dev/null 2>&1 )
docker ps --format '{{.Names}}' | grep -qx "$N2" || { c_ng "p2 のコンテナが起動しませんでした"; }
check "p2 のコンテナローカル認証が共有ボリュームと一致する" \
      "dx $N2 'cmp -s ~/.codex/auth.json ~/.claude-shared/codex/auth.json'"

MARK2=$(dx "$N2" 'M=MARKER_$(openssl rand -hex 4); printf "%s\n" "$M" > /workspace/in.txt; printf "%s" "$M"')
[ -n "$MARK2" ] || die "p2 でマーカーを作成できませんでした"
note "p2 で login-codex なしに作業を依頼します（MARK2=${MARK2}）"
dxw "$N2" /workspace 'codex exec "/workspace/in.txt を読み、その内容を /workspace/out.txt へ書き写してください"' \
  > /tmp/e2e6-run6.log 2>&1
check "別プロジェクトで再ログインなしに codex が動く" \
      "docker exec $N2 grep -qF '$MARK2' /workspace/out.txt"

# =============================================================================
step "⑦ 設定・セッション履歴はコンテナ（プロジェクト）ごとに独立（要件 3-9）"
# =============================================================================
dx "$N2" 'printf "model = \"gpt-5-codex\"\n" >> /workspace/.codex/config.toml' || die "p2 の config.toml を編集できませんでした"
docker restart "$N2" >/dev/null 2>&1; sleep 8
check "p2 の利用者設定が再起動後も保たれる（不足鍵補完で壊れない）" \
      "docker exec $N2 grep -q 'gpt-5-codex' /workspace/.codex/config.toml"
check "p1 には伝播していない" \
      "! docker exec $N1 grep -q 'gpt-5-codex' /workspace/.codex/config.toml"
check "共有ボリュームには config.toml が置かれない（auth.json のみ）" \
      "! docker run --rm --entrypoint sh -v claude-dev-auth:/auth claude-dev-claude:latest -c 'test -e /auth/codex/config.toml'"

# =============================================================================
step "結果"
# =============================================================================
printf '  PASS=%d  FAIL=%d  SKIP=%d\n' "$PASS" "$FAIL" "$SKIP"
note "codex の生ログ: /tmp/e2e6-run2.log /tmp/e2e6-run4.log /tmp/e2e6-run4b.log /tmp/e2e6-run6.log"
note "デバイス認証そのもの（UC-6 基本フロー1〜4）は無人化できないため本スクリプトの対象外です"

if [ "$KEEP" = "1" ]; then
    note "--keep 指定のため後始末をスキップしました（scripts/e2e6-codex.sh --cleanup で片付きます）"
else
    cleanup
fi

[ "$FAIL" -eq 0 ]

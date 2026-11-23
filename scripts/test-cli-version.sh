#!/bin/bash
# =============================================================================
# claude-dev / claude-dev-mac の版の名乗り（--version / -v）の自動テスト
# =============================================================================
# 対象: FR-env-01-37（3つ組の版を印字して 0）/ FR-env-01-38（未リリースは「未リリース」で 0）/
#       FR-env-01-39（読めない台帳は理由を出して 1。未リリースと同一視しない）。BR-12。
# 版の値の持ち主はリリース台帳 .claude/state/releases.json なので、台帳を自由に作れる
# 使い捨てのリポジトリ形（CLAUDE.md・.claude/scripts/stamps.py・CLI 本体）を一時ディレクトリに
# 組み、そこで CLI を叩く。本物の台帳には触れない。Docker も要らない。
#
# 使い方: scripts/test-cli-version.sh   （全件成功で 0、1件でも失敗すれば 1）
# =============================================================================
set -u

REPO="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

pass=0
fail=0

ok()   { pass=$((pass + 1)); echo "  ok   $1"; }
ng()   { fail=$((fail + 1)); echo "  NG   $1"; echo "       $2"; }

# 一時リポジトリを作る。$1=CLI 名、$2=台帳の中身（空文字なら台帳を置かない）
make_root() {
    local cli="$1" ledger="$2" root
    root="$(mktemp -d "$WORK/root.XXXXXX")"
    mkdir -p "$root/.claude/scripts" "$root/.claude/state"
    : > "$root/CLAUDE.md"
    cp "$REPO/.claude/scripts/stamps.py" "$root/.claude/scripts/stamps.py"
    cp "$REPO/$cli" "$root/$cli"
    chmod +x "$root/$cli"
    if [ -n "$ledger" ]; then
        printf '%s\n' "$ledger" > "$root/.claude/state/releases.json"
    fi
    echo "$root"
}

# $1=CLI 名 $2=引数 $3=台帳 $4=期待する終了コード $5=期待する標準出力（正規表現。空なら空であること）
check() {
    local cli="$1" arg="$2" ledger="$3" want_rc="$4" want_out="$5" label="$6"
    local root out rc
    root="$(make_root "$cli" "$ledger")"
    out="$(cd / && "$root/$cli" "$arg" 2>/dev/null)"
    rc=$?
    if [ "$rc" -ne "$want_rc" ]; then
        ng "$cli $arg: $label" "終了コード 期待 $want_rc / 実際 $rc（出力: $out）"
        return
    fi
    if [ -z "$want_out" ]; then
        if [ -n "$out" ]; then
            ng "$cli $arg: $label" "標準出力は空のはず（実際: $out）"
            return
        fi
    elif ! printf '%s\n' "$out" | grep -qE "$want_out"; then
        ng "$cli $arg: $label" "標準出力 期待 /$want_out/ / 実際: $out"
        return
    fi
    ok "$cli $arg: $label"
}

for cli in claude-dev claude-dev-mac; do
    for arg in --version -v; do
        check "$cli" "$arg" '{"releases":[{"version":"1.2.3"},{"version":"1.2.2"}]}' 0 '^claude-dev 1\.2\.3$' \
            "台帳の先頭の版を3つ組で名乗る"
        check "$cli" "$arg" "" 0 '^claude-dev 未リリース$' \
            "台帳が無ければ「未リリース」"
        check "$cli" "$arg" '{"releases":[]}' 0 '^claude-dev 未リリース$' \
            "台帳が空なら「未リリース」"
        check "$cli" "$arg" '{' 1 '' \
            "壊れた台帳は失敗（未リリースと読まない）"
        check "$cli" "$arg" '{"releases":[{"version":"1.2"}]}' 1 '' \
            "3つ組でない版は名乗らない"
        check "$cli" "$arg" '{"releases":[{"version":"01.2.3"}]}' 1 '' \
            "先頭が 0 の桁を持つ版は名乗らない"
    done
done

echo "結果: 成功 $pass / 失敗 $fail"
[ "$fail" -eq 0 ]

#!/usr/bin/env bash
# =============================================================================
# dood-portsync — DooD モード（claude コンテナ → socket proxy → ホスト共有daemon）で、
# ホストに公開されたコンテナポートを claude コンテナの 127.0.0.1 へ socat 転送する。
# VM モードの vm-portsync に相当（設計: docs/02_architecture.md「DooD のポートアクセス」,
# 実装仕様: docs/impl/30_scripts.md）。
#
# DooD ではコンテナはホストの daemon で起動し公開ポートはホストの 0.0.0.0:PORT に出る。
# claude コンテナは別 netns のため 127.0.0.1:PORT では届かない。本スクリプトはホスト公開
# ポート（docker ps の 0.0.0.0:PORT）を検出し、127.0.0.1:PORT →（デフォルトGW=ホスト）:PORT
# の socat 転送を張る。既に 127.0.0.1:PORT がローカル待受中（noVNC 等・自分の転送含む）は
# スキップする。リスナーは 127.0.0.1（コンテナ内ループバック）限定でホストへは公開しない。
#
# 使い方:
#   dood-portsync.sh          一度だけ同期する
#   dood-portsync.sh --loop   常駐して定期同期する（entrypoint が DooD 時に起動）
# =============================================================================
set -u

RUN_DIR="/tmp/dood-portsync"
STATE="${RUN_DIR}/forwarded"          # 転送済みポートを記録（1行1ポート）
LOG="${RUN_DIR}/dood-portsync.log"
INTERVAL="${CLAUDE_DEV_DOOD_PORTSYNC_INTERVAL:-5}"
# デフォルトゲートウェイ = docker bridge の GW = ホスト。ホスト公開ポートはここで到達可能。
GATEWAY="$(ip route 2>/dev/null | awk '/^default/{print $3; exit}')"

mkdir -p "${RUN_DIR}" 2>/dev/null
log() { echo "[dood-portsync] $*" | tee -a "${LOG}" >&2; }

command -v socat >/dev/null 2>&1 || { log "FATAL: socat not found"; exit 1; }
[ -n "${GATEWAY}" ] || { log "FATAL: default gateway not found"; exit 1; }

# ホスト（共有daemon）に公開されているポート一覧（0.0.0.0:PORT の PORT）
published_ports() {
    docker ps --format '{{.Ports}}' 2>/dev/null \
        | grep -oE '0\.0\.0\.0:[0-9]+' | grep -oE '[0-9]+$' | sort -un
}

# 127.0.0.1:PORT が既に待受中か（ローカルサーバ／noVNC／既存の自転送）
local_listening() {
    (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null && { exec 3>&- 3<&-; return 0; }
    return 1
}

sync_once() {
    local p
    for p in $(published_ports); do
        grep -qx "${p}" "${STATE}" 2>/dev/null && continue   # 既に処理済み
        if local_listening "${p}"; then
            echo "${p}" >> "${STATE}"                          # 既に何かが待受（noVNC 等）→ スキップ記録
            continue
        fi
        setsid socat "TCP-LISTEN:${p},fork,reuseaddr,bind=127.0.0.1" "TCP:${GATEWAY}:${p}" \
            >/dev/null 2>&1 &
        echo "${p}" >> "${STATE}"
        log "forward 127.0.0.1:${p} -> ${GATEWAY}:${p}"
    done
}

case "${1:-}" in
    --loop)
        log "loop start (interval=${INTERVAL}s, gateway=${GATEWAY})"
        : > "${STATE}"
        while :; do sync_once; sleep "${INTERVAL}"; done
        ;;
    *)
        sync_once
        n="$(published_ports | wc -l)"
        echo "dood-portsync: ${n} 個のホスト公開ポートを 127.0.0.1 へ同期しました（gateway=${GATEWAY}）"
        ;;
esac

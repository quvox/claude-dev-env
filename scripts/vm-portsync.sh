#!/usr/bin/env bash
# =============================================================================
# vm-portsync — ゲスト VM の dockerd が公開しているポートを、claude コンテナの
# 127.0.0.1 へ QEMU の hostfwd（QMP: hostfwd_add）で自動フォワードする。
#
# VM モードでは compose/docker が公開するポートはゲスト VM 側に出るため、claude
# コンテナ内のテスト等が叩く 127.0.0.1:PORT には既定で繋がらない。本スクリプトが
# ゲストの公開ポートを検出して同名ポートで hostfwd を張り、追加設定なしに
# 127.0.0.1:PORT で到達できるようにする。
#
# 使い方:
#   vm-portsync.sh          一度だけ同期する（現在の公開ポートを反映）
#   vm-portsync.sh --loop   常駐して定期同期する（vm-up.sh が起動時に使う）
# =============================================================================
set -u

VM_HOME="${HOME}/.claude-dev-vm"
LOG_DIR="${VM_HOME}/logs"
RUN_DIR="/run/vm"
QMP_SOCK="${RUN_DIR}/qmp.sock"
PIDFILE="${RUN_DIR}/qemu.pid"
STATE="${RUN_DIR}/portsync.forwarded"   # "<qemu_pid>:<port>" を記録（VM 再起動で pid が変わり自然リセット）
DOCKER_TCP="tcp://127.0.0.1:2375"
NETDEV="n0"
INTERVAL="${VM_PORTSYNC_INTERVAL:-5}"

log() { echo "[portsync] $*" | tee -a "${LOG_DIR}/portsync.log" >&2; }

# QMP に human-monitor-command を1つ送る（接続ごとに capabilities ネゴが要る）
qmp() {
    printf '{"execute":"qmp_capabilities"}\n{"execute":"human-monitor-command","arguments":{"command-line":"%s"}}\n' "$1" \
        | socat - "UNIX-CONNECT:${QMP_SOCK}" 2>/dev/null
}

# ゲスト docker が公開しているホストポート一覧（0.0.0.0:PORT / :::PORT の PORT）
published_ports() {
    docker -H "${DOCKER_TCP}" ps --format '{{.Ports}}' 2>/dev/null \
        | grep -oE '(0\.0\.0\.0|\[::\]):[0-9]+' | grep -oE '[0-9]+$' | sort -un
}

sync_once() {
    [ -S "${QMP_SOCK}" ] || return 0
    local pid ports p
    pid="$(cat "${PIDFILE}" 2>/dev/null)"; [ -n "${pid}" ] || return 0
    ports="$(published_ports)"; [ -n "${ports}" ] || return 0
    for p in ${ports}; do
        grep -qx "${pid}:${p}" "${STATE}" 2>/dev/null && continue   # この VM 起動で追加済み
        qmp "hostfwd_add ${NETDEV} tcp:127.0.0.1:${p}-:${p}" >/dev/null 2>&1
        echo "${pid}:${p}" >> "${STATE}"
        log "forward 127.0.0.1:${p} -> guest:${p}"
    done
}

case "${1:-}" in
    --loop)
        log "portsync loop start (interval=${INTERVAL}s)"
        while :; do sync_once; sleep "${INTERVAL}"; done
        ;;
    *)
        sync_once
        n="$(published_ports | wc -l)"
        echo "portsync: ${n} 個の公開ポートを 127.0.0.1 へ同期しました"
        ;;
esac

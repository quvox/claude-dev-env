#!/usr/bin/env bash
# =============================================================================
# vm-healthd — ゲスト VM の資源逼迫（メモリ不足によるページ回収スラッシング）を
# claude コンテナ側から検知し、警告する常駐デーモン（設計: docs/08_vm-mode.md §3.7,
# 実装仕様: docs/impl/80_vm-mode.md §7.2）。
#
# 検知はコンテナ側の QEMU プロセス CPU 使用率のみに基づく（ゲストには一切問い合わせ
# ない: スラッシング時は ssh/docker がゲストで応答しないため）。QEMU が -smp 由来の
# 上限に対して高い比率を「長め継続窓」で保つとき、資源逼迫の疑いと判定する。
#
# 警告の出し先:
#   (1) tmux: WARN 中は `@vm_health` を set（status-right が表示）、OK 復帰で unset。
#       OK→WARN 遷移時に display-message でフラッシュ（cooldown で再フラッシュ抑制）。
#   (2) health ファイル(${VM_HOME}/health): vm status / orchestrator dashboard が読む。
#
# 使い方:
#   vm-healthd.sh          一度だけ評価して health を書く
#   vm-healthd.sh --loop   常駐して定期評価する（vm-up.sh が起動時に使う）
# =============================================================================
set -u

VM_HOME="${HOME}/.claude-dev-vm"
LOG_DIR="${VM_HOME}/logs"
RUN_DIR="/run/vm"
PIDFILE="${RUN_DIR}/qemu.pid"
HEALTH_FILE="${VM_HOME}/health"

INTERVAL="${VM_HEALTH_INTERVAL:-15}"     # サンプリング窓（秒）＝ループ周期
CPU_PCT="${VM_HEALTH_CPU_PCT:-60}"       # 上限比 何 % 以上を hot とみなすか
SUSTAIN="${VM_HEALTH_SUSTAIN:-12}"       # hot が連続 何回で WARN か（12×15s≒3分）
COOLDOWN="${VM_HEALTH_COOLDOWN:-600}"    # フラッシュ通知の再送抑制（秒）
CLK="$(getconf CLK_TCK 2>/dev/null || echo 100)"

mkdir -p "${VM_HOME}" "${LOG_DIR}"
log() { echo "[healthd] $*" | tee -a "${LOG_DIR}/vm-healthd.log" >&2; }

# QEMU の /proc/<pid>/cmdline から `-smp N` の N を得る（無ければ VM_SMP か 2）。
smp_of() {
    local pid="$1" toks n=""
    if [ -r "/proc/${pid}/cmdline" ]; then
        # cmdline は NUL 区切り。-smp の次トークンを取る（"2" や "cpus=2,..." に対応）。
        mapfile -d '' toks < "/proc/${pid}/cmdline" 2>/dev/null || toks=()
        local i
        for ((i=0; i<${#toks[@]}; i++)); do
            if [ "${toks[$i]}" = "-smp" ]; then
                n="${toks[$((i+1))]:-}"; n="${n%%,*}"; n="${n#cpus=}"; break
            fi
        done
    fi
    [[ "${n}" =~ ^[0-9]+$ ]] || n="${VM_SMP:-2}"
    [[ "${n}" =~ ^[0-9]+$ ]] && [ "${n}" -gt 0 ] || n=2
    echo "${n}"
}

# QEMU の累積 CPU tick（utime+stime, /proc/<pid>/stat の 14+15 フィールド）。
cpu_ticks() {
    local pid="$1"
    awk '{print $14+$15}' "/proc/${pid}/stat" 2>/dev/null
}

# tmux 操作（サーバ未起動なら黙ってスキップ）。
tmux_set()   { command -v tmux >/dev/null 2>&1 && tmux has-session 2>/dev/null && tmux set -g  @vm_health "$1" 2>/dev/null || true; }
tmux_clear() { command -v tmux >/dev/null 2>&1 && tmux has-session 2>/dev/null && tmux set -gu @vm_health          2>/dev/null || true; }
tmux_flash() { command -v tmux >/dev/null 2>&1 && tmux has-session 2>/dev/null && tmux display-message "$1"        2>/dev/null || true; }

write_health() {
    # $1=STATE $2=CPU $3=CEIL $4=MSG
    {
        printf 'STATE=%s\n' "$1"
        printf 'CPU=%s\n'   "$2"
        printf 'CEIL=%s\n'  "$3"
        printf 'TS=%s\n'    "$(date +%s)"
        printf 'MSG=%s\n'   "$4"
    } > "${HEALTH_FILE}.tmp" && mv "${HEALTH_FILE}.tmp" "${HEALTH_FILE}"
}

HOT=0
PREV_STATE="OK"
LAST_FLASH=0

evaluate_once() {
    local pid ticks1 ticks2 smp ceil cpu ratio state msg now
    pid="$(cat "${PIDFILE}" 2>/dev/null)"
    if [ -z "${pid}" ] || [ ! -d "/proc/${pid}" ]; then
        HOT=0
        [ "${PREV_STATE}" = "WARN" ] && tmux_clear
        PREV_STATE="OFF"
        write_health "OFF" "0" "0" "VM 未起動（QEMU プロセスなし）"
        return 0
    fi
    smp="$(smp_of "${pid}")"; ceil=$((smp * 100))
    ticks1="$(cpu_ticks "${pid}")"; [ -n "${ticks1}" ] || { sleep "${INTERVAL}"; return 0; }
    sleep "${INTERVAL}"
    ticks2="$(cpu_ticks "${pid}")"; [ -n "${ticks2}" ] || return 0
    # 1コア基準の CPU%（= 100 * Δticks / (窓秒 * CLK)）。
    cpu=$(( (ticks2 - ticks1) * 100 / (INTERVAL * CLK) ))
    [ "${cpu}" -lt 0 ] && cpu=0
    ratio=$(( ceil > 0 ? cpu * 100 / ceil : 0 ))

    if [ "${ratio}" -ge "${CPU_PCT}" ]; then HOT=$((HOT + 1)); else HOT=0; fi

    if [ "${HOT}" -ge "${SUSTAIN}" ]; then
        state="WARN"
        msg="VM資源逼迫の可能性（QEMU CPU ${cpu}% / 上限 ${ceil}% を継続）。メモリ不足の疑い。vm status / VM_DEV.md を確認"
    else
        state="OK"
        msg="ok (cpu ${cpu}% / ceil ${ceil}%, hot ${HOT}/${SUSTAIN})"
    fi
    write_health "${state}" "${cpu}" "${ceil}" "${msg}"

    if [ "${state}" = "WARN" ]; then
        tmux_set "⚠ VM資源逼迫 CPU${cpu}%/${ceil}%"
        now="$(date +%s)"
        if [ "${PREV_STATE}" != "WARN" ] || [ $((now - LAST_FLASH)) -ge "${COOLDOWN}" ]; then
            tmux_flash "⚠ VM 資源逼迫の可能性: QEMU CPU ${cpu}% (上限 ${ceil}%)。メモリ不足の疑い。vm status を確認"
            log "WARN: cpu=${cpu}% ceil=${ceil}% (sustained ${HOT}×${INTERVAL}s)"
            LAST_FLASH="${now}"
        fi
    elif [ "${PREV_STATE}" = "WARN" ]; then
        tmux_clear
        log "recovered: cpu=${cpu}% ceil=${ceil}%"
    fi
    PREV_STATE="${state}"
}

case "${1:-}" in
    --loop)
        log "healthd loop start (interval=${INTERVAL}s cpu_pct=${CPU_PCT}% sustain=${SUSTAIN})"
        while :; do evaluate_once; done
        ;;
    *)
        evaluate_once
        cat "${HEALTH_FILE}" 2>/dev/null
        ;;
esac

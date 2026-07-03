#!/usr/bin/env bash
# =============================================================================
# vm-up.sh — VM モードのゲスト VM を起動する（設計: docs/08_vm-mode.md,
# 実装仕様: docs/impl/80_vm-mode.md）。
#
# 責務: (1) 初回は Ubuntu cloud image から provision（cloud-init seed）、
#       (2) virtiofsd を起動して /workspace を共有、
#       (3) QEMU を KVM 加速・共有メモリ・virtiofs・user-mode hostfwd で常駐起動、
#       (4) ゲスト dockerd の準備完了を同期ポーリングし、完了で 0 / 失敗で非0 終了。
# 冪等: 既に dockerd が到達可能なら何もせず 0 を返す。
# =============================================================================
set -euo pipefail

VM_HOME="${HOME}/.claude-dev-vm"
LOG_DIR="${VM_HOME}/logs"
RUN_DIR="/run/vm"
CLOUD_IMG="${VM_HOME}/ubuntu-cloud.img"
GUEST_OVERLAY="${VM_HOME}/guest-overlay.qcow2"
SEED_ISO="${VM_HOME}/seed.iso"
SSH_KEY="${VM_HOME}/id_vm"
VFS_SOCK="${RUN_DIR}/vfs.sock"
QMP_SOCK="${RUN_DIR}/qmp.sock"
PIDFILE="${RUN_DIR}/qemu.pid"

# 上書き可能な既定値（docs/impl/80 §4）。VM_MEM は必ず単位付き。
VM_MEM="${VM_MEM:-8192M}"
VM_SMP="${VM_SMP:-2}"
VM_DISK="${VM_DISK:-20G}"
VM_SWAP="${VM_SWAP:-2G}"            # ゲストのスワップファイルサイズ（0/空で無効）
VM_PORTS="${VM_PORTS:-}"            # 例: "8000,8080"
CLOUD_IMG_URL="${CLOUD_IMG_URL:-https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img}"
DOCKER_TCP="tcp://127.0.0.1:2375"
WAIT_SECS="${VM_WAIT_SECS:-180}"
# virtiofsd は PATH に無く /usr/libexec/virtiofsd に入る（Ubuntu）。絶対パスで解決。
VIRTIOFSD="$(command -v virtiofsd 2>/dev/null || echo /usr/libexec/virtiofsd)"

mkdir -p "${VM_HOME}" "${LOG_DIR}" "${RUN_DIR}"
log() { echo "[vm-up] $*" | tee -a "${LOG_DIR}/vm-up.log" >&2; }

dockerd_ready() { docker -H "${DOCKER_TCP}" info >/dev/null 2>&1; }

# ゲスト公開ポートを 127.0.0.1 へ自動 hostfwd する常駐同期を起動（多重起動は避ける）
start_portsync() {
    [ -x /usr/local/bin/vm-portsync.sh ] || return 0
    pgrep -f 'vm-portsync.sh --loop' >/dev/null 2>&1 && return 0
    setsid /usr/local/bin/vm-portsync.sh --loop >/dev/null 2>&1 &
    log "started port auto-forward (vm-portsync --loop)"
}

# ゲスト資源逼迫を QEMU CPU から検知して警告する常駐監視を起動（多重起動は避ける）
start_healthd() {
    [ -x /usr/local/bin/vm-healthd.sh ] || return 0
    pgrep -f 'vm-healthd.sh --loop' >/dev/null 2>&1 && return 0
    setsid /usr/local/bin/vm-healthd.sh --loop >/dev/null 2>&1 &
    log "started resource monitor (vm-healthd --loop)"
}

# VM_FRESH=1: 白紙 provision やり直し。走行中 VM を停止し overlay/seed を削除
# （cloud image DL キャッシュは残す）→ 以降の初回判定で再 provision される。
if [ "${VM_FRESH:-}" = "1" ]; then
    log "VM_FRESH=1: tearing down VM and removing guest disk for re-provision"
    [ -f "${PIDFILE}" ] && kill "$(cat "${PIDFILE}" 2>/dev/null)" 2>/dev/null || true
    pkill -f "virtiofsd.*${VFS_SOCK}" 2>/dev/null || true
    sleep 1
    rm -f "${GUEST_OVERLAY}" "${SEED_ISO}"
elif dockerd_ready; then
    # 既に起動済み（dockerd 到達可能）なら冪等に終了
    log "guest dockerd already reachable"; start_portsync; start_healthd; exit 0
fi

# --- 前提チェック ---
[ -c /dev/kvm ] || { log "FATAL: /dev/kvm not present"; exit 1; }
command -v qemu-system-x86_64 >/dev/null || { log "FATAL: qemu-system-x86_64 not found"; exit 1; }
[ -x "${VIRTIOFSD}" ] || { log "FATAL: virtiofsd not found (${VIRTIOFSD})"; exit 1; }

# --- 初回 provision（overlay が無ければ） ---
FIRST_BOOT=0
if [ ! -f "${GUEST_OVERLAY}" ]; then
    FIRST_BOOT=1
    log "provisioning (first boot)"
    if [ ! -f "${CLOUD_IMG}" ]; then
        log "downloading cloud image: ${CLOUD_IMG_URL}"
        curl -fsSL "${CLOUD_IMG_URL}" -o "${CLOUD_IMG}.part"
        mv "${CLOUD_IMG}.part" "${CLOUD_IMG}"
    fi
    qemu-img create -f qcow2 -F qcow2 -b "${CLOUD_IMG}" "${GUEST_OVERLAY}" "${VM_DISK}" >/dev/null
    [ -f "${SSH_KEY}" ] || ssh-keygen -t ed25519 -N '' -f "${SSH_KEY}" -q
    PUBKEY="$(cat "${SSH_KEY}.pub")"

    # スワップ確保用 runcmd（VM_SWAP=0/空なら作らない）。生成時にサイズを MB へ確定し、
    # fallocate 失敗時の dd フォールバック count も正しい値を焼き込む（docs/impl/80 §3）。
    SWAP_RUNCMD=""
    if [ -n "${VM_SWAP}" ] && [ "${VM_SWAP}" != "0" ]; then
        SWAP_MB="$(numfmt --from=iec "${VM_SWAP}" 2>/dev/null | awk '{print int($1/1048576)}')"
        [ -n "${SWAP_MB}" ] && [ "${SWAP_MB}" -gt 0 ] 2>/dev/null || SWAP_MB=2048
        SWAP_RUNCMD="  - test -e /swapfile || fallocate -l ${SWAP_MB}M /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=${SWAP_MB}
  - chmod 600 /swapfile
  - mkswap /swapfile
  - swapon /swapfile
  - grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab"
    fi

    # cloud-init: docker.io 導入 / dockerd を unix+tcp(127.0.0.1:2375) 待受 /
    # virtiofs を /workspace に自動マウント / スワップ確保 / vm shell 用 SSH 公開鍵注入。
    USER_DATA="${VM_HOME}/user-data"
    cat > "${USER_DATA}" <<EOF
#cloud-config
hostname: claude-dev-vm
users:
  - name: dev
    sudo: "ALL=(ALL) NOPASSWD:ALL"
    shell: /bin/bash
    groups: [docker]
    ssh_authorized_keys:
      - ${PUBKEY}
package_update: true
packages:
  - docker.io
runcmd:
  - mkdir -p /workspace
  - grep -q '^workspace ' /etc/fstab || echo 'workspace /workspace virtiofs defaults,nofail 0 0' >> /etc/fstab
  - mount -a || true
${SWAP_RUNCMD}
  - mkdir -p /etc/systemd/system/docker.service.d
  - |
    DKR=\$(command -v dockerd || echo /usr/bin/dockerd)
    # -H fd:// で docker.socket 経由の unix ソケットを維持しつつ、tcp を追加。
    # tcp は 0.0.0.0（ゲスト内）で待受: QEMU user-mode hostfwd はゲストの SLIRP IP
    # (10.0.2.15) 宛に転送するため 127.0.0.1 では届かない。露出は claude コンテナの
    # 127.0.0.1 に張った hostfwd 経由のみ（ネットワーク非公開）。
    printf '[Service]\nExecStart=\nExecStart=%s -H fd:// -H tcp://0.0.0.0:2375\n' "\$DKR" > /etc/systemd/system/docker.service.d/override.conf
  - systemctl daemon-reload
  - systemctl enable docker
  - systemctl restart docker
EOF
    printf 'instance-id: claude-dev-vm\nlocal-hostname: claude-dev-vm\n' > "${VM_HOME}/meta-data"
    cloud-localds "${SEED_ISO}" "${USER_DATA}" "${VM_HOME}/meta-data"
fi

# --- virtiofsd 起動（既存が生きていなければ） ---
if ! pgrep -f "virtiofsd.*${VFS_SOCK}" >/dev/null 2>&1; then
    rm -f "${VFS_SOCK}"
    log "starting virtiofsd (${VIRTIOFSD}, shared-dir=/workspace)"
    "${VIRTIOFSD}" --socket-path="${VFS_SOCK}" --shared-dir=/workspace --sandbox=none \
        >>"${LOG_DIR}/virtiofsd.log" 2>&1 &
    for _ in $(seq 1 50); do [ -S "${VFS_SOCK}" ] && break; sleep 0.1; done
fi

# --- hostfwd 組み立て（Docker API 2375 / SSH 2222 / アプリポート） ---
HOSTFWD="hostfwd=tcp:127.0.0.1:2375-:2375,hostfwd=tcp:127.0.0.1:2222-:22"
if [ -n "${VM_PORTS}" ]; then
    IFS=',' read -ra _ports <<< "${VM_PORTS}"
    for p in "${_ports[@]}"; do
        p="$(echo "$p" | tr -d ' ')"; [ -n "$p" ] && HOSTFWD="${HOSTFWD},hostfwd=tcp:127.0.0.1:${p}-:${p}"
    done
fi

SEED_OPT=()
[ "${FIRST_BOOT}" = "1" ] && SEED_OPT=(-drive "file=${SEED_ISO},if=virtio,media=cdrom")

# --- QEMU 起動（常駐: -daemonize、シリアル/QMP をログ・socket へ） ---
log "starting QEMU (mem=${VM_MEM} smp=${VM_SMP})"
rm -f "${QMP_SOCK}"
qemu-system-x86_64 \
    -enable-kvm -cpu host -m "${VM_MEM}" -smp "${VM_SMP}" \
    -drive "file=${GUEST_OVERLAY},if=virtio" \
    -object "memory-backend-memfd,id=mem,size=${VM_MEM},share=on" -numa node,memdev=mem \
    -chardev "socket,id=vfs,path=${VFS_SOCK}" \
    -device vhost-user-fs-pci,chardev=vfs,tag=workspace \
    -netdev "user,id=n0,${HOSTFWD}" -device virtio-net-pci,netdev=n0 \
    "${SEED_OPT[@]}" \
    -display none -serial "file:${LOG_DIR}/qemu-serial.log" \
    -qmp "unix:${QMP_SOCK},server,nowait" \
    -pidfile "${PIDFILE}" -daemonize \
    >>"${LOG_DIR}/vm-up.log" 2>&1

# --- ゲスト dockerd 準備待ち（同期ポーリング） ---
log "waiting for guest dockerd (up to ${WAIT_SECS}s)…"
for _ in $(seq 1 "${WAIT_SECS}"); do
    if dockerd_ready; then log "guest dockerd is ready"; start_portsync; start_healthd; exit 0; fi
    sleep 1
done
log "FATAL: guest dockerd did not become ready in ${WAIT_SECS}s (see ${LOG_DIR})"
exit 1

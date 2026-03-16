#!/bin/sh
# =============================================================================
# Samba エントリポイント
# =============================================================================
set -e

SAMBA_USER="${SAMBA_USER:-claude}"
SAMBA_PASSWORD="${SAMBA_PASSWORD:-claude}"

# --- ファイルオーナー用ユーザー作成（Claude コンテナの devuser と UID/GID を合わせる）---
addgroup -g 1500 devuser 2>/dev/null || true
adduser -D -u 1500 -G devuser -s /sbin/nologin devuser 2>/dev/null || true

# --- Samba 認証ユーザー作成 ---
addgroup samba 2>/dev/null || true

# SAMBA_USER が devuser と異なる場合はシステムユーザーとして作成
if [ "${SAMBA_USER}" != "devuser" ]; then
    adduser -D -s /sbin/nologin "${SAMBA_USER}" 2>/dev/null || true
fi
adduser "${SAMBA_USER}" samba 2>/dev/null || true

# Samba パスワード設定
echo -e "${SAMBA_PASSWORD}\n${SAMBA_PASSWORD}" | smbpasswd -a -s "${SAMBA_USER}"

# --- ログディレクトリ ---
mkdir -p /var/log/samba

echo "✅ Samba ready (user: ${SAMBA_USER})"

# --- Samba 起動 ---
exec smbd --foreground --no-process-group

#!/bin/bash
# =============================================================================
# ブラックリスト方式ファイアウォール - Claude コンテナ用
# =============================================================================
# デフォルト: 全許可（ACCEPT）
# 既知の危険な宛先・パターンのみブロック
#
# カスタマイズ:
#   - BLACKLIST_DOMAINS: ブロックしたいドメインを追加
#   - BLACKLIST_PORTS:   ブロックしたいポートを追加
#   - 本番環境のドメインを追加することを強く推奨
# =============================================================================
set -e

echo "🔥 Configuring Claude container firewall (blacklist mode)..."

# --- 既存ルールをクリア ---
iptables -F OUTPUT 2>/dev/null || true
iptables -X 2>/dev/null || true
ipset destroy blacklisted-domains 2>/dev/null || true

# --- デフォルトポリシー: 全許可 ---
iptables -P INPUT ACCEPT
iptables -P FORWARD ACCEPT
iptables -P OUTPUT ACCEPT

# --- 基本ルール ---
iptables -A OUTPUT -o lo -j ACCEPT
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# --- ipset 作成 ---
ipset create blacklisted-domains hash:ip hashsize 1024

# =============================================================================
# ブラックリスト: ドメイン
# =============================================================================
# ここにブロックしたいドメインを追加してください
BLACKLIST_DOMAINS=(
    # --- 本番環境（誤アクセス防止）---
    # "production-api.yourcompany.com"
    # "prod-db.yourcompany.com"

    # --- 既知のペーストサイト・ファイル共有（データ窃取防止）---
    "pastebin.com"
    "paste.ee"
    "hastebin.com"
    "transfer.sh"
    "file.io"
    "0x0.st"
    "ix.io"
    "sprunge.us"
    "dpaste.org"

    # --- 既知の Webhook テストサイト ---
    "webhook.site"
    "requestbin.com"
    "hookbin.com"

    # --- ngrok 等のトンネリングサービス ---
    "ngrok.io"
    "ngrok-free.app"
    "localtunnel.me"
    "serveo.net"
)

for domain in "${BLACKLIST_DOMAINS[@]}"; do
    # コメント行はスキップ
    [[ "$domain" =~ ^#.*$ ]] && continue
    [[ -z "$domain" ]] && continue

    ips=$(dig +short A "$domain" 2>/dev/null || true)
    for ip in $ips; do
        # 有効なIPアドレスのみ追加
        if [[ "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            ipset add blacklisted-domains "$ip" 2>/dev/null || true
        fi
    done
done

# --- ipset によるドメインブロック ---
iptables -A OUTPUT -m set --match-set blacklisted-domains dst -j REJECT --reject-with icmp-port-unreachable

# =============================================================================
# ブラックリスト: 特定IP・ネットワーク
# =============================================================================
# クラウドメタデータエンドポイント（認証情報窃取防止）
iptables -A OUTPUT -d 169.254.169.254 -j REJECT
# Azure メタデータ
iptables -A OUTPUT -d 169.254.169.253 -j REJECT
# GCP メタデータ（上と同じ範囲だが明示的に）
iptables -A OUTPUT -d metadata.google.internal -j REJECT 2>/dev/null || true

# =============================================================================
# ブラックリスト: ポート
# =============================================================================
# SMTP（メール送信によるデータ窃取防止）
iptables -A OUTPUT -p tcp --dport 25 -j REJECT
iptables -A OUTPUT -p tcp --dport 465 -j REJECT
iptables -A OUTPUT -p tcp --dport 587 -j REJECT

# 外部向け SSH（リバースシェル防止）
# ※ internal ネットワーク内の SSH は許可
iptables -A OUTPUT -p tcp --dport 22 -d 10.0.0.0/8 -j ACCEPT
iptables -A OUTPUT -p tcp --dport 22 -d 172.16.0.0/12 -j ACCEPT
iptables -A OUTPUT -p tcp --dport 22 -d 192.168.0.0/16 -j ACCEPT
# それ以外の外部 SSH はブロック
# ※ GitHub SSH (git@github.com) もブロックされます。HTTPS を使ってください
iptables -A OUTPUT -p tcp --dport 22 -j REJECT

# =============================================================================
# 検証
# =============================================================================
echo ""
echo "=== Firewall rules (blacklist mode) ==="
echo "Default policy: ACCEPT (all traffic allowed unless blacklisted)"
echo ""
echo "Blocked domains: ${#BLACKLIST_DOMAINS[@]}"
echo "Blocked IPs in ipset: $(ipset list blacklisted-domains 2>/dev/null | grep -c '^[0-9]' || echo 0)"
echo ""

# ブロック確認テスト
if command -v curl &>/dev/null; then
    # pastebin がブロックされていることを確認
    if curl -s --connect-timeout 3 https://pastebin.com > /dev/null 2>&1; then
        echo "⚠️  WARNING: pastebin.com is reachable (blacklist may not be working)"
    else
        echo "✅ pastebin.com is blocked"
    fi

    # Anthropic API が到達可能であることを確認
    if curl -s --connect-timeout 3 https://api.anthropic.com > /dev/null 2>&1; then
        echo "✅ api.anthropic.com is reachable"
    else
        echo "⚠️  WARNING: api.anthropic.com is not reachable"
    fi
fi

echo ""
echo "🔥 Claude firewall ready."

# 実装仕様: scripts/init-firewall-claude.sh

> **この文書の役割**: Claude コンテナ内で適用されるブラックリスト方式ファイアウォールの実装仕様。脅威モデル上の位置づけは `docs/03_security.md`、カスタマイズ手順は `docs/05_customization.md` を参照。

## 要件（なぜ必要か）

コンテナ隔離下でも、認証情報やコードの外部流出経路（ペーストサイト・Webhook テスト・クラウドメタデータ・SMTP・外部リバースシェル）は塞ぎたい。一方で開発に必要な通信（Anthropic API、GitHub、内部ネットワーク）は広く許可したい。そこで「**デフォルト全許可・既知の危険宛先のみ拒否**」のブラックリスト方式を採る。

## カバーするコード

```
scripts/init-firewall-claude.sh   （ビルド時に /usr/local/bin/init-firewall.sh へ配置、entrypoint が実行）
```

実行には `NET_ADMIN`/`NET_RAW` ケイパビリティ（`claude-dev start` が付与）と `iptables`/`ipset`/`dig`/`curl`/`jq`（イメージに同梱）が必要。

## 適用ルール（成果物としての iptables 構成）

1. **初期化**: `OUTPUT` チェインを `-F`、ユーザーチェインを `-X`、`ipset` `blacklisted-domains` を破棄。
2. **デフォルトポリシー**: `INPUT`/`FORWARD`/`OUTPUT` すべて `ACCEPT`。
3. **基本許可**: ループバック (`-o lo`)、`ESTABLISHED,RELATED`。
4. **ドメインブラックリスト**: `ipset create blacklisted-domains hash:ip`。`BLACKLIST_DOMAINS` 配列の各ドメインを `dig +short A` で解決し、得た IPv4 を ipset に追加。`OUTPUT` でこの ipset 宛を `REJECT`（icmp-port-unreachable）。
   - 既定の対象: ペーストサイト（pastebin.com, paste.ee, hastebin.com, transfer.sh, file.io, 0x0.st, ix.io, sprunge.us, dpaste.org）、Webhook テスト（webhook.site, requestbin.com, hookbin.com）、トンネリング（ngrok.io, ngrok-free.app, localtunnel.me, serveo.net）。本番ドメインはコメントで追記を推奨。
5. **メタデータエンドポイント拒否**: `169.254.169.254`、`169.254.169.253`、`metadata.google.internal` を `REJECT`。
6. **SMTP 拒否**: TCP `25` / `465` / `587` を `REJECT`。
7. **外部 SSH 制御**:
   - 内部ネットワーク（`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`）宛の TCP 22 は `ACCEPT`。
   - GitHub SSH を許可: `https://api.github.com/meta` の `.git[]` CIDR を `curl`+`jq` で取得して各 CIDR の TCP 22 を `ACCEPT`。取得失敗時は `dig +short A github.com` の IP にフォールバック。
   - それ以外の TCP 22 は `REJECT`（外向きリバースシェル抑止）。
8. **検証出力**: ルール要約を表示し、`curl` で pastebin.com がブロックされ api.anthropic.com が到達可能であることを確認するスモークテストを実行（結果を表示するのみ）。

## カスタマイズ点

- `BLACKLIST_DOMAINS` 配列にドメインを追記すればブロック対象を増やせる。本番 API/DB ドメインの追加が推奨される。
- 追加でブロックしたいポートは SMTP 節と同様に `iptables -A OUTPUT -p tcp --dport <port> -j REJECT` を追記する。

## 注意点

- ブラックリスト方式のため、列挙されていない宛先はすべて到達可能。機密性の高い環境では本番ドメインの明示追加が前提となる。
- ドメイン→IP は起動時点のスナップショット解決であり、DNS 変化には追従しない（コンテナ再起動で再解決）。

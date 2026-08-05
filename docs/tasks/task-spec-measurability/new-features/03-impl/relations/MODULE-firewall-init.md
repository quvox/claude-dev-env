---
target: docs/03-impl/relations/MODULE-firewall-init.md
change: replace
sections:
  - "## 呼び出され方"
reason: >
  「ブロック対象ドメイン」の集合が仕様のどこにも無い(docs/issues/041)。決定シート概念#2 /
  論点2 の案D により、集合は「設定で与えられるもの」と 01 で定義し、既定の内訳はカテゴリとともに
  この 03 の機能仕様へ列挙する。実装は変えない(現物の写しである)。
id: MODULE-firewall-init
module: MOD-firewall
kind: tool
sync: sync
impl: scripts/init-firewall-claude.sh::main
callers: MODULE-entrypoint-claude
callees: なし
contracts: CTR-entrypoint-firewall
design: DSN-mod-01, DSN-arch-01
requirements: FR-env-05, NFR-sec-01
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-05
summary: iptables/ipset でブラックリスト型のファイアウォールを構成する
---

## 呼び出され方

- 契機: `MODULE-entrypoint-claude` が起動シーケンス中に1度だけ
  `/usr/local/bin/init-firewall.sh` を引数なしで実行する。
- 前提条件: `NET_ADMIN` / `NET_RAW`(`MODULE-cli-start` が `docker run` で付与)と、
  `iptables` / `ipset` / `dig` / `curl` / `jq`(イメージ同梱)。
- 引数: なし。

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| (なし) | - | - | 設定は環境変数ではなくスクリプト内配列 `BLACKLIST_DOMAINS` を編集する |

- 認可: コンテナ内 root(`NET_ADMIN` 必須)。

### 同梱する既定のブロック対象ドメイン(16件)

用語集「ブロック対象ドメイン」が指す集合の**既定値**である。`scripts/init-firewall-claude.sh` の
`BLACKLIST_DOMAINS` 配列に、**利用者が編集する前提のテンプレート**として同梱している
(配列の直前に「ここにブロックしたいドメインを追加してください」というコメントがある)。
**要件はこの集合の中身を固定しない**(`FR-env-05`。塞ぐのは「設定に列挙されたドメイン」である)。

| カテゴリ | 件数 | ドメイン |
|---|---|---|
| ペーストサイト・ファイル共有(データ窃取防止) | 9 | `pastebin.com` / `paste.ee` / `hastebin.com` / `transfer.sh` / `file.io` / `0x0.st` / `ix.io` / `sprunge.us` / `dpaste.org` |
| Webhook テストサイト | 3 | `webhook.site` / `requestbin.com` / `hookbin.com` |
| トンネリングサービス | 4 | `ngrok.io` / `ngrok-free.app` / `localtunnel.me` / `serveo.net` |

**適用されない雛形が2件ある**: 「本番環境(誤アクセス防止)」カテゴリの
`production-api.yourcompany.com` と `prod-db.yourcompany.com` は**コメントアウトされており**、
利用者が自分の本番ドメインへ書き替えて有効化することを想定した記入例である。
この2件は配列の要素ではなく**シェルのコメント行**として書かれているため、そもそも配列に入らない
(`${#BLACKLIST_DOMAINS[@]}` は 16 である)。読み出しループの
`[[ "$domain" =~ ^#.*$ ]] && continue` は、利用者が値の側に `#` を書いた場合に備えた保険であり、
**この2件には作用しない**。いずれにせよ **ipset に登録されるのは上の16件だけ**である。

**この表に含まれないブロック対象**: クラウドメタデータの宛先(`169.254.169.254` /
`169.254.169.253` / `metadata.google.internal`)と SMTP ポート(TCP 25 / 465 / 587)、
および内部ネットワークと GitHub 以外への TCP 22 は、**`BLACKLIST_DOMAINS` とは別の
iptables 規則**で拒否する(「処理の流れ」5〜7)。用語集「ブロック対象ドメイン」の
「含まない例」はこれを指す。

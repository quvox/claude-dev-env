---
id: firewall
layer: impl
title: firewall 実装説明書
version: 1.0.0
updated: 2026-07-18
verified:
  at: 2026-07-19
  version: 1.0.0
  against:
    - doc: docs/02-design/system.md
      version: 1.1
summary: >
  Claude コンテナ内で起動時に適用する iptables ブラックリスト方式ファイアウォールの実装。
  デフォルト全許可（ACCEPT）とし、ペーストサイト等の危険ドメイン(ipset)・メタデータ・SMTP・
  外部SSH のみを REJECT する。entrypoint から実行される単一 bash スクリプト。
keywords: [ファイアウォール, iptables, ipset, ブラックリスト, SMTP, SSH, メタデータ, セキュリティ]
depends_on: []
source:
  - docs/02-design/system.md
---

# 実装説明書:firewall

## 概要

Claude コンテナ内で外部への機密流出経路（ペーストサイト・Webhook テスト・クラウドメタデータ・
SMTP・外部リバースシェル）を塞ぐ iptables ファイアウォールの実装。方式は「**デフォルト全許可
（ACCEPT）＋既知の危険宛先のみ拒否**」のブラックリスト。開発に必要な通信（Anthropic API・GitHub・
内部ネットワーク）は広く許可する。単一の bash スクリプトで、`entrypoint`（[全体設計](../02-design/system.md)
の entrypoint→firewall 契約）が起動シーケンス中に一度だけ実行する。core/5（FW・ネットワーク）に対応。

## ファイル構成

| パス | 役割 |
|---|---|
| scripts/init-firewall-claude.sh | FW 設定本体。ビルド時に `/usr/local/bin/init-firewall.sh` へ配置され、entrypoint が実行する |

実行前提: `NET_ADMIN`/`NET_RAW` ケイパビリティ（`claude-dev start` が付与）と、
`iptables`/`ipset`/`dig`/`curl`/`jq`（イメージに同梱）が必要。

## モジュール別実装詳細

### init-firewall-claude.sh

- **責務:** （設計書の該当コンポーネント: firewall / iptables ファイアウォール）
  コンテナ起動時に OUTPUT チェインへブラックリストルールを設定する。`set -e` で異常時は停止。
- **公開インターフェース:** 引数なしの実行スクリプト。標準出力に設定サマリと簡易スモークテスト結果を印字する。
- **処理の要点（実行順＝ルール適用順）:**
  1. **初期化**: `iptables -F OUTPUT` で OUTPUT チェインをフラッシュ、`iptables -X` でユーザーチェイン削除、
     `ipset destroy blacklisted-domains` で既存 ipset を破棄（いずれも失敗は `|| true` で無視、再実行可）。
  2. **デフォルトポリシー**: `INPUT`/`FORWARD`/`OUTPUT` すべて `ACCEPT`。
  3. **基本許可**: ループバック（`-o lo`）を ACCEPT、`ESTABLISHED,RELATED`（`-m state`）を ACCEPT。
     これらを先頭に置くことで応答パケットや戻り通信を確実に通す。
  4. **ドメインブラックリスト構築**: `ipset create blacklisted-domains hash:ip hashsize 1024` を作成。
     `BLACKLIST_DOMAINS` 配列（後述）の各ドメインを `dig +short A` で解決し、正規表現
     `^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$` に一致する IPv4 のみを ipset に追加（追加失敗は `|| true`）。
     続けて `iptables -A OUTPUT -m set --match-set blacklisted-domains dst -j REJECT
     --reject-with icmp-port-unreachable` を 1 本だけ追加し、ipset 宛を一括拒否する。
  5. **メタデータエンドポイント拒否**: `169.254.169.254`（AWS 等）、`169.254.169.253`（Azure）、
     `metadata.google.internal`（GCP、解決失敗は `|| true`）宛を `REJECT`。
  6. **SMTP 拒否**: TCP `25` / `465` / `587` の各宛先ポートを `REJECT`。
  7. **外部 SSH 制御（順序が重要）**:
     - 内部ネットワーク（`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`）宛の TCP 22 を先に `ACCEPT`。
     - GitHub SSH を許可するため `curl -sf --connect-timeout 5 https://api.github.com/meta` を取得し、
       `jq -r '.git[]? // empty'` で SSH 用 CIDR を抽出、各 CIDR 宛 TCP 22 を `ACCEPT`。
       取得結果が空のときのみフォールバックで `dig +short A github.com` の IPv4 宛 TCP 22 を `ACCEPT`。
     - 最後に「それ以外の TCP 22」を `REJECT`（外向きリバースシェル抑止）。許可ルールが上に並ぶため、
       許可対象を先に通してから残りを落とす構造になっている。
  8. **検証出力**: ブロックドメイン数・ipset 登録 IP 数を表示。`curl` が使える場合、
     `pastebin.com` がブロックされ（到達したら WARNING）、`api.anthropic.com` が到達可能である
     （不達なら WARNING）ことを確認する簡易スモークテストを実行し、結果を印字するのみ（判定で停止はしない）。
- **実装上の判断:**
  - ドメイン→IP は起動時点の一回解決（スナップショット）。DNS 変化には追従せず、追従にはコンテナ再起動が必要。
  - ドメインブロックは iptables のホスト名指定ではなく ipset（`hash:ip`）で行い、1 ルールへ集約している。
  - 危険なのは OUTPUT のみと割り切り、INPUT/FORWARD はポリシー ACCEPT のまま個別ルールを持たない。

## データアクセス

| データ | 操作 | 実施モジュール | 備考 |
|---|---|---|---|
| ipset `blacklisted-domains`（hash:ip） | create/add/destroy | firewall | `BLACKLIST_DOMAINS` の解決 IPv4 を格納。OUTPUT の match-set が参照 |
| iptables OUTPUT チェイン | flush/append | firewall | NET_ADMIN 前提。ルールは揮発（コンテナ再作成で消える） |

## API実装詳細

外部公開 API なし（コンテナ内でローカルに iptables/ipset を操作するのみ）。

## 設定・環境変数

allowlist/blocklist のカスタマイズは**環境変数ではなくスクリプト内配列の編集**で行う（環境変数による
外部注入インターフェースは持たない）。

| 名前 | 用途 | デフォルト | 必須 |
|---|---|---|---|
| （環境変数なし） | — | — | — |

- **`BLACKLIST_DOMAINS`（スクリプト内 bash 配列）**: ブロック対象ドメイン。既定値はペーストサイト
  （pastebin.com, paste.ee, hastebin.com, transfer.sh, file.io, 0x0.st, ix.io, sprunge.us, dpaste.org）、
  Webhook テスト（webhook.site, requestbin.com, hookbin.com）、トンネリング
  （ngrok.io, ngrok-free.app, localtunnel.me, serveo.net）。本番 API/DB ドメインの追記が推奨（コメントで雛形あり）。
  ループ内で `#` 始まり・空文字はスキップする。
- **追加ポートのブロック**: SMTP 節に倣い `iptables -A OUTPUT -p tcp --dport <port> -j REJECT` を追記する。
  （ヘッダーコメントに `BLACKLIST_PORTS` への言及があるが、実コードにポート配列は存在せず、直接追記する運用。）

## エラーハンドリング実装

| 異常系 | 実装箇所 | 実際の振る舞い | 対応する要件 |
|---|---|---|---|
| 既存ルール/ipset 不在 | 初期化節（`-F`/`-X`/`destroy`） | `2>/dev/null \|\| true` で無視し継続（再実行冪等） | core/5 |
| DNS 解決失敗・無効 IP | ドメイン解決ループ | `dig` 失敗は `\|\| true`、IPv4 正規表現に一致しない値は ipset に追加しない | core/5 |
| GitHub Meta API 取得失敗 | SSH 許可節 | `.git[]` が空なら `dig github.com` へフォールバック。両方失敗時は GitHub SSH 不許可 | core/5 |
| `metadata.google.internal` 未解決 | メタデータ拒否節 | `2>/dev/null \|\| true` で当該行のみスキップ | core/5 |
| スモークテストで想定外の到達性 | 検証節 | WARNING を印字するのみ。`set -e` 対象外（停止しない） | core/5 |

## テスト

自動テストは存在しない（02 テスト戦略のとおりシェル系は**実機確認**。E2E-1 の「FW」で `claude-dev start`
時に FW が適用されることを実機で確認、entrypoint→firewall 契約の結合確認も実機）。

| テスト(ファイル::ケース名) | レベル | 検証内容 | 対応する受け入れ基準/契約 |
|---|---|---|---|
| （自動テストなし。実機: `claude-dev start` 後にスクリプト自身のスモークテスト出力を確認） | 結合 | 起動時に FW が適用される／pastebin ブロック・anthropic 到達 | 契約: entrypoint→firewall（core/5）— 未検証(自動テストなし) |

実行方法: 自動テストコマンドなし。実機では entrypoint 経由で自動実行され、標準出力に
`=== Firewall rules (blacklist mode) ===` 以下のサマリとスモークテスト結果が出る。手動確認は
コンテナ内で `sudo /usr/local/bin/init-firewall.sh` を再実行、または `iptables -L OUTPUT -n` /
`ipset list blacklisted-domains` で確認する。

## 既知の制限・技術的負債

- **ブラックリスト方式の原理的限界**: 列挙されていない宛先はすべて到達可能。機密性の高い環境では
  本番ドメインの明示追加が前提。
- **DNS スナップショット**: ドメイン→IP は起動時の一回解決で、以後の DNS 変化に追従しない。
- **ルール揮発**: OUTPUT ルール/ipset はコンテナ再作成で消える（毎起動で再構築される前提）。
- **INPUT/FORWARD はノーガード**: ポリシー ACCEPT のまま個別ルールを持たない。
- `BLACKLIST_PORTS` はヘッダーコメントにのみ存在し、実装されていない（ポート追加は直接追記）。

## 運用メモ

- `NET_ADMIN`/`NET_RAW` 欠如時は iptables 操作が失敗する（`claude-dev start` が付与している前提）。
- 起動ログの `⚠️ WARNING` 行は、ブロック不発（pastebin 到達）または API 不達（anthropic 不達）の兆候。
  前者は ipset 構築失敗、後者はネットワーク不通を疑う。
- ブロック追加・確認はコンテナ内で完結する（ホスト再ビルド不要。ただし配列変更の永続化はイメージ再ビルドが必要）。

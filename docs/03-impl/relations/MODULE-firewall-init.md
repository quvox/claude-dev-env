---
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

# MODULE-firewall-init ファイアウォールの適用

## 目的

コンテナから外部への機密流出経路(ペーストサイト・Webhook テスト・クラウドメタデータ・SMTP・
外部リバースシェル)を塞ぐ(FR-env-05・NFR-sec-01)。方式は
**既定は全許可(ACCEPT)、既知の危険な宛先だけ拒否**するブラックリストで、開発に必要な通信
(Anthropic API・GitHub・内部ネットワーク)は広く通す。契約 `CTR-entrypoint-firewall` の
被呼び出し側である。

## 処理の流れ

1. **初期化**: `iptables -F OUTPUT` でフラッシュ、`iptables -X` でユーザチェイン削除、
   `ipset destroy blacklisted-domains` で既存 ipset を破棄する(いずれも `|| true` で無視し、
   再実行できるようにする)。
2. **既定ポリシー**: `INPUT` / `FORWARD` / `OUTPUT` をすべて `ACCEPT` にする。
3. **基本許可**: ループバック(`-o lo`)と `ESTABLISHED,RELATED` を先頭で ACCEPT する
   (応答パケットと戻り通信を確実に通すため)。
4. **ドメインブラックリスト**: `ipset create blacklisted-domains hash:ip hashsize 1024` を作り、
   `BLACKLIST_DOMAINS` 配列の各ドメインを `dig +short A` で解決して IPv4 だけを登録する。
   そのうえで `iptables -A OUTPUT -m set --match-set blacklisted-domains dst -j REJECT
   --reject-with icmp-port-unreachable` を**1本だけ**追加する。
5. **メタデータ拒否**: `169.254.169.254`(AWS 等)、`169.254.169.253`(Azure)、
   `metadata.google.internal`(GCP。解決失敗は `|| true`)宛を REJECT する。
6. **SMTP 拒否**: TCP 25 / 465 / 587 を REJECT する。
7. **外部 SSH 制御(順序が重要)**: 内部ネットワーク(`10.0.0.0/8`・`172.16.0.0/12`・
   `192.168.0.0/16`)宛の TCP 22 を先に ACCEPT。次に
   `curl -sf https://api.github.com/meta` の `.git[]` から GitHub の SSH 用 CIDR を取り出して
   ACCEPT(空のときだけ `dig +short A github.com` へフォールバック)。最後に
   **それ以外の TCP 22 を REJECT** する(外向きリバースシェルの抑止)。
8. **検証出力**: ブロックドメイン数と ipset 登録 IP 数を表示し、`curl` が使えるなら
   `pastebin.com` が塞がれていること・`api.anthropic.com` に到達できることを簡易スモークテスト
   する。結果は印字するだけで、判定で停止はしない。

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

## 連携先と連携内容

連携先なし(`iptables` / `ipset` / `dig` / `curl` の実行は外部コマンド呼び出し)。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 0(`set -e` のため途中失敗で非0)。呼び出し元の entrypoint は成否に関わらず起動を続ける |
| 永続化 | なし(揮発)。**ipset `blacklisted-domains`** と **iptables `OUTPUT` チェイン**を書き換える。どちらもコンテナ再作成で消え、毎起動で作り直される |
| 発火するイベント | なし |
| ログ | 標準出力へ `=== Firewall rules (blacklist mode) ===` 以下のサマリとスモークテスト結果。異常の兆候は `⚠️ WARNING` 行 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 既存ルール / ipset が無い | `2>/dev/null \|\| true` で無視して続行する(再実行が冪等になる) | なし |
| DNS 解決に失敗、または IPv4 でない値 | `dig` の失敗は `\|\| true`。IPv4 正規表現に一致しない値は ipset に入れない | そのドメインは塞がれない |
| GitHub Meta API の取得に失敗 | `.git[]` が空なら `dig github.com` へフォールバックする。両方失敗すると GitHub SSH が不許可になる | git over SSH が使えなくなる |
| `metadata.google.internal` が解決できない | その行だけスキップする | GCP メタデータは塞がれない |
| スモークテストで想定外の到達性 | `⚠️ WARNING` を印字するだけ(`set -e` の対象外) | 起動は続く |
| `NET_ADMIN` が無い | `iptables` の操作が失敗し、`set -e` により非0で終わる | **entrypoint は起動を止めない**(適用の成否に関わらず継続する。契約 `CTR-entrypoint-firewall`) |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | ドメイン → IP は起動時点の一回解決(スナップショット)にする。DNS の変化には追従せず、追従にはコンテナ再起動が要る | D0-sec-04 |
| 2 | ドメインのブロックを iptables のホスト名指定ではなく ipset(`hash:ip`)で行い、ルールを1本に集約する | D0-sec-04 |
| 3 | 危険なのは OUTPUT だけと割り切り、INPUT / FORWARD はポリシー ACCEPT のまま個別ルールを持たない | D0-sec-04 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| ブラックリスト方式の原理的な限界 | 列挙されていない宛先はすべて到達できる。機密性の高い環境では本番ドメインの明示追加が前提 | なし |
| DNS スナップショット | 起動後の DNS 変化に追従しない | なし |
| ルールが揮発する | コンテナ再作成で消える(毎起動で再構築する前提) | なし |
| INPUT / FORWARD がノーガード | 受信側の防御を持たない | なし |
| `BLACKLIST_PORTS` はヘッダコメントにあるだけで実装が無い | ポート追加は `iptables -A OUTPUT ...` を直接追記する運用 | なし |

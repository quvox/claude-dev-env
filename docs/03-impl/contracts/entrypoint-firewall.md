---
id: entrypoint-firewall
version: 1.0.0
updated: 2026-08-03
source:
  - docs/02-design/contracts/entrypoint-firewall.md
kind: other
impl: scripts/entrypoint-claude.sh::main
summary: entrypoint がファイアウォール適用を1度だけ呼び、成否に関わらず起動を続ける取り決め(実装側)
keywords: [契約, CTR, 実装]
verified:
  at: 2026-08-06
  version: 1.0.0
  against:
    - doc: docs/02-design/contracts/entrypoint-firewall.md
      version: 1.0.1
---

<!-- 2026-08-04 /doc-check ssot task-impl-depth(新しい実行): **合格証を再発行した(1.0.0)。**
     直前に削除した理由(source の docs/02-design/contracts/entrypoint-firewall.md が未検証)は
     解消した。本文には問題を見つけていない。★本実行は独立レンズが1つも走っていない。 -->

# CTR-entrypoint-firewall entrypoint → firewall(実装)

- 実装: `scripts/entrypoint-claude.sh::main`(呼び出し側)、
  `scripts/init-firewall-claude.sh::main`(受け側)
- 当事者: MOD-entrypoint → MOD-firewall
- 対応する設計: `docs/02-design/contracts/entrypoint-firewall.md`

## 実装上の事実

| 項目 | 実際の値 | 定義箇所 |
|---|---|---|
| 呼び出し | `/usr/local/bin/init-firewall.sh 2>/dev/null \|\| true`。引数なし、起動シーケンス中に1回 | `scripts/entrypoint-claude.sh:471` |
| 失敗の扱い | 標準エラーを捨て、`\|\| true` で終了コードを無視する(`set -e` の下でも起動を止めない) | 同上 |
| イメージ内のパス | ビルド時に `scripts/init-firewall-claude.sh` を `/usr/local/bin/init-firewall.sh` として配置する | `.devcontainer/Dockerfile.claude` |
| 前提 | `NET_ADMIN` / `NET_RAW`(`claude-dev:905`〜`906` が付与)、および iptables・ipset・dig・curl・jq(イメージ同梱) | `claude-dev:905`, `.devcontainer/Dockerfile.claude` |
| 適用範囲 | OUTPUT チェインのみ。INPUT / FORWARD はポリシー ACCEPT のまま個別ルールを持たない | `scripts/init-firewall-claude.sh` |
| ブロックの表現 | ドメインを起動時に一度だけ IP へ解決し、ipset(`hash:ip`)へ入れてルール1本に集約する | 同上 |
| 冪等性 | 既存ルール・ipset の削除を `2>/dev/null \|\| true` で行ってから再構成する | 同上 |
| 適用結果の可視化 | サマリを標準出力へ。適用後に到達性スモークテストを実行し、想定外なら警告行を出す | 同上 |

## 設計との差異

差異なし。

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 名前解決は起動時の一度きり(スナップショット) | DNS の変化に追従しない。追従にはコンテナの再起動が必要 | なし |
| 許可 IP レンジの取得に失敗し、名前解決へのフォールバックも失敗した場合 | GitHub への SSH が不許可になる | なし |
| `NET_ADMIN` が無い環境では適用が丸ごと失敗する | 警告だけが出て、制限のかからない状態で起動が続く | なし |

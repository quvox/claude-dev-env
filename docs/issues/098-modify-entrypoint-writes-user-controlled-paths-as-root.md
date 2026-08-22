---
id: 098-modify-entrypoint-writes-user-controlled-paths-as-root
type: modify
severity: 中
origin_layer: "03"
found: 2026-08-22
found_in: verify 系フロー(F3 実装整合の独立レビュー — Codex)
related: MODULE-entrypoint-claude, FR-env-11-2, FR-env-11-9, FR-env-12-14, scripts/entrypoint-claude.sh
closes_when: entrypoint が `/workspace` 配下の設定ファイルを書くとき、固定名の一時ファイルへの root のリダイレクトと、シンボリックリンクを追う `chown` のどちらも残っていないことが `scripts/entrypoint-claude.sh` の読取で確認できたとき
pattern: なし
pattern_survey: なし
summary: root で動く entrypoint が、利用者が書き換えられる `/workspace` 配下の固定名パスへリダイレクトし、シンボリックリンクを追う chown を行っている
---

# 098 root の entrypoint が利用者の書き換えられるパスをそのまま書いている

## 事象

コンテナの entrypoint は **root** で動く。その中で `/workspace`(ホストのプロジェクト
ディレクトリ。コンテナ内の利用者が書き換えられる)配下のファイルを、次の2つの形で扱っている。

1. **固定名の一時ファイルへのリダイレクト**: `scripts/entrypoint-claude.sh:667`・`:771`・`:686`
   などが `jq ... > "${MCP_JSON}.tmp"` の形で書く。`${MCP_JSON}.tmp` =
   `/workspace/.mcp.json.tmp` は固定名であり、**あらかじめ別のパスへのシンボリックリンクとして
   置いておくと、root のシェルがそのリンク先を切り詰めて書く。**
2. **シンボリックリンクを追う `chown`**: 同 `:678` などの
   `chown "$USERNAME":"$USERNAME" "$MCP_JSON"` は `-h` を持たないため、`/workspace/.mcp.json`
   がリンクであればリンク先の所有者を変える。

`.claude.json` を扱う経路(`:697` 以降)も同じ形である。

再現手順:

1. コンテナ内で `ln -sf /任意のパス /workspace/.mcp.json.tmp` を置く。
2. `claude-dev stop` → `claude-dev start` でコンテナを作り直す。
3. entrypoint の MCP 設定の段が走ると、リンク先が上書きされる。

## 影響

**この不具合が与える権限は、コンテナの中で既に得られるものを超えない**:
イメージは利用者に `NOPASSWD:ALL` の sudo を与えており(`.devcontainer/Dockerfile.claude:106`)、
`/workspace` はその利用者が自由に書けるディレクトリである。したがって
**コンテナ/ホストの隔離境界(`D0-sec-06`)は破れない**。

一方で、`/workspace` はホストのプロジェクトディレクトリそのものなので、リンク先を
`/workspace` 配下の別ファイルにすれば、**利用者が意図していないファイルが起動のたびに
切り詰められる**。これは事故として起きうる(エージェントが置いた残骸、退避目的の symlink)。
severity は 中 — 隔離境界を動かさず、`AC-nn` のどれも落とさないが、
**root で書く処理が利用者の書き換えられる名前を検証せずに使っている**という形そのものが弱い。

## 原因の見当

この形は本件より前から在る(`.mcp.json` の新規作成・追加の経路)。2026-08-22 の
`bundle-chrome-devtools-mcp` が同じ形の分岐を1つ増やしたため、独立レビューが検出した。
**推測**: 当初は「起動時に自分が作るファイルなので競合しない」という前提だったと思われるが、
`/workspace` が利用者の書き換えられる領域であることと噛み合っていない。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| root で `/workspace` 配下へ書くときの安全策 | 何も言っていない(手順18 は書く内容だけを述べる) | 何も言っていない(`NFR-sec-01` は隔離と最小権限を求めるが、この形を名指していない) | 実装が正(仕様の側に穴がある。直しは 03 から始まる) |

## 対処案

| 案 | 内容 | 波及の見込み |
|---|---|---|
| A | 一時ファイルを `mktemp` で作り、`chown` を `chown -h` にする。`config.toml` を扱う python 側は既に `tempfile.mkstemp` + `os.replace` を使っており、同じ形へ揃える | `scripts/entrypoint-claude.sh` の JSON を書く3〜4箇所。振る舞いは変わらない |
| B | 書く前に `[ -L "$path" ]` でリンクを拒否し、警告して飛ばす | 同上。既存の壊れた状態を放置するので、利用者が気づけない |

## 経緯

- 2026-08-22 F3(実装整合)の独立レビュー(Codex)が指摘。F3 は製品コードを書かないため起票した。
  severity は独立レビューの「高」から、コンテナ内 sudo の実測(`Dockerfile.claude:106`)を根拠に
  「中」へ裁定した。

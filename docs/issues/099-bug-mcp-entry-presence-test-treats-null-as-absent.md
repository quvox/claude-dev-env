---
id: 099-bug-mcp-entry-presence-test-treats-null-as-absent
type: bug
severity: 中
origin_layer: "03"
found: 2026-08-22
found_in: verify 系フロー(F3 実装整合の独立レビュー — Codex)
related: MODULE-entrypoint-claude, FR-env-11-9, FR-env-11-2, scripts/entrypoint-claude.sh
closes_when: `.mcp.json` の `chrome-devtools` に `null` または `false` が書かれた状態で起動しても、その値が同梱物を指す値へ書き換わらないことが実機で確認できたとき
pattern: なし
pattern_survey: なし
summary: 登録の有無を `jq -e` の真偽で判定しているため、`null` や `false` が書かれたエントリを「未登録」とみなして上書きし、FR-env-11-9 の「それ以外の値は変更してはならない」に反する
---

# 099 `jq -e` の真偽判定が、書かれている値を「未登録」とみなす

## 事象

`scripts/entrypoint-claude.sh:665` は登録の有無を次で判定している。

```sh
if ! jq -e '.mcpServers["chrome-devtools"]' "$MCP_JSON" >/dev/null 2>&1; then
```

`jq -e` は**出力が `null` または `false` のとき終了コード 1** を返す。したがって利用者が
`"chrome-devtools": null` と書いていると「未登録」の分岐に入り、次の行が同梱物を指す値で
**上書きする**。

再現手順(実測済み: 2026-08-22、`jq` で判定だけを再現):

1. `/workspace/.mcp.json` を `{"mcpServers":{"chrome-devtools":null}}` にする。
2. `jq -e '.mcpServers["chrome-devtools"]' .mcp.json; echo $?` → **1**(= 未登録扱い)。
3. その状態で `claude-dev start` すると、entrypoint がエントリを書き込む。

## 影響

`FR-env-11-9` は「**それ以外の値は変更してはならない**(利用者が自分で書き換えた設定を、
確認なく上書きしないため)」と定めており、この経路はそれに反する。
実害は小さい — `null` は MCP の設定として意味を持たないので、そう書く利用者は多くない。
ただし**仕様に対して振る舞いが誤っている**ので不具合である。severity は 中
(`AC-nn` のどれも落とさず、隔離境界も動かさない)。

## 原因の見当

`jq -e` を「キーが在るか」の判定に使ったため。値の真偽と存在は別である。
この形は本件より前から在り(元々は登録の追加だけを行っていた)、
2026-08-22 に「既存の値は変えない」という条項が加わったことで**仕様との差が生まれた**。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| 値が `null` のときの扱い | 未登録とみなして上書きする(`:665`) | `FR-env-11-9`「それ以外の値は変更してはならない」 | 要件が正(実装を直す) |

## 対処案

| 案 | 内容 | 波及の見込み |
|---|---|---|
| A | 存在の判定を `jq -e 'has("chrome-devtools")'` 相当(`.mcpServers | has("chrome-devtools")`)へ変える | `scripts/entrypoint-claude.sh` の1〜2行。`computer-use` の同じ判定(`:682`)も同型なので同時に直す |

## 経緯

- 2026-08-22 F3(実装整合)の独立レビュー(Codex)が指摘。判定の挙動を `jq` で実測して確認した。
  F3 は製品コードを書かないため起票した。

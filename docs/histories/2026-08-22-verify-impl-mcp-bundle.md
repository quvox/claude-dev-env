---
id: 2026-08-22-verify-impl-mcp-bundle
date: 2026-08-22
record: なし(taskless — flow: verify-impl)
critical: false
origin_layer: "03"
issue: なし
summary: F3 実装整合の増分 run。コールグラフを再生成し、CI が渡さない build 引数の記述を実測へ直し、独立レビューの所見2件を課題票にした
---

# 2026-08-22 実装整合(F3)— chrome-devtools MCP 同梱の後の増分

## 変更理由

### R-01 コードが動いたので、生成物と 03 の事実を実測へ合わせ直した

- 起点層・根拠: 03。`bundle-chrome-devtools-mcp`(コミット `b6a7256`)が
  `scripts/entrypoint-claude.sh` / `.devcontainer/Dockerfile.claude` /
  `.github/workflows/ghcr-images.yml` を動かした。
- 変更が必要になった条件: コールグラフの生成物がコードより古くなり、
  `docs/03-impl/infra/local/ghcr.md` の構成表に、CI が実際には渡していない値が
  「必須」として残っていた。

## 変更内容の要約

- コールグラフと機能グラフを再生成した(新関数 `ensure_codex_mcp_entry` と `main` からの辺が入った)。
- `ghcr.md` の `IMAGE_VERSION` の行を実測へ直した(CI は build-arg として渡さず、
  タイムスタンプは `labels` でイメージのラベルへ付けている)。
- 独立レビュー(Codex)の所見2件を課題票にした。1件は誤検知ではなく実測で裏を取り、
  重大度をコンテナ内 sudo の実測に基づいて「高」から「中」へ裁定した。
- 03 層代表(`docs/03-impl/index.md`)の合格証を現在の版へ打ち直した。

## 更新した仕様ドキュメント

| 理由ID | 仕様ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|---|
| R-01 | docs/03-impl/callgraphs/*.md | (生成物。版を持たない) | 再生成(shell: シンボル 179 → 180 / 辺 274 → 275) |
| R-01 | docs/03-impl/feature-graph.md | (生成物) | 再生成 |
| R-01 | docs/03-impl/infra/local/ghcr.md | 1.3.0 → 1.3.1 | `IMAGE_VERSION` の行を実測へ(CI は渡さない。ラベルで付ける) |
| R-01 | docs/03-impl/index.md | 1.36.0(据え置き) | 合格証を 1.36.0 / 2026-08-22 へ打ち直した |

## 実装したもの

| 理由ID | 対象 | 内容 | コミット |
|---|---|---|---|
| — | なし(F3 は製品コードを書かない) | 所見は課題票へ回した | — |

## 実施した移行

| 理由ID | 対象 | 手順(実行したコマンド / スクリプト) | 実行日 | 結果・確認方法 |
|---|---|---|---|---|
| — | なし | なし | — | なし |

### ロールバック・復旧記録

- 適用外(`critical: false`)

## 機能間連携仕様書の変化

| 種別 | ID | 内容 |
|---|---|---|
| 変更 | (なし) | 生成物のみ。`MODULE-*` の本文と frontmatter は動かしていない |

## 検討した代替案

| 論点 | 採用した案 | 棄却した代替案 | 棄却の理由 / 崩れる条件 |
|---|---|---|---|
| 独立レビューが「高」とした一時ファイルの扱い | 重大度 中 の課題票にする | 高のまま起票する | コンテナ内の利用者は `NOPASSWD:ALL` の sudo を既に持ち(`Dockerfile.claude:106`)、`/workspace` も自由に書ける。この経路で得られる権限はコンテナの中で既に得られるものを超えず、コンテナ/ホストの隔離境界は動かない |
| 同じ所見をこの run で直すこと | 直さず課題票にする | F3 の中で製品コードを直す | F3 は製品コードを書かない(修繕は `/build --repair` のもの) |
| 手動実行の入力に `latest` を渡せること | **所見としない**(仕様どおり) | 課題票にする | 手動入力は不良版を引いたときの逃げ道として `D0-dist-03` 項2 が定めたものであり、Claude Code と Codex CLI の入力も同じ形である。自動経路(空入力)は具体バージョンへ解決している。凍結の risk は `images.md` の落とし穴の表が既に記録している |

## 副産物

| 種別 | 行き先 | 内容 |
|---|---|---|
| 新規の課題票 | docs/issues/098-modify-entrypoint-writes-user-controlled-paths-as-root.md | root の entrypoint が `/workspace` 配下の固定名パスへ書き、`chown` がリンクを追う |
| 新規の課題票 | docs/issues/099-bug-mcp-entry-presence-test-treats-null-as-absent.md | `jq -e` の真偽判定が `null` を「未登録」とみなし、`FR-env-11-9` に反して上書きする |
| 棚上げ | なし | — |

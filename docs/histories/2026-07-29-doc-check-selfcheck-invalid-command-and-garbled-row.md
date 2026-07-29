---
slug: doc-check-selfcheck-invalid-command-and-garbled-row
layer: history
title: /doc-check の指摘修正（存在しない CLI オプション記述の訂正・テスト表の重複文の修復）
date: 2026-07-29
trigger: 検証指摘の修正（/doc-check full）
origin_layer: impl
affected:
  - doc: docs/03-impl/sample-project.md
    version: 1.0.0 -> 1.1.0
  - doc: docs/03-impl/makefile.md
    version: 1.1.0 -> 1.2.0
---

# 変更記録:/doc-check の指摘修正（存在しない CLI オプション記述の訂正・テスト表の重複文の修復）

## 変更理由・背景

`/doc-check full` の検証で、実装コードと突き合わせた結果 2 件の記述誤りが見つかった。

1. `docs/03-impl/sample-project.md` の「実行方法」が自己検証の実走手順を
   `claude-dev orchestrate --workspace workspace/orch-sample` と記していたが、`claude-dev` の
   `orchestrate` サブコマンドは `[<ゴール>] [--fresh]` のみを受け付け、`--workspace`
   オプションを持たない（`--workspace` は コンテナ内の `claude-orchestrator` バイナリ側の引数）。
   同文書の「既知の制限」は正しく「`claude-dev orchestrate` または orchestrator バイナリ直接起動」
   と書いており、文書内で矛盾していた。
2. `docs/03-impl/makefile.md` のテスト表に「`make orch-sample` で `make orch-sample`（E2E-4 の実走）
   ができること」という重複した文が残っており、検証内容が読み取れなかった。要件 orchestration/20-2 の
   とおり `make orch-sample` は scaffold までで実走を含まないため、その区別も曖昧だった。

## 変更内容の要約

- `03-impl/sample-project.md`: 「実行方法」の自己検証実走手順を、存在しないオプションを使わない
  形（作業コピーで `claude-dev start`→`claude-dev orchestrate`、またはローカルビルドした
  `orchestrator --workspace workspace/orch-sample` を直接起動）に訂正した。
- `03-impl/makefile.md`: テスト表の重複文を「`make orch-sample` で題材が scaffold され、そこに
  対するオーケストレーター実走（E2E-4）に入れること」へ修復し、scaffold と実走の境界を明示した。

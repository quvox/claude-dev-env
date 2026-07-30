---
slug: doc-check-makefile-codex-layer-sync
layer: history
title: 検証指摘の修正（update-claude の失効範囲と codex 版の扱いを実装へ同期）
date: 2026-07-30
trigger: 検証指摘の修正（/doc-check full）
origin_layer: impl
affected:
  - doc: docs/03-impl/makefile.md
    version: 1.3 -> 1.4
---

# 変更記録:検証指摘の修正（update-claude の失効範囲と codex 版の扱いを実装へ同期）

## 変更理由・背景

`/doc-check full` の check B（03-impl ⇄ コード）で、`docs/03-impl/makefile.md` の記述が実装と
食い違っていることを検出した。同書は `make update-claude` を「**終端の claude 導入層だけ**を
無効化して高速更新する」と説明していたが、D-27（Codex CLI 同梱）以降、配布ステージの終端は
`claude 導入 RUN` → `codex 導入 RUN` → `codex ランチャー生成 RUN` の順に積まれている。Docker の
レイヤー規則により `CLAUDE_VERSION` の変更は claude 導入層**以降のすべて**を失効させるため、
`update-claude` は codex 導入層も入れ直す。さらに Makefile は `CODEX_VERSION` を渡さないので、
その入れ直しは Dockerfile 既定の `latest`＝実行時点の npm 最新版になる。

「文書とコードのどちらを正とするか」を人間に確認し、**コードを正とする**判断を得た（Makefile 側に
codex の版解決を足すことはしない。配布イメージのピン留めは CI の責務という D-27 ② の線引きを維持
する）。したがって 03-impl を実装の実挙動へ同期した。要件・設計は変更していない（core/12-3 は
「ビルド時にピン留めして導入し、実行時ダウンロードに依存しない」を求めるもので、ローカルビルドで
`latest` を解決することはこれに反しない。core/9 の版追随基準は CI の日次ビルドを対象としている）。

## 変更内容の要約

- **03-impl/makefile.md**: ターゲット一覧の `build-claude` 行を「エージェント CLI の版
  （`CLAUDE_VERSION`/`CODEX_VERSION`）は渡さず Dockerfile 既定に委ねる」に更新。`update-claude` 行の
  失効範囲を「配布ステージの終端レイヤー群（claude 導入層とそれ以降の codex 導入層・codex ランチャー層）」
  に訂正し、codex が既定 `latest` で入れ直される旨を明記。「ビルド構成」節に**終端レイヤー群の内訳と
  codex への波及**の小節を新設（ローカル更新と CI 配布イメージで codex の版が一致しない場合がある点を
  含む）。設定・環境変数表に `CODEX_VERSION`（Makefile はどのターゲットでも渡さない）の行を追加。
  既知の制限に「ローカルビルドは codex の版を制御しない／特定版は `docker build --build-arg` を直接
  使う／codex 単独のピン留め更新ターゲットは設けない」を追加。frontmatter の summary・keywords も同旨に更新。

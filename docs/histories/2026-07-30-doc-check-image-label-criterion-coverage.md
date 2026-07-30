---
slug: doc-check-image-label-criterion-coverage
layer: history
title: 検証指摘の修正（イメージラベル参照の受入基準 core/9-5 に検証行を補完）
date: 2026-07-30
trigger: 検証指摘の修正（/doc-check full）
origin_layer: impl
affected:
  - doc: docs/03-impl/ghcr-workflow.md
    version: 1.4 -> 1.5
---

# 変更記録:検証指摘の修正（イメージラベル参照の受入基準 core/9-5 に検証行を補完）

## 変更理由・背景

`/doc-check full` の check A3（02→03：割り当てられた受け入れ基準に検証手段があるか）で、
`01-requirements/core.md` 要件9 の受入基準5「利用者が配布イメージを取得したとき、イメージの
ラベルとして同梱バージョン（タイムスタンプ）を参照可能にしなければならない」に対応する検証行が、
core/9 を担当する 3 モジュール（makefile / ghcr-workflow / devcontainer）のいずれのテスト表にも
無いことを検出した。

ラベル付与そのものは実装済み（`ghcr-workflow` の build-push-action `labels` 入力で
`io.github.quvox.claude-dev.version` と `org.opencontainers.image.version` に `YYYYMMDDHHmm` を
付与）、参照側も実装済み（`cli` の `image_version` が前者を読む）で、両者は各 03-impl の本文に
記述されている。欠けていたのは**テスト対応表の行だけ**であり、要件・設計・コードは変更していない。
担当を `ghcr-workflow` に置いたのは、本基準が「push された配布イメージが持つメタデータ」を対象と
しており、`labels` を付与するのが本ワークフローだからである。

## 変更内容の要約

- **03-impl/ghcr-workflow.md**: テスト表に受入基準5 の行を追加（`docker buildx imagetools inspect`
  および pull 後の `docker image inspect` で、push されたイメージのラベル 2 種が当該ビルドの
  `YYYYMMDDHHmm` を持ち、利用者が同梱バージョンを参照できることを CI 実機で確認する。
  `claude-dev start` のバージョン表示がこのラベルを読む旨も併記）。他の節・要件・設計は不変。

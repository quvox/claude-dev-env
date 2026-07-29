---
slug: doc-check-coverage-and-wording-fixes
layer: history
title: /doc-check の指摘修正（要件9のシナリオ外根拠の補完・曖昧語の具体化・非機能カバレッジ行の補完）
date: 2026-07-29
trigger: 検証指摘の修正（/doc-check）
origin_layer: requirements
affected:
  - doc: docs/01-requirements/core.md
    version: 1.3.0 -> 1.4.0
  - doc: docs/02-design/system.md
    version: 1.3.0 -> 1.4.0
---

# 変更記録:/doc-check の指摘修正

## 変更理由・背景

`2026-07-29-claude-version-pin-terminal-layer` の直後に `/doc-check`（差分検証）を実施し、
自動修正可能な3件の指摘を得た。いずれも意味の追加・補完を含むため PATCH ではなく MINOR とした。

## 変更内容の要約

- **01-requirements/core.md（1.3.0→1.4.0）**
  - チェック C6（曖昧語）: 要件10 受け入れ基準1 の「適切な実体」を具体化。`uname -s` による判定と、
    Linux は `claude-dev` / macOS（`Darwin`）は `claude-dev-mac` という対応を明記した
    （`Makefile` の `UNAME_S`／`ifeq ($(UNAME_S),Darwin)` と突合して確認）。
  - チェック A1（UC 網羅の根拠）: 要件9 に追加した受け入れ基準2〜4 はビルド時の性質で UC のフローに
    現れないため、「UC-1〜3 のフロー内で満たされる」という既存のシナリオ外根拠では説明が不足していた。
    CI 側の成果物検証で確認する旨を追記し、検証手段の所在（03-impl/ghcr-workflow.md のテスト表）を示した。
- **02-design/system.md（1.3.0→1.4.0）**
  - チェック A2（要件カバレッジ）: 非機能要件に追加した「日次更新後も `docker pull` を増分に保つ」は
    devcontainer（ステージ配置）と ghcr-workflow（cache-from/to・build-args）の双方で実現されるが、
    要件カバレッジ確認表の `core 非機能` 行に ghcr-workflow が載っていなかったため補完した。

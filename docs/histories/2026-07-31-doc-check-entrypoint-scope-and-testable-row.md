---
slug: doc-check-entrypoint-scope-and-testable-row
layer: history
title: 検証指摘の修正（entrypoint の概要へ codex 既定設定生成・要件 core/12 を補完、結合テスト行の曖昧表現を具体化）
date: 2026-07-31
trigger: 検証指摘の修正（/doc-check entrypoint の自動修正）
origin_layer: impl
affected:
  - doc: docs/03-impl/entrypoint.md
    version: 1.5.1 -> 1.6.0
---

# 変更記録:検証指摘の修正（entrypoint の概要へ codex 既定設定生成・要件 core/12 を補完、結合テスト行の曖昧表現を具体化）

## 変更理由・背景

`/doc-check entrypoint` で、`03-impl/entrypoint.md` に 2 点の記述不足が見つかった。いずれも実装・
要件・設計そのものは変えず、上流（`02-design/system.md`）から機械的に導ける範囲の補完である。

1. **概要の責務列挙と担当要件が codex の既定設定生成を含んでいなかった。** モジュール分割定義の
   `entrypoint` 行は責務に「既定設定生成（claude `settings.json` / codex `config.toml`）」を、対応要件に
   `core/12(12-4〜12-6)` を挙げており、frontmatter の summary と本文（起動シーケンス 10・データアクセス表）も
   codex `config.toml` 生成を記述していた。一方で概要だけが `settings.json`・MCP 設定生成と
   `要件 core/2,3,5,11` にとどまり、D-27 ⑥ 反映前の記述が残っていた。
2. **結合テスト対応表の 1 行が曖昧表現（「意図どおり働く」）で検証可能な粒度になっていなかった。**
   契約「cli → コンテナ/entrypoint」の検証内容が、マウントを「共有 3 ボリューム」と数だけで示し
   （実際に `start` が渡すのは `claude-dev-auth`・`claude-dev-config` の 2 つで、`.chrome-profile` は
   VNC 時のみのプロジェクト単位ボリューム）、期待結果を「意図どおり」で済ませていた。

## 変更内容の要約

- **03-impl/entrypoint.md**（1.5.1 → 1.6.0）
  - 概要の責務 (3) を「既定設定生成（claude `settings.json`／codex `config.toml`＝Codex サンドボックス
    無効化の既定）と MCP 設定生成」に補完し、担当要件を `core/2,3,5,11,12(12-4〜12-6)` に修正。
  - テスト対応表の契約「cli → コンテナ/entrypoint」行を、02-design の契約ブロックのマウント定義に
    合わせて列挙し直し、期待結果を「両 rc への export 行追記」「portsync 常駐の 3 条件成立時のみ起動」
    という観測可能な形に書き換えた。

要件文・受け入れ基準・契約・起動シーケンス・E2Eシナリオ一覧は変更していない。

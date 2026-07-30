---
slug: doc-check-requirement-ownership-alignment
layer: history
title: 検証指摘の修正（要件12-7 の担当整合・cli 行の対応要件補完・要件9 の UC 外列挙補完）
date: 2026-07-31
trigger: 検証指摘の修正（/doc-check full の自動修正）
origin_layer: design
affected:
  - doc: docs/02-design/system.md
    version: 1.7 -> 1.8
  - doc: docs/01-requirements/core.md
    version: 1.7 -> 1.8
---

# 変更記録:検証指摘の修正（要件12-7 の担当整合・cli 行の対応要件補完・要件9 の UC 外列挙補完）

## 変更理由・背景

`/doc-check full` で、同一文書内および層間の担当帰属に食い違いが 3 点見つかった。いずれも
要件・設計・振る舞いそのものは変えず、担当と traceability の記述を実態へ合わせる修正である。

1. **要件 core/12-7 の担当が文書内で矛盾していた。** 12-7 は「Codex サンドボックスを動作させる
   ために seccomp/AppArmor を緩めてはならない」であり、これを満たすのは `docker run` を発行する
   cli/cli-mac である（テスト戦略の備考も「cli/cli-mac の起動引数として確認する」と書いていた）。
   一方でモジュール分割定義の entrypoint 行と要件カバレッジ確認表は 12-7 まで entrypoint の担当と
   していた。entrypoint は `docker run` を発行しないため、この帰属は成立しない。
2. **モジュール分割定義の cli 行の「対応する要件」が実態より狭かった。** 要件カバレッジ確認表は
   core/7-5（compose プロジェクト名の一意化）と core/12（`login-codex`・12-7）を cli/cli-mac に
   割り当て、03-impl/cli.md も両方を実装として記述しているのに、分割定義の cli 行には現れていなかった。
3. **要件9 の「UC のフロー中に現れない受け入れ基準」の列挙から 9-1 が漏れていた。** 9-1（GHCR へ
   マルチアーキ push）も 9-2〜9-4・9-6〜9-7 と同じくビルド時の性質で、CI 側の成果物検証で確認する
   （03-impl/ghcr-workflow.md のテスト表が該当行を持つ）。

## 変更内容の要約

- **02-design/system.md**（1.7.0 → 1.8.0）
  - モジュール分割定義 `entrypoint` 行の対応要件を `12(12-4〜12-7)` → `12(12-4〜12-6)` に修正。
  - モジュール分割定義 `cli` 行の対応要件へ `core/7(7-5 compose 名一意化)` と
    `core/12(login-codex, 12-7 --security-opt 不付与)` を追加。`cli-mac` 行は「cli が担う要件の
    macOS 差分を含む」と明記（カバレッジ表が cli-mac にも 7-5・12 を割り当てていることとの整合）。
  - 要件カバレッジ確認表 `core/12` 行の担当を、entrypoint を `12-4〜12-6`、cli/cli-mac に
    `12-7 --security-opt 不付与` を明記する形へ修正。
- **01-requirements/core.md**（1.7.0 → 1.8.0）
  - シナリオ外要件の列挙を「要件9 の受け入れ基準2〜4・6〜7」→「1〜4・6〜7（マルチアーキ push・
    タグ付与・同梱エージェント CLI の版・手動指定）」へ補完。

いずれも要件文・受け入れ基準・契約・E2Eシナリオ一覧・モジュール数は変更していない。

---
id: 2026-08-10-doc-check-ssot-remove-orchestrator-recertification
date: 2026-08-10
task: task-remove-orchestrator(`/task-close` フェーズ4 §6 からの `/doc-check ssot task-<slug>`)
origin_layer: 00
issue: docs/issues/093(案A を実行して解消。ファイル削除だけが残務)
summary: オーケストレーター削除の反映後に SSOT 24 文書を再認証した。反映が変更指示の記法(`種別: delete` の行)を 01 の受入基準表へそのまま持ち込んでいた1件を含む5件を直した
---

# 2026-08-10 オーケストレーター削除の反映後の SSOT 再認証(`/doc-check ssot`)

## 変更理由

`task-remove-orchestrator` の変更指示 68 件が SSOT へ反映され(コミット `420af38`)、
closure の 24 文書から `verified` が外れた。`/task-close` のフェーズ4 §6 がこの実行を起動した。

検査 A〜F と機械検査を走らせたところ、**反映そのものは変更指示と一致**していた
(`check-relations` 56/56 合格 / `check-contracts` 合格 / `build-callgraphs --check` 最新 /
`cluster-features --check` 最新 / `callgraph-check` 重大度「高」0 / `relations-query --health`
循環 0・対応要件が無い機能 0)。検証済みにする前に次の5件を直した。

## 直したもの

| # | 種別 | 内容 |
|---|---|---|
| 1 | **変更指示の記法が SSOT へそのまま反映された(A2 / C)** | `docs/01-requirements/functional.md` の受入基準表に `\| FR-env-12-12 \| delete \| 廃止する。旧内容は「…」… \|` の行が残っていた。`種別` 列の語彙は `正常系` / `境界値` / `異常系` の3値で、`delete` は変更指示側だけの値である(`.claude/directions/change-set.md` 例外1)。**この1行のせいで 01 が条項 141 件、02 の要件カバレッジ表と 03 のテスト対応表が 140 件となり、条項 `FR-env-12-12` を所有する行がどの下流にも無い状態だった**(A2 違反)。また本文が「廃止する」という変更相対の言い方で、廃止済みの `D0-orch-17` を参照していた。**行を削除し、`non-functional.md` / `request.md` と同じ欠番の HTML コメントに置き換えた。** これで 01 = 02 = 03 が条項 140 件で完全一致する。`docs/issues/093` が求めていた案A そのものである |
| 2 | **欠番の記録が 00 だけ無かった(A0。独立レビュー L-01)** | `docs/00-requests/acceptances.md` は `AC-03` の次が `AC-06` だが、`AC-04` / `AC-05` の欠番について本文にもコメントにも記述が無かった。同じ削除を扱う `01-requirements/non-functional.md` / `01-requirements/system.md` / `02-design/system.md` / `00-requests/request.md` はいずれも欠番の HTML コメントを持っており、00 の受入基準だけがこの慣行から外れていた。読み手が欠番を誤りと区別できないため、同じ書式のコメントを補った |
| 3 | **`id` の一意性違反(C10。独立レビュー L-02)** | `docs/01-requirements/system.md` と `docs/02-design/system.md` がどちらも `id: system` だった。CLAUDE.md §7 は「`id` は `docs/` 全体で一意」とし、ファイル名が層をまたぐときは `id` が層を名乗る(`01-system` / `02-system`)と定める。テンプレート `.claude/templates/01-system.md` / `02-system.md` も同じ値を持つ。**規範が値を名指ししているので機械的に直せる。** それぞれ `01-system` / `02-system` にした |
| 4 | **曖昧語(C7。独立レビュー L-08)** | `docs/02-design/system.md`「結合テスト対象」の `CTR-cli-container` の行に「この行が観測するのは「読み手が**正しい**集合を消すか」である」があった。CLAUDE.md §7 が禁じる語である。同じ文書が指している `CTR-cli-container`「削除対象の決め方(4つの規則)」の規則 A〜D を明示する形へ書き換えた |
| 5 | **削除済み issue へのパス参照(CS11)** | `docs/03-impl/index.md`「コードとの乖離として未解決のもの」が `docs/issues/003` を参照していたが、`003` は本タスクが削除した 21 件のうちの1件である(参照を書いたのと同じタスクが対象を消していた)。同じ文書の後段が使っている裸の ID 表記へ揃え、削除済みであることを明記した |

## 更新したドキュメント

| ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|
| `docs/01-requirements/functional.md` | 1.13.0 → **1.13.1** | 直したもの #1。**廃止の意図は元の行が既に書いていたので、記法の訂正 = PATCH** |
| `docs/00-requests/acceptances.md` | 1.4.0 → **1.4.1** | 直したもの #2。**受入基準の内容は変えていないので PATCH** |
| `docs/01-requirements/system.md` | 1.2.0 → **1.2.1** | 直したもの #3(frontmatter の `id` のみ)。**PATCH** |
| `docs/02-design/system.md` | 2.9.0 → **2.9.1** | 直したもの #3 と #4。**PATCH** |
| `docs/03-impl/index.md` | 1.19.0 → **1.19.1** | 直したもの #5。**PATCH** |
| 上記5件を含む **24 文書** | 版は据え置き(上記5件を除く) | **検証済み記録(`verified`)を発行した。** 内訳は 00 が6・01 が5・02 が6・03 が7。`docs/03-impl/relations/MODULE-*.md` 56 本と `features.md` は `03-impl/index.md` がまとめて代表する(原則6 の例外) |

## 残したもの(原則8 のゲートを通した結果)

いずれも**バグでも DoD のブロッカーでもない**ため `docs/pendings.md` の残務へ1行ずつ入れた。

- `docs/issues/` の `related` の陳腐化(`004` / `094` が実在しない orchestrator 由来 ID を指す。
  `095` の実測値 24 箇所が現在 6 箇所)。独立レビュー L-05〜L-07 が検出した
- `id: images` の重複(`03-impl/tests/images.md` と `03-impl/environments/images.md`)。
  独立レビュー L-03。**テンプレートが両方とも `images` を導くため、直すにはキット側の命名規約が要る。
  キットは CLAUDE.md §3 により製品 DoD 未達の間は凍結されている**ので、#3 と違って機械的に直せない
- `MOD-makefile` が 16 本で `relations-query --health` の目安 15 本を超える(削除前は 19 本)
- `docs/issues/093` のファイル削除(本 run では実行権限が無かった。本文には解消済みの注記を入れた)

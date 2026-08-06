---
id: 073-modify-tests-strategy-coverage-counts-are-stale
type: modify
severity: 低
found: 2026-08-07
found_in: /task-doc(task-clause-ids-and-split-policy のドライラン)
related: docs/03-impl/tests/strategy.md, docs/01-requirements/functional.md
pattern: handwritten-aggregate-count-goes-stale
pattern_survey: docs/ の SSOT 4層を「基準・行の合計数を散文/表セルに手書きしている箇所」で走査(grep)。該当はこの1箇所のみ
summary: tests/strategy.md「カバレッジの扱い」の手書き集計(182基準/197行)が現状(201基準/216行)と食い違う
---

# 073 tests/strategy.md のカバレッジ集計が古い

## 事象

`docs/03-impl/tests/strategy.md:115`「カバレッジの扱い」の「現状」セルが
「機能要件の全 182 基準に行がある(非機能要件の 15 行を合わせて対応表は 197 行)」と書いているが、
2026-08-07 時点の実数は**機能要件 201 基準**(`docs/01-requirements/functional.md` の受入基準行)、
対応表の行は **FR 202 行(FR-env-01 受入基準9 の重複3行を含む)+ NFR 14 行**である。
過去のタスクで受入基準が追加された際に、この手書きセルが追随していない。

再現手順:

1. `grep -c '^| [0-9]* | ' docs/01-requirements/functional.md` 相当で受入基準行を数える(201)。
2. `docs/03-impl/tests/strategy.md:115` の「182」「197」と比較する。

## 影響

読者が受入基準のカバレッジ状況を古い数で把握する。検証の合否には影響しない
(同セルの測定コマンド `build-index.py --check` は正しい実数を再生成する)。

## 原因の見当

機械が再生成できる集計値を散文セルに手書きしているため、基準の増減に追随しない
(推測: 導入時の実数のまま)。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| 基準の総数 | strategy.md は 182/197 と記載 | functional.md の実数は 201 基準 | 実数(functional.md)が正 |

## 対処案

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | セルから手書きの実数を消し「実数は `build-index.py --check` の再集計が正」とだけ書く(数を持たない) | strategy.md 1セル。以後陳腐化しない |
| B | 実数(201基準/…行)へ書き直す | strategy.md 1セル。次の基準追加でまた古くなる |

## 経緯

- 2026-08-07 起票(task-clause-ids-and-split-policy のドライラン中に発見。同タスクは記述形式の
  移行で件数を変えないため、本タスクでは直さず起票のみ。条項ID移行の反映後は「受入基準 ID」列の
  条項キー(FR 201 + 重複、NFR 14)が実数になる)

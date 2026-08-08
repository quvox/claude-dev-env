---
id: 093-modify-fr-env-12-12-is-a-clause-id-that-is-not-an-acceptance-criterion
type: modify
severity: 中
origin_layer: 01
found: 2026-08-07
found_in: task-layer-placement フェーズ2 の独立レビュー(`lens: subagent`。01 層の点検)
related: FR-env-12, FR-env-12-12, D0-orch-17, docs/01-requirements/functional.md, docs/02-design/system.md, docs/03-impl/tests/entrypoint.md, .claude/directions/change-set.md
pattern: clause-id-whose-種別-is-outside-the-vocabulary
pattern_survey: "`docs/01-requirements/functional.md` の受入基準表の全 209 行(`^| FR-<domain>-nn-# |` の行)を走査し、`種別` 列が `正常系` / `境界値` / `異常系` のいずれでもない行を数えた。**該当は `FR-env-12-12` の1件だけ**である(値は `対象外`)。`non-functional.md` は条項に分けないため対象外、`usecases.md` は受入基準表を持たない"
summary: FR-env-12-12 は種別が語彙外の「対象外」で、条項 ID を持ちながら受入基準ではない行になっており、02 のカバレッジ表と 03 のテスト対応表が何を充足・検証すべきかを持てない
---

# 093 `FR-env-12-12` は条項 ID を持つが受入基準ではない

## 事象

`docs/01-requirements/functional.md:350` の受入基準表に次の行がある。

> | FR-env-12-12 | **対象外** | 本要件の対象は開発者が対話的に codex を使うことであり、オーケストレーターが
> worker/レビューアーとして codex を常用することは対象外とする(`D0-orch-17` 未決) |

`種別` 列に書ける値は `正常系` / `境界値` / `異常系` の3つ(変更指示ではこれに `delete` が加わる。
`.claude/directions/change-set.md` の例外1)であり、`対象外` は語彙の外である。

内容も受入基準ではない。**システムが満たすべきことを1つも述べておらず**、
「この要件はここまでを対象とする」という**射程の宣言**である。EARS の骨(WHEN/IF/WHILE/WHERE +
SHALL)も持たない。

## 影響

- **02 のカバレッジ表と 03 のテスト対応表が、何を充足・検証すればよいかを持てない。**
  現に `docs/02-design/system.md` はこの条項に `対象外(オーケストレーターが codex を
  worker/レビューアーとして常用するかは未決で、01 自身が本要件の対象外と定める)` を入れており、
  **カバレッジ表の `対象外` は「要件がこの設計に当てはまらない」の意味**なので、
  「条項が受入基準でない」という本当の理由が表からは読めない。
- 機械検査は素通りする。`CS13` は行の**存在**しか見ず、`CS16` は ID の**消失**しか見ない。
  `種別` 列の語彙を検査するものは無い(**この列の制約は読み手が唯一の検出者である**)。

## 原因の見当

`FR-env-12` を起こした時点で、`D0-dist-04` 項5(スコープの限定)を要件側へ写す場所として
受入基準表を使ったと推測する(推測)。射程の宣言は `- 内容:` 行か「未解決事項」に置くのが本来である。

## 正はどちらか

意図の差異ではなく**書き方の誤り**である。振る舞いはどの層も一致している
(オーケストレーターが codex を常用しないことは `D0-orch-17` が未決として持つ)。

## 対処案

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | `FR-env-12-12` を**明示的に廃止**し(変更指示の `種別` に `delete` と書く)、射程の宣言を `FR-env-12` の `- 内容:` へ移す。02 のカバレッジ表と 03 のテスト対応表から当該行を落とす | 01 1行 + 02 1行 + 03 1行。**条項 ID は欠番になる**(`FR-env-12` は 1〜11 と 12 の欠番になる。番号を詰めてはならない — CS16) |
| B | 種別を `正常系` にして EARS へ書き直す(「WHERE オーケストレーターが codex を worker として起動する場合、システムは…」) | **要件が増える**。`D0-orch-17` が未決である以上、書ける振る舞いが無い |
| C | そのまま残す | 語彙の外の値が1件残り続け、同じ書き方が次の要件へ伝播する |

推奨は **A**。ただし**条項 ID の廃止は 01 の意味に触れる編集**であり、`.claude/directions/delegation.md`
§1 の問う基準(00/01 の意味を変える編集)に当たるため、**タスクとして起こして決定シートに載せる**。

## 影響範囲

- `docs/01-requirements/functional.md`(`FR-env-12` の受入基準表と `- 内容:`)
- `docs/02-design/system.md`(要件カバレッジ確認の `FR-env-12-12` の行)
- `docs/03-impl/tests/`(`FR-env-12-12` を持つ対応表の行)
- **コードは変わらない**(振る舞いを1つも変えない)

## 経緯

- 2026-08-07 起票。`task-layer-placement` のフェーズ2 で、01 層を精読した独立レビュー
  (`lens: subagent`)が検出した。**同タスクは記述の置き場だけを動かす範囲なので、条項の廃止は
  範囲外として起票に留めた**(`.claude/directions/issues-pendings.md`。範囲外の修正を混ぜない)。

---
id: 077-modify-unverified-enumeration-target-column-keeps-the-pre-clause-id-notation
type: modify
severity: 低
found: 2026-08-07
found_in: /doc-check ssot task-clause-ids-and-split-policy(反映後の再認証。独立レビュー(サブエージェント)も独立に検出)
related: docs/03-impl/tests/, docs/01-requirements/functional.md, .claude/templates/03-tests-module.md, docs/issues/060
pattern: clause-id-migration-left-the-enumeration-table-behind
pattern_survey: docs/03-impl/tests/ の全32ファイルを `受入基準 [0-9]` で走査。23ファイル・181箇所が該当(「未検証(テスト未実装)の全件」節の「対象」列と、一部の「テスト識別子」列の注記)。「受入基準 ⇄ テスト対応表」本体は全30ファイルが条項ID へ移行済みで該当0件
summary: 条項ID への移行が「受入基準 ⇄ テスト対応表」だけに適用され、同じファイルの「未検証(テスト未実装)の全件」節の「対象」列は旧表記「FR-env-01 — 受入基準 6」のまま残っている
---

# 077 「未検証の全件」節の対象列が条項ID へ移行されていない

## 事象

`task-clause-ids-and-split-policy`(2026-08-07 反映)が `docs/03-impl/tests/` 30 ファイルの
**「受入基準 ⇄ テスト対応表」**を条項ID(`FR-<domain>-nn-#`)キーへ移行したが、
**同じファイルの「未検証(テスト未実装)の全件」節の「対象」列**は旧表記のまま残っている。
その結果、1つのファイルの中で同じ受入基準が2通りに書かれている。

例(`docs/03-impl/tests/cli-stop.md`):

- 対応表: `| FR-env-01-6 | 正常系 | E2E | E2E-01(実機確認手順) | 未検証(テスト未実装) |`
- 全件節: `| 1 | FR-env-01 — 受入基準 6(正常系) | 自動テストランナーを設けない方針(...) | ... |`

走査結果は 23 ファイル・181 箇所(内訳は frontmatter の `pattern_survey`)。

**参照は壊れていない。** 条項ID の採番は現行の通し番号をそのまま初期値としたため、
「受入基準 6」と `FR-env-01-6` は同じ行を指す。`build-index.py` の状態集計は状態列の語だけを
数えるので集計も壊れていない。したがって重大度は「低」である。

## なぜ起きたか(根本原因はキット側)

`.claude/templates/03-tests-module.md:58` の「未検証(テスト未実装)の全件」節の例示が

```
| 1 | FR-<domain>-01 の異常系 | <> | <タスク slug / docs/issues/NNN-...> |
```

と**旧表記のまま**である。テンプレートに倣ってこの節へ追記するたびに旧表記が再生産されるため、
`docs/` 側だけを直しても再発する。

## どうしたいか

1. **キット側**: `.claude/templates/03-tests-module.md` の例示を条項ID 形式へ直す
   (`/kit-improve` 案件。`docs/` の修正では閉じられない)。
2. **`docs/` 側**: 23 ファイル・181 箇所の「対象」列を条項ID 形式へ揃える
   (機械的な置換。意味は変わらない)。

**1 を先に行うこと。** 逆順にすると、次にこの節へ追記した時点で旧表記が混ざり直す。

## なぜ今のタスクで直さなかったか

- `task-clause-ids-and-split-policy` は「やらないこと」に**表記の統一は対象外**と宣言しており、
  変更指示35件のどれもこの節を対象にしていない(反映は全38節が逐語一致で完了している)。
- 根本原因がキット側にあり、`docs/` だけを直しても再発する構造になっている。
- 参照が壊れておらず、機械集計も壊れていないため、検証済みにすることを妨げない。

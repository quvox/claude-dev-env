---
id: 078-modify-two-frontmatter-scalars-start-with-a-backtick-and-break-yaml-parsing
type: modify
severity: 低
found: 2026-08-07
found_in: /doc-check ssot task-clause-ids-and-split-policy(検査 C10 の frontmatter 妥当性を PyYAML で全件解析して検出)
related: docs/feedbacks/018-mv-atomicity-is-about-the-path-not-the-contents.md, docs/issues/076-bug-check-changeset-treats-staged-callgraphs-as-change-instructions.md, docs/issues/080-modify-destructive-commands-appear-in-no-use-case.md, docs/issues/081-bug-check-changeset-aborts-on-a-non-utf8-file-in-the-task-directory.md
pattern: frontmatter-scalar-starts-with-backtick
pattern_survey: docs/ 配下の全 Markdown(仕様ドキュメント4層・issues・feedbacks・histories・pendings)の frontmatter を PyYAML の safe_load で解析。2026-08-08 の再走査で失敗は **4件**(`feedbacks/018` の summary / `issues/076`・`080`・`081` の pattern_survey がバッククォート始まり)。**仕様ドキュメント4層には1件も無い**(5件目だった `issues/083` は 2026-08-08 の task-layer-placement が解消して削除された)
summary: frontmatter の値が引用符なしでバッククォート始まり・コロン混じりになっているため YAML として解析できないファイルが5件ある(いずれも SSOT 外)
---

# 078 frontmatter の値がバッククォートで始まり YAML として解析できない

## 事象

次の2ファイルは frontmatter が **YAML として解析できない**。

| ファイル | 行 | 値 |
|---|---|---|
| `docs/feedbacks/018-mv-atomicity-is-about-the-path-not-the-contents.md` | 4 | ``summary: `mv` の原子性は…`` |
| `docs/issues/076-bug-check-changeset-treats-staged-callgraphs-as-change-instructions.md` | 8 | ``pattern_survey: `new-features/` 配下を走査する…`` |

YAML では **バッククォートは予約文字**で、引用符なしのスカラーの先頭に置けない
(`while scanning for the next token / found character '`' that cannot start any token`)。

**仕様ドキュメント4層(00〜03)には1件も無い。** 該当は上の2件だけである。

## 影響

- キットのスクリプト(`build-index.py` など)は現状動いている(正規表現ベースで読んでいるため)。
  したがって**今すぐ壊れているものは無い**。
- 一方、frontmatter を厳密な YAML パーサで読む道具(`/doc-check` の検査 C10 を機械化したもの、
  外部のドキュメントツール、エディタのプレビュー)はこの2ファイルで例外を出す。

## どうしたいか

値全体をダブルクォートで囲む(バッククォートはそのまま残せる)。

```yaml
summary: "`mv` の原子性は「そのパスの rename に成功するのは1つ」という意味である"
pattern_survey: "`new-features/` 配下を走査するキットのスクリプト…"
```

## なぜ今のタスクで直さなかったか

`task-clause-ids-and-split-policy` の影響範囲(closure)にも、本実行で検証済みにした
SSOT 48 ファイルにも含まれない。`docs/feedbacks/` と `docs/issues/` は版と検証済み記録を持たず、
`/doc-check` の検証対象そのものではないため、独立した修正として残す。

- 2026-08-07 `/doc-check ssot task-stop-session-spawned-containers` で再走査し、2件 → **5件**に増えていることを確認した(`pattern_survey` を持つ issue が増えたため)。**修正はしていない**(SSOT 外で、どの検査もこの解析に依存していない)。

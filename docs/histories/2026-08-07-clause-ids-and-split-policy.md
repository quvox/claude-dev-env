---
id: 2026-08-07-clause-ids-and-split-policy
date: 2026-08-07
task: task-clause-ids-and-split-policy
origin_layer: 01
issue: docs/issues/060-modify-01-and-02-lack-clause-ids-split-policy-and-coverage-status.md
summary: 受入基準201件へ条項IDを振り、全34要件に分割可否を入れ、02の要件カバレッジ表を条項単位+充足列へ作り替えた
---

# 2026-08-07 条項IDと分割可否の導入(要件の部分充足を見えるようにする)

## 変更理由

`.claude/directions/` が規範として定める3つの書式が SSOT に実装されていなかった
(`docs/issues/060`)。規範自身が述べる理由:

> Keyed by requirement, a design that realises one clause out of three is **textually identical**
> to one that realises all three, so partial satisfaction cannot be seen or checked.

**起点は 01**。条項ID と分割可否は要件そのものの記述形式と性質であり、02 のカバレッジ表は
それに従属する(条項ID が無ければ条項単位のキーを作れない)。00 は変更していない
(分割可否は 01 の要件の性質であり `D1-*` に記録すると規範が定めるため。
`request.md` の「やらないこと」5項目のいずれとも衝突しない)。

## 変更内容の要約

- **受入基準の意味・本文・件数は一切変えていない。** 記述形式だけの移行であることを、
  変更指示の本文から追加要素を逆変換すると SSOT と逐語一致することで機械的に証明した
  (`functional.md` 201行 / `non-functional.md` 13行 / `03-impl/tests` 30ファイル)。
- 機能要件の受入基準 **201 件**に条項ID(`FR-<domain>-nn-#`)を振った。現在の通し番号を初期値とし、
  以後は**欠番を埋めない・並べ替えない・再利用しない**(規則を `functional.md` の冒頭に明記。
  検査は `check-changeset.py` の CS16)。
- 機能要件21件・非機能要件13件の全 **34 件**に `分割可否` を入れた。既定は `不可分`、
  `段階可(理由)` は5件(`NFR-perf-01` / `NFR-perf-02` / `NFR-scale-01` / `FR-env-01` / `FR-env-07`)。
- `docs/02-design/system.md` の要件カバレッジ確認を、要件単位54行から**条項単位235行 + `充足` 列**へ
  作り替えた。`充足` は「**設計がその条項を覆っているか**」を言い、実装の達成度は
  `03-impl/tests/` の状態列が持つ(同じ事実を2箇所で持たない)。
- `03-impl/tests/` 30ファイルの対応表を、旧2列形式(`要件 ID` + `受入基準 #`)から
  条項IDキーの5列形式へ移した。旧形式のファイルは0件になった。
- `docs/01-requirements/decisions/` を新設し、分割可否の判断を `D1-split-01` / `D1-split-02` として記録した。

**この移行が可視化した既存の状態**: `FR-env-01-19` と `FR-env-07-5`(どちらも compose 資源の
一意化)の充足が `部分(P-005)` である。要件単位の表では「割り当て済み」と字面が同じで見えなかった。
`不可分` のままだと規範により 01・02 が恒久的に検証済みにできなくなるため、人間が
**論点5 = A** を裁定し、この2要件を `段階可(理由)` にして段階的な条項を理由欄で名指した。

## 更新したドキュメント

| ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|
| docs/01-requirements/functional.md | 1.8.1 → 1.9.0 | 受入基準表の第1列を通し番号から条項IDへ(201件)。全21要件に `分割可否` を追加(`FR-env-01` と `FR-env-07` のみ `段階可`)。冒頭に条項IDの不動規則を明記 |
| docs/01-requirements/non-functional.md | 1.3.1 → 1.5.0 | 5分類の表に `分割可否` 列を追加(13件)。`段階可` は性能2件と拡張性1件。用語集の「安全」の単独使用を1件解消 |
| docs/01-requirements/usecases.md | 1.2.1 → 1.3.0 | UC-06 基本フロー手順6 の受入基準参照を条項ID `FR-env-12-5` へ |
| docs/01-requirements/system.md | 1.0.1 → 1.1.0 | 用語集の「安全」の単独使用を解消(`/doc-check` の自動修正) |
| docs/01-requirements/decisions/split.md | 新設 1.1.0 | `D1-split-01`(既定は不可分、段階可は5件とその理由)/ `D1-split-02`(値と理由欄の条項集合を変える判断は委任範囲外) |
| docs/01-requirements/decisions/index.md | 生成物 | `build-index.py` が新規生成 |
| docs/02-design/system.md | 2.4.0 → 2.5.0 | 要件カバレッジ確認を条項単位235行 + `充足`・`根拠` 列へ。`充足` の定義(設計が覆っているか)を表の直前に明記 |
| docs/03-impl/tests/*.md(30ファイル) | 各 MINOR | 受入基準⇄テスト対応表を条項IDキーの5列形式へ。`cli-stop` / `cli-logout` / `cli-reset` / `entrypoint` は「未検証の全件」節の計上漏れ5件も解消 |
| docs/03-impl/tests/strategy.md | 1.1.2 → 1.2.0 | 手書き集計「全182基準/197行」を実数「201条項/216行」へ(`docs/issues/073` を解消) |
| docs/03-impl/callgraphs/*.md(6件)/ feature-graph.md | 生成物 | キット更新後のツールで再生成。**差分は注記コメントのみでコード由来の内容は不変**(原則2 は保たれていた) |
| 02・03 の他 40 ファイル | 版据え置き | 上流の版が動いたことによる検証済み記録の再発行のみ |

## 実装したもの

| 対象 | 内容 | コミット |
|---|---|---|
| (なし) | **コードは1行も変えていない。** 記述形式の移行であり、観測可能な振る舞いへの影響はゼロ | — |

## 機能間連携仕様書の変化

| 種別 | ID | 内容 |
|---|---|---|
| (なし) | — | `03-impl/relations/` 83本と `features.md` は変更していない。`MODULE-*` の frontmatter は要件を要件単位(`requirements: FR-env-01`)で持ち、条項単位へ落とすことは規範が要求していない |

## 副産物

| 種別 | 行き先 | 内容 |
|---|---|---|
| 解消した issue | docs/issues/060(削除) | 本タスクの起点。条項ID・分割可否・充足列の3つすべてを実装した |
| 解消した issue | docs/issues/073(削除) | `strategy.md` の手書き集計が古い件。`/doc-check ssot` が実数へ直して解消した |
| 新規 issue | docs/issues/074 | `FR-env-01-9` のテスト対応行が3行に重複(主担当1つの規則違反)。**人間が論点4 = A を裁定**し、今回は行を動かさず本issueで追跡すると決めた |
| 新規 issue | docs/issues/075 | 生成物 `feature-graph.md` が、資源0件では生成されない `callgraphs/resources.md` を無条件に参照する。**キット側の修正が要る**(`/kit-improve` 案件) |
| 新規 issue | docs/issues/076 | `check-changeset.py` の変更指示モードが staged コールグラフを変更指示と誤認し、規範どおり staged を生成するとフェーズ2のゲートが通らなくなる。**キット側の修正が要る** |
| 新規 issue | docs/issues/077 | 「未検証の全件」節の「対象」列に旧表記が23ファイル181箇所残る。根本原因は `.claude/templates/03-tests-module.md` の例示自体が旧表記であること |
| 新規 issue | docs/issues/078 | frontmatter のスカラーがバッククォート始まりで YAML 解析できない2件(SSOT 外) |
| 記述の訂正 | docs/pendings.md P-005 | `関連` を条項 `FR-env-01-19`・`FR-env-07-5` の名指しへ書き替えた(02 の `部分(P-005)` の裏付けとして規範が要求する形) |
| 記録 | docs/histories/2026-08-07-doc-check-ssot-clause-ids-recertification.md | `/doc-check ssot` 自身が行った自動修正10件の記録(本エントリとは別の理由なので別ファイル) |

## 残る「中」の指摘(消えない。PASS はブロックしない)

`FR-env-01` / `FR-env-07` は `段階可` で、条項 `FR-env-01-19` / `FR-env-07-5` の充足が `部分(P-005)`
である。妥当な `段階可 × 部分` は重大度「中」に留まり、**決して「高」へ上げてはならない**
(不変則3 の例外は1つだけという理由。`/doc-check` 認証段階 §3)。
解消は `docs/pendings.md` P-005 の「どうなったら解消が必要か」— 同時に扱うプロジェクト数が
数百規模になったとき、または衝突が実際に観測されたとき — が満たされたときである。

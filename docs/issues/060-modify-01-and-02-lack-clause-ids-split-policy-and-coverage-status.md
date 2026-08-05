---
id: 060-modify-01-and-02-lack-clause-ids-split-policy-and-coverage-status
type: modify
severity: 中
found: 2026-08-05
found_in: /task-doc task-spec-measurability(§1「書く前に読む」で directions と SSOT の書式を突き合わせて発見)
related: docs/01-requirements/functional.md, docs/01-requirements/non-functional.md, docs/02-design/system.md, .claude/directions/01-requirements.md, .claude/directions/02-design.md
summary: 01 の受入基準に条項ID(FR-<domain>-nn-#)が無く、機能要件・非機能要件のどちらにも「分割可否」欄が無い。02 の要件カバレッジ表も要件単位のままで「充足」列を持たないため、要件の部分充足が構造的に見えない
---

# 060 01 に条項IDと分割可否が無く、02 のカバレッジ表に充足列が無い

## 事象

`.claude/directions/` が規範として定める書式のうち、**3つが SSOT に実装されていない**。
2026-08-05 に実測した。

| 規範 | 出どころ | 現状 |
|---|---|---|
| 受入基準ごとの**条項ID** `FR-<domain>-nn-#` | `.claude/directions/01-requirements.md`「functional.md」 | **0 件**。`functional.md` の受入基準表は `\| # \| 種別 \| 基準 \|` の3列で、`#` は表内の連番であって参照可能なIDではない |
| 要件ごとの **`分割可否`**(`不可分` / `段階可(理由)`) | 同上(「非機能要件も持つ」と明記) | **0 件**(`functional.md` / `non-functional.md` を `分割可否` で走査して 0) |
| 02 の要件カバレッジ表の **`充足` 列**(`完全` / `部分(P-nn)` / `対象外(理由)` / `-`)と**条項単位のキー** | `.claude/directions/02-design.md`「★ Requirement coverage」(**この規則はこのファイルが持つ**と明記) | `docs/02-design/system.md:146`〜 の表は `\| 要件 ID \| 割り当てモジュール \| 備考 \|` の3列。**キーは要件単位**で、充足列が無い |

あわせて `docs/01-requirements/decisions/` が存在しない(`D1-*` の置き場)。
`分割可否` は「要件の性質なのでフェーズ1の決定シートで決め `D1-*` として記録する」と
規範が定めているので、この2つは同じ欠落の表と裏である。

## 影響

**要件の部分充足が構造的に見えない。** 規範自身が理由を書いている:

> Keyed by requirement, a design that realises one clause out of three is **textually identical**
> to one that realises all three, so partial satisfaction cannot be seen or checked.

具体的に本プロジェクトで起きている形:

- `docs/pendings.md` の各エントリは `関連` に**要件ID**を書いており、条項IDを書けない。
  規範は「`部分` を裏付ける pendings は条項IDを名指すこと」と定め、`/doc-check` A2 が
  重大度「高」で検査すると書いているが、**キーが無いのでこの検査が成立しない**。
- `/task-new` §2 の「★ 影響範囲が乗っている条項の充足を引く」という手順が、
  引く先の列が無いため実行できない(本タスクのフェーズ1でも「該当なし: 02 の要件カバレッジ表は
  充足列を持たない」と記録するしかなかった)。
- `分割可否` は**未記載なら `不可分`** というフェイルクローズ既定があるため、
  **現状が誤りになっているわけではない**。ただし「段階的に満たしてよい要件」を宣言する手段が
  無いので、部分実装は常に規範違反として現れる。

severity は「中」: 振る舞いにも既存の合格証にも影響しないが、
**測定可能性を担保する仕組みそのものの欠落**である。

## 原因の見当

**推測**: 本プロジェクトの 01/02 はブートストラップ(`/reverse-doc`)で既存コードから起こしたもので、
そのとき条項ID・分割可否・充足列を持つ書式が規範に無かったか、
ブートストラップの範囲に入っていなかった。以後のタスクは既存の書式に追随してきた。

## 正はどちらか

**ドキュメントが規範に追いついていない**(規範が正)。
規範側を緩める選択もありうるが、`.claude/directions/02-design.md` は
「なぜ条項単位でなければならないか」を理由つきで書いており、緩めると
`/doc-check` A2 と pendings の `部分` の検査が同時に成立しなくなる。

## 対処案

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | 独立タスクを立て、`functional.md` の受入基準 180 行に条項IDを振り、`functional.md` / `non-functional.md` に `分割可否` 列を足し、`02-design/system.md` のカバレッジ表を条項単位 + `充足` 列へ作り替える。あわせて `docs/01-requirements/decisions/` を作り `D1-*` を起こす | 01×2・02×1・(pendings の `関連` の書き替え)。**受入基準の意味は変えない**ので下降はここで止まる |
| B | 段階導入。まず `分割可否` 列だけを足し(既定 `不可分` を明記)、条項IDと充足列は次段へ回す | 01×2 |
| C | 規範側を緩める(`/kit-improve` 案件) | `.claude/directions/01-requirements.md` と `02-design.md` |

**推奨は A**(規範が理由を持って条項単位を要求しており、緩めると連鎖して検査が2つ死ぬ)。
ただし 180 行の受入基準へ ID を振る作業は本タスク(仕様の測定可能化)の範囲を超えるため、
**独立タスクとして起票にとどめる**(CLAUDE.md 原則8)。

## 追加(2026-08-05 `/task-doc task-spec-measurability` §4)— CS9 が一度も走っていない

同じ「規範の書式に SSOT が従っていない」型の欠落をもう1つ実測した。**こちらは機械検査が
丸ごと無効になっている**ぶん影響が大きい。

`check-changeset.py` の **CS9(02 の `PLAN-*` ⇄ 03 の `MODULE-*` の呼び出し関係の一致)** は、
`check-changeset.py:343` で次の正規表現を使う。

```
^\| `(PLAN-[a-z0-9-]+)` \|
```

**PLAN-ID がバッククォートで囲まれていることを要求する。**
`.claude/directions/02-design.md` の書式例も `` | `PLAN-auth-login` | MOD-auth | … `` と囲んでいる。
ところが `docs/02-design/relations.md` の「一覧」表(64 行)は **囲んでいない**
(`| PLAN-cli-attach | MOD-cli-attach | tool | …`)。

結果として CS9 は毎回

```
CS9 02 PLAN ⇄ 03 MODULE: 未検査 — 02-design/relations.md に PLAN-* の表行が無い
```

を返し、**この検査は本プロジェクトで一度も実行されていない**。
CLAUDE.md §1 は 02 と 03 の突き合わせを「この仕組みの中心」と位置づけており、
CS9 はその機械側にあたる(`/doc-check` の check E)。**「検査したが違反なし」と
「一度も検査していない」が見分けられる出力になっているのは救いだが、
未検査のまま 64 行が積み上がっている。**

| 案 | 内容 |
|---|---|
| A | `docs/02-design/relations.md` の「一覧」表の `PLAN-*` をバッククォートで囲む(64 行 + 変更指示の追随)。**規範側に SSOT を合わせる** |
| B | `check-changeset.py:343` の正規表現をバッククォートの有無どちらでも通す(`` `? ``)。**キット側を緩める**(`/kit-improve` 案件) |

**推奨は B と A の併用**: まず B で検査を効かせ(未検査を解消し、実際の不一致があるかを見てから)、
そのうえで A で表記を規範へ揃える。A だけを先にやると、64 行を直した直後に
初めて CS9 が動いて大量の不一致が出る、という順序になりやすい。
キット側の検討は `.claude/improvements/KIT-changeset-cs2-closure-and-deletes-as-sections.md` に併記した。

## なぜ task-spec-measurability で直さないか

同タスクの closure は「測定不能な記述を閉じる」ことに限定されており、
`01-requirements/functional.md` については `FR-env-05` / `FR-env-08` / `FR-orch-02` の
3要件しか触らない。条項IDと分割可否は**全要件に一斉に入れないと意味が無い**
(一部だけ ID を持つ表は、持たない行を参照できないまま残る)ため、混ぜると
影響範囲・DoD・履歴のいずれもが実態と食い違う。

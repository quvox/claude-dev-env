---
id: task-clause-ids-and-split-policy
phase: 決定
origin_layer: 01
issue: docs/issues/060-modify-01-and-02-lack-clause-ids-split-policy-and-coverage-status.md
date: 2026-08-06
updated: 2026-08-06
source: []
summary: 01 の受入基準に条項ID を振り、全要件に分割可否を入れ、02 の要件カバレッジ表を条項単位 + 充足列へ作り替える
---

**回答待ち: `docs/tasks/task-clause-ids-and-split-policy/sheet.md`**
(概念の明確化 4 件 / 論点 3 件 / 委任の確認 1 件。回答後この行を「回答済み」へ変える)

## 目的

`.claude/directions/` が規範として定める3つの書式が SSOT に実装されていない状態を解消し、
**要件の部分充足を構造的に見えるようにする**(`docs/issues/060`)。規範自身の理由:

> Keyed by requirement, a design that realises one clause out of three is **textually identical**
> to one that realises all three, so partial satisfaction cannot be seen or checked.

## やること・やらないこと

**やること**

- `docs/01-requirements/functional.md` の受入基準 **201 行**に条項ID(`FR-<domain>-nn-#`)を振る。
- `functional.md`(21要件)と `non-functional.md`(13要件)に **`分割可否`**(`不可分` / `段階可(理由)`)を入れる。
- `docs/01-requirements/decisions/` を新設し、分割可否の判断を **`D1-*`** として記録する。
- `docs/02-design/system.md` の要件カバレッジ表(現 59 行)を**条項単位のキー + `充足` 列**へ作り替える。
- `docs/pendings.md` の `関連` を、`部分` を裏付ける条項ID で名指す形へ書き替える。

**やらないこと(理由つき)**

- **受入基準の意味は変えない。** 本タスクは記述形式の移行であり、要件の内容には触れない
  (触る必要が出たら別タスクにする)。
- **コードは変えない。** 実装への影響はゼロである。
- **`.claude/directions/` は変えない**(キット側の変更は `/kit-improve` 案件)。
- 03-impl/tests/*.md 30 ファイルの移行と CS9 の件を含めるかは**論点1・論点2**(回答待ち)。

## 影響範囲(closure)

| 層 | SSOT | 変更指示 | 変更の種類 |
|---|---|---|---|
| 01 | docs/01-requirements/functional.md | new-features/01-requirements/functional.md | modify |
| 01 | docs/01-requirements/non-functional.md | new-features/01-requirements/non-functional.md | modify |
| 01 | docs/01-requirements/system.md | new-features/01-requirements/system.md | modify(概念3 の回答しだいで「変更なし」) |
| 01 | docs/01-requirements/usecases.md | new-features/01-requirements/usecases.md | modify(AC⇄UC 表の参照を条項ID へ) |
| 01 | docs/01-requirements/decisions/index.md | new-features/01-requirements/decisions/index.md | add |
| 01 | docs/01-requirements/decisions/split.md | new-features/01-requirements/decisions/split.md | add(`D1-split-*`) |
| 02 | docs/02-design/system.md | new-features/02-design/system.md | modify |
| 02 | docs/02-design/relations.md | new-features/02-design/relations.md | modify(論点2 の回答しだいで「変更なし」) |
| — | docs/pendings.md | (SSOT ではないので変更指示を持たない。`/task-close` が直接直す) | modify |
| 03 | docs/03-impl/tests/*.md(30ファイル) | new-features/03-impl/tests/*.md | modify(論点1 の回答しだいで「変更なし」) |

**変更の起点: 01**。理由 = 条項ID と分割可否は**要件そのものの記述形式と性質**であり、
02 のカバレッジ表はそれに従属する(条項ID が無ければ条項単位のキーを作れない)。
`.claude/directions/task-memo.md` §3.3 も「分割可否は 00/01 の概念で、答えは `D1-*` に記録する」と定める。

**触らない層の明示的な判断**

- **00: 変更なし。** 分割可否は 01 の要件の性質であり、`D1-*` に記録すると規範が定めている。
  `request.md` の「やらないこと」5項目のいずれとも衝突しない(いずれも機能の話で、記述形式の話ではない)。
- **03-impl/relations/(83本): 変更なし。** `MODULE-*` の frontmatter は要件を `requirements: FR-env-01`
  の**要件単位**で持つ。条項単位へ落とすかは規範が要求しておらず、今回は触らない。

**既存タスクとの関係**: なし(`docs/tasks/` は本タスク以外に空)。

**解消できる pending / issue**: `docs/issues/060`(本タスクの起点。全体)。
`docs/issues/066`(6件の NFR の目標値が要件文の一部しか測っていない)は**解消しない**が、
条項ID が入ると測定対象を条項で名指せるようになるため、次のタスクの前提が整う。

## 読む範囲(読了記録)

- 全文読了: 2026-08-06(本タスク直前の `/doc-check full` で 00〜02 を全ファイル読了。
  その実行で 01・02 を書き換えたので、下の版はいずれも書き換え後の現在値である)
  - docs/00-requests/acceptances.md@1.2.0
  - docs/00-requests/decisions/auth.md@1.2.0
  - docs/00-requests/decisions/dist.md@1.0.1
  - docs/00-requests/decisions/env.md@1.2.0
  - docs/00-requests/decisions/index.md@-
  - docs/00-requests/decisions/orch.md@1.3.0
  - docs/00-requests/decisions/scope.md@1.2.0
  - docs/00-requests/decisions/sec.md@1.1.2
  - docs/00-requests/request.md@1.3.0
  - docs/00-requests/terminology.md@1.2.0
  - docs/01-requirements/functional.md@1.8.1
  - docs/01-requirements/non-functional.md@1.3.1
  - docs/01-requirements/system.md@1.0.1
  - docs/01-requirements/usecases.md@1.2.1
  - docs/02-design/architecture.md@1.3.0
  - docs/02-design/contracts/cli-container.md@1.4.2
  - docs/02-design/contracts/cli-orchestrator.md@1.1.0
  - docs/02-design/contracts/docker-api.md@1.0.0
  - docs/02-design/contracts/entrypoint-firewall.md@1.0.1
  - docs/02-design/contracts/index.md@-
  - docs/02-design/contracts/orchestrator-prompt.md@1.3.0
  - docs/02-design/environments.md@1.1.0
  - docs/02-design/logging.md@1.3.0
  - docs/02-design/relations.md@1.4.0
  - docs/02-design/system.md@2.4.0
- 不要: docs/00-requests/decisions/._sec.md@- — 理由: macOS の AppleDouble メタデータファイル
  (バイナリ・git 未追跡)。仕様ドキュメントではない。**削除の可否は人間に確認中**

## 決定シート(回答済み)

(未回答。`sheet.md` に回答が入り次第ここへ転記する)

## 未決点

(フェーズ2の実装ドライランで洗い出す)

## 調査メモ

**実測値**(2026-08-06。移行対象の規模)

| 対象 | 件数 | 出どころ |
|---|---|---|
| 機能要件 | 21 | `functional.md` の `## FR-` 見出し |
| 受入基準の行(= 条項ID を振る対象) | **201** | `functional.md` の `\| N \| 種別 \|` 行 |
| 非機能要件 | 13 | `non-functional.md` の `\| NFR-` 行 |
| システム要件 | 21 | `system.md` の `\| SR-` 行 |
| 02 の要件カバレッジ表の行 | 59 | `02-design/system.md` の `\| FR/NFR/SR-` 行 |
| 03-impl/tests の旧2列形式ファイル | **30** | `\| 要件 ID \| 受入基準 # \|` を含むファイル |
| pendings のエントリ | 5(P-001〜P-005) | `pendings.md` の `## P-` 見出し |

**仕様ドキュメントの一括検査(母集団の凍結)** — 2026-08-06 `check-changeset.py --ssot docs`:

```
## 仕様ドキュメントの一括検査(SSOT 全体): 154 ファイル
  CS8 曖昧語・未決点: 違反 8 件
  CS11 参照実在: 違反 23 件
  CS12 同型の走査記録: OK
✗ 違反 31 件
```

CS8 の 8 件は全件 `pendings.md` P-002 / P-003 が追跡する「将来設定」、
CS11 の 23 件は全件 `docs/issues/054` が追跡する削除済み issue のパスである。**本タスクの対象外。**

**関連する既知の事実**

- `docs/03-impl/tests/` の対応表は **264 行が「未検証(テスト未実装)」**で、E2E-01〜06 は全件未検証。
  `充足` 列を「実装が満たしているか」で書くと、ほぼ全件が根拠を持たない値になる(概念4 の論点)。
- CS9(02 `PLAN-*` ⇄ 03 `MODULE-*`)は `check-changeset.py:343` が PLAN-ID をバッククォートで
  囲むことを要求するのに `02-design/relations.md` の一覧表(64行)が囲んでいないため、
  **本プロジェクトで一度も実行されていない**(`docs/issues/060` の追加節。論点2)。

## 質問キュー(未提示)

(なし)

## タスクリスト

(フェーズ2で埋める)

## Definition of Done

(フェーズ3で埋める)

## 進捗メモ

- 2026-08-06 `/task-new 060` でタスクを作成。`docs/issues/060` からの昇格。
  直前の `/doc-check full` が 00〜02 を全文読了しており、その読了記録を転記した。
  **`/doc-check full` の SSOT 修正はすべてタスク作成前に完了している**(タスクが存在すると
  原則1 により `/doc-check` は SSOT を直せなくなるため、順序を意図的にこうした)。

## 申し送り事項

- 本タスクは**記述形式の移行**であり、受入基準の意味とコードは変えない。
  意味を変える必要が出た時点で、それは別タスクの起点である。

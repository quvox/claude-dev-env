---
id: 056-modify-ssot-retains-change-relative-wording
type: modify
severity: 中
found: 2026-08-05
found_in: task-relations-code-sync フェーズ1(着手時の残件突き合わせ。SSOT を「現状記述」として読み直す過程で検出)
related: docs/03-impl/relations/MODULE-cli-reset.md, docs/03-impl/relations/MODULE-cli-stop.md, docs/03-impl/contracts/cli-container.md, docs/02-design/system.md, docs/02-design/contracts/cli-container.md, docs/issues/038
summary: 反映後の SSOT に「〜へ改める」「本変更で」という変更相対の言い回しが 8 箇所残っており、うち 1 箇所は現行実装について事実と異なることを書いている
---

## 事象

`task-fix-destructive-scope` の反映後の SSOT に、**変更指示の言い回し(変更前の状態を基準に
「これからこう改める」と書く形)がそのまま残っている**箇所が 8 箇所ある。
CLAUDE.md §1 は「SSOT は常に**いまの姿だけ**を記述する」と定めており、
「本変更」という参照先が SSOT の中に存在しない語である。

| # | 箇所 | 現在の記述 | 何が問題か |
|---|---|---|---|
| 1 | `docs/03-impl/relations/MODULE-cli-reset.md:49` | 「**現行実装は 0 を返すが**、自動実行で『何もしなかった』ことに気づけないため **1 に改める**」 | **現行実装についての記述が事実と異なる**。`claude-dev:2007`〜`:2011` は非 TTY かつ `--yes` 無しで `exit 1` する。**原則2(コード ⇄ 03-impl の一致)の侵害** |
| 2 | `docs/03-impl/relations/MODULE-cli-reset.md:94` | 「`exit 1`(…**現行の「キャンセル扱いで 0」から改める**。従来の `yes y \| claude-dev reset` は `--yes` に置き換わる)」 | 同上。結論(`exit 1`)は正しいが、同じ文が「現行 = 0」と書いており自己矛盾する |
| 3 | `docs/03-impl/relations/MODULE-cli-reset.md:158` | 「…`exit 1`。**現行の「空入力=キャンセル扱いで 0」から改めた**」 | 過去との差分の記述。現状記述としては不要 |
| 4 | `docs/03-impl/relations/MODULE-cli-reset.md:179` | 判断5「非 TTY で `--yes` が無い場合の終了コードを **0 から 1 へ改める**」 | 同上(判断の記録としては「1 とする。理由=…」で足りる) |
| 5 | `docs/03-impl/relations/MODULE-cli-stop.md:207` | 判断4「ラベル: **本変更前に起動した**既存コンテナが持たない」 | 「本変更」の参照先が SSOT に無い |
| 6 | `docs/03-impl/contracts/cli-container.md:81` | 既知の制限「**本変更より前に起動した資源は**管理ラベルも一意化された compose 名も持たない」 | 同上 |
| 7 | `docs/02-design/system.md:328` | 「`ports` / `forward` などは**本変更で制約を変えない**」 | 同上 |
| 8 | `docs/02-design/contracts/cli-container.md:348` | 「**本変更の値打ちは**『ありふれた組み合わせで確実に起きる衝突』を…」 | 同上 |

**除外したもの**: `MODULE-cli-logout.md` / `MODULE-cli-stop.md` / `MODULE-cli-reset.md` が
`「本変更より前に起動した可能性があります」`を**利用者向けメッセージの文面として引用している箇所**は
記述として正しい(`claude-dev:1091`・`:1669`、`claude-dev-mac:1159`・`:1627`・`:2083` に同じ文言が
実在する)。文面そのものが利用者にとって不明瞭であるかどうかは別の論点であり、本 issue では扱わない。

## 影響

- **#1 と #2 は現行実装について誤った事実を書いている**(「0 を返す」)。ドキュメントだけを読んで
  自動実行の終了コードを判断すると誤る。`FR-env-03` 受入基準15 は `exit 1` を要求しており、
  実装はそれを満たしているので、**誤っているのはドキュメントだけ**である。
- #3〜#8 は結論は正しく、読み手が「本変更」の指す時点を知らないと**いつを基準にした話か決められない**。
  時間の経過とともに(次の変更が入るほど)意味が失われる。
- 合格証(`verified`)は書式ではなく版の一致だけを見るため、この種の言い回しは機械検査を通過する。

## 原因の見当

**推測**: `/task-close` の SSOT 反映が、`new-features/` の変更指示の文をほぼそのまま持ち込んだ。
変更指示は「変更前の状態を基準に何を変えるか」を書く形式(`.claude/directions/change-set.md`)
なので、**その形式のまま SSOT へ移ると必ずこの残留が起きる**。
`docs/histories/2026-08-04-fix-destructive-scope.md` に相当する反映で入ったものとみられる。

## 正はどちらか

**ドキュメントが誤り**(#1・#2 はコードが正であることを `claude-dev:2007`〜`:2011` で確認済み)。
#3〜#8 は事実としては正しく、**書き方だけが SSOT の規則に反している**。
どちらも判断の余地は無いので、`D0-scope-06`(旧記述とコードの軽微な食い違いはコードを正とする)の
範囲で直せる。

## 対処案

| 案 | 内容 |
|---|---|
| A | `issue 038` / `032` の relations 全面揃えタスク(`task-relations-code-sync`)の影響範囲に**8 箇所すべて**を足す。ただし `MODULE-cli-reset` / `-stop` / `contracts/cli-container` / `02-design` の 5 ファイルは同タスクの影響範囲に**入っていない**ので、closure が 4 ファイル増える |
| B | 独立したタスクとして切る(対象 5 ファイル・8 箇所・機械的な言い換えのみ) |
| C | `#1`・`#2`(現行実装について誤っている 2 箇所)だけを先に直し、#3〜#8 は本 issue に残す |

**併せて `/kit-improve` 案件がある**: 反映のときに変更相対の言い回しを落とす手順(または検査)が
無いため同じ残留が繰り返される。`/task-close` の反映手順に「変更指示の言い回し(「改める」「本変更」
「従来は」)が SSOT に残っていないことを確認する」を入れるか、`.claude/scripts/` に走査を足すかは
キット側の判断である。**この issue はドキュメント側の残留だけを追跡する。**

## 裁定の記録(2026-08-05)

**人間の裁定: 案A(8箇所すべてを `task-relations-code-sync` の影響範囲に入れる)。**
`task-relations-code-sync` の決定シート論点6 に対する回答である(「全部推奨どおり」)。

- 推奨の根拠は `docs/feedbacks/015-partial-fixes-resurface-in-the-next-verification.md`
  (同じ層・同じ性質の乖離を部分的に切ると次の検証で必ず再浮上する。**切るなら層ごと切る**)。
  この教訓を生んだのは `issue 038` 自身の切り方である。
- 代償として **02 層(`02-design/system.md` / `02-design/contracts/cli-container.md`)の版が上がり、
  合格証の再発行が必要になる**ことを提示した上での回答である。
- **本 issue は `task-relations-code-sync` の完了時に閉じる**(`/task-close` が histories へ記録して削除)。
- **キット側の再発防止は本タスクの範囲外**: `/task-close` の反映手順に「変更指示の言い回しが SSOT に
  残っていないこと」の確認が無い点は `/kit-improve` 案件として残す(上の「対処案」末尾)。

## /doc-check(task) の追加検出(2026-08-05。裁定の後)

`/doc-check task-relations-code-sync` が合成ビューを走査したところ、**この issue の表に無い同種の
残留がさらに 15 箇所ある**ことが分かった。表の 8 箇所は「〜へ改める / 本変更で / 本変更の値打ちは」
という形だけを拾っており、**(a) 「本変更より前に起動した…」という散文**(利用者向けメッセージの
引用ではない箇所)と **(b) 「本タスク」というタスク相対の参照**を拾っていなかった。

**closure 内のファイルに残るもの(6 箇所)** — 本タスクが同じファイルを書き替えるが、
`sections:` に入っていない節にあるため反映後も残る:

| # | 箇所 | 節 | 現在の記述 |
|---|---|---|---|
| 9 | `MODULE-cli-reset.md:193` | 既知の制限 | 「**本変更より前に**起動したコンテナが残り」 |
| 10 | `MODULE-cli-reset.md:192` | 既知の制限 | 「対象範囲の拡大は**本タスク**の『やらないこと』」 |
| 11 | `MODULE-cli-stop.md:30` | 冒頭の要約 | 「残る限界は『**本変更より前に**起動した compose 資源』だけ」 |
| 12 | `MODULE-cli-stop.md:63` | 処理の流れ | 「『**本変更より前に**起動した compose 資源が残っている可能性』と…の方法」(**コードはこの文言を出力しない**ので引用ではない) |
| 13 | `MODULE-cli-stop.md:222`・`:224` | 既知の制限 | 「**本変更より前に**起動した compose 資源は旧い名前を持つため片付けられない」ほか |
| 14 | `MODULE-cli-start.md:341` | 既知の制限 | 「分割は 02 の分割定義の見直し事項であり、**本タスク**では行わない」 |

**closure 外のファイルに残るもの(9 箇所)**:

| # | 箇所 | 現在の記述 |
|---|---|---|
| 15 | `docs/01-requirements/functional.md:72` | 「(**本変更より前に**起動した既存コンテナ)」 |
| 16 | `docs/02-design/contracts/cli-container.md:144` | 「**本変更より前に**起動した Claude コンテナはラベルを持たない」 |
| 17 | `docs/02-design/contracts/cli-container.md:189` | 「**本変更より前に**起動した compose 資源は古い名前を持つため」 |
| 18 | `docs/02-design/contracts/cli-container.md:314` | 「**本変更より前に**起動した既存コンテナはラベルを持たないため」 |
| 19 | `docs/02-design/system.md:133` | 「Actions のコールグラフ抽出器を作る — **本タスク**の範囲外」 |
| 20 | `docs/03-impl/features.md:158` | 「…で報告し、**本タスク**では直さない」 |
| 21 | `docs/03-impl/relations/MODULE-cli-logout.md:248` | 「**本変更より前に**起動したコンテナは…1件ずつ止める必要がある」 |
| 22 | `docs/03-impl/relations/MODULE-cli-logout.md:252`・`:253` | 「実装を直すかは `FR-env-03` を動かす判断なので**本タスク**では決めない」×2 |
| 23 | `docs/03-impl/relations/MODULE-cli-logout.md:233` | 判断7「**本タスク**の範囲は『対象を広げること』ではなく」 |

**除外は維持する**(引用として正しいもの): `MODULE-cli-reset` の処理の流れ・異常系、
`MODULE-cli-logout.md:34`・`:211`、`docs/02-design/logging.md:82`、
`docs/01-requirements/functional.md:125`、`docs/02-design/contracts/cli-container.md:112`、
`docs/03-impl/tests/e2e.md:154` は、`claude-dev:1091`・`:1669`・`:2110` ほかが実際に出力する
文言をそのまま引用している。**ただし文言そのものが変更相対であるという事実は残る**
(利用者は「本変更」がいつを指すか知らない)。これはコード側の文言の問題で、
本 issue は「扱わない」と書いたまま**どこにも記録されていなかった**ので、ここに事実として残す。

**本タスク(`task-relations-code-sync`)で直したもの**: #1〜#8 のほかに、
`new-features/02-design/contracts/cli-container.md` の `### compose 資源の識別` 節に残っていた
「本変更より前に起動した compose 資源」1 箇所(#8 と同じ節にあった)と、
`new-features/03-impl/index.md` の `## この層の状態` に残っていた「本タスクが修正して解消した」
1 箇所(→ `task-fix-destructive-scope`)を、同じ節を書き替える範囲内の自動修正として直した。

**#9〜#23 をどうするかは人間の判断**として `docs/tasks/task-relations-code-sync/memo.md` の
決定シートに載せた。**採る案によって本 issue を本タスクの完了時に閉じられるかが変わる**
(裁定の記録は「本タスクの完了時に閉じる」と書いているが、それは 8 箇所だけを前提にしている)。

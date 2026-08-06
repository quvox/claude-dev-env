---
id: 074-modify-fr-env-01-9-has-three-owning-rows-in-test-tables
type: modify
severity: 低
found: 2026-08-07
found_in: /doc-check(task-clause-ids-and-split-policy の合成ビュー検証)
related: FR-env-01, MOD-cli-stop, MOD-cli-logout, docs/03-impl/tests/strategy.md
pattern: acceptance-criterion-row-in-more-than-one-owning-module
pattern_survey: docs/03-impl/tests/ の全30ファイルの受入基準⇄テスト対応表(FR 202行・NFR 14行)を機械照合。2ファイル以上に現れる条項は FR-env-01-9 の1件のみ(計3行)
summary: FR-env-01 受入基準9 の行が cli-stop.md に1行・cli-logout.md に2行あり、主担当1つの規則に反する
---

# 074 `FR-env-01-9` のテスト対応行が3行に重複している

## 事象

`docs/03-impl/tests/strategy.md`「状態列の語彙の定義」の直後は
「**受入基準の行は主担当モジュール1つにだけ置く。**(重複させると集計が二重になり、進捗が読めなくなる)」
と定めているが、`FR-env-01` 受入基準9(移行後の条項 ID は `FR-env-01-9`)は3行ある。

| ファイル | 行 | テスト識別子 |
|---|---|---|
| `docs/03-impl/tests/cli-stop.md` | 28 | `E2E-01(実機確認手順)` |
| `docs/03-impl/tests/cli-logout.md` | 33 | `-(実機確認手順。**`logout` 側**。E2E-01 手順8-5)` |
| `docs/03-impl/tests/cli-logout.md` | 34 | `-(実機確認手順。**`reset` 側**(docker-proxy と `claude-dev-net` の両方)。E2E-01 手順8-12)` |

3行は内容が異なる(汎用 / `logout` 側 / `reset` 側)。同じ条項を3つの観点で検証する意図が読み取れる。

再現手順:

1. `grep -n 'FR-env-01 | 9 ' docs/03-impl/tests/*.md` を実行する(移行後は `FR-env-01-9`)。
2. 3行が2ファイルに現れることを確認する。

## 影響

`build-index.py` の状態集計でこの条項が3回数えられる(`docs/03-impl/tests/index.md` の
「実装済み/未検証/対象外」の合計が受入基準の実数より2多くなる)。
また `docs/02-design/system.md` の要件カバレッジ表は1条項につき主担当をちょうど1つ書くため、
02 と 03 で主担当の対応が1対1にならない。実装・利用者への影響は無い。

## 原因の見当

推測: `FR-env-01` 受入基準9 が `stop` / `logout` / `reset` の3コマンド共通の条件であるため、
コマンドごとの対応表に別々の検証手順として書き足すうちに重複した。
`strategy.md` の主担当規則は「1条項1行」を求めており、観点ごとに行を分ける形を想定していない。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| 1条項の行数 | 3行(汎用・logout 側・reset 側) | `strategy.md` は「主担当モジュール1つにだけ置く」 | 規則(strategy.md)が正。ただし3行が持つ観点の情報を失わない形が要る |

## 対処案

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | `cli-logout.md` の2行を `cli-stop.md` の1行へ統合し、テスト識別子欄に3手順(E2E-01 手順8-5 / 8-12)を併記する | `tests/cli-logout.md` と `tests/cli-stop.md` の2ファイル。集計が1に戻る |
| B | `strategy.md` の規則を「1条項につき主担当モジュールは1つ。同一ファイル内で観点ごとに行を分けてよい」へ改める | `strategy.md` と、集計を読む `build-index.py` の解釈 |

## 経緯

- 2026-08-07 起票。`task-clause-ids-and-split-policy`(条項ID への移行)の `/doc-check` で、
  02 の条項単位カバレッジ表が主担当を1つに決める必要が生じたときに表面化した。
  同タスクは記述形式の移行(機械的置換のみ)であり、行の統合は範囲外としたため別issueとした。
  同タスクの決定シート 論点4 が「今回は行を動かさず 02 の主担当を `MOD-cli-stop` に確定し、
  解消は本issueで追跡する(既定 A)」を人間に問うている。**論点4 が B(今回統合する)で
  回答された場合、本issueはそのタスクで解消され削除される。**

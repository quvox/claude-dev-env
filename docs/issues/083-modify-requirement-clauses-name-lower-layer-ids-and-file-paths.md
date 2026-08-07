---
id: 083-modify-requirement-clauses-name-lower-layer-ids-and-file-paths
type: modify
severity: 中
found: 2026-08-07
found_in: 規範更新後の再検査(check-changeset.py --ssot docs の CS18。新設された検査)
related: FR-env-01, FR-env-03, FR-env-07, FR-orch-01, FR-orch-05, NFR-perf-03, NFR-sec-01, UC-02, CTR-cli-container, CTR-orchestrator-prompt, MODULE-firewall-init, MODULE-orchestrator-claude-exec, docs/01-requirements/functional.md, docs/01-requirements/non-functional.md, docs/01-requirements/usecases.md, .claude/directions/01-requirements.md
pattern: requirement-states-the-mechanism-instead-of-the-observable
pattern_survey: docs/01-requirements/ の全4ファイル(functional.md / non-functional.md / usecases.md / system.md)を check-changeset.py --ssot docs の CS18 で走査し 27 件。system.md は規範により対象外(技術を名指すことがその文書の目的)。うち 11 件は task-stop-session-spawned-containers が置き換える3節(FR-env-01 / FR-env-03 / FR-env-07)の中にあり、人間の指示(2026-08-07)で同タスクの変更指示の中で移した。**残るのは 16 件**(FR-orch-* / NFR-* / usecases.md)。あわせて同タスクが触る 00-requests/decisions/env.md と terminology.md、02-design の全変更指示を目視で走査した(CS18 は 01 しか見ない): 00 に 5 件あり同じ指示の中で移した / 02 には実装識別子が 0 件(関数名・main.go・行番号・出力書式を全文検索)。**docs/00-requests/ の他のファイルと docs/01-requirements/decisions/ 以外の残りは未走査**
summary: 要件(01)の条項が下位層の ID(CTR-* / MODULE-*)と実装のファイル名を直接名指しており、実現方式を差し替えると偽になる文が 16 箇所残っている(FR-orch-* / NFR-* / usecases.md。FR-env-* と 00 の分は移し済み)
---

# 083 要件の条項が下位層の ID と実装のファイル名を名指している

## 症状

`.claude/directions/01-requirements.md` が定める **置き換えテスト**(実現方式を丸ごと別のものに
差し替えても、その文はまだ真であってほしいか)と **観測者テスト**(システムの内側を見ずに
確かめられるか)に、`docs/01-requirements/` の 27 箇所が掛からない。検査は **CS18**
(`check-changeset.py --ssot docs`)。この検査は 2026-08-07 の規範更新で新設されたもので、
**該当箇所は以前からあり、今回はじめて機械に見えた**。

代表例(全件は下の一覧):

| # | 場所 | 原文の該当部分 | どちらのテストに落ちるか |
|---|---|---|---|
| 1 | `docs/01-requirements/functional.md:92`(`FR-env-01-14`) | 「名前と値は `CTR-cli-container` が定める」 | 置き換えテスト。ラベル以外の識別方式にすると文が意味を失う |
| 2 | `docs/01-requirements/functional.md:132`(`FR-env-03-1`) | 「`.credentials.json` / `.claude.json`」 | 観測者テスト。ファイル名は内側を見ないと確かめられない |
| 3 | `docs/01-requirements/functional.md:180`(`FR-env-05`) | 「`MODULE-firewall-init`」 | 置き換えテスト。03 の機能 ID が要件に在る |
| 4 | `docs/01-requirements/non-functional.md:64`(`NFR-perf-03`) | 「`MODULE-orchestrator-claude-exec`」 | 同上 |
| 5 | `docs/01-requirements/usecases.md:54` | 「`.claude-dev.yaml`」 | 観測者テスト |

## なぜ問題か

機構が要件として書かれると、**それは「要件」なので細部まで人間の合意が要る判断に化ける**
(`.claude/directions/delegation.md` §0)。`CTR-cli-container` がラベルの名前を変えるだけの
02 層の変更が、01 の条項の書き換えを伴うことになり、変更のたびに人間の承認が要る範囲が広がる。
逆に 01 が「外から見える結果」だけを持てば、実現方式の差し替えは 02/03 の中で完結する。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| ラベルの名前・値 | `CTR-cli-container` と `MODULE-cli-*` が定義と参照を持つ | 01 が「`CTR-cli-container` が定める」と 02 を名指している | **要件・設計が正**(機構は 02/03 に在り、01 はそれを名指すべきではない) |
| 認証ファイルの名前 | `MODULE-entrypoint-claude` と `03-impl/contracts/` が持つ | 01 が具体名を列挙している | **要件・設計が正**(01 は「認証が引き継がれること」だけを述べればよい) |

**これは実装の誤りではない。** 01 の記述の位置の問題であり、コードは1行も動かない。

## 決着済みの 11 件(2026-08-07。この issue の対象から外れる)

人間の指示「下位の階層に書くべきものは全て移動する」により、
**`task-stop-session-spawned-containers` が置き換える3節の中にあった 11 件は同タスクの
変更指示で移した**(`FR-env-01-14` / `-19` / `FR-env-03-1` / `-4` / `-6` / `-7` / `-17` / `-20` /
`-22` / `FR-env-07-5`。理由と移し先の確認は
`docs/tasks/task-stop-session-spawned-containers/new-features/01-requirements/functional.md` の
`reason`)。**この issue が追跡するのは、そのタスクが触らない節に残る 16 件と、00 の2件である。**

## 00-requests の同型4件は、同じタスクの変更指示で移した(**人間の確認対象**)

`docs/00-requests/decisions/env.md` の該当4箇所は、**すべて
`task-stop-session-spawned-containers` が置き換える節(`D0-env-05` / `D0-env-08`)の中**にあり、
人間の指示(2026-08-07)により同タスクの変更指示で移した。

| 場所(SSOT 側。反映前) | 落とした記述 | 移し先 |
|---|---|---|
| `docs/00-requests/decisions/env.md`(`D0-env-05` 項1) | `COMPOSE_PROJECT_NAME` | 次の文が既に指す `CTR-cli-container` |
| 同(`D0-env-05` 項2。本タスクが書いた行) | `docker rm -f` 相当 | `CTR-cli-container` / `MODULE-cli-stop` |
| `docs/00-requests/decisions/env.md:138`(`D0-env-08` 項1) | `docker ps --filter ancestor=...` | `docs/02-design/contracts/cli-container.md:310`(同じ禁止をコマンドつきで持つ) |
| `docs/00-requests/decisions/env.md:169`(`D0-env-08` 項4) | 認証ファイル3件の列挙 | `MODULE-cli-logout`(実ファイル名を持つ) |

**00 は人間の層である**(`.claude/directions/00-requests.md`「This layer is the human's」)。
**決定の意味は1つも変えていない**(落としたのは「どうやるか」だけ)が、**反映前に差し戻せるよう
理由を変更指示の末尾コメントに残してある**。差し戻す場合は
`docs/tasks/task-stop-session-spawned-containers/new-features/00-requests/decisions/env.md` を直す。
**`docs/00-requests/` の他のファイル(`request.md` / `acceptances.md` / 他カテゴリの `decisions/`)は
走査していない** — このタスクが触らないためで、同じ観点での全数走査は別タスクになる。

## 全件(残り 16 件 / 走査時点は 27 件)

`python3 .claude/scripts/check-changeset.py --ssot docs` の CS18 の出力がそのまま全件である
(行番号つき)。内訳:

- **下位層の ID(残り4件)**: `functional.md:180`(`MODULE-firewall-init`)/
  `functional.md:369` `:436` `:453`(`CTR-orchestrator-prompt`)/ `non-functional.md:41`
  (`CTR-orchestrator-prompt`)/ `non-functional.md:64`(`MODULE-orchestrator-claude-exec`)
  — **`FR-env-*` の4箇所(`:92` `:97` `:232` と `FR-env-03-17`)は移し済み**
- **実装のファイル名・パス(残り12件)**: `functional.md:153` `:167` `:168` `:169` `:172`
  (`.claude-dev.yaml`)/ `:398`(`~/.config/claude-dev.yaml` / `<workspace>/.orchestrator/config.yaml`)/
  `:436`(`plan.json` / `state.json` / `intervention/open.json` / `control.json`)/
  `usecases.md:54`(`.claude-dev.yaml`)
  — **認証まわりの7件(`:132` `:135` `:137` `:138` `:151`)は移し済み**
- **注意**: 行番号は走査時点(2026-08-07、`task-stop-session-spawned-containers` の反映前)のもの。
  反映後は `check-changeset.py --ssot docs` を流し直して取り直すこと

## どう直すか(案)

**1件ずつ判断が要る。一括置換はできない。** 3通りのどれかになる:

1. **層の名指しに置き換える** — 「名前と値は `CTR-cli-container` が定める」→「名前と値は 02 の
   契約が定める」。本タスク(`task-stop-session-spawned-containers`)が新しく書いた3箇所は
   この形で直した。**下位層の ID 8 箇所はすべてこれで済むと見込む**。
2. **観測できる言い方へ書き直す** — 「`.claude-dev.yaml` に指定された鍵を使う」→「利用者が
   プロジェクトごとに指定した鍵が使われること」。ファイル名 19 件の多くはこれで、**条項の意味を
   変えないことの確認が要る**(利用者にとって設定ファイル名そのものが外部インターフェースで
   ある場合は、名前が要件として正しい — `.claude-dev.yaml` はその可能性がある)。
3. **要件ではないと判断して 02/03 へ移す** — 移す先が既にその事実を持っているかを確かめる。

**2 の判断は 01 の意味に触れるので、タスクとして起こして決定シートに載せる**
(`.claude/directions/delegation.md` §1 の問う基準の例外「00/01 の意味を変える編集」)。

## 影響範囲

- `docs/01-requirements/functional.md` / `non-functional.md` / `usecases.md`
- 波及: 条項の**本文だけ**が変わり、**条項 ID は1つも動かない**(CS16)。02 のカバレッジ表・
  03 のテスト対応表は条項 ID で参照しているので影響を受けない
- `docs/issues/072`(実装者が値を発明するしかない箇所)と向きが逆の欠陥である
  (072 は「書かれていない」、本件は「書きすぎている」)

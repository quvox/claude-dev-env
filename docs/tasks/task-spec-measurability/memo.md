---
id: task-spec-measurability
phase: 反映
origin_layer: 00
issue: docs/issues/043-modify-nfr-targets-do-not-measure-whole-requirement.md
date: 2026-08-04
updated: 2026-08-05
source:
  - docs/00-requests/request.md
  - docs/00-requests/terminology.md
  - docs/00-requests/acceptances.md
  - docs/00-requests/decisions/scope.md
  - docs/00-requests/decisions/sec.md
  - docs/00-requests/decisions/env.md
  - docs/00-requests/decisions/orch.md
  - docs/00-requests/decisions/auth.md
  - docs/00-requests/decisions/dist.md
  - docs/01-requirements/functional.md
  - docs/01-requirements/non-functional.md
  - docs/01-requirements/usecases.md
  - docs/01-requirements/system.md
  - docs/02-design/architecture.md
  - docs/02-design/system.md
  - docs/02-design/logging.md
  - docs/02-design/relations.md
  - docs/02-design/contracts/entrypoint-firewall.md
  - docs/03-impl/relations/MODULE-firewall-init.md
  - docs/03-impl/relations/MODULE-vm-mode-healthd.md
  - docs/03-impl/relations/MODULE-vm-mode-cli.md
  - docs/03-impl/relations/MODULE-makefile-update-claude.md
  - docs/03-impl/relations/MODULE-hooks-save-prompt.md
  - docs/03-impl/relations/MODULE-hooks-send-slack-message.md
  - docs/03-impl/relations/MODULE-container-tools-wait-limit-reset.md
  - docs/03-impl/features.md
  - docs/03-impl/index.md
  - docs/03-impl/tests/firewall.md
  - docs/03-impl/tests/images.md
  - docs/03-impl/tests/orchestrator.md
  - docs/03-impl/tests/cli-login-codex.md
summary: 仕様を測定可能にする(NFR-sec-02 と NFR-ops-01 の廃止 + issue 043 の残り3件 + 017 の測定不能語 + 041 のブロック対象 + 042/049 の AC-02 + 044 の用語定義)
---

<!-- タスクの背骨。フェーズ1で作られフェーズ4で削除されるまで、このファイルだけで
     どのフェーズからでも再開できること(/clear を挟んでも)。
     ・仕様ドキュメントではない(version / verified を持たない)
     ・未決点はここに置く。仕様ドキュメントには絶対に書かない
     ・削除は /task-close の機械ゲート経由(close-task.py)。rm 禁止 -->

# task-spec-measurability 仕様を「測れる」形にする

> 解決済みの経緯: `memo-1.md`(1本目・2本目からの申し送り。2026-08-05 の再実測で消化済み)

## 目的

**「形は整っているが測れない」記述を全部閉じる。** `/doc-check` が繰り返し検出してきた同型の欠落で、
5つの issue が同じ性質を持つ。

| issue | 内容 | severity |
|---|---|---|
| `043` | **NFR 5件**(`NFR-perf-02` / `sec-03` / `ops-01` / `ops-04` / `scale-02`)で、「要件」列が述べる内容の一部しか「目標値」「測定方法」列が測っていない(**2026-08-05 の裁定で `ops-01` は削除されるので対象は4件**) | 中 |
| `017` | 測定不能語が残る(起票時 28 箇所。**2026-08-05 の再実測で残存 10 箇所** + `資源逼迫` の下降先 6 箇所) | 低 |
| `041` | `NFR-sec-02` と `FR-env-05` #4・#6 が参照する「**ブロック対象ドメイン**」の集合が 00・01 のどこにも無い | 中 |
| `042` | `AC-02`「`start` しただけではポートが公開されていない」が **既定構成(`USE_VNC=1`)で成立しない** | 中 |
| `044` | `terminology.md` 1.1.0 の「資源逼迫」の閾値定義が**承認済み(案A′)だが下降していない** | 中 |
| `049` | `AC-02` が例外なしで要求する「ポート非公開」が、`AC-01` / `D0-env-02` の noVNC ポート公開と矛盾する(**`042` と同一事象の別起票**。前タスクの申し送りで本タスク担当) | 中 |

起点層は **00**(`terminology.md` の用語定義、`acceptances.md` の `AC-02`、`decisions/scope.md` の
`D0-scope-06` の委任範囲が起点になる)。`decisions/sec.md` は**検証履歴コメントだけ**を触る
(`D0-sec-04` の委任本文は変えない = `041` 案D の前提)。

## やること・やらないこと

**2026-08-05 の決定シートで範囲が変わった(★重要)**: 人間の裁定により
**`NFR-sec-02` と `NFR-ops-01` を要件から削除**する(理由:「その品質特性自体を本システムでは
追わない」)。`043` の対象は5件から**3件**(`NFR-perf-02` / `NFR-sec-03` は測定可能化、
`NFR-ops-04` / `NFR-scale-02` は「測らない」明記)へ縮み、代わりに**2要件の削除に伴う下降**が増えた。
また `request.md:7` の枕詞「安全な」を落とし、**`terminology.md` に「安全」の定義を追加**する。

| 種別 | 内容 |
|---|---|
| やること(追加分) | **`NFR-sec-02` を削除**する(`FR-env-05` は残すので、「ブロック対象ドメイン」の定義は `FR-env-05` 受入基準4・6 側へ書き `041` をそこで閉じる)/ **`NFR-ops-01` を削除**し、それだけが根拠になっている記述(`02-design/logging.md` の追記型ログ2行 `dispatch` / `result`)も要件・設計の裏付けから外す / **`terminology.md` に「安全」を追加**(人間の定義: ホストのあらゆる情報を破壊しないこと、鍵情報が直接漏洩しないこと。ただし claude や codex のログイントークンのような一過性のものは除く)/ `request.md:7` の枕詞「安全な」を落とす |
| やること | `044` の裁定(**案A′ = 承認 + 00 から環境変数名を落とす**)を下降させ、`FR-env-08` #4 と 02 の5箇所を用語集参照へ揃える / `041` を**案D**(01 で「設定で与えられる集合」と定義し、既定の内訳を 03 に列挙)で閉じる / `042` と `049` を**案A**(`AC-02` を Web アプリ用ポートに限定)で閉じる / `043` の5件の目標値・測定方法を要件本文の全体に合わせる(論点1)/ `017` の残る測定不能語を実装の条件へ置換 / **`terminology.md` に「破壊的操作」「管理ラベル」の2行を追加する**(1本目 `task-fix-destructive-scope` からの引き継ぎ。**2026-08-05 に未追加であることを実測**)/ `terminology.md` に合格証を発行できる状態にする |
| やらないこと | **コードの変更**(すべて記述の精密化。`041` で許可リストへ変える案 C は採らない)/ `NFR` の目標値を**新しく厳しくすること**(現状を測れるようにするだけ)/ `docs/issues/006`(E2E 手順の再現性)と `P-003`(QA レーン)— 別件 / **`docs/issues/056` の残り8箇所**(コードが実際に出力する文面の逐語引用なので、ドキュメントだけ直すと原則2 を破る。コード修正タスクが要る)/ **`057` / `058` / `059`**(いずれもコード修正が要る。`059` の「`tests/orchestrator.md:67` を未検証へ落とすか」の人間判断も本タスクの対象 issue ではないので混ぜない = 原則8)/ **`docs/issues/054` そのものの解消**(参照表記の規約はキット側の案件。本タスクは新しい宙吊り参照を作らないだけ)/ **削除した2 NFR に相当する品質特性を別の形で書き直すこと**(人間の裁定は「追わない」であり、置き換えではない) |

## 影響範囲(closure)

**2026-08-05 に確定**(タスクリスト0番の再実測 → 決定シートの回答による拡張)。**★条件付きの行は無い**
(概念#5 で `request.md` が確定し、`NFR-sec-02` / `NFR-ops-01` の削除で `tests/` 4本も確定した)。

| 層 | SSOT のパス | 変更指示のパス | 変更の種類 |
|---|---|---|---|
| 00 | docs/00-requests/terminology.md | new-features/00-requests/terminology.md | replace(**★起点**。`044` の案A′: 定義から環境変数名を落とし「既定値。上書き手段は 03-impl」とする + 冒頭コメントの `017`/`043`/`044` 参照を整理) |
| 00 | docs/00-requests/acceptances.md | new-features/00-requests/acceptances.md | replace(**★起点**。`042`/`049` の案A: `AC-02` の期待結果と不合格条件を「利用者の Web アプリ用ポート」に限定し noVNC を `D0-env-02` の例外として明記) |
| 00 | docs/00-requests/decisions/scope.md | new-features/00-requests/decisions/scope.md | replace(`D0-scope-06` の見出しと委任範囲の「軽微な」2箇所 = `:80`・`:84`。**委任の外延を変えるので概念シート #3 の回答で内容が決まる**) |
| 00 | docs/00-requests/decisions/env.md | new-features/00-requests/decisions/env.md | replace(`:106` の理由文「環境依存の分岐を安全に行える」= `017` 残件) |
| 00 | docs/00-requests/decisions/sec.md | - | 本文は**変更なし**(`D0-sec-04` の委任は案D の前提なので触らない)。`:29` の**検証履歴コメント**が `docs/issues/041` を参照しており、本タスクが 041 を削除すると宙に浮く。**コメントは `/doc-check` が書いた `/doc-check` の持ち物**なので変更指示の対象にせず、認証時に更新する(委任 c) |
| 00 | docs/00-requests/request.md | new-features/00-requests/request.md | replace(**確定**。概念#5 の回答=枕詞は不要。`:7` の目的文と frontmatter `summary` から「安全な」を落とす。**MINOR 相当なので下流の合格証が失効する**) |
| 00 | docs/00-requests/decisions/orch.md | new-features/00-requests/decisions/orch.md | replace(**2026-08-05 フェーズ3 で訂正**。旧版は「変更指示のパス = `-`・本文は変更なし」と書いていたが、`:108` の `関連: FR-orch-07 / NFR-ops-01` から1語を外すのは**本文の変更**であり、フェーズ2 は正しく変更指示を書いていた。表だけが追随していなかった。節は `## D0-orch-07 通知の失敗許容`、決定の内容は変えない)+ `request.md` の MINOR に伴う**合格証の再発行**が要る |
| 00 | docs/00-requests/decisions/auth.md | - | 本文は変更なし。`request.md` の MINOR に伴う**合格証の再発行**が要る(`source` に `request.md` を持つため) |
| 00 | docs/00-requests/decisions/dist.md | - | 同上(合格証の再発行のみ) |
| 01 | docs/01-requirements/functional.md | new-features/01-requirements/functional.md | replace(`FR-env-08` #4 を用語集参照へ / `FR-env-05` #4・#6 の「ブロック対象ドメイン」を定義付きへ / `FR-orch-02` #3 の「必要な文脈だけ」/ 冒頭コメント `:40`〜`:42`) |
| 01 | docs/01-requirements/non-functional.md | new-features/01-requirements/non-functional.md | replace(**★最大の変更**。`NFR-sec-02`(`:60`)と `NFR-ops-01`(`:67`)の**行を削除** + `043` の残り3件(`NFR-perf-02` / `NFR-sec-03` を測定可能化、`NFR-ops-04` / `NFR-scale-02` を「測らない」明記)+ 冒頭コメント `:23`〜`:27`) |
| 01 | docs/01-requirements/usecases.md | new-features/01-requirements/usecases.md | replace(`:98` の事後条件「安全な操作のみが Docker Engine に届いている」を `FR-env-07` の拒否規則参照へ + `:131`・`:234` の `NFR-ops-01` / `NFR-sec-02` 参照を外す) |
| 01 | docs/01-requirements/system.md | - | 本文は**変更なし**。`request.md` の MINOR に伴う**合格証の再発行**が要る(`source` に `request.md` を持つため) |
| 02 | docs/02-design/architecture.md | new-features/02-design/architecture.md | replace(`:87` の「資源逼迫」を用語集参照へ + `:81`(firewall)から `NFR-sec-02`、`:85`(hooks)・`:86`(container-tools)から `NFR-ops-01` を外す。**`:86` は `NFR-ops-01` が唯一の要件なので `FR-env-01` へ差し替える**(`system.md:64` が根拠)) |
| 02 | docs/02-design/system.md | new-features/02-design/system.md | replace(`:61` の `MOD-vm-mode` 責務の「資源逼迫」+ `:58`・`:61`・`:63`・`:64` の要件列から2 NFR を外す + **要件カバレッジ表 `:177`(NFR-sec-02)と `:179`(NFR-ops-01)の行を削除**) |
| 02 | docs/02-design/logging.md | new-features/02-design/logging.md | replace(`:102` の「検知した指標と閾値」を用語集の定義で確定 + `:129` + `:69`・`:107` の「必要な範囲を超えて出さない」+ **`:97`・`:98`(`dispatch` / `result`)は `NFR-ops-01` が唯一の対応要件なので、その扱いが未決点#1**) |
| 02 | docs/02-design/relations.md | new-features/02-design/relations.md | replace(`:99` `PLAN-vm-mode-healthd` の「資源逼迫」+ `:92` `PLAN-makefile-update-claude` の「高速更新」+ `:70`・`:74`・`:75`・`:98`・`:99` の要件列から `NFR-ops-01` を外す) |
| 02 | docs/02-design/contracts/entrypoint-firewall.md | new-features/02-design/contracts/entrypoint-firewall.md | replace(`:21` の検証履歴コメント + `:27` の「対応要件: FR-env-05, NFR-sec-02」から `NFR-sec-02` を外す) |
| 02 | docs/02-design/environments.md | - | **変更なし**(理由: lint/テストの実コマンドは変わらない。コード差分が空のタスクである) |
| 03 | docs/03-impl/relations/MODULE-firewall-init.md | new-features/03-impl/relations/MODULE-firewall-init.md | replace(`041` 案D: 既定リストの内訳をカテゴリとともに列挙。**実測 = 有効16件**(paste 系9 / webhook テスト系3 / トンネル系4)+ 本番環境の雛形2件はコメントアウト。**旧 memo の「20件」は誤り**) |
| 03 | docs/03-impl/relations/MODULE-vm-mode-healthd.md | new-features/03-impl/relations/MODULE-vm-mode-healthd.md | replace(`:21`・`:89` の `RAM 逼迫` を定義のある語へ + frontmatter `requirements` から `NFR-ops-01` を外す) |
| 03 | docs/03-impl/relations/MODULE-vm-mode-cli.md | new-features/03-impl/relations/MODULE-vm-mode-cli.md | replace(frontmatter `requirements` と `:21` から `NFR-ops-01` を外す) |
| 03 | docs/03-impl/relations/MODULE-hooks-save-prompt.md | new-features/03-impl/relations/MODULE-hooks-save-prompt.md | replace(frontmatter `requirements` から `NFR-ops-01` を外す) |
| 03 | docs/03-impl/relations/MODULE-hooks-send-slack-message.md | new-features/03-impl/relations/MODULE-hooks-send-slack-message.md | replace(同上) |
| 03 | docs/03-impl/relations/MODULE-container-tools-wait-limit-reset.md | new-features/03-impl/relations/MODULE-container-tools-wait-limit-reset.md | replace(frontmatter `requirements` と `:22` から `NFR-ops-01` を外す。**`FR-env-01` が残る**ので機能自体は要件の裏付けを失わない) |
| 03 | docs/03-impl/relations/MODULE-makefile-update-claude.md | new-features/03-impl/relations/MODULE-makefile-update-claude.md | replace(`:14` frontmatter `summary` の「高速更新」。**`017` が本タスクの closure に含めよと明記**) |
| 03 | docs/03-impl/features.md | new-features/03-impl/features.md | replace(`:76`・`:102` の概要列。上の MODULE 2本の `summary` に追随する) |
| 03 | docs/03-impl/relations/index.md | - | **生成物**。`build-index.py` が MODULE の `summary` から再生成する(`:63`・`:89`) |
| 03 | docs/03-impl/index.md | - | **変更指示を書かない**(`.claude/directions/03-impl.md`:「`index.md` は生成物。絶対に書かない。変更指示の `target:` にもならない」)。`/task-close` §2 と `/doc-check` が書く: relations 層の合格証の再発行 / 冒頭コメントの検証履歴 / **「01(要件)との差異」表から `NFR-ops-01` をキーにした行を削除**(未決点#4・タスクリスト5番) |
| 03 | docs/03-impl/tests/firewall.md | new-features/03-impl/tests/firewall.md | replace(`:30`・`:51` の `NFR-sec-02` の行を**削除**する。`FR-env-05` の行は残る) |
| 03 | docs/03-impl/tests/images.md | new-features/03-impl/tests/images.md | replace(`:42`・`:74` の `NFR-perf-02`。測定方法の具体化に追随する) |
| 03 | docs/03-impl/tests/orchestrator.md | new-features/03-impl/tests/orchestrator.md | replace(`:89`・`:165` の `NFR-ops-01` の行を**削除** + `:88` `NFR-sec-03` は測定可能化に追随 + `:90` `NFR-ops-04` を「測らない」へ) |
| 03 | docs/03-impl/tests/cli-login-codex.md | new-features/03-impl/tests/cli-login-codex.md | replace(`:29`・`:49` の `NFR-scale-02` を「測らない」へ) |
| 03 | docs/03-impl/tests/e2e.md | - | **変更なし**(理由: NFR の測定方法は既存の E2E-01/04/06 の実機確認手順を指すだけで、シナリオは増えない。増やす案を採るなら `02-design/system.md` の E2E 一覧が起点になる) |

**層ごとの「触らない」判定**: `01-requirements/system.md` と `02-design/environments.md` は変更なし
(上表に理由を記載)。`docs/03-impl/contracts/` は変更なし(**理由**: 本タスクは契約の項目・型・
エラーを変えない。`CTR-entrypoint-firewall` は 02 側の検証履歴コメントだけを触る)。

## 決定シート(回答済み → `memo-2.md` へ転出)

**2026-08-05 に人間が回答し、`decisions/` と `new-features/` へ反映済み。**
回答の全文・根拠の三方向・削除の波及の実測は **`memo-2.md`** にある(逐語)。
運用に効く結論は上の「やること・やらないこと」と「影響範囲(closure)」が持っているので、
この節を読み返さずに次フェーズへ進んでよい。

- 覆された3件: 概念#2(`NFR-sec-02` を削除)/ #5(`request.md` の枕詞を削除し「安全」を定義)/
  #6(`NFR-ops-01` を廃止)。理由は共通で「**その品質特性自体を本システムでは追わない**」。
- 論点1〜5 と委任 a・b・c は空欄 = 既定を適用(1=B / 2=D / 3=A / 4=A′ / 5=A、委任は3件とも承認)。

## 決定シートの追加回答(フェーズ2末。`sheet.md` 論点#6)

**2026-08-05、人間が会話で「A」と回答した**(`sheet.md` の「★人間の記入」列は AI が書かない規約の
ため空のまま。**この節が回答の正である**。シートの「未回答時の既定 B」は適用しない)。

- **論点**: `/doc-check` の実行で独立レンズが1本も立たなかった(Codex が利用上限。復旧 2026-08-11)。
- **回答: A = サブエージェントで代替して `/doc-check` をやり直す。**
- **適用範囲**: CLAUDE.md 不変則7 のとおり、この承認は**やり直す `/doc-check` の1実行に限る**。
  次の実行・次のフェーズ(`/implement` / `/task-close`)には持ち越さない。
- **記録すべきこと**: レポートには **`lens: subagent`** と、実際に使ったモデルを明記する
  (Codex の監査として提示しない)。

## 決定シートの回答(フェーズ3末。2026-08-05)

**人間が「既定でいい」と回答した。** 論点1〜4 はすべて既定 = A を適用する。
論点5 は本タスクの範囲外なので `docs/issues/065` のまま保留する。

| # | 論点 | 回答 | 適用したこと |
|---|---|---|---|
| 1 | DoD 5 が達成不能だった | **A**(訂正版 5a/5b を採る) | DoD 5 は訂正済み。**タスクリスト7番は広げない**(014・026・061 の本文は触らない) |
| 2 | E2E を実行していない | **A**(実行しないまま `/task-close` へ) | `environments.md:132` の「QA = 無効(未運用)」と**コード差分が空**であることが根拠。実施しなかった事実は histories に残す |
| 3 | `terminology.md` の合格証が無いままフェーズ3 に着手した | **A**(既知として進む) | `/task-close` が合格証を発行する = DoD 4 |
| 4 | CS2 の既知の誤検出1件を残す | **A**(残して進む) | `.claude/improvements/KIT-changeset-cs2-closure-and-deletes-as-sections.md` が追跡する |
| 5 | レンズ代替方針の置き場(`docs/issues/065`) | **保留** | 本タスクの範囲外。issue のまま次の判断を待つ |

**回答による文書の変更は無い**(4件とも既定 = フェーズ3 で既に適用済みの内容)ため、
変更指示 26 件はこの回答で1文字も変わらない。よって `/task-close` の反映・認証へそのまま進める。

## 未決点

**8件すべて帰着した。逐語は `memo-3.md` にある。** 運用に効く帰着は次のとおり:

- **`/task-close` が引き継ぐ手順が3件** → タスクリスト **5番**(`03-impl/index.md` の差異表)/
  **6番**(`decisions/sec.md:29` の検証履歴コメント)/ **7番**(`docs/issues/014`・`026` の
  `related:`)。この3行が唯一の追跡先である。
- **キット側の課題が3件** → `.claude/improvements/KIT-changeset-cs2-closure-and-deletes-as-sections.md`
  (CS2 が部分的な relations 編集を原理的に通せない / CS9 が一度も走っていない)と
  `KIT-callgraph-output-during-task.md`(staged コールグラフと CS1 が同時に成立しない)。
  **本タスクではドキュメントを歪めて通すことはしない。**
- **ドキュメント記載で解決済みが2件** → 追記型ログ `dispatch` / `result` は「対応要件: なし」と
  明記して `docs/issues/061` で追跡(#1)/ 用語「安全」は `NFR-sec-01` と `D0-env-08` を
  参照する形にして観測可能にした(#3)。`request.md` の MINOR による合格証の失効(#2)は
  closure に計上済み。

## 調査メモ

- `044` の裁定は済んでいる(2026-08-04、案A′)。残作業は `docs/issues/044` の「経緯」に
  (a)〜(e) として列挙済み。閾値は `scripts/vm-healthd.sh:28`〜`:30`(既定 15 / 60 / 12)。
- `041` の実装: `scripts/init-firewall-claude.sh:38`〜`:64` に**有効16件**
  (paste 系9 / webhook テスト系3 / トンネル系4)+ 本番環境の雛形2件はコメントアウト。
  **「既定20件」と書いていた旧版は誤りで、2026-08-05 の再実測で 16 件に訂正した**
  (雛形2件は配列要素ではなくシェルのコメントなので `${#BLACKLIST_DOMAINS[@]}` は 16)。
  `MODULE-firewall-init.md:61` は「設定は環境変数ではなくスクリプト内配列 `BLACKLIST_DOMAINS` を編集する」と記述済み。
- `042` の実装: `claude-dev:695`(`USE_VNC=1` が既定)/ `:846`〜`:848`(`-p <6080番台>:6080`)/
  `:929`〜`:934`(競合時は別ポートで最大20回再試行)。**`tests/` に `AC-02` を検査する行は無い**。
- `043` の5件は `docs/issues/043` の表が「要件が述べていること / 測っていること / 測られていない部分」の
  3列で整理済み。
- `017` は 28 行の表で、各行に `path:line` と該当語が入っている。**「資源逼迫」7箇所は `044` の
  下降で測定不能語ではなくなる**(同 issue に明記済み)。


> 日付つきの調査節(2026-08-05 の再実測 / フェーズ2 独立レンズの指摘と裁定 / フェーズ2 パス2 /
> `/doc-check` 2回目のパス2)は **`memo-3.md` へ転出した**。実測値はすべて変更指示 26 件の
> 本文へ書き込み済みで、再開に必要な結論は上の箇条書きと「影響範囲(closure)」表が持つ。

## 質問キュー(未提示)

| # | 質問 | 前提 | いつ聞くか |
|---|---|---|---|
| 1 | ~~`NFR-ops-01` の廃止で要件の裏付けを失う追記型ログ `dispatch` / `result` の扱い~~ | **提示不要になった**。未決点#1 の方針(行は残し「対応要件: なし」と明記し、事実を `docs/issues/061` で追跡)がそのまま採れたため。**質問キューは空である** | — |

**独立レンズについて(記録)**: フェーズ2 のドライランで `/codex-audit readiness` を起動したが、
Codex が利用上限(復旧 2026-08-11)で `audit_failed(unavailable)` になった。
**人間が代替を承認した**ため、CLAUDE.md 不変則7 の手順どおりサブエージェント
(`Explore` / `sonnet`。reasoning は Agent ツールに指定口が無いのでセッションの値)で
同じ依頼を実行した。**レンズは `subagent` であって Codex ではない**。
この承認は `/task-doc` の本実行に限る(次の実行・次のフェーズには持ち越さない)。

**2026-08-05 フェーズ3 で承認の範囲が変わった(★以後はこちらが正)**: 人間が
「**今後、codex が利用できない時は subagent を使って**」と**常設で**指示した。
以後は実行のたびに決定シートで問い直さない。ただし省略してよいのは「問うこと」だけで、
(a) まず Codex を実際に起動して不可を確認する、(b) レポートに `lens: subagent` と実モデル名を
明記する、(c) レンズ自体は省略しない、の3つは残る。経緯と一般化した学びは
`docs/feedbacks/022`、規範化の要否は `docs/issues/065` が追跡する。

## タスクリスト

- [x] 0. **着手時**: 1本目・2本目の反映後の SSOT に対して `017` / `043` の残件を再確認し closure を確定する
      (2026-08-05 完了。結果は「調査メモ」の再実測節、確定した closure は「影響範囲」表)
- [x] 1. `/task-doc task-spec-measurability`(00→03 の1回の下降) _Depends:_ 0, 決定シートの回答
      (2026-08-05 完了。変更指示 26 ファイル。`check-changeset.py` は CS2 の既知の誤検出1件を除き OK)
- [x] 2. `/doc-check task-spec-measurability` が PASS _Depends:_ 1
      (2026-08-05 PASS。新しい文脈のサブエージェントが実行し、重大度「高」1件を含む4件を自動修正した)
- [x] 3. `/implement task-spec-measurability`(**コードは変えない**。記述のみ) _Depends:_ 2
      (2026-08-05 完了。コード差分は空のまま。自動修正1件・memo の訂正3件・新規 issue 1件)
- [ ] 4. `/task-close task-spec-measurability` _Depends:_ 3
- [ ] 5. **`/task-close` の中で `docs/03-impl/index.md` を更新する**(未決点#4)。
      「01(要件)との差異」表から `NFR-ops-01` をキーにした行を削除し(追跡は
      「02 との差分」の `docs/issues/014` の行が引き継ぐ)、relations 層の合格証を再発行する。
      **`index.md` は生成物なので変更指示を書いていない** — この行が唯一の追跡先である _Depends:_ 3
- [ ] 6. **`/task-close` の反映後の認証で `docs/00-requests/decisions/sec.md` の検証履歴コメントを直す**(未決点#6)。
      `:29` の次の1行を逐語で削除する(本タスクが `docs/issues/041` を解消するため事実でなくなる):
      「ブロック対象ドメインの集合そのものは 00/01 のどこにも定義されていない(docs/issues/041)。」を含む
      `D0-sec-04` の残課題の記述。**同コメントの `docs/issues/005` の記述は残す**(別件で未解消)。
      **あわせて末尾の「いずれも「高」ではないため認証を妨げない。」を「これは「高」ではないため
      認証を妨げない。」に直す**(「いずれも」は 005 と 041 の2件を指しているので、041 側を消すと
      残り1件に対して複数形が残る。2026-08-05 の独立レンズが検出)。
      本文・決定・委任は1文字も触らない(委任 c のガードレール)。
      **`decisions/sec.md` は変更指示を書いていない** — この行が唯一の追跡先である _Depends:_ 3
- [ ] 7. **`/task-close` の反映後に `docs/issues/014` と `docs/issues/026` の `related:` から
      `NFR-ops-01` を外す**(2026-08-05 の独立レンズが検出。未決点#7)。
      両 issue は本タスクの対象外で**オープンのまま残る**のに、`related:` が本タスクで削除される
      要件 ID を指しているため、反映後は宙吊り参照になる。**本文の記述は触らない**
      (014 の実体は「追記型ログが `02-design/logging.md` の必須フィールドを満たさない」であり、
      `docs/02-design/logging.md` と `FR-orch-05` が `related:` に残るので追跡先は消えない)。
      `related:` を直したら `python3 .claude/scripts/build-index.py` で
      `docs/issues/index.md` を再生成する。**この2件は変更指示を書けない**(issue は SSOT 層では
      ないが `/doc-check` の task モードは削除前の要件を指す状態を直せない)ため、この行が唯一の
      追跡先である _Depends:_ 3

## Definition of Done

**2026-08-05 フェーズ2末に具体化した**(それまでは「フェーズ2/3 が具体化する」という置き書きだった)。
すべて機械または逐語で判定できる形にしてある。

- [ ] 1. **コード差分が空である**: `git status --porcelain` に `scripts/` `orchestrator/`
      `docker-proxy/` `claude-dev` `claude-dev-mac` `Makefile` `Dockerfile*` の変更が1件も無い
- [ ] 2. **変更指示 26 件がすべて反映済み**: `python3 .claude/scripts/close-task.py --check
      task-spec-measurability` の (a) が全件 OK
- [ ] 3. **`docs/issues/` から6件が削除されている**: `017` / `041` / `042` / `043` / `044` / `049`。
      あわせて `docs/issues/index.md` が `build-index.py` で再生成されている
- [ ] 4. **`docs/00-requests/terminology.md` に合格証が発行されている**(本タスクの目的そのもの。
      `044` の下降が終わった証拠)。`close-task.py --check` の (b) が全件 OK
- [ ] 5. **削除した2要件の宙吊り参照が0件**(**2026-08-05 フェーズ3 で判定条件を訂正した**。
      旧版は「`grep -rn "NFR-ops-01\|NFR-sec-02" docs/ --exclude-dir=callgraphs` の結果が
      `docs/histories/` と `docs/feedbacks/` だけになる」だったが、**これは達成できない**:
      `docs/issues/061` は「`NFR-ops-01` の廃止で追記型ログが要件の裏付けを失う」という
      **廃止そのものを主題とする issue** で、本タスクでは解消せず残る。`docs/issues/014`・`026` も、
      タスクリスト7番が外すのは `related:` だけで**本文は触らないと明記**している。
      issue と histories と feedbacks は仕様ドキュメントではなく**経緯の記録**なので、
      実在しない ID を経緯として述べるのは宙吊り参照ではない)。訂正後の判定は次の2つ:
      - (5a) **仕様ドキュメントに1件も残らない**:
        `grep -rn "NFR-ops-01\|NFR-sec-02" docs/00-requests/ docs/01-requirements/ docs/02-design/ docs/03-impl/ --exclude-dir=callgraphs`
        の結果が**空**である(タスクリスト5番の `03-impl/index.md`・6番の `decisions/sec.md` を含む)
      - (5b) **生きている issue の `related:` が実在しない要件 ID を指さない**:
        `grep -n "^related:.*NFR-ops-01\|^related:.*NFR-sec-02" docs/issues/*.md` の結果が
        **空**である(タスクリスト7番の実施結果)
- [ ] 6. **`lint` とテストが緑**: `go vet ./...`(`docker-proxy/` と `orchestrator/`)/
      `cd docker-proxy && go test ./...` / `cd orchestrator && go test -mod=vendor ./...` /
      `cd examples/orch-sample && pytest`(`02-design/environments.md` の逐語)
      (**2026-08-05 フェーズ3 で最後の1項の扱いを明示した**。`examples/orch-sample` は
      **わざと未実装のテンプレート**(`src/mathkit/*.py` が `NotImplementedError`。
      `GOAL.md`「実装対象は各スタブ関数」)なので、`pytest` は **12 failed が正常な初期状態**である。
      これは既知で `docs/issues/033` が起票済み(severity 低・本タスクの範囲外)。
      **本タスクはコード差分が空**なので実行結果は HEAD と同一であり、退行ではない。
      判定は残る3コマンド(`go vet` × 2 モジュール、`go test` × 2 モジュール)で行う)
- [ ] 7. **機械検査が緑**: `check-relations.py` 合格 / `check-contracts.py` 合格 /
      `callgraph-check.py` の重大度「高」0 件 / `build-index.py --check` 差分なし /
      `build-callgraphs.py --out "$(resolve-callgraph-out.py)" --check` が最新
      (**2026-08-05 フェーズ3 で最後の1項の判定時期を明示した**。タスク進行中は
      `resolve-callgraph-out.py` が `new-features/03-impl/callgraphs/` を返すが、そこへ生成すると
      `check-changeset.py` の **CS1 が 25 件落ちる**(未決点#8 のキット競合)。フェーズ3 では
      規範どおり生成して **SSOT とバイト一致することを実測**したうえで staged を残さない状態に
      戻したので、**この1項は `/task-close` が SSOT へ再生成した後に判定する**。
      現時点の `build-callgraphs.py --check` は `callgraphs/index.md` の HTML コメント1箇所だけ
      差分を出すが、これは抽出器のテンプレート更新分で**コードの内容は同一**であり、
      `/task-close` の再生成で解消する。フェーズ3 は SSOT を書けない(原則1))
- [ ] 8. **`docs/histories/` にエントリが1本ある**(反映した版遷移と具体行を持つ)

## 進捗メモ

- 2026-08-04 フェーズ1。`issue 043` を起点に `017` / `041` / `042` / `044` を同時対象として宣言。
  3本連続タスクの3本目。決定シート5論点 + 委任2件を提示。
  **`044` は既に裁定済み(案A′)なので論点ではなく作業として扱う。**
- 2026-08-05 フェーズ1の再開(`/task-new task-spec-measurability`)。2本目が閉じたので着手した。
  タスクリスト0番を実施し、**closure を 26 行で確定**(旧版の ★下降中に判定 4 行をすべて解決し、
  `decisions/scope.md` / `decisions/env.md` / `contracts/entrypoint-firewall.md` /
  `MODULE-makefile-update-claude.md` / `features.md` / `tests/` 4本を追加した)。
  **`049` を対象 issue に追加**(前タスクの申し送り。`042` と同一事象)。
  **`sheet.md` を新設**(前回は memo.md 内に表を書いており、`.claude/templates/sheet.md` の
  「概念の明確化」の節が無かった = `check-sheet.py` SH2/SH3 で不合格になる状態だった)。
  概念の明確化6件を追加し、論点5 の古い前提を訂正、委任 c を追加した。
- 2026-08-05 **決定シートに回答があり、フェーズ1 を終えた**(`phase: ドキュメント`)。
  概念 #2・#5・#6 で AI 推奨が覆り、**`NFR-sec-02` と `NFR-ops-01` の削除**という
  当初になかった作業が入った。波及を実測して closure を **26 → 35 行**へ広げた
  (`decisions/orch.md`/`auth.md`/`dist.md`・`01-requirements/system.md`・
  `MODULE-vm-mode-cli`・`MODULE-hooks-*`2本・`MODULE-container-tools-wait-limit-reset` を追加。
  `tests/` 4本と `request.md` は ★条件付きから確定へ)。未決点3件・質問キュー1件を登録。
  原則11 の学習を `docs/feedbacks/021-a-quality-attribute-can-be-declined-not-only-measured.md`
  へ記録した。
- 2026-08-05 **フェーズ2(`/task-doc`)。00→03 の1回の下降で変更指示 26 ファイルを書いた。**
  内訳: 00×6 / 01×3 / 02×5 / 03×12。`check-changeset.py` は CS1・CS3・CS4・CS8・CS10 が OK、
  **CS2 だけが違反1件**(キットの限界。未決点#5)。CS5・CS6・CS7・CS9 は未設定/対象なしで未検査。
  **実装ドライラン**: パス1 で未決点を5件に整理し、パス2 で `SLACK_BOT_TOKEN` の除去経路3種と
  `VM_HEALTH_*` の一次情報を実測した(調査メモ)。**パス2 の結果で `NFR-sec-03` の目標値を
  実装に合わせて緩めた**(私の草案が実装より厳しかった)。
  **独立レンズ**: Codex は利用上限(復旧 2026-08-11)で `audit_failed(unavailable)`。
  人間が代替を承認したためサブエージェント(`Explore` / `sonnet`)で同じ依頼を実行した。
  新しく起票した issue: **`060`**(01 に条項ID・分割可否が無く 02 に充足列が無い)/
  **`061`**(`dispatch` / `result` の追記型ログが要件の裏付けを失う)。
  キット課題: `.claude/improvements/KIT-changeset-cs2-closure-and-deletes-as-sections.md`。
- 2026-08-05 **`/doc-check task-spec-measurability` 判定: PASS(残存の「高」なし)。
  レンズ: なし(Codex 利用上限で `audit_failed(unavailable)`。代替は人間の承認が要るので実行していない)。**
  実行形態はサブエージェント(新規コンテキスト)。**自動修正4件**:
  (1) `new-features/01-requirements/usecases.md` — `sections` に `## UC-03` / `## UC-04` を挙げながら
      本文が節の最終形でなかった(代替フロー・例外フローの表と UC-04 の基本フロー 7・8 は**見出しではない**ので、
      `replace` を機械適用すると消える)。**唯一の「高」**。SSOT の現行文面を逐語で再掲して最終形にし、
      節の中にあった反映者向けコメント2件(反映後の SSOT に「変更したのは…」という変更相対の記述と
      削除済み `NFR-ops-01` への参照を残してしまう)を frontmatter 直後へ移した。
  (2) `new-features/00-requests/decisions/scope.md` — 末尾コメントが**本タスクが削除する
      `docs/issues/044`** を参照していた(memo の「やらないこと」=「新しい宙吊り参照を作らない」に反する)。
      `docs/histories/` の該当エントリを指す形へ書き替えた。
  (3) `new-features/02-design/contracts/entrypoint-firewall.md` — closure 表が「`:21` の検証履歴コメント」を
      変更対象と宣言していたのに、当該コメントは H1 の**前**にあり `sections` の範囲外で、
      反映指示も無かった(委任 c の実行漏れ)。削除する1行を逐語で引用する注記を足した。
  (4) 未決点#6 を新設し、`decisions/sec.md:29` の追跡をタスクリスト6番として明示した。
  **新しく起票した issue: `062`**(`MODULE-makefile-build-orchestrator.md:27` の「自己検証の高速ループ」。
  `docs/issues/017` が同ファイルを「解消済み」と記録しているため、017 を削除すると追跡先が消える)。
  機械検査: CS2 の既知の誤検出1件のみ。`check-relations` / `check-contracts` / `cluster-features --check` /
  `build-index --check` はすべて合格。`callgraph-check.py` の「高」は 0 件。
  検査 E(02 ⇄ 03)は差分なし(MODULE 83 ⇄ PLAN 65 の差 18+1 は 02 が「網羅の範囲」で宣言済みの内部関数)。

- 2026-08-05 **`/doc-check task-spec-measurability`(2回目。人間が承認した代替レンズつき)
  判定: PASS(残存の「高」なし)。レンズ: サブエージェント(`Explore` / `sonnet`。reasoning は
  Agent ツールに指定口が無いのでセッションの値)。Codex は利用上限で `audit_failed(unavailable)`
  のまま(復旧 2026-08-11 12:56。起動して確認済み)。** 実行形態はサブエージェント(新規コンテキスト)。
  **独立レンズを4本立てた**(docs / readiness / 修正後の再監査 / 最終監査。task モードの上限4本)。
  **自動修正6件**(うち重大度「高」3件。**すべて「記述の精密化」が実装より厳しい要求を新しく
  作ってしまった型**である):
  (1) **高** `NFR-sec-03` の測定方法が**実態と逆**だった。「worker とレビューアーは単体テスト、
      対話 Claude は実機確認」と書いていたが、実際は `claudeChildEnv()` を固定する単体テストは
      1件も無く、対話 Claude の起動スクリプトだけ `orchestrator/mode_test.go` が固定している。
      実態に合わせ、`tests/orchestrator.md` の未検証理由(#33)も同じ形へ揃えた。
  (2) **高** `NFR-perf-02` の新しい目標値(2)が「VNC 系(`x11vnc`)・Chrome・その依存以外は1件も
      現れないこと」で、`vnc-base` が実際に積む openbox・ibus/mozc・フォント・xdotool・
      `rmcp-xdotool` を**すべて禁じていた**(しかも `x11vnc` は導入されておらず実体は TigerVNC)。
      **`FR-env-11` 受入基準1・3 が要求している資産**なので、字面どおり測ると必ず不合格になる。
      6カテゴリへの割り当て方式へ直し、`tests/images.md` の該当行も揃えた。
  (3) **高** `FR-orch-02` 受入基準3 の「worker へ渡す文脈を4種**だけ**で構成する」が
      `Worker.BuildPrompt` と食い違う(実装は `VMModePreamble` / `ORCHESTRATOR.md` /
      `workerResultGuide` も必ず入れる)。**`FR-orch-08` 受入基準5 が前置を要求している**ので
      01 が 01 と衝突していた。「**タスク固有の文脈**を4種だけ」へ範囲を明示した。
  (4) `MODULE-firewall-init` の「コメント行を飛ばすので雛形2件は登録されない」が機序として不正確
      (2件は配列要素ではなくシェルのコメント。結論の16件は正しい)。
  (5) `non-functional.md` の反映コメント「削除する6行」が実際は7行。`functional.md` の「3行」は
      行境界と一致しない(削除開始が行の途中)ので、行数に依存しない表現へ。
  (6) `logging.md` の「起動ディレクトリの絶対パスの扱い」が、改訂で消える文言を引用していた。
  **新しく起票した issue: `063`**(ダッシュボードの VM 資源逼迫バナーに受入基準が無い。実装済み・
  単体テスト4件つき)/ **`064`**(`DSN-prompt-03` の「だけ」が共通の前置き・後置きを数えていない。
  02 側の同型の問題で本タスクの影響範囲外)。
  **新しく起こしたタスクリスト項目: 7番**(`docs/issues/014` と `026` の `related:` から
  `NFR-ops-01` を外す)。**6番に「いずれも」の言い換え**を追記した。
  **Definition of Done を8項目へ具体化した**(それまで置き書きだった)。
  機械検査: CS2 の既知の誤検出1件のみ。**CS9 が一度も走っていないこと**(未決点#7)を確認したので
  同じ照合を手で実行し、PLAN 64 行 × callers/callees/contracts で実質違反0件を確かめた。
  `check-relations` / `check-contracts` / `cluster-features --check` / `build-index --check` は合格。
  `callgraph-check.py` の「高」は 0 件。検査 E(02 ⇄ 03)は差分なし
  (MODULE 83 ⇄ PLAN 64 の差 19 は 02 が「網羅の範囲」で宣言済みの内部関数18本 + 題材本体1本)。

- 2026-08-05 **フェーズ3(`/implement`)。コード差分ゼロで完了した。**
  本タスクは記述の精密化だけなので**実装タスクは1件も無く**、フェーズBは
  「コードが変わっていないことの実測」と検査の実行だけである。
  **ゲート**: 検証済みチェーン 23 件中 22 件 OK。残る `docs/00-requests/terminology.md` は
  合格証が無いが、**それが本タスクの目的そのもの**(`docs/issues/044` の承認待ち)で、
  発行できるのは `/task-close` だけ(原則1 により `/doc-check ssot` はタスク進行中に走らせられない)。
  **構造的に満たせない条件**なので、既知として明示したうえで進めた。未決点8件はすべて帰着済み、
  質問キューは空。
  **lint・テスト**: `go vet` 2 モジュール rc=0 / `go test` 2 モジュール ok。
  `examples/orch-sample` の `pytest` は **12 failed だが題材がわざと未実装**(`docs/issues/033` が
  起票済み)。コード差分が空なので HEAD と同一結果であり退行ではない(DoD 6 に明記した)。
  **機械検査**: `check-relations` / `check-contracts` / `build-index --check` 合格。
  `callgraph-check.py --to-be` は 47 件だが**重大度「高」0 件**(すべて既存の CG2/CG3/CG4 参考)。
  `check-changeset.py` は **CS1 OK・CS2 の既知の誤検出1件のみ**。
  **コールグラフ(C-1)**: 規範どおり `--out` でタスク配下へ生成し、**SSOT とバイト一致**を確認した
  (唯一の差分は `callgraphs/index.md` の HTML コメントで、抽出器のテンプレート更新分。
  コードの内容は同一)。生成したまま残すと **CS1 が 25 件落ちる**ことを実測で確認したので
  (未決点#8 のキット競合)、フェーズ2 の決定どおり staged を残さない状態へ戻した。
  **独立レンズ**: Codex は**実際に起動して**利用上限を確認した(復旧 2026-08-11 12:56)。
  **人間が「今後、codex が利用できない時は subagent を使って」と常設で承認した**ため、
  サブエージェント(`Explore` / `sonnet`。reasoning は Agent ツールに指定口が無いのでセッションの値)で
  変更指示 26 件の監査を実行した。**レンズは `subagent` であって Codex ではない。**
  読み取り 58 ファイル、verdict は `fail`(指摘2件)。裁定:
  (F1・高)「`decisions/orch.md` への変更指示が無く `NFR-ops-01` が宙吊りになる」→ **誤検知**。
  `new-features/00-requests/decisions/orch.md` は**実在し**(`target: docs/00-requests/decisions/orch.md`、
  節 `## D0-orch-07 通知の失敗許容`)、本文は既に `関連: FR-orch-07` へ直っている。
  ただし**指摘は実在する欠陥を掘り当てた**: closure 表の当該行が「変更指示 = `-`・本文は変更なし」の
  ままフェーズ2 に追随しておらず、しかも「1語だけ外す」と書いていて自己矛盾していた
  (1語を外すのは本文の変更である)。**表を訂正した。**
  (F2・低)`new-features/01-requirements/non-functional.md:17` の反映コメントが
  「次の**6**行を削除」と書きながら同じ段落で「削除するのはこの**7**行だけ」と矛盾していた。
  **確認済み・自動修正可能**(SSOT `non-functional.md:22`〜`:28` = 7 行が正)。**7 へ訂正した。**
  **DoD の訂正2件**(フェーズ2 の記述が達成不能だったもの):
  項目5 は `docs/issues/061`(廃止そのものを主題とする issue)と `014`/`026` の本文が
  正当に `NFR-ops-01` を述べ続けるため字面どおりには満たせない。**仕様ドキュメント側の0件(5a)と
  生きている issue の `related:` の0件(5b)**という2条件へ具体化した。
  項目7 の `--out` 形式は CS1 と同時に成立しないので、**判定時期を `/task-close` の再生成後**と明示した。
  **新しく起票した issue: `065`**(レンズ代替の可否を書く欄が `environments.md` に無く、人間の
  常設承認が会話の中にしか存在しない)。**新しい feedbacks: `022`**(承認の有効範囲は承認した人間が
  決める。AI が「1実行限り」へ勝手に狭めない)。
  **自分の手順違反を1件記録する**: 読み取り専用レンズの実行中に作業ツリー
  (staged コールグラフの生成と削除)を触った。`docs/feedbacks/012` が明確に禁じている行為である。
  今回はレンズが当該ディレクトリに一切言及しなかったため実害は出なかったが、
  **待ち時間に進めてよいのは作業ツリーを変更しない作業だけ**という 012 の教訓は再確認された。

## 申し送り事項

- **1本目・2本目からの申し送りは `memo-1.md` へ逐語で移した**(2026-08-05 のローテーション)。
  未消化だった1件(`terminology.md` に「破壊的操作」「管理ラベル」の2行を追加)は
  「やること」へ引き上げてある。
- **残件は `python3 .claude/scripts/close-task.py --check task-spec-measurability` が数える。**
  2026-08-05 時点の (b) は 19 件中 `docs/00-requests/terminology.md` だけが NG(合格証なし)で、
  これは `044` の下降待ちという本タスクの目的そのものである。
- `041` の「既定リストの16件が妥当か」のセキュリティレビューは本タスクの範囲外。
  測れる形にした後、必要なら別 issue として起票する。
- **relations 層 83 本のうち独立レンズがコードと全文照合できたのは 1 本だけ**(22 本一括の監査が
  900 秒でタイムアウトしたため)。`MOD-orchestrator` の残り 18 本を1本1監査で回す独立タスクの要否は
  `/doc-check ssot` の決定シート #2 のまま(既定 A =「2026-08-10 以降の `/doc-check full` に委ねる」)。
- **2026-08-10 19:52 以降に `/doc-check full`** を新しいセッションで1回(前タスクからの申し送り)。
  本タスクまで終わっていれば、そこが**全層そろった状態でのマイルストーン監査**になる。


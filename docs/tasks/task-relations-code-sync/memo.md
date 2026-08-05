---
id: task-relations-code-sync
phase: 反映
origin_layer: 03
issue: docs/issues/038-modify-closure-relations-still-diverge-from-code.md
date: 2026-08-04
updated: 2026-08-05
source:
  - docs/02-design/contracts/orchestrator-prompt.md
  - docs/03-impl/contracts/orchestrator-prompt.md
  - docs/03-impl/tests/orchestrator.md
  - docs/03-impl/index.md
  - docs/03-impl/relations/MODULE-orchestrator-controller.md
  - docs/03-impl/relations/MODULE-orchestrator-slack.md
  - docs/03-impl/relations/MODULE-orchestrator-claude-exec.md
  - docs/03-impl/relations/MODULE-orchestrator-worker.md
  - docs/03-impl/relations/MODULE-orchestrator-review.md
  - docs/03-impl/relations/MODULE-orchestrator-term.md
  - docs/03-impl/relations/MODULE-orchestrator-session.md
  - docs/03-impl/relations/MODULE-orchestrator-worktree.md
  - docs/03-impl/relations/MODULE-orchestrator-state-intervention.md
  - docs/03-impl/relations/MODULE-orchestrator-mode.md
  - docs/03-impl/relations/MODULE-orchestrator-streamlog.md
  - docs/03-impl/relations/MODULE-orchestrator-trigger.md
  - docs/03-impl/relations/MODULE-orchestrator-dashboard.md
  - docs/03-impl/relations/MODULE-orchestrator-main.md
  - docs/03-impl/relations/MODULE-orchestrator-plan.md
  - docs/03-impl/relations/MODULE-orchestrator-state.md
  - docs/03-impl/relations/MODULE-orchestrator-config.md
  - docs/03-impl/relations/MODULE-cli-start.md
  - docs/03-impl/relations/MODULE-docker-proxy-serve.md
  - docs/03-impl/relations/MODULE-cli-reset.md
  - docs/03-impl/relations/MODULE-cli-stop.md
  - docs/03-impl/contracts/cli-container.md
  - docs/02-design/system.md
  - docs/02-design/contracts/cli-container.md
summary: relations の記述をコードへ全面追随させる(2026-08-05 に再突き合わせ: 038 の残22件 + 032 の18件 + 019 の残1件 + 005 の1行 + 017 の2行 + 056 の8箇所 = 実質50件)
---

<!-- タスクの背骨。フェーズ1で作られフェーズ4で削除されるまで、このファイルだけで
     どのフェーズからでも再開できること(/clear を挟んでも)。
     ・仕様ドキュメントではない(version / verified を持たない)
     ・未決点はここに置く。仕様ドキュメントには絶対に書かない
     ・削除は /task-close の機械ゲート経由(close-task.py)。rm 禁止 -->

# task-relations-code-sync relations の記述をコードへ全面追随させる

> 解決済みの経緯: memo-1.md(1本目の反映で消えた9行の内訳 = closure から外した根拠) / memo-2.md(フェーズ1 の決定シート全文) / memo-3.md(フェーズ2〜3 で決着した分: 未決点4件・レンズの判定・#7/#8 の既定適用・質問キュー・フェーズ2末尾の決定シート・フェーズ1 の決定シートの回答要点・**パス2 の技術調査で確定させたコードの事実**)

## 実行順(★重要)

**3本連続タスクの2本目。1本目 `task-fix-destructive-scope` は 2026-08-04 に完了・削除済み。**
**フェーズ1〜3 は 2026-08-05 に完了した**(フェーズ3 = `/implement` はドライランの6ステップを
実行しただけで、コードは1行も変えていない)。**次は `/task-close task-relations-code-sync`。**
ただしフェーズ3末尾の決定シート #9(QA レーンを対象外としたこと)が未回答なので、
`/implement` C-4-4 に従って `/task-close` の起動を保留している。既定 A のままでよければそのまま進む。

3本目 `task-spec-measurability` は本タスクの後。**重なりが増えている**ので下の申し送りを見る。

## 目的

**CLAUDE.md 原則2(コード ⇄ 03-impl の完全一致)の侵害を解消する。** relations の本文が
コードと食い違う箇所が、2026-08-05 の再突き合わせで **実質 50 件**ある
(`038`+`032` の重複2件を除いた数。うち 10 件は論点5・6 の回答で加わった分)。

| issue | 残件(2026-08-05 実測) | 対象 |
|---|---|---|
| `038` | **中15件 / 低6件 + 追加#6 の1件 = 22件** | `task-impl-depth` が掘り下げた21本のうち、変更指示の `sections` に入っていなかった節(`## 処理の流れ` / `## 連携先と連携内容` / `## 戻り値・副作用` と frontmatter の `callers` / `callees`)。**cli 系5件は1本目が解消した** |
| `032` | **中11件 / 低7件 = 18件**(うち2件は `038` と同一の事実) | 影響範囲外だった orchestrator 7本(`-streamlog` / `-state-intervention` / `-dashboard` / `-main` / `-plan` / `-state` / `-config`) |
| `019` | **残1件** | `tests/orchestrator.md:57`・`:110` の `TestReadyTasks_Basic`(実在しないテスト識別子) |
| `005` | **1件** | `MODULE-docker-proxy-serve` の `## 既知の制限` に「解釈できないボディは検査せず中継する」が無い(**`005` の対処案1 が「`038` と同じタスクで行う」と指定している**) |
| `038` 追加#6 | (上の22件に含む) | `02-design/contracts/orchestrator-prompt.md` が「必須」の意味(検証失敗か既定値補完か)を書いていない ← **02 起点** |
| `017` | **2件**(論点5 = A) | `MODULE-orchestrator-claude-exec` の目的と `-session` の連携先に残る測定不能語「安全に」。**本タスクが同じ文を書き替えるため同時に直す**(`017` 自体は閉じない) |
| `056` | **8件**(論点6 = A) | SSOT に残る変更相対の言い回し。うち `MODULE-cli-reset.md:49`・`:94` は**現行実装について事実と異なる**(原則2 の侵害) |

**合計 50 件。** 起点層は **03**(記述の誤り)。ただし `038` 追加#6 と `056` #7・#8 は
**02 起点**なので同じ下降で直す(CLAUDE.md §3「フェーズをまたいで往復しない」)。

## やること・やらないこと

| 種別 | 内容 |
|---|---|
| やること | `038` の残22件と `032` の18件を**コードで裏取りして記述を直す**(実装は変えない)/ `019` の残1件を実名へ / `005` の1行を `MODULE-docker-proxy-serve` の既知の制限へ / `038` 追加#6 で 02 の契約に「必須だが検証しない」を明記 / **`017` の relations 2行の測定不能語**(論点5 = A)/ **`056` の変更相対の言い回し8箇所**(論点6 = A)/ `03-impl/index.md` の集計を更新 |
| やらないこと | **コードの変更**(記述をコードへ合わせるタスク。実装の誤りが見つかったら issue 起票のみ)/ **`issue 009` (a) の17件**(`ctx` 省略の規約が未決 = `/kit-improve` 案件。論点2)/ NFR の測定可能性と 00・01 の測定不能語、`makefile-build-orchestrator` の「素早く」(3本目)/ `056` の**キット側の再発防止**(`/task-close` の反映に検査を足すこと = `/kit-improve` 案件)/ `03-impl/contracts/cli-container.md` の「設計との差異」(1本目が実態へ直したので**その行は対象外**。`056` #6 の既知の制限だけを直す) |

## 影響範囲(closure)

<!-- 2026-08-05 に 038 / 032 / 019 の残件表をコードと突き合わせ直して確定した(タスク0 完了)。
     frontmatter の source: はこの表と一致させてある(close-task.py 条件b が両方の和を取る)。
     論点5・論点6 の回答で行が増える場合は、その時点で本表と source: の両方を直すこと。 -->

| 層 | SSOT のパス | 変更指示のパス | 変更の種類(対象の行) |
|---|---|---|---|
| 02 | docs/02-design/contracts/orchestrator-prompt.md | new-features/02-design/contracts/orchestrator-prompt.md | replace(`038` 追加#6。「必須だが検証しない」を明記) |
| 03 | docs/03-impl/relations/MODULE-orchestrator-controller.md | new-features/… | replace(`038` #10 並行性 / #11 `callees` に slack) |
| 03 | docs/03-impl/relations/MODULE-orchestrator-slack.md | new-features/… | replace(`038` #11 `callers` に controller / #30 既知の制限) |
| 03 | docs/03-impl/relations/MODULE-orchestrator-claude-exec.md | new-features/… | replace(`038` #12 `callers` に worker・review) |
| 03 | docs/03-impl/relations/MODULE-orchestrator-worker.md | new-features/… | replace(`038` #13 `Dispatch` の引数表) |
| 03 | docs/03-impl/relations/MODULE-orchestrator-review.md | new-features/… | replace(`038` #14 戻り値 / #15 処理の流れ / #27 レビュアログのパス) |
| 03 | docs/03-impl/relations/MODULE-orchestrator-term.md | new-features/… | replace(`038` #16 引数・戻り値 / #17 異常系 / #28 出力先 / #29 `tests`) |
| 03 | docs/03-impl/relations/MODULE-orchestrator-session.md | new-features/… | replace(`038` #18 処理の流れ3点) |
| 03 | docs/03-impl/relations/MODULE-orchestrator-worktree.md | new-features/… | replace(`038` #19 `HasCommits` / #20 git の stderr) |
| 03 | docs/03-impl/relations/MODULE-orchestrator-state-intervention.md | new-features/… | replace(`038` #21 = `032` #12 sidecar / `032` #11 `open.json` の項目) |
| 03 | docs/03-impl/relations/MODULE-orchestrator-mode.md | new-features/… | replace(`038` #22 `ResolveArgsOne`) |
| 03 | docs/03-impl/relations/MODULE-orchestrator-streamlog.md | new-features/… | replace(`038` #23 = `032` #13 未知種別 / `032` #3 `callees` に oneline) |
| 03 | docs/03-impl/relations/MODULE-orchestrator-trigger.md | new-features/… | replace(`038` #31 `TriggerContext` の引数表) |
| 03 | docs/03-impl/relations/MODULE-orchestrator-dashboard.md | new-features/… | replace(`032` #4 引数・戻り値 / #5 処理の流れ / #6 未代入フィールド / #16 actions / #17 戻り値の破棄) |
| 03 | docs/03-impl/relations/MODULE-orchestrator-main.md | new-features/… | replace(`032` #7 `--workspace` 必須 / #8 手順 / #18 出力先) |
| 03 | docs/03-impl/relations/MODULE-orchestrator-plan.md | new-features/… | replace(`032` #9 不存在依存 / #19 `NormalizeForResume`) |
| 03 | docs/03-impl/relations/MODULE-orchestrator-state.md | new-features/… | replace(`032` #10 archive の退避 / #20 `NewStore` の絶対パス) |
| 03 | docs/03-impl/relations/MODULE-orchestrator-config.md | new-features/… | replace(`032` #14 既定の列挙 / #15 `worker_grace_seconds` の 0) |
| 03 | docs/03-impl/relations/MODULE-cli-start.md | new-features/… | replace(`038` #9 entrypoint の副作用 / #26 行番号根拠) |
| 03 | docs/03-impl/relations/MODULE-docker-proxy-serve.md | new-features/… | replace(`005` 対処案1。既知の制限に1行) |
| 03 | docs/03-impl/contracts/orchestrator-prompt.md | - | **変更なし**(`/task-doc` が層ごとに判定して closure から外した。03 側は既に「必須フィールドが欠けているとき = Go のゼロ値」を書いておりコードと一致する)。**ただし `source:` には残す**: 上流の `02-design/contracts/orchestrator-prompt.md` が MINOR で上がるため**合格証が失効し、`/task-close` で再認証が必要**になる(close-task.py 条件b の対象)。2026-08-05 /doc-check(task) が訂正 |
| 03 | docs/03-impl/tests/orchestrator.md | new-features/03-impl/tests/orchestrator.md | replace(`019` の残1件を実名へ) |
| 03 | docs/03-impl/index.md | new-features/03-impl/index.md | replace(「コードとの乖離として未解決のもの」から 038 / 032 / 019 を外す。集計の数も更新) |
| 03 | docs/03-impl/relations/index.md | - | **生成物**(`build-index.py`。手で書かない) |
| 01 | docs/01-requirements/ 全ファイル | - | 変更なし(理由: 要件は変わらない。記述をコードへ合わせるだけ) |
| 00 | docs/00-requests/ 全ファイル | - | 変更なし(理由: 決定・委任・受入基準は変わらない。`D0-orch-15` は 2026-08-04 に改まっており、追加#6 はその決定を 02 へ書き下すだけ) |

**論点5・論点6 の回答(ともに A)で確定した追加分**(2026-08-05):

| 層 | SSOT のパス | 変更指示のパス | 変更の種類(対象の行) |
|---|---|---|---|
| 03 | docs/03-impl/relations/MODULE-cli-reset.md | new-features/… | replace(`056` #1〜#4。`:49`・`:94` は**現行実装について事実と異なる**ので優先) |
| 03 | docs/03-impl/relations/MODULE-cli-stop.md | new-features/… | replace(`056` #5。判断4 の「本変更前に」) |
| 03 | docs/03-impl/contracts/cli-container.md | new-features/03-impl/contracts/cli-container.md | replace(`056` #6。既知の制限の「本変更より前に起動した資源」) |
| 02 | docs/02-design/system.md | new-features/02-design/system.md | replace(`056` #7。`:328` の「本変更で制約を変えない」) |
| 02 | docs/02-design/contracts/cli-container.md | new-features/02-design/contracts/cli-container.md | replace(`056` #8。`:348` の「本変更の値打ちは」) |

- 論点5 = A で**ファイルは増えない**(`MODULE-orchestrator-claude-exec` の目的と `-session` の
  連携先に**行が増えるだけ**)。
- **`02-design/system.md` は3本目 `task-spec-measurability` の `source:` にも入っている。**
  本タスクが先に閉じて SSOT を動かすので、3本目は着手時にこのファイルを読み直すこと(申し送り済み)。

## 着手時の再突き合わせ(タスク0。2026-08-05 に完了)

**memo-1.md に移動**(突き合わせの方法・抜き取り確認3件・消えた9行・残した cli 2行・
新たに入れた1行、および1本目からの申し送り全文)。**結論だけ再掲**: 残件は
`038` 22件 / `032` 18件 / `019` 1件 / `005` 1件 / `056` 8件 = **実質 50 件**で、
その内訳は「影響範囲(closure)」の表の「変更の種類」欄が持つ。

## 決定シート(回答済み)

**memo-3.md に移動**(2026-08-05 に人間が「全部推奨どおり」と回答した論点1〜6 と委任 a、
その推奨・根拠・反映先。フェーズ1 の全文は memo-2.md)。**全件が変更指示へ反映済み**である。

## 未決点

**未決点なし。** フェーズ2 で決着した4件と、その帰着・レンズの判定・#7/#8 の既定適用の記録は
**memo-3.md に移動**した。2026-08-05 の `/doc-check task-relations-code-sync` が
「新しい未決点 0 件・未解決の未決点 0 件」を確認しており、フェーズ3(`/implement`)でも
新しい未決点は発生しなかった。

## 調査メモ

**memo-3.md に移動**(`038`/`032` の行単位作業リストの所在、パス2 の技術調査で確定させた
コードの事実 約60項目、フェーズ1 からの調査メモ)。**コードは 2026-07-06(`b634206`)以降
変わっていない**ので、これらの事実は `/task-close` の時点でも有効である。
ここに書かれた事実は**すべて変更指示の本文へ反映済み**で、`/doc-check(task)` が
91 箇所の `path:line` をコードと照合してずれ 0 件を確認している。

## 質問キュー(提示済み・既定を適用)

**空(全件が既定の適用で決着した)。** 質問1・2(`FR-orch-05` 受入基準2 の覆う範囲)と
フェーズ2末尾の決定シート #7・#8、プロセス質問 P3 の全文は **memo-3.md に移動**した。
反映結果は DoD の #10・#11 にある。

## 決定シート(フェーズ2末尾。2026-08-05 `/doc-check task-relations-code-sync` が提示)

**memo-3.md に移動**(#7 / #8 とプロセス質問 P3。いずれも未回答で既定を適用済み)。

## 決定シート(フェーズ3末尾。2026-08-05 `/implement` が提示。★未回答)

**新しい未決点・委任の行使・02 や変更指示からの逸脱は 0 件**だったので、載るのは
**プロセスに関する1件だけ**である(不変則6 により未決点ではなく、原則7 のゲートを塞がない)。

| # | 論点 | 選択肢 | 推奨案(理由・崩れる条件) | 未回答時の既定 | 根拠(上流/同層/下流) |
|---|---|---|---|---|---|
| 9 | **QA レーン(`/codex-qa` と E2E)を本タスクでは実行しなかった。** 本タスクは**コード差分がゼロ**(記述だけを直す)で、`03-impl/tests/e2e.md` の E2E-01〜06 は**全件が自動ランナーの無い実機確認**である(`environments.md`「E2Eテスト = 自動テストランナーは無い」)。実行には実 Docker・実 tmux・課金を伴う実エージェントが要り、変わっていない振る舞いを確かめることになる | **A**: 対象外のまま `/task-close` へ進む(`/codex-qa` も E2E も走らせない) / **B**: それでも E2E-04/05 を実機で1回通してから閉じる(人間が実行する。半日規模) / **C**: `/codex-qa` を走らせ、E2E は流せなくても CDP 探索的テストだけ行う | **A**。QA レーンの目的は「実装した振る舞いを独立に確かめる」ことだが、本タスクは実装を1行も変えていない(`build-callgraphs.py` が「書き換え: なし」を返したことが機械的な裏付け)。品質ゲートとして働いたのはフェーズ2 の Codex 独立レンズ3本で、そちらは実際に走っている。**崩れる条件**: `/task-close` の SSOT 反映が誤ってコードに触れた場合(そのときは B へ切り替える。close-task.py 条件で検出できる) | **A** | 上流: CLAUDE.md §9(完了は DoD で判定する。本タスクの DoD に E2E 項目は無い)/ `.claude/directions/issues-pendings.md` 同層: `docs/pendings.md` P-003(QA レーンの各設定は未定のまま) 下流: `docs/03-impl/tests/e2e.md` の状態(全件「未検証(テスト未実装)」のまま変わらない) |

**独立レンズについて**(不変則7): 本フェーズでは**独立レンズを走らせていない**。
走ったのは**フェーズ2 の Codex 3本**(`readiness` / `docs` / 再監査)であり、
**サブエージェントによる代替は行っていない**。フェーズ2末尾のプロセス質問 P3
(レンズのタイムアウトをどう固定するか。既定 = C「何もしない」)は**引き続き未回答**である。

## タスクリスト

- [x] 0. **着手時**: `038` / `032` の残件表をコードと突き合わせ直し、1本目の反映で消えた行を除いて closure を確定する(2026-08-05 完了。結果は「着手時の再突き合わせ」節)
- [x] 1. `/task-doc task-relations-code-sync`(02→03 の1回の下降。**27 ファイルの変更指示を作成**) _Depends:_ 0, 決定シートの回答
- [x] 2. `/doc-check task-relations-code-sync` が PASS(2026-08-05。**PASS**。自動修正 8 件 / 6 ファイル。残存指摘は中2件・低4件で、重大度「高」の未解決は 0 件。「未検証(テスト未実装)」47 行は不変則3 の例外) _Depends:_ 1, 質問キュー #1 の回答
- [x] 3. `/implement task-relations-code-sync`(**コードは変えない**。記述のみ)(2026-08-05 完了。
      ドライランの6ステップをすべて実行し全項目グリーン。**コード差分ゼロ**を確認。
      変更指示の更新は**不要**と判定 = C-1。詳細は進捗メモ) _Depends:_ 2
- [ ] 4. `/task-close task-relations-code-sync` _Depends:_ 3, 決定シート #9(未回答。既定 A でよければ即実行)

### フェーズ3 の作業内容(ドライランで確定。実装コードは書かない)

1. **コード差分が空であることを確認**する: `git status --porcelain` の変更が
   `docs/` と `.claude/` の下だけであること。
2. lint(`docs/02-design/environments.md` の厳密な文字列):
   `cd docker-proxy && go vet ./...` / `cd orchestrator && go vet ./...`
3. 単体・結合テスト: `cd docker-proxy && go test ./...` /
   `cd orchestrator && go test -mod=vendor ./...`
   (`cd examples/orch-sample && pytest` は `docs/issues/033` により必ず失敗するので対象外)
4. `python3 .claude/scripts/build-callgraphs.py` → `python3 .claude/scripts/callgraph-check.py`
   (重大度「高」0 件)
5. `python3 .claude/scripts/check-relations.py`(合格)/ `check-contracts.py`(合格)/
   `check-changeset.py docs/tasks/task-relations-code-sync/new-features`
   (**I1 が OK であること**。I2 の「callee が存在しない」は変更指示だけを見る道具の限界による偽陽性で、
   合成ビューでの対称性は別に確認済み = 下の DoD)
6. `python3 .claude/scripts/build-index.py`

## Definition of Done

<!-- 2026-08-05 フェーズ3(C-4)で1項目ずつ実際に実行して検証した。
     [x] = 本フェーズで検証済み / 「/task-close で実施」= SSOT 反映が前提の項目。 -->

| # | 項目 | 判定 | 根拠(実行したこと) |
|---|---|---|---|
| 1 | `019` / `032` / `038` / `056` を削除できる状態 | **`/task-close` で実施** | 変更指示側は全行が揃っている(下の #9・#10 と C-1 の照合)。SSOT へ反映されて初めて成立する |
| 2 | `005` の文書側1行 | **[x]** | `new-features/…/MODULE-docker-proxy-serve.md:34` に「解釈できないリクエストボディは検査せず中継する」が既知の制限として入っている(issue 005 自体は開いたまま) |
| 3 | `001` / `017` は開いたまま | **[x]** | 両 issue とも `docs/issues/` に存在し閉じていない(001 は2シンボル追記済み・017 は空振りの経緯を記録済み) |
| 4 | **コード差分が空** | **[x]** | `git status --porcelain` の変更が `docs/` と `.claude/` の下だけ。`build-callgraphs.py` も「書き換え: なし(既に最新)」 |
| 5 | lint 2本と `go test` 2本がグリーン | **[x]** | `go vet` 両モジュール exit=0 / `go test` 両モジュール ok(`environments.md` の厳密な文字列で実行) |
| 6 | `callgraph-check.py` の重大度「高」が 0 件 | **[x]** | `--to-be task-relations-code-sync` で指摘 47 件・**高 0 件**。中3件は closure 外の既存 |
| 7 | `check-relations.py` / `check-contracts.py` 合格 | **[x]** | 前者 83 ファイル/83 ID 合格、後者 不整合なし |
| 8 | **合成ビューで `callers` / `callees` の対称性** | **[x]** | `check-changeset.py` の **I2 が OK**(合成ビュー 83 件)。追加した3組はインターフェース越しの実装をコードで裏取り済み(C-1) |
| 9 | `tests/orchestrator.md` に実在しないテスト識別子が 0 件 | **[x]** | 変更指示が参照する **92 種**を実ファイルの `func Test*` と機械照合し不一致 0 件。`TestReadyTasks_Basic` は変更指示の `:69`・`:115` が両方を消している |
| 10 | 質問キュー #1(`FR-orch-05` 受入基準2 の覆う範囲)の回答が反映 | **[x]** | 未回答のため既定 B(「未検証(テスト未実装)」)を適用済み。`:69` が該当行、`:178` が全件表 #47 |
| 11 | 決定シート #7 / #8 の回答が反映 | **[x]** | 既定(#7=A / #8=A)を適用済み。`docs/issues/057` / `058` を起票し、`03-impl/index.md` の集計を 18 件へ |
| 12 | `03-impl/contracts/orchestrator-prompt.md` の合格証が有効 | **`/task-close` で実施** | 上流 `02-design/contracts/orchestrator-prompt.md` が MINOR で上がるため失効する。認証で `against` を 1.2.0 → 1.3.0 へ再発行すること(close-task.py 条件b) |
| 13 | SSOT 反映 / `/doc-check` PASS / histories | **`/task-close` で実施** | フェーズ4 の仕事 |
| 14 | QA レーン(E2E) | **対象外(理由あり)** | 決定シート #9。コード差分ゼロで、`e2e.md` の E2E-01〜06 は全件が自動ランナーの無い実機確認 |

**補足(#8)**: 追加した3組は `controller ⇄ slack` / `claude-exec ⇄ worker` / `claude-exec ⇄ review`。
`streamlog ⇄ dashboard` は**追加しない**: `dashboard.go::oneline` は
`03-impl/features.md:145` が「畳み込む薄いユーティリティ」と判定した共有関数で MODULE-ID を
持たないため、`callees` に載る対象ではない(`docs/issues/032` #3 は誤検知として棄却)。

## 進捗メモ

- フェーズ1 の最古2エントリ(2026-08-04 の宣言・2026-08-05 のタスク0 完了)は **memo-3.md に移動**。
  論点5・6 の A により closure を **26 ファイル・実質 50 件**へ拡張(02 層が2本増えた)。
  裁定を `docs/issues/056` / `017` / `005` に記録(memo が消えても経緯が残るように)。
  委任 a は既存の `D0-scope-06` と一致するので **00 層は変更なし**のままとした。
  `phase:` を `ドキュメント` へ進めた。次は `/task-doc task-relations-code-sync`。
- 2026-08-05 **フェーズ2(`/task-doc`)**。00→03 の1回の下降で **27 ファイルの変更指示**を作成
  (02 が3本 / 03 の relations が21本 / 03 の contracts・tests・index が3本)。
  **`03-impl/contracts/orchestrator-prompt.md` は closure から外した**: `038` 追加#6 は 02 側の
  記述不足であり、03 側は既に「必須フィールドが欠けているとき = Go のゼロ値」を書いていて
  コードと一致しているため、変更する理由が無い(層ごとの明示的判定)。
  **`issue 017` の relations 3行は既に解消済みだった**ので論点5 は空振り(受け皿の確認漏れ。
  `docs/feedbacks/017` と同じ失敗を繰り返した)。
  ドライラン: 機械検査(27ファイル/27target・見出し一致・deletes 明示)0 件、
  合成ビューの対称性 0 件、`check-changeset.py` の I1 OK。
  独立レンズ(Codex `readiness`)は**キットのスキーマ不備で1回失敗**し、スクラッチパッド上の
  修正版スキーマで再実行した(`.claude/improvements/KIT-audit-schema-missing-required-keys.md`)。
- **`2026-08-05` /doc-check(task) 判定: PASS(残存 0 件の重大度「高」)。レンズ: Codex(`readiness` /
  `docs` / 再監査の3本)。** 以下は内訳(反復 2/5)。
  実行形態: サブエージェント(呼び出し元の指示による新規文脈)。**合格証は書かない**(task モード)。
  レンズ: **Codex `readiness` と Codex `docs` の2本が成功**(`gpt-5.6-terra` / reasoning `max`)。
  ただし**最初の起動は2本ともタイムアウト**(900 秒。終了コード 124)で、
  **対象集合を 27+27 ファイルへ絞り「探索的なシェルを組まない」と明示した再試行で成功した**
  (`environments.md` のタイムアウト 900 秒に対し、対象が広すぎると JSON を返す前に打ち切られる。
  この経験は決定シート P3 と申し送りに残した)。
  自動修正 **8 件 / 6 ファイル**: (1) `MODULE-orchestrator-plan` の `tests` が `tests/orchestrator.md` の
  表と2件食い違い / (2) `tests/orchestrator.md` 全件表 #38 の対象と理由が同ファイルの ⇄ 表と矛盾 /
  (3) `02-design/contracts/cli-container.md` の同じ節に「本変更」が残存(→ さらにレンズの指摘で
  「観測できる性質で識別する」形へ再修正)/ (4) `03-impl/index.md` に「本タスク」が残存 /
  (5) `MODULE-cli-start`「### 並行性」の表の2行が同じ入力で相反(**独立レンズが重大度「高」で検出**。
  コードでロックキーを裏取りして限定を足した)/ (6) 02 契約の「停止させたい場合は `D0-orch-15` から
  改める」(レンズ検出)/ (7) `03-impl/index.md` の「次にそのモジュールを触るタスクで」(同)/
  (8) `MODULE-cli-stop` 判断8 の「現行も」(同)。
  修正後に**対象を6ファイルへ絞った再監査**を1本走らせた(§0.5「意味のある修正後の再監査」)。
  機械検査: `build-callgraphs.py --check` 最新 / `cluster-features.py --check` 最新 /
  `callgraph-check.py --to-be` 高0・中3(closure 外の既存)/ `check-contracts.py` 合格 /
  `check-relations.py` 合格 / `build-index.py --check` 差分なし /
  `check-changeset.py` I1 OK(I2 の 27 件は道具の限界による偽陽性。合成ビューで対称性 0 件を別途確認)。
  **変更指示の 91 箇所の `path:line` 引用をすべてコードで照合し、ずれ 0 件**。
- 2026-08-05 **フェーズ3(`/implement`)完了**。ゲート3条件を通過(合格証チェーン: 変更指示 27 target +
  `source:` を再帰的に辿った **38 文書すべてが verified**・自身と各 `against` が MAJOR.MINOR で一致し
  問題 0 件 / 未決点ゼロ / lint・テストのコマンドが「未定」でない)。
  **本タスクはコードを書かないので、フェーズ3 の実体はドライランの6ステップの実行である。**
  - **コード差分ゼロを確認**(`git status --porcelain` の変更が `docs/` と `.claude/` の下だけ)。
  - lint: `cd docker-proxy && go vet ./...` = 0 / `cd orchestrator && go vet ./...` = 0。
  - テスト: `cd docker-proxy && go test ./...` = ok / `cd orchestrator && go test -mod=vendor ./...` = ok。
  - `build-callgraphs.py` は「**書き換え: なし(既に最新)**」= コードが変わっていないことの機械的な裏付け。
    `cluster-features.py` 再生成後も `feature-graph.md` に差分なし。
  - `callgraph-check.py --to-be` 指摘 47 件。**重大度「高」 0 件**。中3件は
    `MODULE-entrypoint-claude` の CG3(closure 外・shell Tier 3 の既存)でフェーズ2 の記録と一致。
  - `check-relations.py` 合格(83 ファイル/83 ID)/ `check-contracts.py` 合格 /
    `check-changeset.py` は **I1〜I10 すべて OK**(合成ビュー 83 件。フェーズ2 で偽陽性 27 件だった
    I2 も今回は OK)/ `build-index.py` は `docs/tasks/index.md` のみ更新。
- **C-1 の判定: 変更指示の更新は不要**。コードを1文字も変えていないためコールグラフは phase 2 時点と同一で、
  `/doc-check(task)` が 91 箇所の `path:line` を照合済み。表の各検査に対する裁定:
  - **CG3「低(実装前)」のうち本タスクが追加した3組**(`controller → slack` / `worker → claude-exec` /
    `review → claude-exec`)は**実装漏れではない**。いずれも**インターフェース越しの呼び出し**で、
    静的コールグラフが辺を出せないだけである。コードで裏取りした:
    `controller.go:323`/`:454`/`:741`/`:1038`/`:1050`/`:1053`/`:1090` が `Notifier`(`worker.go:77`)経由で
    `slack.go:31 SlackNotifier.Notify` を呼び、`worker.go:231` と `review.go:81`/`:126` が
    `ClaudeRunner`(`worker.go:48`〜`:51`)経由で `worker.go:350 ExecClaude.RunPrompt` を呼ぶ。
    変更指示は既にこの `path:line` を根拠として持っている(例: `MODULE-orchestrator-slack.md` の
    コメント欄)。**実装・記述とも変更なし。**
  - **CG4 の確度「候補」7本は全件棄却した**(`claude-exec`/`mode`/`session`/`term` → `controller`/`session`)。
    理由: すべて `exec.Cmd.Run()` の呼び出しが `Controller.Run` / `SessionManager.Run` と**同名衝突**した
    ものである(`term.go:54 cmd.Run()` / `session.go:119 exec.CommandContext(...).Run()` /
    `mode.go` の `cmd.Run()` / `worker.go` の claude 子プロセス起動)。実在する経路ではないので
    `callees` に載せない。**この棄却は `/task-close` で histories へ残すこと**(次回の実行が
    再導出しなくて済むように)。
  - CG4 の `MODULE-makefile-*` 12 本と CG2 の未到達候補は closure 外の既存(severity 参考・低)。本タスクの範囲外。
  - **FT1〜FT4 / CG1 / CG6 / CG7 の指摘は 0 件。**
- **QA レーン(`/codex-qa`)は実行していない。理由は下の決定シート #9 に載せた**(コード差分ゼロで、
  `e2e.md` の E2E-01〜06 は全件が自動ランナーの無い実機確認であるため、対応するシナリオが無い)。
  **独立レンズが走ったのはフェーズ2 の Codex(`readiness` / `docs` / 再監査の3本)だけ**である。
- **DoD の機械検証**(C-4 の表の根拠):
  - 反映される本文(変更指示のコメント欄・`reason:` を除く)に残る変更相対語は
    `MODULE-cli-reset.md` の 2 箇所だけで、いずれも**コードが実際に出力する文面の逐語引用**である
    (`claude-dev:1091`・`:2110` の「本変更より前に起動した可能性があります」)。原則2 のため
    ドキュメント側だけを変えられない。文言自体の是正は `docs/issues/056` が追跡する。
  - 変更指示が参照するテスト識別子 **92 種をすべて実ファイルの `func Test*` と照合し、実在しないもの 0 件**。
    `TestReadyTasks_Basic` は現行 SSOT の `tests/orchestrator.md:57`・`:110` に残っているが、
    変更指示の `:69`(→ 未検証)と `:115`(→ 実在する3件へ差し替え)が両方を消している。
- **C-3(記録の確認)**: (1) **フェーズ3 で新たに行使した委任は 0 件**(変更指示に値と方針が確定して
  書かれており、判断の余地が生じなかった)。既存の委任 `D0-scope-06` の行使記録は「調査メモ」と
  変更指示の「実装上の判断」にあり、欠落なし。(2) **人間が理由なく差し戻した提案は無い**ので
  `docs/feedbacks/` への追加は無し。(3) 範囲外の問題の記録: `docs/issues/056`(変更相対の言い回し。
  残り9箇所は3本目へ)/ `057`(壊れた `open.json`)/ `058`(未知の `severity`)がフェーズ2 で起票済み。
  フェーズ3 で新たに見つけた範囲外の問題は無い(CG4 の候補辺7本はツールの同名衝突であり、
  プロジェクト側の問題ではないので issue にはしない。棄却の理由は上に残した)。

## 申し送り事項

- **着手前に判断が要ること**: 決定シート論点2 で「規約を先に決める」を選ぶ場合は、
  **本タスクの前に `/kit-improve`** を回して `.claude/directions/relations.md` に
  `ctx` 省略の規約を書く(そうすれば `issue 009` (a) の17件も本タスクで閉じられる)。
- 3本目 `task-spec-measurability` は本タスクの後。**重なりは `03-impl/index.md` だけではない**
  (2026-08-05 に判明):
  - ~~`issue 017` の relations 2行が `MODULE-orchestrator-claude-exec` / `-session` にある~~
    → **空振りだった**(2026-08-05 のフェーズ2 で確認。3行とも現行 SSOT に存在しない)。
    **3本目の決定シート論点5 は前提が古い**: 「2本目のタスクで同じファイルを開くので、そこで直すのが
    最も安い」という推奨理由が成立しないので、3本目は `017` の残件表を着手時に読み直すこと
    (経緯は `docs/issues/017` に記録済み)。
  - 論点6 = A を採ると `docs/02-design/system.md` も重なる(3本目の `source:` に入っている)。
  - いずれも**先に閉じた本タスクが SSOT を動かす**ので、3本目は着手時に該当ファイルを読み直すこと。
- **`/kit-improve` 案件が1件増えた**: `/task-close` の反映で変更指示の言い回し(「改める」「本変更」
  「従来は」)が SSOT に残る経路に検査が無い(`docs/issues/056` の末尾に記録した)。
- **`/kit-improve` 案件がさらに2件(2026-08-05 の `/doc-check(task)` が検出)**:
  1. `.claude/templates/03-tests-module.md:53`〜`:57` が「未検証(テスト未実装)の全件」表に
     **「閉じる予定」列を必須**とし、`:57` が「閉じる予定を書く」と指示している。これは
     CLAUDE.md §1「SSOT は計画・TODO を書かない」と**正面から緊張する**(独立レンズ Codex `docs` が
     中として指摘した。本実行では原則9 に従いテンプレートを変えず誤検知として棄却したが、
     **規範の側に矛盾が残っている**)。「閉じる予定」を issue へ出すか、列名を
     「解消の条件」のような現状記述へ変えるかはキット側の判断である。
  2. **`docs/issues/056` の言い回し検査は「本変更」「〜へ改める」しか拾えていなかった**
     (`/doc-check(task)` が「本タスク」「次のタスクで」「現行も」という同型を追加で 15 箇所見つけた)。
     `.claude/scripts/` に走査を足すなら、**語彙は最低でも「本変更 / 本タスク / 従来は / 現行も /
     旧実装 / 次のタスク / 〜へ改める」**を含める必要がある。
- **2026-08-10 19:52 以降に `/doc-check full`** を新しいセッションで1回(前タスクからの申し送り)。
- **`/task-close` への申し送り(版の見込み。2026-08-05 の `/doc-check(task)` が算定)**:

  | ドキュメント | 現在 | 見込み | 理由 |
  |---|---|---|---|
  | `02-design/contracts/orchestrator-prompt.md` | 1.2.0 | **1.3.0(MINOR)** | 「必須」の意味(検証しない・既定値で埋める)を新たに規定する = 意味が変わる |
  | `02-design/system.md` | 2.2.0 | **2.2.1(PATCH)** | `#### SCR-01` の1文の言い換えだけ。**PATCH なら下流(`03-impl/index.md` / `tests/orchestrator.md` / 02 の contracts 2本)の合格証は失効しない** |
  | `02-design/contracts/cli-container.md` | 1.4.1 | **1.4.2(PATCH)** | 言い換え3箇所のみ。下流 `03-impl/contracts/cli-container.md` は失効しない |
  | `03-impl/contracts/cli-container.md` | 1.5.0 | 1.5.1(PATCH) | 既知の制限1行の言い換え |
  | `03-impl/tests/orchestrator.md` | 1.1.1 | **1.2.0(MINOR)** | テスト対応の付け替えと状態の変更 |
  | `03-impl/index.md` | 1.11.0 | **1.12.0(MINOR)** | 集計 15→16、解消済み issue の記述 |
  | `03-impl/relations/MODULE-*.md`(21本) | — | 層として `03-impl/index.md` が認証(原則6 の例外) | — |
  | **`03-impl/contracts/orchestrator-prompt.md`** | 1.1.0 | **本文は変えないが合格証を再発行**(against を 1.2.0 → 1.3.0 へ) | 上流が MINOR で上がるため失効する。**忘れると close-task.py 条件b が落ちる** |

  **`02-design/system.md` と `02-design/contracts/cli-container.md` を MINOR にしてしまうと
  再認証の連鎖が広がる**(3本目 `task-spec-measurability` の closure と重なる)。
  どちらも言い回しの修正だけなので PATCH が正しい。

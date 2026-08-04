---
id: 019-modify-tests-orchestrator-cites-nonexistent-test-names
type: modify
severity: 中
found: 2026-08-03
found_in: /doc-check task-impl-depth(check B5)。独立監査(サブエージェント / readiness)が3件を指摘し、Claude が全件をコードで走査
related: FR-orch-03, FR-orch-05, CTR-orchestrator-prompt, MODULE-orchestrator-plan, MODULE-orchestrator-trigger, MODULE-orchestrator-worker, MODULE-orchestrator-mode
summary: 【2026-08-04 に 8 件のうち 7 件を実名へ置換済み。残 1 件は `TestReadyTasks_Basic`(`tests/orchestrator.md:57`・`:110`)で、覆う範囲の判断が要るため本 issue は閉じない】docs/03-impl/tests/orchestrator.md が実在しないテスト識別子を「実装済み」の根拠として挙げている
---

## 事象

`docs/03-impl/tests/orchestrator.md` が挙げるテスト識別子のうち **8件がコードに存在しない**。
`docs/03-impl/tests/` と `docs/03-impl/relations/` の参照テスト 102 件を
`orchestrator/` `docker-proxy/` の `func Test*` と機械的に突き合わせて確認した(実在しないのはこの8件だけ)。

| 対応表の記述 | コードの実名 | 所属節 |
|---|---|---|
| `TestParseWorkerResult_StreamJSON` | `TestParseWorkerResultStreamJSON` | 受入基準 ⇄ テスト対応表 / 機能間連携仕様書 ⇄ テスト |
| `TestParseWorkerResult_Bare` | `TestParseWorkerResultBare` | 同上 |
| `TestParseWorkerResult_RealSample` | `TestParseWorkerResultRealSample` | 同上 |
| `TestEvaluate_StuckTakesPrecedence` | `TestEvaluate_StuckTakesPrecedenceOverNeedsHuman` | 同上 |
| `TestBuildPrompt_IncludesPolicy` | `TestBuildPrompt_IncludesPolicyWhenPresent` | 契約の結合テスト / 機能間連携仕様書 ⇄ テスト |
| `TestModeArgs_IncludesPolicy` | `TestModeArgs_IncludePolicyWhenPresent` | 契約の結合テスト |
| `TestVMModePreamble_VMMode` | `TestVMModePreamble_PrependedInVMMode` | 機能間連携仕様書 ⇄ テスト |
| `TestReadyTasks_Basic` | **一意に決まらない**。`plan_test.go` には `TestReadyTasks_DependencyResolution` / `TestReadyTasks_ParallelLimit` / `TestReadyTasks_FailedDepExcluded` がある | 受入基準 ⇄ テスト対応表(FR-orch-05 #2)/ 機能間連携仕様書 ⇄ テスト |

`MODULE-*.md` の `tests:` フロントマター側は**正しい名前**を持っている
(例: `MODULE-orchestrator-worker` は `TestParseWorkerResultStreamJSON`)。
食い違っているのは `tests/orchestrator.md` の対応表だけである。

## 影響

8件はいずれも状態が「実装済み」の行の根拠になっている。したがって
**「自動テストで固定されている」という主張が事実に反する行が存在する**。
`go test` を名指しで再実行しようとすると識別子が見つからず、再試験の手順が成立しない。

対象の受入基準は `FR-orch-03` #7、`FR-orch-05` #2、および `CTR-orchestrator-prompt` の結合テスト。
テスト自体は実在するので**振る舞いが検証されていないわけではない**(名前だけが古い)。
よって severity は「中」。

## 原因の見当

`_` 区切りの命名規約へ揃えようとした改名が、コード側とドキュメント側で片方だけ進んだ、
あるいはドキュメント作成時に規約から名前を推測して書いた、という**推測**。
`TestReadyTasks_Basic` は3つのテストへ分割された際に更新されなかった可能性がある(**推測**)。

## 正はどちらか

**コードが正**(テストが実在するかどうかは機械的に確かめられる事実であり、解釈の余地がない)。
`D0-scope-06`(旧ドキュメントとコードで表現が食い違う軽微な点はコードを正とする)の対象。

ただし `TestReadyTasks_Basic` は**どのテストを指していたかが一意に決まらない**ため、
`FR-orch-05` #2(未完了 plan の run 継続)と `MODULE-orchestrator-plan` を覆うのが
3つのうちどれか(あるいは3つ全部か)は確認が要る。

## 対処案

| 案 | 内容 |
|---|---|
| A | 7件を実名へ置換し、`TestReadyTasks_Basic` は覆う範囲を確認して1つ以上の実名へ置き換える。あわせて `relations/MODULE-*.md` の `tests:` と3つの表の表記を揃える |
| B | あわせて `.claude/scripts/` にテスト識別子の実在検査を追加する(`check-relations.py` は `impl` パスを検査するが `tests` の実在は検査していない)。`/kit-improve` 案件 |

B を入れると同種の乖離が機械で止まる。**`task-impl-depth` の範囲外**である
(同タスクは `tests/orchestrator.md` に行を追加するだけで既存行を変更しない方針であり、
この8件はいずれも変更前から SSOT に存在する)。

## 裁定の記録(2026-08-04)

**人間の裁定: 案B(`task-impl-depth` の反映には含めない)。別タスクで扱う。**
`task-impl-depth` の質問キュー #12「`issue 019` を本タスクの反映に含めるか」に対する回答である。

- 「コードが正」という判定自体は変わらない(テストが実在するかは機械的に確かめられる事実)。
  含めない理由は、本タスクの対象が `issue 004` の観点1〜5 と契約の型であり、
  テスト識別子の付け替えはその範囲外だからである。
- したがって `03-impl/index.md`「コードとの乖離として未解決のもの」に 8 件として残るのは正常である。
- 記録先をこの issue にした理由: 判断の経緯がタスクの `memo.md` にしか無いと、
  `/task-close` が memo.md を削除した時点で「誰がいつ先送りを決めたか」が失われる。

★2026-08-04 `/doc-check task-impl-depth` が「人間の裁定が memo.md にしか無い」ことを検出して追記した。

## 追加(2026-08-04 `/doc-check ssot task-impl-depth` の新しい実行)— 8件のうち 7 件を解消

`docs/03-impl/tests/orchestrator.md` に合格証を書く前提として、**実名が一意に決まる 7 件**を
本 issue の表どおりに置換した(機械的な綴りの誤りであり、新しい判断は含まない)。
`orchestrator/` と `docker-proxy/` の `*_test.go` から `func Test…` を機械抽出して照合し、
置換後の 7 件がすべて実在することを確認した。

| 置換前 | 置換後 |
|---|---|
| `TestParseWorkerResult_StreamJSON` | `TestParseWorkerResultStreamJSON` |
| `TestParseWorkerResult_Bare` | `TestParseWorkerResultBare` |
| `TestParseWorkerResult_RealSample` | `TestParseWorkerResultRealSample` |
| `TestEvaluate_StuckTakesPrecedence` | `TestEvaluate_StuckTakesPrecedenceOverNeedsHuman` |
| `TestBuildPrompt_IncludesPolicy` | `TestBuildPrompt_IncludesPolicyWhenPresent` |
| `TestModeArgs_IncludesPolicy` | `TestModeArgs_IncludePolicyWhenPresent` |
| `TestVMModePreamble_VMMode` | `TestVMModePreamble_PrependedInVMMode` |

**`relations/MODULE-orchestrator-trigger.md` と `-worker.md` の `tests:` は既に実名だった**
(誤名を持っていたのは `tests/orchestrator.md` だけ)。

### 残る 1 件 — **本 issue は閉じない**

`TestReadyTasks_Basic`(`docs/03-impl/tests/orchestrator.md:57`, `:110` の2箇所)は
`plan_test.go` に同名が無く、`TestReadyTasks_DependencyResolution` /
`TestReadyTasks_ParallelLimit` / `TestReadyTasks_FailedDepExcluded` のどれに対応するかが
**一意に決まらない**(`FR-orch-05` 受入基準2 が「どの範囲を覆えば実装済みと言えるか」に依存する)。
これは記述の選択ではなくテストの覆う範囲の判断なので、`/doc-check` の委任範囲外である。
`issue 038` / `issue 032` の全面揃えタスクで、覆う範囲を確認して実名へ置き換えること。

**なお 8 件はいずれも「テスト自体が無い」のではなく「識別子の綴りが違う」ものだったので、
`実装済み` という状態そのものは substantively 正しかった**(severity「中」の据え置きは妥当)。

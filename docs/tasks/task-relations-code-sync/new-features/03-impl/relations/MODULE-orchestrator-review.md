---
target: docs/03-impl/relations/MODULE-orchestrator-review.md
change: replace
sections:
  - "## 処理の流れ"
  - "## 戻り値・副作用"
  - "## 呼び出され方"
  - "### MODULE-orchestrator-worker"
deletes: []
reason: 戻り値を「findings[] とゲート通過可否」と書くが実体は (GateOutcome, error)(docs/issues/038 #14)。ReviewFormatErrors の加算主体が違う(同 #15)。レビュアログのパスが実体と違う(同 #27)。callees に claude-exec が無い(同 #12 の対称)
id: MODULE-orchestrator-review
module: MOD-orchestrator
kind: function-call
sync: sync
impl: orchestrator/review.go::Reviewer.RunGate, orchestrator/review.go::ParseReviewResult
callers: MODULE-orchestrator-controller
callees: MODULE-orchestrator-claude-exec, MODULE-orchestrator-state, MODULE-orchestrator-state-intervention, MODULE-orchestrator-worker
contracts: CTR-orchestrator-prompt
design: DSN-mod-01, DSN-orch-01
requirements: FR-orch-06
tests: orchestrator/accept_test.go::TestReview_ReformatsProseToJSON, orchestrator/review_parse_test.go::TestFindReviewResultJSON_StrictAndTolerant
updated: 2026-08-05
summary: worker の成果をレビューし重大指摘があれば差し戻す品質ゲート
---

<!-- 変更指示。反映後の最終形を書く。version / verified は持たない。
     callees に MODULE-orchestrator-claude-exec を追加した(review.go:81・:126 が Claude.RunPrompt を呼ぶ)。 -->

## 処理の流れ

1. `Reviewer.RunGate(ctx context.Context, p *Plan, t *Task)` が1つの Attempt に対する
   「レビュー → 差し戻し」のループを回す。**レビュア自身の起動は `Reviewer.Review` が
   `MODULE-orchestrator-claude-exec` の `RunPrompt` を直接呼ぶ**(`reviewerProfile` = opus / high。
   worktree を CWD にし、ログは `workers/<taskID>.review.log`)。
   **`MODULE-orchestrator-worker` の `Worker.Dispatch` を使うのは差し戻し(revise)のときだけ**である。
2. **採点基準は `Task.Completion` のみ**とする(`Plan.Completion` や `Goal` へのフォールバックは
   禁止。`Plan.Goal` は「文脈のみ・採点に使うな」と明示してプロンプトへ入れる)。
   1回のレビューで2観点(①要件充足・動作 ②セキュリティ・エラー処理・保守性)を評価させる。
3. 出力は構造化(`findings[]`: `severity` = critical / major / minor、`file`、`message`、`aspect`)を
   **プロンプトで要求する**。**`{"findings":[]}` が合格**、`critical` / `major` が1件でもあれば差し戻しになる。
   **ただし検証は「`findings` キーが在るか」だけ**である(`orchestrator/review.go:296`〜`:312` の
   `tryReviewResult`)。各 finding の必須項目も **`severity` の値域も検証しない**ため、
   `severity` が未知の値(綴り違い・別語彙)の指摘は `HasSevere` の完全一致
   (`critical` / `major`)に当たらず、**重大でない扱いでゲートを通過する**(`docs/issues/058-bug-unknown-severity-passes-the-review-gate.md`)。
4. `ParseReviewResult` が結果を解釈する。`findReviewResultJSON` が
   (a) 最終行の厳密一致を優先し、(b) フェンスを除去してブレース対応でスキャンし
   (`findJSONObjects`)、`findings` キーを持つ最後のオブジェクトを拾う。
   共通の封筒解釈は `MODULE-orchestrator-worker` の `extractFromClaudeEnvelope` /
   `resultFromStream` を使う。
5. それでもパースできなければ `reformatToJSON` を1回だけ試す(散文の結論を haiku / low で規定の
   JSON へ変換する。判定内容は変えない)。成功したら `review_reformat_ok` を audit に残す。
6. 重大な severity が残る間は revise を繰り返す(`max_review_rounds` まで。`Attempts` は増やさない)。
7. **フォーマット違反と内容不合格を分離する**: パース不能なら**ローカル変数 `formatErrs` を増やし**
   (`orchestrator/review.go:181`・`:197`)、`review_format_error` を監査ログへ追記して、
   **実作業を再ディスパッチせずレビューだけ再試行**する(**この再試行はレビュー往復数を消費しない**)。
   **`RunGate` 自身は live な `Task.ReviewFormatErrors` に代入しない**: 上限に達したときに
   `GateOutcome.FormatErrorCount` として返し(`:203`)、それを `plan.json` の
   `Task.ReviewFormatErrors` へ書くのは呼び出し元の `MODULE-orchestrator-controller`
   (`controller.go:685`)である。内容の判定が1回でも解釈できたら `formatErrs` は 0 に戻り(`:207`)、
   `Task.ReviewFormatErrors` の 0 リセットも呼び出し元(`controller.go:699`)が行う。
   `review_format_error_limit`(既定 2。**設定値が 0 以下なら 2 として扱う**)に
   達したら `review_gate_defect` として介入キューへ積む(seed に「completion 充足の一次確認」と
   `accept` / `resume` の指示を添えて介入ループを断つ)。内容不合格の場合は
   連続回数をリセットして revise を続ける。上限に達しても重大指摘が残っていれば
   条件3のトリガーへ回す。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | **`(GateOutcome, error)`**(`orchestrator/review.go:161`〜`:167` / `:179`)。`GateOutcome` は `Passed`(重大指摘が残っていない)/ `LastSevere`(重大指摘の要約。差し戻しと行き詰まりの材料)/ `FormatError`(フォーマットエラーが上限に達した)/ `FormatErrorCount` の4つで、**`findings[]` は返さない**(指摘の生データは `Reviewer.Review` の内部で消費される)。`error` が非 `nil` になるのは**中断(context キャンセル)と revise の失敗だけ**である |
| 永続化 | `audit.jsonl` への追記(`review_reformat_ok`(`:94`)/ `review_result`(`:101`。`usage` が非 `null` のときだけ)/ `review_format_error`(`:198`)/ `revise_error`(`:242`))。**`plan.json` はこの機能が書かない**: `Task.ReviewFormatErrors` の更新は戻り値を受けた `MODULE-orchestrator-controller`(`controller.go:685`・`:699`)が行う |
| 発火するイベント | なし |
| ログ | **`workers/<taskID>.review.log`**(`review.go:79` が `WorkerLogPath(t.ID + ".review")` を渡す)。worker 本体の `workers/<taskID>.log` とは**別ファイル**で、整形ライタ(`MODULE-orchestrator-streamlog`)は同じものを通る。再整形の呼び出し(`:126`)は `logPath` に空文字を渡すので**ログを残さない** |

## 呼び出され方

- 契機: `MODULE-orchestrator-controller` が worker の実装完了を受けて品質ゲートを通すとき。
- 前提条件: 対象タスクの worktree にコミットがあること。`Task.Completion` が非空であること。
- 引数(実シグネチャは `Reviewer.RunGate(ctx context.Context, p *Plan, t *Task) (GateOutcome, error)`。
  `orchestrator/review.go:179`):

| 引数 | 型 | 必須 | 制約 | 実装が行う検証 |
|---|---|---|---|---|
| `ctx` | `context.Context` | 必須 | 中断時にキャンセルされる。キャンセルは `error` として呼び出し元へ伝播する(唯一の非 `nil` error 経路の1つ) | **検証しない**(プロセス内呼び出し) |
| `p` | `*Plan` | 必須 | レビュープロンプトの文脈(`Plan.Goal` を「採点に使うな」と明示して載せる)と、revise を `MODULE-orchestrator-worker` へ回すときの引数に使う | 検証しない |
| `t` | `*Task` | 必須 | `Completion` が**唯一の採点基準**。`Status` を `review` へ書き、`ID` はレビュアログのパス要素になる。**`ReviewFormatErrors` はこの機能が更新しない**(戻り値の `GateOutcome.FormatErrorCount` を受けた `MODULE-orchestrator-controller` が書く) | 検証しない。`Task.Completion` が空でも呼べるが、plan の検査が実行前に弾く |

- 認可: プロセス内呼び出し。

### MODULE-orchestrator-worker

- 何のために呼ぶか: **(1) 差し戻し(revise)のディスパッチ**と、**(2) 応答封筒の解釈**
  (`extractFromClaudeEnvelope` / `resultFromStream`)のため。
  **レビュア自身の起動には使わない**: `Reviewer.Review` が `MODULE-orchestrator-claude-exec` の
  `RunPrompt` を直接呼ぶ(`orchestrator/review.go:81`)。
- 何を渡すか: revise では `Worker.Dispatch(ctx, p, t, feedback)` に重大指摘の要約を `feedback` として
  渡す。封筒解釈では stream-json のバイト列。 / 何を受け取るか: revise は `*WorkerResult` とエラー、
  封筒解釈は復号済みの結果。
- **失敗したときどうなるか**: revise のディスパッチが失敗した場合は `Attempts` を保持したまま
  条件3のトリガーへ回す(エラーで `Attempts` が巻き戻らないようにしてある)。

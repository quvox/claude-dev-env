---
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

# MODULE-orchestrator-review 品質ゲート(相互レビュー)

## 目的

実装した worker とは**別の** worker に独立レビューさせ、重大な指摘が残る間は改訂を繰り返す
(FR-orch-06)。自己レビューを避けることが要件であり、この機能がそれを構造として保証する。

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
   **ただし検証は (a) JSON オブジェクトとして復号できること (b) `findings` キーが在ること
   (c) `ReviewResult` 型へ復号できること の3点だけ**である(`orchestrator/review.go:296`〜`:312` の
   `tryReviewResult`)。(c) が弾くのは `findings` を `[]Finding` へ復号できないとき(数値・文字列・オブジェクト、および
   `[1]` のように要素が `Finding` にならない配列)である。**`{"findings":null}` は nil スライスとして
   復号できるので通る** —
   このとき `HasSevere` は偽になり、**指摘が1件も無かったのと同じ扱いでゲートを通過する**
   (`Findings []Finding`。`orchestrator/review.go:20`)。
   各 finding の必須項目も **`severity` の値域も検証しない**ため、
   `severity` が未知の値(綴り違い・別語彙)の指摘は `HasSevere` の完全一致
   (`critical` / `major`)に当たらず、**重大でない扱いでゲートを通過する**(`docs/issues/058-bug-unknown-severity-passes-the-review-gate.md`)。
4. `ParseReviewResult` が結果を解釈する。`findReviewResultJSON` が
   (a) 末尾の行から順に「その行全体が JSON オブジェクト」であるものを探し、
   (b) 見つからなければ**フェンスを除去せず出力全体を**ブレース対応でスキャンして
   (`findJSONObjects`)、`findings` キーを持つ最後のオブジェクトを拾う
   (フェンスや前置きの散文は、対応の取れた `{...}` だけを拾うことで結果的に無視される)。
   共通の封筒解釈は `MODULE-orchestrator-worker` の `extractFromClaudeEnvelope` /
   `resultFromStream` を使う。
5. それでもパースできなければ `reformatToJSON` を1回だけ試す(散文の結論を haiku / low で規定の
   JSON へ変換する)。**「内容は一切変えず」はプロンプトの文言で要求しているだけで、
   コードは元の結論と変換結果を突き合わせない**(`:126` の `RunPrompt` の戻り値を
   `:130` でそのまま `ParseReviewResult` に渡すだけである)。したがって**変換で判定が変わっていないことは保証されない**。
   成功したら `review_reformat_ok` を audit に残す。
6. 重大な severity が残る間は revise を繰り返す(`max_review_rounds` まで。`Attempts` は増やさない)。
   **ただし revise の結果が `NeedsHuman` を持っていたら、往復の残りがあってもそこで打ち切る**:
   `t.Result` にその結果を代入して `(GateOutcome{LastSevere}, nil)` を返し、
   判断は呼び出し元へ委ねる(`orchestrator/review.go:232`〜`:235`)。
7. **フォーマット違反と内容不合格を分離する**: パース不能なら**ローカル変数 `formatErrs` を増やし**
   (`orchestrator/review.go:181`・`:197`)、`review_format_error` を監査ログへ追記して、
   **実作業を再ディスパッチせずレビューだけ再試行**する(**この再試行はレビュー往復数を消費しない**)。
   **`RunGate` 自身は live な `Task.ReviewFormatErrors` に代入しない**: 上限に達したときに
   `GateOutcome.FormatErrorCount` として返し(`:203`)、それを `plan.json` の
   `Task.ReviewFormatErrors` へ書くのは呼び出し元の `MODULE-orchestrator-controller`
   (`controller.go:685`)である。内容の判定が1回でも解釈できたら `formatErrs` は 0 に戻り(`:207`)、
   `Task.ReviewFormatErrors` の 0 リセットも呼び出し元(`controller.go:699`)が行う。
   `review_format_error_limit`(既定 2。**設定値が 0 以下なら 2 として扱う**)に
   達したら `GateOutcome{FormatError: true, FormatErrorCount}` を返して呼び出し元へ渡す。
   **`review_gate_defect` として介入キューへ積むのはこの機能ではなく
   `MODULE-orchestrator-controller` である**(seed に「completion 充足の一次確認」と
   `accept` / `resume` の指示を添えて介入ループを断つ)。内容不合格の場合は
   連続回数をリセットして revise を続ける。上限に達しても重大指摘が残っていれば
   条件3のトリガーへ回す。

## 呼び出され方

- 契機: `MODULE-orchestrator-controller` が worker の実装完了を受けて品質ゲートを通すとき。
- 前提条件: 対象タスクの worktree にコミットがあること。`Task.Completion` が非空であること。
- 引数(実シグネチャは `Reviewer.RunGate(ctx context.Context, p *Plan, t *Task) (GateOutcome, error)`。
  `orchestrator/review.go:179`):

| 引数 | 型 | 必須 | 制約 | 実装が行う検証 |
|---|---|---|---|---|
| `ctx` | `context.Context` | 必須 | 中断時にキャンセルされる。キャンセルは `error` として呼び出し元へ伝播する。**これがこの関数で `error` が非 `nil` になる唯一の経路**である(`:191` と `:221` の2箇所。どちらも `ctx.Err() != nil` が条件) | **検証しない**(プロセス内呼び出し) |
| `p` | `*Plan` | 必須 | レビュープロンプトの文脈(`Plan.Goal` を「採点に使うな」と明示して載せる)と、revise を `MODULE-orchestrator-worker` へ回すときの引数に使う | 検証しない |
| `t` | `*Task` | 必須 | `Completion` が**唯一の採点基準**。`Status` を `review` へ書き、`ID` はレビュアログのパス要素になる。**`ReviewFormatErrors` はこの機能が更新しない**(戻り値の `GateOutcome.FormatErrorCount` を受けた `MODULE-orchestrator-controller` が書く) | 検証しない。`Task.Completion` が空でも呼べるが、plan の検査が実行前に弾く |

- 認可: プロセス内呼び出し。

## 連携先と連携内容

### MODULE-orchestrator-claude-exec

- 何のために呼ぶか: **レビュアそのものを起動するため**(`Reviewer.Review` が
  `ClaudeRunner.RunPrompt` を直接呼ぶ。`orchestrator/review.go:81`)と、**散文の再整形**のため
  (`reformatToJSON`。`orchestrator/review.go:126`)。**インターフェース `ClaudeRunner`
  (`orchestrator/worker.go:47`〜`:52`)越しの呼び出し**なので、静的コールグラフには
  呼び出し辺が出ない(実体は `orchestrator/worker.go:350` の `ExecClaude.RunPrompt`)。
- 何を渡すか: レビューでは worktree の絶対パス・`reviewerProfile()` のモデル(opus)・
  レビュープロンプト・ログのパス(`workers/<taskID>.review.log`)・
  `RunOpts{GraceSeconds, Effort: high}`。再整形では **worktree を CWD にしたまま**モデル `haiku` /
  `Effort: low` を渡し、**ログのパスは空文字**にする(表示ログにはレビュー本体が既に残っているため)。
   / 何を受け取るか: stream-json の生バイト列とエラー。
- **失敗したときどうなるか**: どちらの経路も `Review` が `(nil, err)` を返し、`RunGate`
  (`orchestrator/review.go:189`〜`:203`)が受ける。**そこで伝播するのは中断のときだけ**である:
  `ctx.Err()` が非 `nil` なら `(GateOutcome{}, rerr)` を返して呼び出し元へ伝える。
  **中断でないエラーはすべて「フォーマットエラー」として扱う** — `formatErrs` を増やし、
  エラー文字列を含む `review_format_error` を監査ログへ追記し、**worker を再ディスパッチせず
  レビューだけをやり直す**(このやり直しはレビュー往復数を消費しない)。
  `review_format_error_limit` に達したら `GateOutcome{FormatError: true, FormatErrorCount}` を
  **`error` は `nil` のまま**返す。したがって、**`claude` の起動失敗やモデル側のエラーは
  「レビュアの出力が壊れていた」と同じ扱いになり、区別されない**。

### MODULE-orchestrator-worker

- 何のために呼ぶか: **(1) 差し戻し(revise)のディスパッチ**と、**(2) 応答封筒の解釈**
  (`extractFromClaudeEnvelope` / `resultFromStream`)のため。
  **レビュア自身の起動には使わない**: `Reviewer.Review` が `MODULE-orchestrator-claude-exec` の
  `RunPrompt` を直接呼ぶ(`orchestrator/review.go:81`)。
- 何を渡すか: revise では `Worker.Dispatch(ctx, p, t, feedback)` に重大指摘の要約を `feedback` として
  渡す。**実際の文字列は固定の指示文 `Address these review findings (this is a revise, not a new approach):`
  に続けて要約を連ねたもの**である(`orchestrator/review.go:218`)。封筒解釈には stream-json の文字列を渡す。
   / 何を受け取るか: revise は `*WorkerResult` とエラー。**封筒解釈が返すのは復号済みの結果ではなく
  封筒の中の `result` テキスト(文字列)**で、それを `findReviewResultJSON` が復号する。
- **失敗したときどうなるか**: revise のディスパッチが失敗した場合は `Attempts` を保持したまま
  条件3のトリガーへ回す(エラーで `Attempts` が巻き戻らないようにしてある)。

### MODULE-orchestrator-state

- 何のために呼ぶか: worktree の絶対パス(`WorktreeAbs`)、レビュアログのパス(`WorkerLogPath`)、
  `ORCHESTRATOR.md`(`LoadProjectPolicy`)の取得。
- 何を渡すか: `WorktreeAbs` にはタスク ID(`orchestrator/review.go:78`)、`WorkerLogPath` には
  **`t.ID + ".review"`**(`:79`。worker のログと同じディレクトリに `.review` 付きで分けるため)、
  `LoadProjectPolicy` には **`rv.Worker.Workspace`**(`:142`。Reviewer は自分では
  ワークスペースを持たず Worker のものを使う)。 / 何を受け取るか: パスと前置文。
- **失敗したときどうなるか**: 前置なしでレビューを行う。

### MODULE-orchestrator-state-intervention

- 何のために呼ぶか: レビューの経過(`review_reformat_ok` など)を `audit.jsonl` へ追記するため。
- 何を渡すか: 監査レコード。 / 何を受け取るか: エラー。
- **失敗したときどうなるか**: 監査が欠落するだけで、ゲートの判定は変わらない。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | **`(GateOutcome, error)`**(`orchestrator/review.go:161`〜`:167` / `:179`)。`GateOutcome` は `Passed`(重大指摘が残っていない)/ `LastSevere`(重大指摘の要約。差し戻しと行き詰まりの材料)/ `FormatError`(フォーマットエラーが上限に達した)/ `FormatErrorCount` の4つで、**`findings[]` は返さない**(指摘の生データは `Reviewer.Review` の内部で消費される)。**`error` が非 `nil` になるのは context がキャンセルされたときだけ**である(`:191` のレビュー中断と `:221` の revise 中断の2箇所。どちらも `ctx.Err() != nil` が条件)。**中断でない revise のディスパッチ失敗は `error` にならない**: `revise_error` を監査へ追記して `lastSevere` を保ったままループを抜け、`(GateOutcome{LastSevere}, nil)` を返す(`:222`〜`:229` で `break` し `:237` で返る。エラーを上げると controller が一過性の失敗として再ディスパッチし、行き詰まりの信号が消えるため) |
| 永続化 | `audit.jsonl` への追記(`review_reformat_ok`(`:94`)/ `review_result`(`:101`。`usage` が非 `null` のときだけ)/ `review_format_error`(`:198`)/ `revise_error`(`:242`))。**`plan.json` のファイルはこの機能が書かない**が、**共有 plan 上の `Task` は書き替える**: `t.Status` を `review` / `revise` へ、revise が結果を返したら `t.Result` へ代入する(`orchestrator/review.go:188`・`:217`・`:231`)。`Task.ReviewFormatErrors` の更新は戻り値を受けた `MODULE-orchestrator-controller`(`controller.go:685`・`:699`)が行う |
| 発火するイベント | なし |
| ログ | **`workers/<taskID>.review.log`**(`review.go:79` が `WorkerLogPath(t.ID + ".review")` を渡す)。worker 本体の `workers/<taskID>.log` とは**別ファイル**で、整形ライタ(`MODULE-orchestrator-streamlog`)は同じものを通る。再整形の呼び出し(`:126`)は `logPath` に空文字を渡すので**ログを残さない** |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| レビュー結果がパースできない | `reformatToJSON` で1回回収を試み、なお不能なら**ローカル変数 `formatErrs` を増やして**(`plan.json` の `Task.ReviewFormatErrors` には代入しない)**レビューのみ再試行**する。上限未満のあいだは呼び出し元へ返らずループ内で繰り返す | 実作業はやり直さない |
| `review_format_error_limit` に到達 | **この機能は `GateOutcome{FormatError: true, FormatErrorCount}` を `error` は `nil` のまま返すだけ**である。`review_gate_defect` として介入キューへ積むのは戻り値を受けた `MODULE-orchestrator-controller` | 人間の判断待ちになる |
| `max_review_rounds` に到達しても重大指摘が残る | 条件3のトリガーへ回す | `waiting_human` になる |
| `Task.Completion` が空 | 採点基準が無いため、controller 側の `reportNotExecutable` で executing に入る前に弾かれる | ここには到達しない |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 採点基準を `Task.Completion` のみに限定し、`Plan.Completion` / `Goal` へフォールバックしない(基準が曖昧になると差し戻しが恣意的になる) | D0-orch-05 |
| 2 | 散文を JSON へ再整形する経路を1回だけ設ける。**判定内容を変えないことはプロンプトで要求するだけで、コードは元の結論と突き合わせない**(処理の流れ 5) | D0-orch-05 |
| 3 | revise では `Attempts` を増やさない(行き詰まり判定は Attempt 単位のため) | D0-orch-05 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| **構造化出力がスキーマ強制(tool-forced)ではない**。レビュアの起動引数に**出力の JSON スキーマを渡す仕組みが無い**(`--output-format stream-json` が指定するのは CLI のストリーム出力形式であって、レビュー結果の構造ではない。`orchestrator/worker.go:355`〜`:365`)。プロンプト本文に `OUTPUT FORMAT — MANDATORY.` と書いて JSON を要求しているにすぎない(`orchestrator/review.go:66`〜`:70` / `orchestrator/worker.go:355`。`json_schema` / `tool_choice` の指定は 0 件) | 形式崩れが起きうる。寛容パースと `reformatToJSON` の1回の再整形で吸収し、`review_format_error_limit` 回続けば介入へ回す | なし(**裁定済み・不一致は解消**: `docs/issues/034` として起票し 2026-08-04 に人間が「実装が正」と裁定した。`FR-orch-06` 受入基準3 は「プロンプトで JSON の形を明示して構造化出力を要求する。**ツールによるスキーマ強制は行わない**」へ、`D0-orch-15` も同じ形へ改まったので、**現在は 01・02 との不一致は存在しない**。ここに残すのは仕様どおりの制限としての記述である) |
| `reviewer_vendor: codex`(別ベンダーレビュー)はフェーズ2 | v1 は常に Claude がレビューする。設定キー自体は読めるが選択には使われない | `docs/issues/012-modify-reviewer-vendor-setting-has-no-effect.md`(設定が無効であることを起票済み) |

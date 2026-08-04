---
id: MODULE-orchestrator-review
module: MOD-orchestrator
kind: function-call
sync: sync
impl: orchestrator/review.go::Reviewer.RunGate, orchestrator/review.go::ParseReviewResult
callers: MODULE-orchestrator-controller
callees: MODULE-orchestrator-state, MODULE-orchestrator-state-intervention, MODULE-orchestrator-worker
contracts: CTR-orchestrator-prompt
design: DSN-mod-01, DSN-orch-01
requirements: FR-orch-06
tests: orchestrator/accept_test.go::TestReview_ReformatsProseToJSON, orchestrator/review_parse_test.go::TestFindReviewResultJSON_StrictAndTolerant
updated: 2026-08-04
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
   **ただし検証は「`findings` キーが在るか」だけ**である(`orchestrator/review.go:296`〜`:312` の
   `tryReviewResult`)。各 finding の必須項目も **`severity` の値域も検証しない**ため、
   `severity` が未知の値(綴り違い・別語彙)の指摘は `HasSevere` の完全一致
   (`critical` / `major`)に当たらず、**重大でない扱いでゲートを通過する**(`docs/issues/038`)。
4. `ParseReviewResult` が結果を解釈する。`findReviewResultJSON` が
   (a) 最終行の厳密一致を優先し、(b) フェンスを除去してブレース対応でスキャンし
   (`findJSONObjects`)、`findings` キーを持つ最後のオブジェクトを拾う。
   共通の封筒解釈は `MODULE-orchestrator-worker` の `extractFromClaudeEnvelope` /
   `resultFromStream` を使う。
5. それでもパースできなければ `reformatToJSON` を1回だけ試す(散文の結論を haiku / low で規定の
   JSON へ変換する。判定内容は変えない)。成功したら `review_reformat_ok` を audit に残す。
6. 重大な severity が残る間は revise を繰り返す(`max_review_rounds` まで。`Attempts` は増やさない)。
7. **フォーマット違反と内容不合格を分離する**: パース不能なら `Task.ReviewFormatErrors++` とし、
   **実作業を再ディスパッチせずレビューだけ再試行**する(**この再試行はレビュー往復数を消費しない**)。
   `review_format_error_limit`(既定 2。**設定値が 0 以下なら 2 として扱う**)に
   達したら `review_gate_defect` として介入キューへ積む(seed に「completion 充足の一次確認」と
   `accept` / `resume` の指示を添えて介入ループを断つ)。内容不合格の場合は
   `ReviewFormatErrors` をリセットして revise を続ける。上限に達しても重大指摘が残っていれば
   条件3のトリガーへ回す。

## 呼び出され方

- 契機: `MODULE-orchestrator-controller` が worker の実装完了を受けて品質ゲートを通すとき。
- 前提条件: 対象タスクの worktree にコミットがあること。`Task.Completion` が非空であること。
- 引数:

| 引数 | 型 | 必須 | 制約 | 実装が行う検証 |
|---|---|---|---|---|
| `task` | `*Task` | 必須 | `Completion` が採点基準。`ReviewFormatErrors` を更新する | **検証しない**(プロセス内呼び出し)。`Task.Completion` が空でも呼べるが、plan の検査が実行前に弾く |
| `ctx` | `context.Context` | 必須 | 中断時にキャンセルされる | 同上 |

- 認可: プロセス内呼び出し。

## 連携先と連携内容

### MODULE-orchestrator-worker

- 何のために呼ぶか: レビュア / revise の `claude -p` 実行と、応答封筒の解釈
  (`extractFromClaudeEnvelope` / `resultFromStream`)のため。
- 何を渡すか: レビュープロンプトと profile。 / 何を受け取るか: stream-json の結果。
- **失敗したときどうなるか**: revise のディスパッチが失敗した場合は `Attempts` を保持したまま
  条件3のトリガーへ回す(エラーで `Attempts` が巻き戻らないようにしてある)。

### MODULE-orchestrator-state

- 何のために呼ぶか: worktree の絶対パス(`WorktreeAbs`)、worker ログのパス(`WorkerLogPath`)、
  `ORCHESTRATOR.md`(`LoadProjectPolicy`)の取得。
- 何を渡すか: タスク ID。 / 何を受け取るか: パスと前置文。
- **失敗したときどうなるか**: 前置なしでレビューを行う。

### MODULE-orchestrator-state-intervention

- 何のために呼ぶか: レビューの経過(`review_reformat_ok` など)を `audit.jsonl` へ追記するため。
- 何を渡すか: 監査レコード。 / 何を受け取るか: エラー。
- **失敗したときどうなるか**: 監査が欠落するだけで、ゲートの判定は変わらない。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | レビュー結果(`findings[]`)と、ゲートを通過したかどうか |
| 永続化 | `audit.jsonl` への追記、`Task.ReviewFormatErrors` の更新(`plan.json` に反映される) |
| 発火するイベント | なし |
| ログ | `workers/<taskID>.log`(レビュアの出力も同じ整形ライタを通る) |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| レビュー結果がパースできない | `reformatToJSON` で1回回収を試み、なお不能なら `ReviewFormatErrors++` して**レビューのみ再試行**する | 実作業はやり直さない |
| `review_format_error_limit` に到達 | `review_gate_defect` として介入キューへ積む | 人間の判断待ちになる |
| `max_review_rounds` に到達しても重大指摘が残る | 条件3のトリガーへ回す | `waiting_human` になる |
| `Task.Completion` が空 | 採点基準が無いため、controller 側の `reportNotExecutable` で executing に入る前に弾かれる | ここには到達しない |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 採点基準を `Task.Completion` のみに限定し、`Plan.Completion` / `Goal` へフォールバックしない(基準が曖昧になると差し戻しが恣意的になる) | D0-orch-05 |
| 2 | 散文を JSON へ再整形する経路を1回だけ設け、判定内容は変えない | D0-orch-05 |
| 3 | revise では `Attempts` を増やさない(行き詰まり判定は Attempt 単位のため) | D0-orch-05 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| **構造化出力がスキーマ強制(tool-forced)ではない**。レビュアの起動引数は `-p <prompt> --output-format stream-json --verbose` だけで、プロンプト本文に `OUTPUT FORMAT — MANDATORY.` と書いて JSON を要求しているにすぎない(`orchestrator/review.go:66`〜`:70` / `orchestrator/worker.go:355`。`json_schema` / `tool_choice` の指定は 0 件) | 形式崩れが起きうる。寛容パースと `reformatToJSON` の1回の再整形で吸収し、`review_format_error_limit` 回続けば介入へ回す | なし(**裁定済み・不一致は解消**: `docs/issues/034` として起票し 2026-08-04 に人間が「実装が正」と裁定した。`FR-orch-06` 受入基準3 は「プロンプトで JSON の形を明示して構造化出力を要求する。**ツールによるスキーマ強制は行わない**」へ、`D0-orch-15` も同じ形へ改まったので、**現在は 01・02 との不一致は存在しない**。ここに残すのは仕様どおりの制限としての記述である) |
| `reviewer_vendor: codex`(別ベンダーレビュー)はフェーズ2 | v1 は常に Claude がレビューする。設定キー自体は読めるが選択には使われない | `docs/issues/012-modify-reviewer-vendor-setting-has-no-effect.md`(設定が無効であることを起票済み) |

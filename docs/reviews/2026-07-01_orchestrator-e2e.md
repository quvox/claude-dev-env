# オーケストレーター 実機 E2E 動作確認（自己検証サンプル）

日付: 2026-07-01
対象: `orchestrator/`（タスク単位介入・中断再開の作業保全・品質ゲート是正）
方法: 同梱サンプル `examples/orch-sample`（mathkit）を `make orch-sample SEED=1` で scaffold し、ローカルビルドした本体を実 `claude -p` worker で駆動（[docs/07_self-verification.md](../07_self-verification.md) のシナリオ S1〜S5）。

実行コマンド:
```
make build-orchestrator && make orch-sample FORCE=1 SEED=1
orchestrator/orchestrator --workspace workspace/orch-sample \
  --instructions orchestrator/instructions --start-executing "$(cat examples/orch-sample/GOAL.md)"
```

## 結果サマリ

| シナリオ | 結果 | 根拠 |
|---|---|---|
| S1 介入で peer を止めない | ✅ | `t-announce`(irreversible) が `waiting_human` に parked（attempts=0＝未ディスパッチ）。その間に `t-stats`/`t-strings`/`t-geometry` が並行実行→attempt 1 で `done`→`main` へマージ。`pytest` 12/12 green（実装が正しい） |
| S2/S3 中断/再開で完了タスクを再実行しない | ✅ | SIGTERM で「↩️ 前回の executing フェーズから再開」→ 再開後の `dispatch` イベント数が変化なし（各 done タスク 1 回のまま）。`task_done`×3 の重複なし、マージ重複なし、`pytest` 12/12 維持 |
| S4 レビューはタスク固有 completion で採点 | ✅ | 各タスク attempt 1・revise 0 で合格（別タスク責務での誤 critical なし） |
| S5 複数同時介入 | ✅ | 初回走行時 `intervention/open.json` に 4 件同時（t-announce=irreversible ＋ 3 件=review_gate_defect）。キューが複数を同時保持 |
| 品質ゲート フォーマット違反の扱い（MODIFICATION #3/#5） | ✅ | レビュー出力パース不能時、worker を再ディスパッチせず 2 回で `review_gate_defect` にエスカレーション（実作業のやり直しなし） |

## 実機検証で発見し修正した不具合（単体テストで見逃していたもの）

1. **相対 `--workspace` で worktree パスが二重ネスト（exit 128 で全タスク stuck）**
   - 症状: `git worktree add` が `exit status 128`。`git worktree list` で `.../workspace/orch-sample/workspace/orch-sample/.orchestrator/worktrees/...` の二重パスを確認。
   - 原因: Store のパスが相対で、`git` の `cmd.Dir`（相対 repoDir）配下に相対 worktree パスが解決され二重化。単体テストは `t.TempDir()`（絶対）を使うため未検出。本番の `--workspace /workspace`（絶対）でも未発生。
   - 修正: `main.go` で `filepath.Abs(workspace)` に正規化。
   - なお、この不具合下でも**新設計の安全網は機能**（全タスクが個別に stuck 介入へ。クラッシュせず）。

2. **`ParseReviewResult` が stream-json 出力を解釈できない**
   - 症状: 全レビューが「no parseable ReviewResult JSON」→ `review_gate_defect` 介入。
   - 原因: レビュアも `--output-format stream-json` で起動するのに、`ParseReviewResult` が（`ParseWorkerResult` と違い）`resultFromStream` を通さず最終 result イベント内の JSON を取り出せていなかった。
   - 修正: `ParseReviewResult` を `ParseWorkerResult` と同型化（stream-json → envelope → bare の順で `findReviewResultJSON`）。
   - なお、この不具合下でも**「フォーマット違反は実作業を再実行しない」挙動は機能**（worker 再ディスパッチ 0）。

## 所見

- 4 観点（要件/ユースケース合致・無駄処理・処理時間・セキュリティ）:
  - 要件合致: S1〜S5 と MODIFICATION 方針の実挙動を確認。ユースケース（並行・介入・中断再開・ゲート）を満たす。
  - 無駄処理: 完了タスクの再実行・フォーマット違反時の実作業やり直しが無いことを実測で確認。
  - 処理時間: 単体テストは waitFor ポーリングで最長 ~120s（-race ~312s）。実 E2E は小規模サンプルで数分。
  - セキュリティ: worker は worktree 隔離・`SLACK_BOT_TOKEN` 非付与・後戻り不可操作は介入ゲート（irreversible）で停止（t-announce/t-release が未ディスパッチで parked）を確認。
- 上記 2 修正はコードへ反映済み。`go build`/`vet`/`test`（`-race` 含む）緑・`gofmt` 済み。
- 残: S5 の「[i] でまとめて回答→復帰」を対話 TUI 上で人手確認（headless の本検証では open.json への同時 4 件までを確認）。t-release（統合後の irreversible）の承認後実行は t-announce 承認が前提のため未到達。

---

## 追補: 整合性是正後の再動作確認（同日）

仕様↔実装の整合性是正（`NormalizeForResume` の `ResumeSession` 付与ほか）後、修正版バイナリで再検証。

- **Part 1（実 claude・回帰）**: 再 scaffold→実行で S1 再確認。`t-stats`/`t-strings`/`t-geometry` が attempt 1 で done（各 dispatch 1 回）、`t-announce` は attempts=0 で parked、pytest 12/12。回帰なし。
- **Part 2（決定論・スクリプト claude で resume 経路を検証）**: クラッシュ状態（`t1`=running+`session_id`、`t2`=done、`t3`=pending）を手作りし、実バイナリで再開。結果:
  - `t1`: `--resume`（`resume=1 session=SESS-CRASH-1`）で同一セッション再開・**attempts 据置(1)**・done。
  - `t2`: worker 呼び出しなし（done を再実行しない）。
  - `t3`: 新規セッション（`resume=0`）で done。run は `phase=done` で完了。

### 動作確認で発見・修正した3つ目の実バグ
- **`--resume` が実際には渡らない**（session-resume が無効化）: `scheduleTick` が worker のスナップショット取得**前**に `ResumeSession=false` へクリアしていたため、`RunOpts.Resume` が常に false になっていた（`resume=0`）。
  - 修正: resume ケースでは `scheduleTick` で `ResumeSession` を落とさず、`runTaskPipeline` がスナップショット後に消費（クリア）。再試行は新規セッションになる。
  - 回帰防止に単体テスト `TestResume_UsesResumeFlagAfterCrash` / `TestFreshDispatch_NewSession` を追加（mock が `RunOpts.Resume/SessionID` を記録）。
- この不具合は「クラッシュ→再開で作業を捨てない」という主要目的に直結するもので、単体テスト（mock が RunOpts を無視）では検出できず、**実バイナリを回す動作確認で初めて顕在化**した。

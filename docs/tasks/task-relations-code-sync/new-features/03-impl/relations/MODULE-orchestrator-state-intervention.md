---
target: docs/03-impl/relations/MODULE-orchestrator-state-intervention.md
change: replace
sections:
  - "## 処理の流れ"
  - "## 戻り値・副作用"
  - "## 異常系"
deletes: []
reason: open.json の項目が実際の型と違う(docs/issues/032 #11)。サイドカー API の用途が実態と違う(docs/issues/038 #21 = 032 #12)
id: MODULE-orchestrator-state-intervention
module: MOD-orchestrator
kind: function-call
sync: sync
impl: orchestrator/state.go::Store.AddOpenIntervention, orchestrator/state.go::Store.RemoveOpenIntervention, orchestrator/state.go::Store.LoadOpenInterventions, orchestrator/state.go::Store.SaveOpenInterventions, orchestrator/state.go::Store.AppendIntervention, orchestrator/state.go::Store.AppendAssumption, orchestrator/state.go::Store.AppendAudit, orchestrator/state.go::Store.ReadAnswer, orchestrator/state.go::Store.WriteQuestion, orchestrator/mode.go::Store.ReadQuestion, orchestrator/state.go::Store.LoadControl, orchestrator/state.go::Store.DeleteControl, orchestrator/state.go::Store.ReadAtomicSidecar, orchestrator/state.go::Store.WriteAtomicSidecar
callers: MODULE-orchestrator-controller, MODULE-orchestrator-handoff, MODULE-orchestrator-mode, MODULE-orchestrator-review, MODULE-orchestrator-worker
callees: MODULE-orchestrator-state, MODULE-orchestrator-state-io
contracts: なし
design: DSN-mod-01, DSN-orch-01
requirements: FR-orch-04, FR-orch-05
tests: orchestrator/state_test.go::TestControlRoundTripAndDelete, orchestrator/state_test.go::TestAuditAppend, orchestrator/state_test.go::TestSidecarRoundTrip
updated: 2026-08-05
summary: 介入・質問・監査ログの永続化と、制御ファイルの読取と破棄を担う
---

<!-- 変更指示。反映後の最終形を書く。version / verified は持たない。frontmatter は `updated` の日付以外変更なし。 -->

## 処理の流れ

1. **未解決キュー**: `AddOpenIntervention` / `RemoveOpenIntervention` /
   `LoadOpenInterventions` / `SaveOpenInterventions` が `intervention/open.json` を読み書きする。
   `Items[]` の1要素は **`OpenIntervention`**(`orchestrator/state.go:209`〜`:214`)で、
   JSON のフィールドは **`id` / `task_id` / `trigger_reason` / `opened_at` の4つ**である
   (`interventions.jsonl` の1行に使う `Intervention`(`:192`〜`:200`)とは別型で、そちらは
   `id` / `task_id` / `trigger_reason` / `question` / `answer` / `ts` を持つ)。
2. **質問と回答**: `WriteQuestion` が `intervention/<id>/question.md` を書き、`ReadQuestion` が
   それを読む(`mode.go` 側に定義されている `Store` メソッド)。`ReadAnswer` が
   `intervention/<id>/answer.md` を読む。
3. **追記型ログ**: `AppendAudit` が `audit.jsonl`、`AppendAssumption` が `assumptions.jsonl`、
   `AppendIntervention` が `interventions.jsonl` へ1行 JSON を追記する。
4. **制御ファイル**: `LoadControl` が `control.json` を読み、`DeleteControl` が消費後に削除する。
5. **サイドカー**: `WriteAtomicSidecar` / `ReadAtomicSidecar`(`orchestrator/state.go:546` / `:551`)は
   **ストア直下の任意名の小さな値ファイル**を原子的に読み書きする汎用 API である。
   **製品コードでの用途は `handoff_note.md` の1つだけ**で(`controller.go:324` が書き、
   `mode.go:67` が読む)、**`sessions/<key>.sys` / `.prompt` はこの API を通らない**:
   それらは `MODULE-orchestrator-mode` の `Mode.WriteLaunchScript` が `writeAtomic` で直接書く。
6. パスの解決はすべて `MODULE-orchestrator-state` の `Store.path` を通す。書き込みは
   `MODULE-orchestrator-state-io` の原子的置換または追記を通す。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 各関数の対象とエラー |
| 永続化 | `intervention/open.json`(未解決キュー)、`intervention/<id>/question.md`、`intervention/<id>/answer.md`、`audit.jsonl`、`assumptions.jsonl`、`interventions.jsonl`、`control.json`(読取と削除)、**サイドカー `handoff_note.md`**(`WriteAtomicSidecar` / `ReadAtomicSidecar` の製品コードでの唯一の用途)。**`sessions/<key>.sys` / `.prompt` はこの機能が書くものではない**(`MODULE-orchestrator-mode` が直接書く)。**追記型ログは `ArchiveRun` でも残す** |
| 発火するイベント | なし |
| ログ | なし(自身が監査ログの書き手である) |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| `open.json` が存在しない | 空のキューを返す | 判断待ち0件として扱われる |
| **`open.json` が壊れている / 読めない** | `LoadOpenInterventions` は **`readJSON` のすべてのエラー**で空のキューを返し、**エラーを返さない**(`orchestrator/state.go:396`〜`:402`)。判断待ちキュー全体が**黙って失われ**、その後の追加が空のキューを上書きする | 判断待ちのタスクが `waiting_human` のままダッシュボードから消える。**`FR-orch-05` 受入基準7(読めない状態ファイルの既存内容を破壊しない)と食い違う**(`docs/issues/057-bug-broken-open-json-silently-drops-the-intervention-queue.md`) |
| `answer.md` が未作成 | 空文字を返す | controller は「未回答」とみなして open を維持する |
| 追記に失敗する | エラーを返すが、監査ログは実行を止める理由にしない | ログが欠落する |
| `control.json` が壊れている / 読めない | `LoadControl` がデコードエラーを返す。**呼び出し元の `MODULE-orchestrator-handoff` はそれを「無い」と同じ扱いにし、`DeleteControl` でファイルを削除する**(壊れた指示で以後の実行が詰まらないようにするため)。**未消費として残すのではない** | 対話が終われば停止条件で打ち切られ、`selectMenu` で人間に選ばせる経路へ倒れる |
| `control.json` の `request` が未知の値 | 同じく**削除して「無い」と同じ扱い**にする | 同上 |
| `DeleteControl` が失敗した | `Consume` がエラーを返し、**control を返さない**(同じ指示が二重に消費されることはない) | エラーが `MODULE-orchestrator-controller` へ伝播する |

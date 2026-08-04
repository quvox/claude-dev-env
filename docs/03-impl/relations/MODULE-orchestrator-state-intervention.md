---
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
updated: 2026-08-04
summary: 介入・質問・監査ログの永続化と、制御ファイルの読取と破棄を担う
---

# MODULE-orchestrator-state-intervention 介入と監査の永続化

## 目的

介入をタスク単位で扱う(FR-orch-04)ために、未解決の判断待ちキューと質問/回答、および
監査・仮定・介入の追記型ログを永続化する。run をまたいで判断待ちが失われないことが要件
(FR-orch-05)。

## 処理の流れ

1. **未解決キュー**: `AddOpenIntervention` / `RemoveOpenIntervention` /
   `LoadOpenInterventions` / `SaveOpenInterventions` が `intervention/open.json` を読み書きする
   (`Items[]` に `{InterventionID, TaskID}` を持つ)。
2. **質問と回答**: `WriteQuestion` が `intervention/<id>/question.md` を書き、`ReadQuestion` が
   それを読む(`mode.go` 側に定義されている `Store` メソッド)。`ReadAnswer` が
   `intervention/<id>/answer.md` を読む。
3. **追記型ログ**: `AppendAudit` が `audit.jsonl`、`AppendAssumption` が `assumptions.jsonl`、
   `AppendIntervention` が `interventions.jsonl` へ1行 JSON を追記する。
4. **制御ファイル**: `LoadControl` が `control.json` を読み、`DeleteControl` が消費後に削除する。
5. **サイドカー**: `WriteAtomicSidecar` / `ReadAtomicSidecar` が巨大なプロンプトを
   `.sys` / `.prompt` の別ファイルとして原子的に読み書きする。
6. パスの解決はすべて `MODULE-orchestrator-state` の `Store.path` を通す。書き込みは
   `MODULE-orchestrator-state-io` の原子的置換または追記を通す。

## 呼び出され方

- 契機: controller が介入を開く/閉じるとき、worker と review が監査を残すとき、handoff が
  `control.json` を消費するとき、mode が質問を組み立てるとき。
- 前提条件: `.orchestrator/` が書き込み可能であること。
- 引数:

| 引数 | 型 | 必須 | 制約 | 実装が行う検証 |
|---|---|---|---|---|
| `id` | 文字列 | 一部の関数で必須 | 介入 ID。`intervention/<id>/` のディレクトリ名になる | **検証しない**(プロセス内呼び出し)。ID は呼び出し元が採番する |
| `taskID` | 文字列 | 一部の関数で必須 | 対象タスク | 同上 |
| record | 構造体 | 追記系で必須 | JSON へエンコードできること | 同上 |

- 認可: プロセス内呼び出し。

## 連携先と連携内容

### MODULE-orchestrator-state

- 何のために呼ぶか: `.orchestrator/` 配下のファイル位置を `Store.path` で解決するため。
- 何を渡すか: 相対パスの構成要素。 / 何を受け取るか: 絶対パス。
- **失敗したときどうなるか**: 想定されない(文字列連結のみ)。

### MODULE-orchestrator-state-io

- 何のために呼ぶか: 原子的置換(`writeJSONAtomic` / `writeAtomic`)と追記(`appendJSONL`)のため。
- 何を渡すか: パスと構造体。 / 何を受け取るか: エラー。
- **失敗したときどうなるか**: 呼び出し元へエラーが返る。open.json の更新が失敗した場合、
  判断待ちがキューに載らないまま `waiting_human` のタスクだけが残りうる。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 各関数の対象とエラー |
| 永続化 | `intervention/open.json`(未解決キュー)、`intervention/<id>/question.md`、`intervention/<id>/answer.md`、`audit.jsonl`、`assumptions.jsonl`、`interventions.jsonl`、`control.json`(読取と削除)、`sessions/<key>.sys` / `.prompt`。**追記型ログは `ArchiveRun` でも残す** |
| 発火するイベント | なし |
| ログ | なし(自身が監査ログの書き手である) |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| `open.json` が存在しない | 空のキューを返す | 判断待ち0件として扱われる |
| **`open.json` が壊れている / 読めない** | `LoadOpenInterventions` は **`readJSON` のすべてのエラー**で空のキューを返し、**エラーを返さない**(`orchestrator/state.go:396`〜`:402`)。判断待ちキュー全体が**黙って失われ**、その後の追加が空のキューを上書きする | 判断待ちのタスクが `waiting_human` のままダッシュボードから消える。**`FR-orch-05` 受入基準7(読めない状態ファイルの既存内容を破壊しない)と食い違う**(`docs/issues/038`) |
| `answer.md` が未作成 | 空文字を返す | controller は「未回答」とみなして open を維持する |
| 追記に失敗する | エラーを返すが、監査ログは実行を止める理由にしない | ログが欠落する |
| `control.json` が壊れている / 読めない | `LoadControl` がデコードエラーを返す。**呼び出し元の `MODULE-orchestrator-handoff` はそれを「無い」と同じ扱いにし、`DeleteControl` でファイルを削除する**(壊れた指示で以後の実行が詰まらないようにするため)。**未消費として残すのではない** | 対話が終われば停止条件で打ち切られ、`selectMenu` で人間に選ばせる経路へ倒れる |
| `control.json` の `request` が未知の値 | 同じく**削除して「無い」と同じ扱い**にする | 同上 |
| `DeleteControl` が失敗した | `Consume` がエラーを返し、**control を返さない**(同じ指示が二重に消費されることはない) | エラーが `MODULE-orchestrator-controller` へ伝播する |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 介入をタスク単位のキュー(`open.json`)として持ち、最上位状態 `intervening` を置かない(発火したタスクだけを `waiting_human` にし、他の worker は止めない) | D0-orch-04 |
| 2 | 巨大なプロンプトはサイドカーに逃がし、launch script からは `$(cat ...)` で読む(コマンドライン長の上限を避ける) | D0-orch-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| `ReadQuestion` だけ `mode.go` に定義されている(他は `state.go`) | ファイル配置が責務と一致していない | なし |

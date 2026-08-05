---
id: 057-bug-broken-open-json-silently-drops-the-intervention-queue
type: bug
severity: 中
found: 2026-08-04
found_in: /doc-check ssot task-impl-depth(独立監査 Codex relations)。2026-08-05 に task-relations-code-sync が docs/issues/038 から切り出した
related: FR-orch-05, MODULE-orchestrator-state-intervention, MODULE-orchestrator-controller, docs/03-impl/index.md, docs/issues/021, docs/issues/026
summary: 壊れた intervention/open.json をすべて空キューとして扱うため、判断待ちキュー全体が黙って失われ、その後の Add が内容を上書きする
---

## 事象

`Store.LoadOpenInterventions`(`orchestrator/state.go:396`〜`:402`)が
**`readJSON` のすべてのエラー**(ファイル不在・読み取り失敗・JSON 破損)で
`&OpenInterventions{}`(空のキュー)を返し、**エラーを返さない**。

```go
func (s *Store) LoadOpenInterventions() *OpenInterventions {
	var q OpenInterventions
	if err := readJSON(s.path("intervention", "open.json"), &q); err != nil {
		return &OpenInterventions{}
	}
	return &q
}
```

呼び出し元は「不在」と「壊れている」を区別できない。**その後の `AddOpenIntervention` は
空のキューに1件足した状態を書き戻す**ので、壊れる前に積まれていた判断待ちは復旧できない。

## 影響

`FR-orch-05` 受入基準7 は「**永続状態ファイル**(`plan.json` / `state.json` /
`intervention/open.json` と履歴)が読み取れないならば、システムは既存の内容を破壊してはならない」
と定めており、**この実装はそれを満たしていない**。

- 判断待ちのタスクは `plan.json` 側で `waiting_human` のまま残るため、**run は終了しない**が、
  ダッシュボードの判断待ち一覧と `[i]` の遷移先が空になる。**人間が回答する経路が消える。**
- 利用者から見ると「待っているのに開けない」状態で、原因を示すメッセージも出ない。
- ファイルが壊れる契機は `docs/issues/021`(ストアにロックが無く2つ目のコントローラが起動できる)
  と `docs/issues/026`(状態保存の失敗を握りつぶす)にもある。

## 原因の見当

**推測**: 「ファイルが無いときは空として扱う」(`FR-orch-05` 受入基準10 が求める挙動)を
実装するときに、`readJSON` のエラーを**種類で分けずに**まとめて扱った。
受入基準10(不在は未作成として扱う)と受入基準7(読めないものを破壊しない)は**別の要求**である。

## 正はどちらか

**要件が正で、実装が誤りである。** `FR-orch-05` 受入基準7 が明文で「破壊してはならない」と
定めており、解釈の余地がない。2026-08-04 に人間が
「**事実を 03 に明記し、コードの修正は別タスク**」と裁定済みで、
`MODULE-orchestrator-state-intervention` の `## 異常系` に事実と要件との食い違いが書いてある。

## 対処案

| 案 | 内容 |
|---|---|
| A | `LoadOpenInterventions` を `(*OpenInterventions, error)` にし、**不在は空+`nil`、破損は error** に分ける。呼び出し元は破損を人間へ提示して `Add` を行わない |
| B | 破損時に `open.json.broken-<timestamp>` へ退避してから空で続行する(`ArchiveRun` と同じ「削除ではなく退避」の方針) |
| C | 破損を検出したら run を止める |

**A と B は併用できる**(退避してから error を返す)。`docs/issues/021` のロック導入と同じ
タスクで扱うと、壊れる契機と壊れた後の扱いを一度に閉じられる。

## 経緯

- 2026-08-04 `docs/issues/038` #3 として起票され、人間が「記述を直す。コードは別タスク」と裁定。
- 2026-08-05 `task-relations-code-sync`(記述をコードへ合わせるタスク)の `/doc-check` が、
  **`038` を削除すると本欠陥の追跡先が消える**ことを検出した。
  `038` は「記述の乖離」の issue として起票されており、`03-impl/index.md` の
  「実装の欠陥として起票済み」の集計にも入っていなかったため、
  **削除すると誰も追っていない状態になる**。そこで本 issue として切り出した(同タスクの決定シート #8)。
  **記述側(`MODULE-orchestrator-state-intervention` の異常系と `03-impl/index.md` の
  「01(要件)との差異」)の参照先は本 issue へ付け替える。**

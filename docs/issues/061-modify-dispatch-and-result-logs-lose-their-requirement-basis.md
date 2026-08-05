---
id: 061-modify-dispatch-and-result-logs-lose-their-requirement-basis
type: modify
severity: 低
found: 2026-08-05
found_in: /task-doc task-spec-measurability(決定シート概念#6「NFR-ops-01 は廃止する」の波及を実測)
related: docs/02-design/logging.md, docs/01-requirements/non-functional.md, MODULE-orchestrator-controller, FR-orch-05
summary: NFR-ops-01 の廃止により、追記型ログの dispatch(タスクの委譲)と result(実行結果)が要件の裏付けを失う。実装は audit.jsonl へ出力し続けるため、要件に無いものを実装と設計が持つ状態が残る
---

# 061 `dispatch` / `result` の追記型ログが要件の裏付けを失う

## 事象

2026-08-05 の人間の裁定により、`NFR-ops-01`(運用補助と可観測性)を
`docs/01-requirements/non-functional.md` から削除する
(理由:「**その品質特性自体を本システムでは追わない**」。`task-spec-measurability` の決定シート概念#6)。

`docs/02-design/logging.md`「主要イベントのログ仕様」の 11 行のうち、
**`NFR-ops-01` を唯一の対応要件としていたのは次の2行**である(2026-08-05 に実測)。

| イベント | 出力内容 | 削除前の対応要件 |
|---|---|---|
| タスクの委譲 | `dispatch`。task_id / attempt / モデル | `NFR-ops-01` |
| 実行結果 | `result`。成否と要約 | `NFR-ops-01` |

他の追記型ログは根拠が残る: `assumption` と `intervention` は `FR-orch-04` 受け入れ基準4、
`VM の資源逼迫` は `FR-env-08` 受け入れ基準4 が引き続き要求する。

**実装は `.orchestrator/audit.jsonl` へ `dispatch` / `result` を出力し続ける。**
本タスクはコードを変えないため(`task-spec-measurability` の「やらないこと」)、
**要件には無いが設計と実装には在る**という状態が残る。

## 影響

- 振る舞いは変わらない。利用者に見える差は無い。よって severity は「低」。
- ただし `NFR-perf-03` の測定方法が「`.orchestrator/audit.jsonl` の起動イベント数をタスク数と
  突き合わせる」と**このログに依存している**。ログの出力が要件で保証されなくなったので、
  **`NFR-perf-03` の測定方法は「要件が保証しない出力」に依存する**ことになる。
  現状は実装が出し続けるので測定は成立するが、将来このログを削るとき
  `NFR-perf-03` が同時に測れなくなることを見落としやすい。
- `FR-orch-05` 受け入れ基準8・9 は追記型ログの一貫性・耐久性(1ファイル1書き込み、
  末尾の不完全な行を許容)を定めるが、**ログが存在すべきことは要求していない**
  (2026-08-05 に本文を確認した事実)。したがってこの2種の存在を要求する条項は
  01 のどこにも無くなる。

## 正はどちらか

**人間の裁定が正**(この品質特性は追わない)。実装の誤りでも設計の誤りでもない。
`docs/02-design/logging.md` は行を残したまま対応要件を「なし」と明記することで、
**要件に無いものを実装が出しているという事実を隠さない**形にした
(行ごと削除すると「02 に無いログを実装が出す」状態を作り、CLAUDE.md 原則2 の
コード ⇄ 03-impl の突き合わせで検出されるだけの、理由の分からない差分になる)。

## 対処案

| 案 | 内容 |
|---|---|
| A | **現状のまま維持する**(対応要件「なし」と明記して追跡する)。`NFR-perf-03` を測る限りログは必要なので、実装から消す動機は当面ない |
| B | `NFR-perf-03` の測定方法を audit.jsonl に依存しない形へ変え、そのうえで `dispatch` / `result` の出力をコードから削除する(**コード変更 → 別タスク**) |
| C | `dispatch` / `result` の存在を `FR-orch-05` の受け入れ基準として明示的に要求し直す(**人間の裁定「この品質特性は追わない」と衝突するので、採るなら 00/01 から改めて合意が要る**) |

**推奨は A。** B は測定方法の作り替えを伴い、C は今回の裁定を部分的に取り消すことになる。
どちらも本 issue 単独では決められない。

## どうなったら見直すか

`NFR-perf-03`(worker の割り当て粒度)の測定方法を変更するとき、または
`.orchestrator/audit.jsonl` の出力をコードから削除する提案が出たとき。

# task-remove-orchestrator memo-1(フェーズ2 の引き渡しで追い出した内容)

<!-- 追い出した元: memo.md の `## 決定シート(回答済み)`。フェーズ1 で回答され、フェーズ2 の変更指示(`new-features/00-requests/decisions/orch.md` ほか)へ反映済み。 -->

## 決定シート(回答済み)


**転記の根拠**: 人間の指示「orchestratorに関する全ての記述、機能、実装を削除して、辻褄を
合わせたい。新しいタスクを作って、作業を始めて。とにかく全く無かったことにしたい。
いちいち質問しなくて良いから、一気にやりきってほしい」(2026-08-08、本タスクの起票発話)。
この発話を sheet.md の「一括回答」として扱い、全ブロックを **推奨を承認** として転記した。

| # | 論点 | 回答 | 反映先 |
|---|---|---|---|
| 概念1 | 「オーケストレーター」の外延(何を削除対象と数えるか) | 推奨を承認(一括回答による) | `docs/00-requests/terminology.md`(語ごと削除)。境界の記録は本 memo の調査メモ 1 |
| 概念2 | 通知フック(`save_prompt.sh` / `sendslackmsg.sh` = MOD-hooks)を範囲に含めるか | 推奨を承認(一括回答による) = **含める(削除する)** | `docs/01-requirements/functional.md`(FR-orch-07 削除)/ `docs/02-design/system.md`(MOD-hooks 削除) |
| 概念3 | `docs/orch/` と `docs/histories/` / `docs/feedbacks/` を範囲に含めるか | 推奨を承認(一括回答による) = **含めない(残す)** | 本 memo「やらないこと」 |
| 論点1 | `request.md` の目的・対象ユーザー・完成イメージから並列開発の記述を落とす(00 の意味変更) | 推奨を承認(一括回答による) | `docs/00-requests/request.md` |
| 論点2 | 「やらないこと」4・5 を削除し、1〜3 の番号は動かさない | 推奨を承認(一括回答による) | `docs/00-requests/request.md` |
| 論点3 | 対象の消えた `docs/issues/` を削除する | 推奨を承認(一括回答による) | `docs/issues/`(該当ファイル削除)。経緯は `docs/histories/` |
| 論点4 | `SR-21` / `SR-22` / `SR-23` / `SR-31` の縮小と削除 | 推奨を承認(一括回答による) | `docs/01-requirements/system.md` |


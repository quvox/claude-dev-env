---
target: docs/03-impl/relations/MODULE-hooks-save-prompt.md
change: delete
deletes: []
reason: '通知フックの削除(決定シート 概念2 = 推奨どおり「hooks も削除する」)。この機能の実装は `scripts/save_prompt.sh` で、`sendslackmsg.sh` が読むプロンプトの一時ファイルを作るためだけに存在する。対応要件は `FR-orch-07`(通知)だけで、その要件ごと消えるため**要件の裏付けを1つも持たない実装**になる。所属モジュール `MOD-hooks` も 02 から消える。イメージへの同梱(`.devcontainer/Dockerfile.claude`)も外す。**同時に `docs/03-impl/features.md` の同名の行も `種別: delete` で消す**'
---

削除の理由: 上の `reason` のとおり。

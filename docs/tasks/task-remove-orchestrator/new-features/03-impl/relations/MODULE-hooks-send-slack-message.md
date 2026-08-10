---
target: docs/03-impl/relations/MODULE-hooks-send-slack-message.md
change: delete
deletes: []
reason: '通知フックの削除(決定シート 概念2 = 推奨どおり「hooks も削除する」)。この機能の実装は `scripts/sendslackmsg.sh` で、対応要件は `FR-orch-07`(通知)、関連する非機能要件は `NFR-sec-03`(通知トークンの到達範囲)と `NFR-avail-03`(通知の失敗が主機能を止めない)である。3 つとも 01 から消えるため、要件の裏付けを1つも持たない実装になる。`docs/issues/013`(Slack の API レベルの失敗を検出しない)と `docs/issues/067`(失敗を握りつぶすのが `D0-orch-07` のガードレールに反する)は対象ごと消えるので、両 issue を削除する。イメージへの同梱(`.devcontainer/Dockerfile.claude`)も外す。**同時に `docs/03-impl/features.md` の同名の行も `種別: delete` で消す**'
---

削除の理由: 上の `reason` のとおり。

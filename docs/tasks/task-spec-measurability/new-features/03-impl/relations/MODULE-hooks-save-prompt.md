---
target: docs/03-impl/relations/MODULE-hooks-save-prompt.md
change: replace
sections:
  - "## 目的"
reason: >
  NFR-ops-01 の削除(決定シート概念#6)に伴い requirements から同 ID を外す。
  FR-orch-07(通知)が引き続き根拠として残る。目的の本文は元から NFR-ops-01 を引いていない。
id: MODULE-hooks-save-prompt
module: MOD-hooks
kind: tool
sync: sync
impl: scripts/save_prompt.sh::main
callers: なし
callees: なし
contracts: なし
design: DSN-mod-01, DSN-mod-03
requirements: FR-orch-07
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-05
summary: Claude Code フックから渡されたプロンプトを一時ファイルへ保存する
---

## 目的

Slack 通知(FR-orch-07)の本文に「直前にユーザが入力したプロンプト」を含められるようにする。
hook の入力からプロンプト先頭を取り出し、セッション別の一時ファイルへ置くのがこの機能の役割で、
通知側(`MODULE-hooks-send-slack-message`)とはファイル経由で疎結合にしてある。

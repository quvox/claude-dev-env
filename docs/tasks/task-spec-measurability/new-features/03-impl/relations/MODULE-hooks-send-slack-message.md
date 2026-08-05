---
target: docs/03-impl/relations/MODULE-hooks-send-slack-message.md
change: replace
sections:
  - "## 目的"
reason: >
  NFR-ops-01 の削除(決定シート概念#6)に伴い requirements から同 ID を外す。
  FR-orch-07(通知)が引き続き根拠として残る。目的の本文は元から NFR-ops-01 を引いていない。
id: MODULE-hooks-send-slack-message
module: MOD-hooks
kind: tool
sync: sync
impl: scripts/sendslackmsg.sh::main
callers: なし
callees: なし
contracts: なし
design: DSN-mod-01, DSN-mod-03
requirements: FR-orch-07
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-05
summary: Claude Code フックの通知をプロンプト文脈つきで Slack へ送る
---

## 目的

Claude Code の節目(停止・通知イベント)を Slack へ知らせる(FR-orch-07)。
`MODULE-hooks-save-prompt` が置いたプロンプト文脈を本文に添えることで、どのセッションの
通知かが分かるようにしている。

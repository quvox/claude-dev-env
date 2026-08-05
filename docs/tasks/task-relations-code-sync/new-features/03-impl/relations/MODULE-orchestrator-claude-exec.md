---
target: docs/03-impl/relations/MODULE-orchestrator-claude-exec.md
change: replace
sections: []
deletes: []
reason: callers に MODULE-orchestrator-worker / -review が無い(docs/issues/038 #12)。worker.go:231 と review.go:81・:126 が Claude.RunPrompt を呼ぶ
reflected: 2026-08-05
id: MODULE-orchestrator-claude-exec
module: MOD-orchestrator
kind: function-call
sync: sync
impl: orchestrator/worker.go::ExecClaude.RunPrompt, orchestrator/claudebin.go::claudeChildEnv, orchestrator/claudebin.go::claudePath, orchestrator/claudebin.go::localBinDir
callers: MODULE-orchestrator-controller, MODULE-orchestrator-mode, MODULE-orchestrator-review, MODULE-orchestrator-worker
callees: MODULE-orchestrator-streamlog
contracts: CTR-orchestrator-prompt
design: DSN-mod-01, DSN-orch-01
requirements: FR-orch-03, FR-orch-07
tests: なし(未実装。claudebin.go に対応する単体テストが無く、E2E-04 の実機確認で代替する)
updated: 2026-08-05
summary: Claude CLI を子プロセスとして起動し環境と PATH を整える
---

<!-- 変更指示。**本文の変更は無い**(frontmatter の callers だけを直す)。
     裏取り: orchestrator/main.go:144〜:156 が同じ ExecClaude を Worker と Reviewer に注入し、
     orchestrator/worker.go:231 / orchestrator/review.go:81・:126 が Claude.RunPrompt を呼ぶ。
     controller.go:1068 も c.Worker.Claude.RunPrompt を呼ぶので controller は据え置き。
     mode.go:41・:50・:133・:138 が claudePath / claudeChildEnv / localBinDir を直接使うので mode も据え置き。
     対称性のため MODULE-orchestrator-worker.md / -review.md の callees 側も同時に直す。

     なお docs/issues/017 が挙げていた本ファイルの目的「安全に」は現行 SSOT に存在しない
     (task-impl-depth の反映で解消済み)ため、本タスクでの修正対象ではない。 -->

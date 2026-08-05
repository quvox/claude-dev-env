---
target: docs/03-impl/relations/MODULE-container-tools-wait-limit-reset.md
change: replace
sections:
  - "## 目的"
reason: >
  NFR-ops-01 の削除(決定シート概念#6)に伴い requirements と目的の参照から同 ID を外す。
  FR-env-01(tmux セッションで作業を続ける体験)が引き続き根拠として残る。
id: MODULE-container-tools-wait-limit-reset
module: MOD-container-tools
kind: tool
sync: sync
impl: scripts/wait-limit-reset.sh::main
callers: なし
callees: なし
contracts: なし
design: DSN-mod-01, DSN-mod-03
requirements: FR-env-01
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-05
summary: Claude のレート制限解除時刻まで待機し tmux 経由で作業を再開させる
---

## 目的

Claude の利用上限に当たったとき、リセット時刻まで待って自動で作業を再開させる補助道具。
**tmux セッションで作業を続ける体験(FR-env-01)を、上限で中断させないためのもの**である。
システムの制御フローには関与しない。

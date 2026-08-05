---
target: docs/03-impl/relations/MODULE-vm-mode-cli.md
change: replace
sections:
  - "## 目的"
reason: >
  NFR-ops-01 の削除(決定シート概念#6)に伴い requirements と目的の参照から同 ID を外す。
  FR-env-08 が引き続き根拠として残るので、機能の要件の裏付けは消えない。
id: MODULE-vm-mode-cli
module: MOD-vm-mode
kind: tool
sync: sync
impl: scripts/vm::main
callers: なし
callees: なし
contracts: なし
design: DSN-mod-01, DSN-mod-03, DSN-arch-01
requirements: FR-env-08
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する。静的検証として `bash -n` は緑)
updated: 2026-08-05
summary: VM の起動状態・health・ポート同期を操作するヘルパー
---

## 目的

コンテナ内から VM を操作・観測する入口(FR-env-08)。ゲストの状態を見る、入る、
作り直す、といった日常操作を1コマンドに束ねる。

---
target: docs/03-impl/relations/MODULE-vm-mode-healthd.md
change: replace
sections:
  - "## 目的"
  - "## 既知の制限"
reason: >
  「RAM 逼迫」は用語集が定義した「資源逼迫」(CPU 使用率の閾値)とは別概念で、定義がどこにも無い
  (docs/issues/017)。実装は CPU 使用率しか見ないので、実装の事実に合わせて書き替える。
  あわせて NFR-ops-01 の削除(決定シート概念#6)に伴い requirements から同 ID を外す。
id: MODULE-vm-mode-healthd
module: MOD-vm-mode
kind: tool
sync: sync
impl: scripts/vm-healthd.sh::main#--loop, scripts/vm-healthd.sh::main
callers: なし
callees: なし
contracts: なし
design: DSN-mod-01, DSN-mod-03, DSN-arch-01
requirements: FR-env-08
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する。静的検証として `bash -n` は緑)
updated: 2026-08-05
summary: QEMU の CPU 使用率から資源逼迫を検知し tmux と health へ書く
---

## 目的

ゲスト VM が**資源逼迫**(用語集。QEMU プロセスの CPU 使用率が割り当て上限に対して 60% 以上の
状態が 15 秒周期で 12 回連続して観測された状態)に入ったことに人間が気づけるようにする
(FR-env-08 受け入れ基準4)。**ゲストがスラッシングに陥ると ssh も docker も応答しなくなる**ため、
ゲストの中を観測せず、**claude コンテナ側から見える QEMU プロセスの CPU 使用率だけ**で判定するのが
この機能の要点である。

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| CPU 使用率からの間接推定 | メモリ不足以外の理由による高負荷(ゲスト内のビルド・テストなど)も WARN になる。**この機能はゲストのメモリ使用量を観測しない** | なし |
| `VM_HEALTH_*` は環境変数の上書きのみ | CLI からの明示的な受け渡し口が無い(既定値運用)。**用語集「資源逼迫」の3つの数値を上書きする唯一の手段がこの環境変数である** | なし |

---
target: docs/03-impl/features.md
change: replace
sections:
  - "## 機能一覧"
deletes: []
reason: >
  MODULE-makefile-update-claude の summary から測定不能語「高速更新」を落とす(docs/issues/017)。
  機能表と relations は 1:1 なので両方に変更指示を書く(change-set.md 例外1)。境界は変えない。
---

<!-- 機能表は表そのものが内容なので、**差分としての表**を書く(`.claude/directions/change-set.md`
     の例外1)。既存の機能ID の行は「変更指示が勝つ」= その行だけを差し替える。
     `MODULE-vm-mode-healthd` の概要にある「資源逼迫」は用語集の定義語なので書き替えない。 -->

## 機能一覧

| 機能ID | 種別 | 入口 | 所属 | 概要 |
|---|---|---|---|---|
| MODULE-makefile-update-claude | tool | dispatch update-claude @ Makefile::update-claude | MOD-makefile | コンテナイメージを作り直さずに Claude Code だけを更新する(ビルドキャッシュを使う) |
| MODULE-firewall-init | tool | dispatch init-firewall-claude.sh @ scripts/init-firewall-claude.sh::main | MOD-firewall | iptables/ipset でブラックリスト型のファイアウォールを構成する |
| MODULE-vm-mode-healthd | tool | dispatch --loop @ scripts/vm-healthd.sh::main, scripts/vm-healthd.sh::main | MOD-vm-mode | QEMU の CPU 使用率から資源逼迫を検知し tmux と health へ書く |
| MODULE-vm-mode-cli | tool | dispatch vm @ scripts/vm::main | MOD-vm-mode | VM の起動状態・health・ポート同期を操作するヘルパー |
| MODULE-hooks-save-prompt | tool | dispatch save_prompt.sh @ scripts/save_prompt.sh::main | MOD-hooks | Claude Code フックから渡されたプロンプトを保存する |
| MODULE-hooks-send-slack-message | tool | dispatch sendslackmsg.sh @ scripts/sendslackmsg.sh::main | MOD-hooks | Claude Code フックの通知を Slack へ送る |
| MODULE-container-tools-wait-limit-reset | tool | dispatch wait-limit-reset.sh @ scripts/wait-limit-reset.sh::main | MOD-container-tools | Claude のレート制限解除時刻まで待機する |

<!-- 下の6行は**内容が変わっていない**。機能表と `relations/MODULE-*.md` は 1:1 であり
     (`.claude/directions/change-set.md` 例外1「片側だけは FT3 違反」)、本タスクは
     この6本の relations に変更指示を書くため、対応する機能表の行も同じ変更指示に載せている。
     境界(機能ID・種別・入口・所属)はどれも変えていない。 -->

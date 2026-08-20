---
id: 032-a-precondition-probe-must-measure-the-path-actually-used
date: 2026-08-20
context: 02-design/03-impl。issue 102(コンテナ内で codex が起動しない)の切り分け
summary: 起動前の可否判定は、使わないと決めた経路の状態ではなく、実際に使う経路そのものを1コマンドで測る
---

# 032 可否の判定は、実際に使う経路で測る

## 状況

「claude-dev コンテナの中から codex が起動しない」という人間の報告(`docs/issues/102`)を
切り分けていた。報告文は「bwrap が非ゼロのため codex を起こせず」だった。

## AI の提案

起票時の見立ては2つで、どちらも外れた。(1) 同梱の colabtmux が起動前に bwrap を見ている、
(2) 既定3鍵が codex に届いていない。実測すると、colabtmux の4ビルドすべてに `bwrap` /
`bubblewrap` / `landlock` / `sandbox` の文字列が0件で、既定3鍵は現に届いていた
(旗を付けない `codex sandbox -- /bin/true` が exit 0)。

## 人間の判断とその理由

人間が覆したのではなく、実機の測定が覆した。判定の出どころはキットの規範
(`.claude/directions/orchestration.md` §1.1.1)であり、
`bwrap --unshare-user --unshare-net --ro-bind / / /bin/true` の終了コードを
「codex を使えるか」の判定に使っていた。**この1行が非ゼロであることは、このコンテナでは
仕様どおりの正常な状態である**(`D0-dist-04` 項6 / `DSN-dist-02` がその経路を使わないと決めた)。
つまり判定は、使わないと決めた経路の状態を見ていた。

## 今後どう活かすか

**起動前の可否判定は、その道具が実際に通る経路を1コマンドで測る。** 依存関係の途中にある
下位機構の状態を代理指標にしてはならない — 「その下位機構を使わない」ことが仕様に書かれて
いる場合、代理指標は常に赤になり、判定は常に間違う。ここでは
`codex sandbox -- /bin/true` が exit 0 かどうかが正しい判定である。

同じ形の罠は、**報告文の出どころを名指しできていない段階で原因を推測すること**にもある。
報告文は本文検索で在処を突き止められる。今回、報告文はリポジトリにも同梱バイナリにも無く、
キットの規範に在った。**「どのファイルがこの文を出すのか」を先に決めれば、推測は2つとも
不要だった。**

## 関連

- `docs/issues/102-bug-colabtmux-refuses-to-launch-codex-on-a-nonzero-bwrap-probe.md`
- `docs/02-design/environments.md`(「codex を起こす側が前提にしてよいこと」)
- `docs/03-impl/relations/MODULE-entrypoint-claude.md`(「既知の制限」)
- `docs/pendings.md`(残務。キット側の修正は `/kit-improve` が持つ)

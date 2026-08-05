---
target: docs/00-requests/request.md
change: replace
sections: []
deletes: []
summary: >
  Claude Code を Docker コンテナで動かす開発環境と、その上で複数エージェントを連携させる
  AIオーケストレーターを、チームの並列開発力を上げるために提供する。信頼できる社内開発用途に限定。
reason: >
  決定シート概念#5 の回答「枕詞は不要」により、frontmatter `summary` から測定不能語「安全な」を
  落とす(docs/issues/017)。語そのものは terminology.md へ定義付きで移す。本文は変更しない。
---

<!-- **frontmatter の `summary` だけを変える変更指示である。**
     `sections` が空なのはそのためで、本文の見出しは1つも書き替えない。
     反映時に `summary` を上の値へ差し替えること(記法の根拠は
     `.claude/directions/change-set.md` §4.5 = 「テンプレートの既定のままでは実態と食い違う
     frontmatter は変更指示自身の frontmatter に置き、/task-close が写す」)。

     変更前: 「Claude Code を**安全な** Docker コンテナで動かす開発環境と、…」
     変更後: 「Claude Code を Docker コンテナで動かす開発環境と、…」

     本文(`## 背景と目的` ほか)を触らない理由: `.claude/directions/00-requests.md` が
     「request.md は人間の言葉で書かれる。AI が整えるために書き替えてはならない」と定めており、
     人間の回答は枕詞の削除と「安全」の定義だけを認めたものだからである。
     本文中の「安全上の懸念がある」(背景の段落)は `docs/issues/017` の対象に挙がっておらず、
     今回の回答の範囲外なので残す。 -->

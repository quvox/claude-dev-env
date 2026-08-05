---
target: docs/02-design/contracts/entrypoint-firewall.md
change: replace
sections:
  - "# CTR-entrypoint-firewall entrypoint → firewall"
deletes: []
reason: >
  NFR-sec-02 の削除(決定シート概念#2)に伴い、契約の「対応要件」から同 ID を外す。
  外向き通信の制御は FR-env-05 が引き続き要求するので、契約の根拠は消えない。
---

<!-- **反映時に、frontmatter 直後の HTML コメント(2026-08-04 /doc-check ssot task-impl-depth)
     から次の1行を逐語で削除すること**(見出しの**前**にあるので `sections` では指せない。
     **削除するのはこの1行だけ**で、同じコメントの他の行は1文字も変えない)。
     本タスクで `docs/issues/041` を解消するため、この記述は反映後に事実でなくなる
     (「ブロック対象ドメイン」の集合は用語集に定義され、既定の内訳は `MODULE-firewall-init`
     が列挙する)。

     削除する1行(逐語):
       残る「中」: 「ブロック対象ドメイン」の集合が 00・01 に無い(docs/issues/041)。
     この行を消しても直前の行「本文には問題を見つけていない。」でコメントは自然につながり、
     直後の「★本実行は独立レンズが…」の行と `-->` はそのまま残る。 -->

<!-- ★反映時の注意(範囲の明示)。**この変更指示が触るのは H1 直下の3行だけ**である。
     `# CTR-entrypoint-firewall entrypoint → firewall` の節とは、この H1 から
     **次の見出し `## 呼び出しの形` の直前まで**を指す(記法の正:
     `.claude/directions/change-set.md` §2「`sections` に挙げた見出しの最終形だけを本文に書く」)。

     したがって現行文書の次の5節は**変更対象ではなく、そのまま残す**:
     `## 呼び出しの形` / `## エラーケース` / `## 設計判断` / `## 順序性・冪等性・並行性の背景` /
     `## 認可の考え方`。**1節も削除しない。**
     `deletes` が空であることがその宣言であり(削除を省略で表すのは禁止)、
     この注記は独立監査の指摘(反映者が H1 を「文書全体」と解釈する余地がある)に対する
     明示的な打ち消しである。 -->

# CTR-entrypoint-firewall entrypoint → firewall

- 当事者: MOD-entrypoint → MOD-firewall
- 対応要件: FR-env-05
- 責任モジュール(結合テスト): MOD-entrypoint

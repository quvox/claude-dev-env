---
id: 2026-08-25-residual-split
since: 2026-08-25
kind: mechanical
detect: test -d docs && { test ! -f docs/residual.md || grep -qE '^## *残務' docs/pendings.md 2>/dev/null; }
paths: docs/residual.md docs/pendings.md
summary: 残務の置き場が docs/pendings.md の1節から docs/residual.md へ分かれた。既存の行を手で移す
---

## 何が変わったか

2026-08-25 の裁定で、**残務**(課題票にするほどではない小さな気付きを1件1行で書き留める欄)が
`docs/pendings.md` から `docs/residual.md` へ独立した。`docs/pendings.md` に残るのは
棚上げ(`P-nnn`)だけである。同時に 50 行の上限が廃止され、50 件でのローテーションに変わった。

## 手順

**正は `.claude/directions/issues-pendings.md` §2.1 の「旧い版から上げたとき」である**
(ここには写さない — 写しは片方だけが直る)。要点は、雛形を複写し、旧い節の行を
**1行も捨てずに**移し、件数が移す前と一致することを `check-backlog.py` で確かめること。

**`docs/` が無いプロジェクトは「要る」に数えない** ★ — まだ `/setup` を打っていないので
移す行が1つも無い。**展開が壊れて `docs/` が消えた場合の検出は、この移行の仕事ではない**:
`check-backlog.py` が `docs/residual.md` の欠落を終了コード 2 で拒む(`/kit-migrate` の段5 が
それを回す)。ここを「`docs/` が無ければ要る」に変えると、**導入前のディレクトリで毎回
移行が要ると出る。**

## 移らなかったときに何が起きるか

**上書き展開は `docs/` を作らないので、既存の残務の行はどの道具からも見えなくなる。**
`check-backlog.py` はそれを「残務0行」と読まず、終了コード 2 で拒む(`doc-health.py` も同じ)。
`/build` は入口で台帳を読むので、**移し終えるまで構築が始まらない。**

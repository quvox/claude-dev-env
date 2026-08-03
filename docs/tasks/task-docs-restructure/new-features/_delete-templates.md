---
target: docs/_templates/
change: delete
sections: []
deletes: []
reason: 旧体系のドキュメント雛形。新体系の雛形は `.claude/templates/` が唯一の正であり、二重管理になる。
---

削除理由(ディレクトリごと): `.claude/templates/` が正本。対象ファイル: `01-requirements-template.md` / `02-design-template.md` / `03-impl-template.md` / `03-impl-e2e-template.md` / `history-template.md` / `task-template.md` / `00-requests/{request,acceptance,glossary,decisions}-template.md` / `_steering/{product,structure,tech}-template.md`。

**適用時の停止条件**: 上に列挙したファイル**以外**が対象ディレクトリに存在する場合、削除せずに
停止して人間に報告する(移設漏れの可能性があるため)。削除は再帰削除でよいが、列挙と実在が
一致することを確認してから行う。

---
target: docs/_steering/
change: delete
sections: []
deletes: []
reason: 旧体系の steering 3ファイル。新体系では product→00-requests、tech→01-requirements/system.md と 02-design/environments.md、structure→02-design/system.md が担う。
---

削除理由(ディレクトリごと): `product.md` は `docs/00-requests/request.md`、`tech.md` は `docs/01-requirements/system.md`(要件)と `docs/02-design/environments.md`(実コマンド・Codex実行設定)、`structure.md` は `docs/02-design/system.md`(モジュール分割定義)へ移設済み。対象ファイル: `product.md` / `structure.md` / `tech.md`。

**適用時の停止条件**: 上に列挙したファイル**以外**が対象ディレクトリに存在する場合、削除せずに
停止して人間に報告する(移設漏れの可能性があるため)。削除は再帰削除でよいが、列挙と実在が
一致することを確認してから行う。

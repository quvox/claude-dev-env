---
id: 081-bug-check-changeset-aborts-on-a-non-utf8-file-in-the-task-directory
type: bug
severity: 低
found: 2026-08-07
found_in: /doc-check(task-stop-session-spawned-containers。独立レビュー(サブエージェント)の check F 指摘)
related: .claude/scripts/check-changeset.py, .claude/directions/change-set.md, docs/issues/076
pattern: script-aborts-instead-of-skipping-an-unreadable-file
pattern_survey: `new-features/` 配下または `docs/` 配下を走査するキットのスクリプト5本(check-changeset.py / close-task.py / callgraph-check.py / check-relations.py / build-index.py)の読み取り箇所を確認。`OSError` しか捕捉せず `UnicodeDecodeError` で異常終了しうるのは check-changeset.py の 1 箇所のみ(他の4本は明示的に対象拡張子と場所を絞るか、例外を握る)
summary: タスクディレクトリに UTF-8 でない .md ファイルが1つあると check-changeset.py が UnicodeDecodeError で異常終了し、変更指示の検査が1件も走らない
---

# 081 UTF-8 でないファイルが1つあると `check-changeset.py` が全体を落とす

## 事象

`docs/tasks/task-stop-session-spawned-containers/` に macOS が作る AppleDouble のサイドカー
`._sheet.md`(`file -b` = `AppleDouble encoded Macintosh file`)が存在する状態で

```bash
python3 .claude/scripts/check-changeset.py docs/tasks/task-stop-session-spawned-containers
```

を実行すると、次で異常終了する。

```
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xb0 in position 37: invalid start byte
```

`.claude/scripts/check-changeset.py:176` の `p.read_text()` が **`OSError` しか捕捉していない**ため、
デコードに失敗したファイルが1つあると**検査そのものが1件も走らない**。
`new-features` のパスを直接渡した場合は正常に終わる(`合格: 不変条件の違反なし`、exit 0)。

**このサイドカーは人間が macOS のエディタで `sheet.md` を編集すると自動生成される**ので、
本プロジェクトの運用(決定シートを人間が記入する)では再発しうる。

## 影響

- **フェーズ2 のゲート(`/task-doc` §4)が「違反あり」ではなく「異常終了」で止まる。**
  終了コードは 2(使い方・解析のエラー)ではなく Python の未捕捉例外なので、
  CI で回した場合の切り分けが「設定の誤り」なのか「検査の欠陥」なのか読み取れない。
- **本文の欠陥ではないのに、変更指示の検査結果が得られない。** `docs/issues/076`
  (staged コールグラフを変更指示とみなす)と**同じ根**である: 走査対象に
  「変更指示ではないファイル」が混じったときの扱いが決まっていない。

severity を「低」とする根拠: 回避が容易で(`new-features` を直接渡す / サイドカーを消す)、
誤った文書が検査を通ることもない。壊れるのは検査の実行そのものである。

## 再現手順

1. 進行中タスクのディレクトリに UTF-8 でないファイルを置く
   (`printf '\x00\x05\x16\x07\xb0' > docs/tasks/<slug>/._x.md`)。
2. `python3 .claude/scripts/check-changeset.py docs/tasks/<slug>` を実行する。
3. `UnicodeDecodeError` で異常終了することを確認する。

## 対処案

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | `p.read_text()` の例外捕捉に `UnicodeDecodeError` を足し、**読み飛ばしたファイルを1件ずつ報告する**(黙って飛ばさない) | `.claude/scripts/check-changeset.py` 1ファイル。`/kit-improve` 案件 |
| B | 走査対象から `._*`(AppleDouble)と隠しファイルを除く | 同上。ただし「UTF-8 でない普通の名前のファイル」には効かない |
| C | A と B の両方 | 同上。**推奨**(B が典型例を消し、A が残りを落とさずに報告する) |

**この issue はキット側の欠陥であり、`docs/` の仕様ドキュメントは正しい。**
対処は `/kit-improve` が扱う(`docs/issues/076` と同じ扱い)。

## 経緯

- 2026-08-07 `/doc-check`(task-stop-session-spawned-containers): 独立レビューが検出。
  **サイドカー `._sheet.md` は同実行で削除した**(`CLAUDE.md` §3「memo.md と、memo.md が
  名指すファイルだけがタスクディレクトリに存在してよい」に反するため)。スクリプト側は未修正。

---
id: 101-bug-reset-omits-the-unmanaged-container-warning-when-deletion-fails
type: bug
origin_layer: 03
severity: 中
found: 2026-08-11
found_in: /implement task-fix-logout-records-and-marker(タスク4 で `logout` 側の同型を直した際に `reset` 側を確認して検出)
related: docs/03-impl/relations/MODULE-cli-reset.md, docs/02-design/logging.md, docs/01-requirements/functional.md, claude-dev, claude-dev-mac
closes_when: 削除に失敗した `reset` の実行でも、管理ラベルを持たないコンテナの名前が表示されるようになり、E2E-01 手順8 でそれを確認できたとき
summary: reset が削除に失敗した実行では、管理ラベルを持たないコンテナの名前の表示より前に exit 1 するため、受入基準17 が無条件に課している表示が出ない
---

# 101 `reset` が削除に失敗すると、ラベル無しコンテナの表示が出ない

## 事象

`claude-dev reset` の結果表示は、失敗が1件以上あると**ラベル無しコンテナの表示より前に
`exit 1`** する(`claude-dev:2260`〜`:2264` の失敗ブロックと、`:2270` の
`if [ ${#_rc_unmanaged[@]} -gt 0 ]`)。したがって**削除に失敗した実行では、管理ラベルを
持たないコンテナの名前と「本変更より前に起動した可能性がある」ことが表示されない**。

`reset` は使用中のボリュームなどで失敗しやすく(E2E-01 手順8-12 がまさにその状態を作る)、
**失敗する実行のほうが表示を必要とする**。

## 何が仕様に反するか

`docs/01-requirements/functional.md` の `FR-env-03` 受入基準17 は
「管理ラベルを持たない Claude コンテナは削除せず、**その名前と『本変更より前に起動した
可能性がある』ことを表示して残さなければならない**」と定め、**削除の成否で条件づけていない**。
`docs/02-design/logging.md` の「管理ラベルを持たないため削除しなかったコンテナ」の行も
成否の条件を持たない。

## `logout` 側との関係

**同型の欠陥は `logout` にも在り、`task-fix-logout-records-and-marker` のタスク4 で修正した**
(決定シート 論点1 で人間が「畳む」と裁定した分)。`reset` 側は同タスクの「やらないこと」に
`reset` の振る舞いの変更を挙げていたため範囲外で残った。**直し方は `logout` と同じ**で、
失敗ブロックの `exit 1` の直前に残したものの表示を置く(`logout` 側は
`docs/histories/` の該当エントリが実装を記録する)。

## 範囲外とした理由

`task-fix-logout-records-and-marker` の closure は `MODULE-cli-logout` と `logout` の実装であり、
`MODULE-cli-reset` は入っていない。原則8 に従い直さずに起票する。
同型の全件列挙は行っていない(severity が「高」ではないため)。ただし
**`destructive_report` を使う破壊的操作は `logout` と `reset` の2つだけ**であり、
`logout` は修正済みなので、この形が残るのは `reset` の1箇所である。

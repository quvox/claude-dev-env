---
id: index
version: 1.0.0
updated: <YYYY-MM-DD>
source:
  - docs/02-design/system.md
  - docs/02-design/relations.md
  - docs/02-design/contracts/<name>.md
summary: 03-impl 層の目次。機能間連携仕様書群の代表として層全体の版と検証済み記録を持つ
keywords: [目次]
# verified: verify 系フロー(/verify-docs、03層代表は /verify-impl)だけが書く
---

<!-- このファイルは 03-impl 層の代表である。
     relations/MODULE-*.md は個別の版と検証済み記録を持たず、この index が層としてまとめて検証済み記録を持つ
     (1本ごとに版を刻むと変更のたびに全体が失効して実務が回らない)。
     個々の relations の正しさは check-relations.py とコードとの突き合わせで担保する。

     「## 目次」の表は build-index.py が生成する。手書きしない。
     **生成されるのは BEGIN/END GENERATED で囲まれた表だけである。**
     「この層の状態」「02 との差分(未解消のもの)」は手で書く(directions/03-impl.md と同じ集合)。 -->

# 03-impl 目次

## この層の状態

<!-- 鮮度(本数・網羅・最終合格日・乖離件数)はここに写さない — コードが1行動いた瞬間に嘘になる。
     コマンドで測る:
       本数・網羅   python3 .claude/scripts/build-index.py(目次の生成が数える)
       内部整合     python3 .claude/scripts/check-relations.py
       コードとの乖離 python3 .claude/scripts/callgraph-check.py -->

鮮度・件数は上のコメントのコマンドで測る。ここに書くのは**コマンドで測れない状態だけ**
(例: 「MOD-x は分割見直し中(docs/issues/NNN-...)」)。無ければ「特記なし」と明記する。

## 02 との差分(未解消のもの)

<!-- .claude/directions/relations.md §7 の比較結果のうち、未解消のものだけを残す。
     未実装 PLAN 行(PLAN あり / MODULE なし)に限り、認識の正は 02-relations 側(/verify-impl
     check E の読み先)— ここに残って 02 側に無い未実装 PLAN 行は 02 の記載漏れである。 -->

| 種別 | 対象 | 内容 | 対処 |
|---|---|---|---|
| PLAN あり / MODULE なし | PLAN-<slug> | 未実装 | docs/issues/NNN-... |

差分なしの場合は「差分なし」と明記する。

## 目次

<!-- BEGIN GENERATED: build-index.py -->
<!-- END GENERATED -->

## 機能間連携仕様書

`docs/03-impl/relations/index.md` を参照(こちらも生成物)。

## コールグラフ

`docs/03-impl/callgraphs/index.md` を参照。**ツールだけが書く場所**であり、機能間連携仕様書ではない
(`.claude/directions/callgraphs.md`)。版も検証済み記録も持たない純粋な導出物で、鮮度は
`CG_OUT=$(python3 .claude/scripts/resolve-callgraph-out.py) && python3 .claude/scripts/build-callgraphs.py --out "$CG_OUT" --check` で検査する
(進行中タスクがある間、生成先はタスク配下である。同 §3.1)。

<!-- 鮮度・未解決件数はここに写さない(コードが1行動いた瞬間に嘘になる)。
     コマンドで測る: build-callgraphs.py --out "$CG_OUT" --check / callgraph-check.py -->

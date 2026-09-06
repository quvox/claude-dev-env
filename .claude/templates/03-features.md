---
id: features
updated: <YYYY-MM-DD>
summary: <1行。このシステムの機能の一覧と、その入口>
keywords: [機能表, 境界]
# version / verified は持たない(relations 層の代表として docs/03-impl/index.md が持つ)
---

# 機能表

<!-- ★ 境界の定義。仕様の正は .claude/directions/features.md
     ・1入口 = 1機能が既定。複数入口を1行にまとめてよいのは、人間が統合を決めたときだけ
     ・機能ID は relations/<機能ID>.md のファイル名と同一(1:1 は写像ではなく同一ID)
     ・**MODULE-* が機能、MOD-* がモジュール**(接頭辞の直感と逆 — docs/README.md の注記も参照)
     ・入口は callgraphs/ の表記と1文字も違わないこと(違えば突き合わせが黙って空振りする)
       エンドポイントID: `POST /v1/orders` / シンボルID: `path::symbol`
       (まずエンドポイントIDとして照合し、無ければシンボルIDとして照合する)
     ・セル内の `|` は `\|` に逃がす(入口IDは `dispatch ALL|GROUP @ ...` のように `|` を含みうる)
     ・並びは 所属 → 機能ID の辞書順に固定する
     ・種別は relations の kind と同一語彙
     ・材料の出し方:
         python3 .claude/scripts/propose-features.py            # 機能候補・共通基盤候補
         CG_OUT=$(python3 .claude/scripts/resolve-callgraph-out.py) && python3 .claude/scripts/cluster-features.py --out "$CG_OUT"   # ①〜⑤(この表を入力にする)
     ・この表を確定させてから relations を書く。逆順にしない -->

## 機能一覧

| 機能ID | 種別 | 入口 | 所属 | 概要 |
|---|---|---|---|---|

<!-- 種別: user-action | event | function-call | rest-api | tool | other
     行の書式(例。プレースホルダの行を表に残さない — 機械がそのまま照合対象に読む):
       | MODULE-<module-slug>-<feature> | rest-api | <METHOD> </path> | MOD-<slug> | <1行80字以内> |
       | MODULE-<module-slug>-<feature> | function-call | <path>::<symbol> | MOD-<slug> | <1行80字以内> | -->

## 統合した機能

<!-- 複数の入口を1行にまとめた場合だけ、その理由をここに残す。
     機械は「関数集合の重なりが大きい機能対」を統合候補として出すが、束ねる判断は人間が行う。
     まとめていないなら「なし」と書く。 -->

| 機能ID | まとめた入口 | まとめた理由 |
|---|---|---|
| <> | <> | <> |

## 昇格させた共通基盤機能

<!-- ファンイン(到達できる機能の数)が2以上の関数は境界の実体である(.claude/directions/features.md §4)。
     機能表に足すとルートに昇格し、呼んでいた側に callees の辺が1本立つ。
     ファンインが高くても畳み込んだままにしたものは、その判断もここに残す(次に候補として再提示されるため)。 -->

| 機能ID / シンボル | ファンイン | 昇格したか | 判断の理由 |
|---|---|---|---|
| <path>::<symbol> | <n> | 昇格 / 畳み込む | <> |

## 棄却した候補辺・確認済みの境界辺

<!-- CG4(候補)の辺をコードを読んで棄却した場合、および境界辺(REST/キュー越し)の
     「AI の主張・根拠要」を人間が確認した場合の記録(.claude/directions/callgraphs.md §6)。
     ここに無い棄却はレポート限りで消え、次回の検査で同じ候補が未判断として再提示される。
     無ければ「なし」と書く。 -->

| 辺(A→B) | 種別(候補棄却 / 境界確認) | 判断 | 理由・根拠 | 日付 |
|---|---|---|---|---|
| <> | <> | 棄却 / 採用 / 確認済み | <> | <YYYY-MM-DD> |

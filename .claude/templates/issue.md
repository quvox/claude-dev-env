---
id: <NNN>-<bug|modify|future>-<slug>
type: bug
severity: 中
origin_layer: <00|01|02|03>
found: <YYYY-MM-DD>
found_in: <**誰が見つけたか**。verify 系フロー / 実装中 / QA / 人間の指摘 — 「人間の指摘」だけが昇格後の構築記録を origin: human-report にする(delegation.md §5)>
related: <FR-..., MODULE-..., CTR-...>
closes_when: <この課題票が閉じたと言える観測可能な条件。必須 — 書けないものは課題票ではなく docs/residual.md の残務1行>
pattern: <同型のID。kebab-case。severity: 高 のときだけ必須。それ以外は「なし」でよい(directions/issues-pendings.md §3.1)>
pattern_survey: <どのファイル群を走査して何件あったか。pattern があるなら空にできない(CS12。§3.1)>
summary: <1行>
---

<!-- タスク化前の課題票(不具合を含む)。1件1ファイル。
     ファイル名は docs/issues/NNN-<TYPE>-<slug>.md。NNN は3桁の昇順連番(欠番は埋めない)。
     type: bug | modify | future / severity: 高 | 中 | 低
     **severity の判定表の正は .claude/directions/issues-pendings.md §3.0**(ここに写さない。
      複数当たれば最上位。頻度は判定材料にしない — 全件走査は「高」だけの義務なので循環する)
     frontmatter の値の後ろに `# コメント` を書かない(build-index.py が値として index に写す)。
     仕分けの基準(記録先の振り分け)は .claude/directions/issues-pendings.md §1 —
     **課題票にできるのは「仕様に対して振る舞いが誤っている(bug)」か「完了定義を塞ぐもの」だけ。**
     (後者には「人間の回答がまだ SSOT に反映されていない」= type: modify が含まれる。flows.md §5)
     それ以外の文書整合・言い回し・技術的負債は docs/residual.md の「残務」に1行で書く(ファイルを作らない)。
     ・**origin_layer は「直しが始まる層」であって、見つけた場所ではない**(見つけた場所は found_in)。
       規則は .claude/directions/issues-pendings.md §1、検査は CS20。
       **迷ったら上へ** — 「実装が仕様と違う」は 03 だが、「その仕様が要求と違う」なら 01 か 00 である
     ・黙って直すのも黙って放置するのも禁止(記録先が振り分けで変わるだけ)
     ・**同型の全件列挙(pattern / pattern_survey)は severity: 高 のときだけ必須**
       (directions/issues-pendings.md §3.1)。中・低に列挙を要求してはならない
     ・severity: 高 の bug が残る状態で「仕様ドキュメントは完全である」と報告してはならない
     ・/build <issue-id> でタスクに昇格する。昇格してもファイルは残し、/build が完了時に削除する
     ・**closes_when は後から読み返される。** doc-health.py が記録日つきで
       docs/reverification.md の「鮮度確認の候補」に載せる。**本文が読まれるのは昇格のときだけ**
       なので、昇格時に「もう満たされていないか」を1回確かめる(規範:
       .claude/directions/issues-pendings.md §8)。満たされていれば昇格せず経緯に1行追記する
     ・found は発見日であって最終確認日ではない。**確認しても上書きしない** -->

# <NNN> <タイトル>

## 事象

<観測した事実だけ。再現手順があれば書く>

再現手順:

1. <>

## 影響

<誰に・何が起きるか。severity の根拠>

## 原因の見当

<分かっている範囲。**推測は「推測」と明示する**>

## 正はどちらか

<!-- 実装が誤りか、要件・設計が誤りか。**勝手に寄せない**が、
     事実の差異(パス・シグネチャ・呼び出しの有無)はコードを読めば決まるので
     「実装が正」/「要件・設計が正」と書き切る。**どちらも正でありうる意図の差異だけ**を
     「要確認」にする(原則2 の振り分けの正は .claude/directions/03-impl.md)。
     「判断できなかった」は、それ自体では要確認の理由にならない -->

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| <> | <> | <> | 要確認 |

## 対処案

<分かる範囲で。工数見積は書かない>

| 案 | 内容 | 波及の見込み |
|---|---|---|
| A | <> | <> |

## 経緯

- <YYYY-MM-DD> <起票 / 昇格 / 誤検知と判明した理由 など>

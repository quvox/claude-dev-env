---
id: 2026-08-20-delete-issue-110-per-human-adjudication
date: 2026-08-20
record: docs/build-records/delete-issue-110-per-human-adjudication.md
critical: false
origin_layer: 03
issue: docs/issues/110-bug-bundled-arm64-binary-is-a-darwin-build.md
summary: 人間の裁定により issue 110 を削除した(closes_when は未充足)。参照していた 03 層の集計文と生成索引を整合させ、残務行は足さないと裁定した
---

# 2026-08-20 issue 110 を人間の裁定で削除し、参照側を整合させた

## 変更理由

### R-01 issue 110 の削除が人間の裁定で決まった(`closes_when` は未充足である)

- 起点層・根拠: 人間の裁定(逐語。要望台帳 006 / 2026-08-20)
  > externalsについてはあなたは今は何もしなくてよい。issueも閉じて

  `.claude/directions/issues-pendings.md` §8 は issue の削除を人間の判断と定めており、その判断が下りた。
- 変更が必要になった条件: **`closes_when` の3項目はどれも満たされていない。**
  (a) `file externals/arm64/colabtmux` は 2026-08-20 現在も
  `Mach-O 64-bit arm64 executable, flags:<|DYLDLINK|PIE>`(8,343,362 バイト)を返す。
  (b) 同ファイルはリポジトリに在る(HEAD の内容も同じ。`git log -1 -- externals/arm64/colabtmux` → `a411581`)。
  (c) 人間は「arm64 には同梱しない」とは述べておらず「今は何もしなくてよい」と述べたので、
  `externals/README.md` と `03-impl/environments/images.md` の記述変更も行っていない。
  **削除の根拠は人間の裁定のみであり、`closes_when` を満たしたからではない。**

## 変更内容の要約

- `docs/issues/110-bug-bundled-arm64-binary-is-a-darwin-build.md` を削除した。
- 削除で宙づりになる 03 層の集計文の 110 参照を、削除の事実・`closes_when` 未充足・
  集計 4件 が変わらないこと・**同梱物が darwin ビルドである事実は残ること**に書き替えた。
- 生成索引4本(`docs/issues/index.md` 7→6件 / `docs/reverification.md` /
  `docs/build-records/index.md` / `docs/histories/index.md`)をツールで再生成した。手書きしていない(原則10)。
- **`externals/` には一切触れていない**(人間の裁定)。`.devcontainer/` と
  `01-requirements/functional.md`(issue 110 の案 C)にも触れていない。
- **`docs/pendings.md` に残務行を足していない**(裁定の理由は「検討した代替案」の表に書いた)。
- 当時の事実の記録(`docs/build-records/fix-make-status-hides-docker-query-failure.md` と
  `docs/histories/` の2ファイル)の 110 参照は直していない。

## 更新したドキュメント

| 理由ID | ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|---|
| R-01 | docs/03-impl/index.md | 1.35.0 → 1.35.1 | 「この層の状態」の「実装の欠陥として起票済み」行の `110` の文を、2026-08-20 に人間の裁定で削除したこと・`closes_when` 3項目が未充足であること・もともとこの集計に入っておらず 4件 は変わらないこと・同梱物が darwin ビルドである事実は残ることに書き替えた(集計値が動かないので PATCH) |
| R-01 | docs/issues/index.md | (生成物) | `build-index.py` で再生成。7件 → 6件 |
| R-01 | docs/reverification.md | (生成物) | `doc-health.py` で再生成。鮮度確認の候補(issue)から 110 の行が外れた |
| R-01 | docs/build-records/index.md | (生成物) | `build-index.py` で再生成(本タスクの構築記録の追加) |
| R-01 | docs/histories/index.md | (生成物) | `doc-health.py` で再生成(本履歴の追加) |

## 実装したもの

| 理由ID | 対象 | 内容 | コミット |
|---|---|---|---|
| R-01 | (なし) | 製品コードの変更は無い。文書と課題記録のみを変更した | - |

## 実施した移行

なし。

| 理由ID | 対象 | 手順(実行したコマンド / スクリプト) | 実行日 | 結果・確認方法 |
|---|---|---|---|---|
| R-01 | なし | なし | - | - |

### ロールバック・復旧記録

適用外(`critical: false`。認証・決済・不可逆・個人情報・監査のいずれにも触れていない。削除した
issue ファイルは git 履歴に残るので `git show` で復元できる)。

## 機能間連携仕様書の変化

| 種別 | ID | 内容 |
|---|---|---|
| 変更なし | - | 機能間連携仕様書には触れていない |

## 検討した代替案

| 論点 | 採用した案 | 棄却した代替案 | 棄却の理由 / 崩れる条件 |
|---|---|---|---|
| 同梱物が darwin ビルドである事実を `docs/pendings.md` の残務に1行残すか | **残さない** | 残務1行を足す | (1) 原則8 のゲートはこの事実を **issue** へ振り分ける(`AC-07` の不合格条件に逐語で当たる severity 「高」の bug である)。残務は `closes_when` も severity も追跡義務も持たず、**検証が読み返さない**列である(`.claude/directions/issues-pendings.md` §2.1 冒頭)。severity 「高」をそこへ移すのは記録ではなくゲートの緩めである。(2) 行の `path` が `externals/arm64/colabtmux` になるが、人間が externals に触るなと裁定した以上この path は closure に入り得ず、**排出義務(§2.1 (3))が誰にも発生しない**。50 行の上限に達したとき「恒久的に受容する」という決定を**人間ではなく上限が下す**ことになる。(3) 事実は失われない — 本履歴と構築記録に実測値つきで残る。崩れる条件: 人間が externals を触ってよいと裁定したとき(そのとき改めて issue として起票する) |
| 同じ論点 | 同上 | キットの規範(`issues-pendings.md` §8)に「人間の裁定で閉じた issue の残る事実の扱い」を足す案を残務1行にする | §8 の末尾は既に「staleness の指摘を新規 issue にも残務にもしてはならない」と定めており、そこから導ける。CLAUDE.md §3 は「規範かスコープを減らす、process を足さない」と定めている。崩れる条件: 同じ判断を3回目に迫られたとき |
| `docs/03-impl/index.md` の 110 の文の始末 | 削除済みであることを裸の番号 `110` で明記し、`closes_when` 未充足と集計が変わらない理由を残す | 文ごと削除する | この節は「この集計そのものを維持する責任は本節にある」と自ら定めており、増減の経緯を残す書式を既に採っている(同じ行の `106` / `002` / `046` / `102`) |
| 同上 | 同上 | `docs/issues/110` の表記のまま残す | 削除後は `check-ssot.py` の CS11(参照実在)違反になる(`.claude/scripts/check-ssot.py:181`) |
| 同上 | 同上 | 「(c) を満たしたので閉じた」と書く | **偽である。**人間は「arm64 には同梱しない」と裁定しておらず、(c) が要求する `externals/README.md` と `03-impl/environments/images.md` の記述もこのタスクは変えていない(原則1・原則2) |
| `docs/03-impl/index.md` の版の上げ幅 | PATCH(1.35.0 → 1.35.1) | MINOR(1.36.0) | 集計値 4件 は変わらず、消えた issue への言及を現状に合わせただけで意味は動かない。崩れる条件: この節の集計値そのものが動くとき |
| `externals/arm64/colabtmux` の差し替え(issue 110 の案 A)・削除(案 B)・設置時検査の新設(案 C) | いずれも採らない | 案 A / 案 B / 案 C | 人間が「externals についてはあなたは今は何もしなくてよい」と逐語で裁定した。崩れる条件: 人間が arm64 イメージの公開を再開すると決めたとき |
| 残務行の排出義務(closure に載る3行) | 3行すべて **持ち越す** | 直す / 不要と裁定する | 3行はいずれも本タスクの降下が触っていない箇所を指す。(1) 2026-08-11「コード引用の行番号のずれ」(`docs/03-impl/index.md` を含む9件)= 実コードに1件ずつ当て直す作業が要り closure の外。(2) 2026-08-19「削除済み issue を指す参照が6件」(`reverification.md:87` の `docs/issues/024` を含む)= `reverification.md` は生成物で、参照の出どころは `issues/028` 側にある。(3) 2026-08-20「廃止された `compose-changeset.py` 等を指す記録」(`docs/03-impl/index.md:41`・`:48`・`:50`)= 日付で固定された検証記録であり、本タスクは 28 行目しか触っていない |

## 副産物

| 種別 | 行き先 | 内容 |
|---|---|---|
| 知見 | 今回限り(`.claude/directions/issues-pendings.md` §8 が「削除は人間の判断」と定めており、AI の見立て(severity 「高」の起票)が外れたわけではない。次も同じく人間に聞く) | **`closes_when` を満たさない削除は「満たした」と書かず、未充足であることと裁定が唯一の根拠であることを削除の記録に残す。**そして、issue が消えても事実が消えないとき、その事実を残務行へ移してはならない — 残務は追跡義務も severity も持たず検証が読み返さない列であり、severity 「高」の降格路になる |
| 解消した issue | docs/issues/110-bug-bundled-arm64-binary-is-a-darwin-build.md(削除) | 人間の裁定による削除。**`closes_when` (a)(b)(c) はいずれも未充足である。**`stamps.py check` のデプロイ関門から bug 1件が外れた |
| 新規 issue | なし | - |
| 棚上げ | なし | - |
| 気づき | なし | - |

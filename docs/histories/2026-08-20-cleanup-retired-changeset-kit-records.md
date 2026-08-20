---
id: 2026-08-20-cleanup-retired-changeset-kit-records
date: 2026-08-20
record: docs/build-records/cleanup-retired-changeset-kit-records.md
critical: false
origin_layer: 00
issue: なし
summary: 規約刷新で廃止された変更指示系スクリプト・規範に紐づくキットパッチ1本・残務8行・issue3件を消した
---

# 2026-08-20 廃止済みスクリプトに紐づく記録の後始末

## 変更理由

### R-01 人間が「キットの修正は破棄する」と決めた

- 起点層・根拠: 人間の要望(`.claude/missions/2026-08-20-converge-contract-green/requests.md` 001、
  2026-08-20)「規約を新しくしたので、まずキットの修正は破棄する」。
- 変更が必要になった条件: 規約刷新で `.claude/scripts/check-changeset.py` / `close-task.py` /
  `compose-changeset.py` / `changeset-invariants.json` と `.claude/directions/change-set.md` が
  廃止され、それらへ戻すためのパッチが宛先を失った。

### R-02 廃止された道具だけを対象にした記録が残っていた

- 起点層・根拠: 原則8(記録はゲートを通す)と `issues-pendings.md` §8(記録は書かれた日の事実。
  対象が消えたなら記録も残らない)。
- 変更が必要になった条件: 上記スクリプトと規範ファイルが実在しなくなり、それだけを対象にした
  残務8行と issue 3件が、誰も手を付けられない記録として滞留していた。

## 変更内容の要約

- `kit-patches/2026-08-10-compose-changeset-and-close-task.patch` を削除した(要望001 の実行)。
- `docs/pendings.md` の残務から、廃止済みの道具・規範だけを対象にした8行を消し、
  1行を実測で取り直し、2行のスクリプト名を現行の `check-ssot.py` へ直し、
  取りこぼした参照について1行を足した(42行 → 35行)。
- `docs/issues/` の 076 / 079 / 081 を削除した(対象ファイルが3件とも実在しない)。
- 生成物 `docs/issues/index.md` / `docs/build-records/index.md` / `docs/reverification.md` /
  `docs/histories/index.md` をツールで再生成した。

## 更新したドキュメント

| 理由ID | ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|---|
| R-02 | docs/pendings.md | 版を持たない(状態層) | 残務8行を削除、1行を実測で更新、2行のスクリプト名を訂正、1行を追加 |
| R-02 | docs/issues/index.md | 生成物 | build-index.py で再生成(13件 → 10件) |
| R-02 | docs/reverification.md | 生成物 | doc-health.py で再生成(削除した issue 3件が消えた) |

00 / 01 / 02 / 03 の仕様ドキュメントは1バイトも変えていない。この変更は状態層(記録)に閉じており、
目的・振る舞い・構造・実装詳細のどれも動かないためである(原則3)。

## 実装したもの

| 理由ID | 対象 | 内容 | コミット |
|---|---|---|---|
| R-01 | kit-patches/ | 廃止済みスクリプトへ戻すパッチ1本を削除 | <sha1> |
| R-02 | docs/issues/ | 076 / 079 / 081 を削除 | <sha1> |

## 実施した移行

なし

### ロールバック・復旧記録

適用外(critical: false。製品の振る舞いに触れず、消えたものはすべて git 履歴に残る)

## 機能間連携仕様書の変化

なし(`MODULE-*` / `PLAN-*` の増減は0件。製品コードを触っていない)

## 検討した代替案

| 論点 | 採用した案 | 棄却した代替案 | 棄却の理由 / 崩れる条件 |
|---|---|---|---|
| `docs/03-impl/index.md:41,48,50` が廃止済み `check-changeset.py` を検証の道具として名指している | 触らず残務1行にする | 道具名を書き換える | 当該記述は**日付つきの検証記録**であり、当時その道具で確認したことは事実である。書き換えると事実でない記録になる。加えて同ファイルは並走中の別タスクの closure に入っており、交差を作る |
| `docs/02-design/system.md:465` の HTML コメントが廃止済み `compose-changeset.py` と `change-set.md` を根拠に挙げている | 触らず残務1行にする | 本タスクでコメントを消す | `@triage` が取った closure 非交差の証明(T1×T2=T1×T3=T1×T4=0)を壊す。証明の取り直しは中央の仕事であり、1行のコメントのために並走を止める価値が無い |
| `docs/issues/079` を残すか消すか | 消す | 残す | `related:` の3件(`changeset-invariants.json` / `change-set.md` / `check-changeset.py`)がすべて実在しない。CS6 / CS7 という検査そのものが消えたので、要否を決める対象が無い |
| 残務190行(issue の `origin_layer` / `closes_when` 欠落)の扱い | 件数を実測で取り直して持ち越す | 削除する | 残る5件(005 / 010 / 028 / 046 / 055)は廃止済み道具と無関係で、欠落は今も本当である |

## 副産物

| 種別 | 行き先 | 内容 |
|---|---|---|
| 知見 | 今回限り(規約刷新という一度きりの事象に固有。同型の知見は `docs/feedbacks/026` が既に持つ) | 規範を差し替えたら、その規範だけを対象にしていた記録(issue・残務・パッチ)は同じ降下で消す。残すと「誰も手を付けられない記録」として滞留し、負債ゲージの数だけを押し上げる |
| 解消した issue | docs/issues/076(削除) | 対象の `check-changeset.py` / `close-task.py` / `change-set.md` が実在しない |
| 解消した issue | docs/issues/079(削除) | 対象の `changeset-invariants.json` / `change-set.md` / `check-changeset.py` が実在しない |
| 解消した issue | docs/issues/081(削除) | 対象の `check-changeset.py` が実在しない |

### 排出した残務の裁定(`issues-pendings.md` §2.1(3))

| 旧行 | 内容(要約) | 裁定 |
|---|---|---|
| :167 | `change-set.md` 例外2 と `check-changeset.py` CS1 の食い違い | 不要と裁定(両方とも実在しない) |
| :170 | キット書き換えで `*.local.json` が失われた件 | 不要と裁定(`callgraph-config.local.json` は実在、`entrypoint-patterns.local.json` は「無いのが既定」= `check-kit-refs.py:197-201`、`changeset-invariants.local.json` は対象スクリプトごと廃止) |
| :171 | `change-set.md` §2 で親本文の変更と子見出しの改名を同時に表せない | 不要と裁定(規範ファイルが実在しない) |
| :172 | `compose-changeset.py` が `features.md` の一部節に届かない | 不要と裁定(スクリプトが実在しない) |
| :173 | `kit-patches/…patch` を本流へ戻すこと | 直した(人間の要望001 により破棄) |
| :174 | `change-set.md` §2 で最初の見出しより前の本文を指せない | 不要と裁定(規範ファイルが実在しない) |
| :176 | 変更指示の語彙が SSOT へ漏れても機械検査が落ちない | 不要と裁定(変更指示の仕組みそのものが廃止。`/build` が SSOT を直接書く) |
| :179 | `check-changeset.py` CS19 と `change-set.md` §2 が両立しない | 不要と裁定(両方とも実在しない) |
| :190 | issue の `origin_layer` / `closes_when` 欠落 | 持ち越す(残る5件は別の根。削除3件を反映して件数を 9/11 → 5/6 に取り直した) |
| :191 :193 | 削除済み issue への参照 / E2E-01 手順7-3 の同期点欠落 | 持ち越す(実体は生きている。名指していた `check-changeset.py --ssot` を現行の `check-ssot.py` へ直しただけ) |

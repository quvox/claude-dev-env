---
id: 2026-08-20-delete-issue-102-per-human-adjudication
date: 2026-08-20
record: docs/build-records/delete-issue-102-per-human-adjudication.md
critical: false
origin_layer: 03
issue: docs/issues/102-bug-colabtmux-refuses-to-launch-codex-on-a-nonzero-bwrap-probe.md
summary: 人間の裁定により issue 102 を削除し、参照していた 03 層の集計文・残務行・生成索引を整合させた
---

# 2026-08-20 issue 102 を人間の裁定で削除し、参照側を整合させた

## 変更理由

### R-01 issue 102 の削除が人間の裁定で決まり、製品側に残る作業が無い

- 起点層・根拠: 人間の裁定(逐語。要望台帳 003 / 2026-08-20)
  > issue 102 は消していい。バイナリ差し替えは意図したものなので起票して。kitの不備は修正してパッチを作って

  `.claude/directions/issues-pendings.md` §8 は issue の削除を人間の判断と定めており、その判断が下りた。
- 変更が必要になった条件: `closes_when` 3項目のうち未達の「colabtmux から codex を起動でき報告が出ないこと」は
  直す先がキットの `.claude/directions/orchestration.md` §1.1.1 であり、それは `/kit-improve` の別タスクが担う。
  「`codex exec` が起こすコマンドが成功すること」は共有ボリュームに codex の認証が無く無人では確認できない。
  **製品側にやることが残っていない状態での削除である。**

## 変更内容の要約

- `docs/issues/102-bug-colabtmux-refuses-to-launch-codex-on-a-nonzero-bwrap-probe.md` を削除した。
- 削除で嘘になる・宙づりになる参照を3箇所直した(03 層の集計文・残務1行・生成索引2本)。
- 当時の事実の記録(`docs/histories/` 6ファイル・`docs/feedbacks/032`・
  `docs/build-records/document-codex-sandbox-preconditions.md`)の 102 参照は直していない。
  `docs/pendings.md` の残務行が「履歴は当時の事実なので直さない」と定めているためである。

## 更新したドキュメント

| 理由ID | ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|---|
| R-01 | docs/03-impl/index.md | 1.34.0 → 1.34.1 | 「この層の状態」の「実装の欠陥として起票済み」行から `docs/issues/102` への参照を外し、102 は 2026-08-20 に人間の裁定で削除したこと・もともとこの集計に入っておらず 4件 は変わらないことに書き替えた(集計値が動かないので PATCH) |
| R-01 | docs/pendings.md | (版を持たない) | 残務行の `docs/issues/102` 参照を「2026-08-20 に人間の裁定で削除した issue `102`」と履歴への案内に書き替えた。**行そのものは残した** — この行が指す仕事はキットの規範の修正であり、102 の削除では消えない |
| R-01 | docs/issues/index.md | (生成物) | `build-index.py` で再生成。8件 → 7件 |
| R-01 | docs/reverification.md | (生成物) | `doc-health.py` で再生成。鮮度確認の候補(issue)8 → 7 |
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
| `docs/03-impl/index.md` の 102 の文の始末 | 削除済みであることを裸の番号 `102` で明記し、集計が変わらない理由を残す | 文ごと削除する | この節は「この集計そのものを維持する責任は本節にある」と自ら定めており、増減の経緯を残す書式を既に採っている(同じ行の `106` / `002` / `046`)。崩れる条件: 集計の経緯を別の場所が持つようになったとき |
| 同上 | 同上 | `docs/issues/102` の表記のまま残す | 削除後は `check-ssot.py` の CS11(参照実在)違反になる(`.claude/scripts/check-ssot.py:181`) |
| `docs/03-impl/index.md` の版の上げ幅 | PATCH(1.34.0 → 1.34.1) | MINOR(1.35.0) | 集計値 4件 は変わらず、消えた issue への言及を現状に合わせただけで意味は動かない。MINOR にすると同日に `/verify-impl all` が書いた合格証(`verified.version: 1.34.0`)を無効にしてしまう。崩れる条件: この節の集計値そのものが動くとき |
| `docs/pendings.md` の 102 由来の残務行 | 行を残し、宙づりになる参照だけを直す | 行ごと削除する | この行が指す仕事は `.claude/directions/orchestration.md` §1.1.1 の判定を `codex sandbox -- /bin/true` に替えることであり、キット側で未了である。102 の削除では消えない |
| コード引用の行番号のずれ(2026-08-11 の残務行。`docs/03-impl/index.md` の4箇所を含む) | 持ち越す | 本タスクで取り直す | 取り直しには `claude-dev` / `claude-dev-mac` に1件ずつ当て直す作業が要り、本タスクの closure(issue 102 の削除と参照整合)の外である。本タスクはコード引用を1箇所も触っていない |

## 副産物

| 種別 | 行き先 | 内容 |
|---|---|---|
| 知見 | 今回限り(`.claude/directions/issues-pendings.md` §8 が「削除は人間の判断」と定めており、AI の見立てが外れたわけではない。次も同じく人間に聞く) | `closes_when` の未達項目の直す先が凍結中のキットにしか無い issue は、製品側に作業が残らない。それでも削除は人間の裁定を待つ |
| 解消した issue | docs/issues/102-bug-colabtmux-refuses-to-launch-codex-on-a-nonzero-bwrap-probe.md(削除) | 人間の裁定による削除。`stamps.py check` のデプロイ関門から bug 1件が外れ、残るブロッキング issue は `109` だけになった |
| 新規 issue | なし | - |
| 棚上げ | なし | - |
| 気づき | なし | - |

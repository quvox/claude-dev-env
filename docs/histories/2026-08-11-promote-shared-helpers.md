---
id: 2026-08-11-promote-shared-helpers
date: 2026-08-11
task: task-promote-shared-helpers
origin_layer: 02
issue: docs/issues/096-modify-fourteen-shared-helpers-with-fanin-2-or-more-are-absent-from-the-feature-table.md
summary: ファンイン2以上の共有関数14シンボルの昇格・畳み込みを決めて機能表・PLAN・MODULE へ反映した(コード変更なし)
---

# 2026-08-11 ファンイン2以上の共有関数を機能へ昇格させる

## 変更理由

`propose-features.py` が共通基盤候補として挙げるファンイン2以上の共有関数 14 シンボル
(OS 別実装を数えると 28)が、`docs/03-impl/features.md` の「昇格させた共通基盤機能」表に
**1件も現れていなかった**(`docs/issues/096`)。
`.claude/directions/features.md` §3 は「昇格させないと決めた場合もその判断を機能表に記録する
(そうしないと次回同じ候補が再提示され、議論をやり直すことになる)」と定めており、
実測として同じ候補が再提示されていた。

害は記録の欠落にとどまらなかった。**`MODULE-cli-logout` と `MODULE-cli-reset` が同一実装
(`claude-dev:634`-`:700` の1組の関数)について別々の文を4項目分持っており**、片方だけを直すと
2つの仕様が食い違う経路が開いていた。

起点層が 02 なのは、**境界の位置がモジュール分割の問題**だからである(`.claude/directions/features.md`
§7「境界は設計判断であり、人間が合意する」)。

## 変更内容の要約

- ファンイン2以上の 14 シンボルについて、**昇格 / 畳み込みの判断を全件記録した**。
- うち5機能を新設した(8関数の統合1件・3関数の統合1件・単独3件)。
- 呼び出し元4機能の `callees` に辺を立て、**重複していた記述を昇格先へ移した**。
- `MOD-cli-common` が 12 → 17 機能になることを `DSN-mod-07` として許容した。
- 共有基盤の分類を3種類(判定系・用意系・排他系)から**4種類**にし、「記録系」を加えた。
- **コードは1行も変更していない**(コールグラフを再生成して SSOT 版と1バイトも違わないことを確認した)。

## 更新したドキュメント

| ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|
| docs/02-design/system.md | 2.9.1 → 2.10.0 | `MOD-cli-common` の責務に昇格した5つを追記、対応要件に `FR-env-07` を追加、冒頭注記の機能数 56 → 61、`DSN-mod-07`(17機能の許容)を新設 |
| docs/02-design/relations.md | 1.8.0 → 1.9.0 | `PLAN-cli-common-*` を5件追加、`PLAN-cli-start` / `-stop` / `-logout` / `-reset` の呼び出す先を更新、共有基盤の分類に「記録系」を追加 |
| docs/03-impl/features.md | (版を持たない。代表は 03-impl/index.md) | 機能一覧 56 → 61 行、統合した機能に2行、昇格させた共通基盤機能に **14シンボル全件**の判断を記録 |
| docs/03-impl/index.md | 1.21.0 → 1.22.0 | 層代表の版。「この層の状態」の本数を 61 へ、`check-relations.py` / `relations-coverage.py` の再実行結果を更新、`docs/issues/097` の原因(抽出器の決定 D)を追記、「02 との差分」に「差分なし」を明記 |
| docs/03-impl/tests/cli-common.md | 1.3.0 → 1.4.0 | 機能 ⇄ テスト表に5行、未検証の全件に #21〜#25、summary を 17 機能へ |
| docs/03-impl/relations/MODULE-cli-logout.md | (層代表が持つ) | `callees` に destructive / net-other を追加、判断3・9・13 から重複規則を昇格先へ移設 |
| docs/03-impl/relations/MODULE-cli-reset.md | 〃 | `callees` に3件を追加、判断4・8・10・13・17 を同様に整理 |
| docs/03-impl/relations/MODULE-cli-start.md | 〃 | `callees` に compose-project-name / container-project-dir を追加、判断3 を昇格先を名指す形へ |
| docs/03-impl/relations/MODULE-cli-stop.md | 〃 | `callees` に4件を追加。**判断20「この関数は機能表の1機能ではなく共有関数である」が偽になったので書き換えた** |

## 実装したもの

| 対象 | 内容 | コミット |
|---|---|---|
| (なし) | **コード変更なし**。本タスクは境界の記録と文書の再配置だけである | — |

## 実施した移行

なし(データ・スキーマの移行を伴わない)。

## 機能間連携仕様書の変化

| 種別 | ID | 内容 |
|---|---|---|
| 追加 | MODULE-cli-common-destructive | `destructive_*` 8関数(OS 別を含め16シンボル)を1機能へ統合。削除の記録・報告と中断の遅延 |
| 追加 | MODULE-cli-common-compose-project-name | `compose_project_name` / `_legacy` / `sha256_hex` を1機能へ統合。compose 一意化名の導出 |
| 追加 | MODULE-cli-common-container-project-dir | 管理ラベル `claude-dev.project-dir` の読み取り |
| 追加 | MODULE-cli-common-spawned-resources | セッション由来の資源の列挙 |
| 追加 | MODULE-cli-common-net-other-running-containers | 遊休判定に使う集合の算出(ファンイン3で最大) |
| 変更 | MODULE-cli-logout | `callees` +2。重複していた記録・中断の規則を昇格先へ移した |
| 変更 | MODULE-cli-reset | `callees` +3。同上 |
| 変更 | MODULE-cli-start | `callees` +2 |
| 変更 | MODULE-cli-stop | `callees` +4。判断20 を書き換えた |

**昇格の収束**: 反映後に `cluster-features.py` を再実行し、**共有関数 0 件**を実測した
(反映前は 28 件)。1回の昇格で新たなファンイン2以上は現れなかった。

## 検討した代替案

| 論点 | 採用した案 | 棄却した代替案 | 棄却の理由 / 崩れる条件 |
|---|---|---|---|
| 14シンボルをどこまで昇格させるか | **案A′**(5機能へ昇格。`compose_project_name_legacy` を統合に含める) | **`docs/issues/096` の案A**(`legacy` を統合しない) | `legacy` は `stop` の本体からも直接呼ばれる(`claude-dev:1615` / `:1692`)ので、`compose_project_name` だけを昇格させてもファンイン2が残り、次回同じ候補が再提示される |
| 同上 | 同上 | **案B**(14件すべて畳み込むと記録するだけ) | `MODULE-cli-logout` / `-reset` の重複4項目が残り、片方だけを直すと2つの仕様が食い違う経路も残る |
| 同上 | 同上 | **案C**(破壊的操作の8関数だけ昇格) | compose 一意化名も「2機能が共有する形式の規則」であり、同じ理由が当てはまる |
| `MOD-cli-common` が17機能になること | **許容**(`DSN-mod-07`) | **`MOD-cli-destructive` / `MOD-cli-naming` へ分割** | 入口を持たないモジュールが2つ増え、`DSN-mod-01`(モジュール = 利用者から見た入口と1対1)と `DSN-mod-03`(共有基盤は1モジュールに集約)の両方に反する。**崩れる条件**: `MOD-cli-common` が 20 機能を超えたとき、または共有基盤どうしが呼び合う辺が5本を超えたとき(現在2本) |
| 用語「破壊的操作」を機能名に冠するか | **冠さない**(用語は3サブコマンドの定義のまま据え置き) | 用語を機能に合わせて広げる | `stop` を含む3コマンドを指す 00 の語が2コマンドの実装を指すことになり、`D0-env-08` 項5(`stop` だけが例外)の読み方が壊れる |
| 共有基盤の分類 | **4つ目「記録系」を認めて `MOD-cli-common` に置く** | 共有基盤の外に出す | 機能1本だけのモジュールが増え、`DSN-mod-01` とも合わない(この手順は利用者から見た入口を持たない) |
| `docs/issues/097` を畳み込むか | **畳み込まない**(issue のまま残す) | 畳み込む(人間が当初こちらを選択) | **フェーズ2 のドライランで実施不能と判明した** — シェル抽出器の決定 D が `help\|*)` のラベルを丸ごと入口から外すため、機能表に足すと FT1 が重大度「高」で落ちる。回避策はコード変更(本タスクの範囲外)かキット変更(製品 DoD 未達で凍結中)しかない。**崩れる条件**: 凍結が解けたとき |

## 副産物

| 種別 | 行き先 | 内容 |
|---|---|---|
| 解消した issue | docs/issues/096-...(削除) | ファンイン2以上の14件の判断を全件記録した |
| 更新した issue | docs/issues/097 | 案Aが実施不能である原因(抽出器の決定 D)と、`help` / 未知サブコマンドの終了コード(どちらも 0)を実測して追記した |
| 棚上げ | docs/pendings.md 残務 | (1) CS19 と `change-set.md` §2 が `02-design/system.md` で両立しない (2) シェル抽出器の決定 D がラベル全体を落とす (3) `relations/` の「実装上の判断」の書式が2つある(既存56本は見直す条件を持たない) |
| 削除した残務 | docs/pendings.md | 「到達しない関数についての判断に4件の仕分けが無い」は 2026-08-11 の `/relations` で解消済みだった |
| 気づき | docs/feedbacks/027-a-single-remaining-option-is-not-a-question.md | 実行できる選択肢が1つしか残らないものを決定シートに載せた。問う基準を適用する前に選択肢の数を数える |

## 計測

`python3 .claude/scripts/task-metrics.py task-promote-shared-helpers report`:
lane = `standard` / 経過 11,135 秒(約3.1時間)/ 記録イベント: start(intake)1件。

## 独立レビュー(Codex `gpt-5.6-sol` / effort high)

2回実行した。**指摘は計 21 件、誤検知 0 件。**

- フェーズ2(変更指示に対して): 13 件 — うち2件が重大度「高」で、**どちらも AI が書いた事実の誤り**だった
  (`destructive_*` の呼び出し順を実コードと逆に書いていた / `start` がハッシュコマンドを検査していると
  書いていたが `check_host_deps` は `docker` と `jq` しか見ていない)。11 件を修正、2 件を残務へ。
- フェーズ4(反映後の SSOT に対して): 8 件 — 委任IDの適用範囲の誤り2件(`DS-04` は
  外部から見える値には使えない)、機能表の行順が辞書順から外れていたこと、
  「1関数」「17件すべて同名対」の不正確さなど。全件修正した。

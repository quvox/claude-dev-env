---
id: 2026-08-06-doc-check-full-after-kit-update
date: 2026-08-06
task: なし(タスク外の /doc-check full。docs/tasks/ は空)
origin_layer: 02
issue: docs/issues/071, docs/issues/072(069 と 070 は同一実行内で解消して削除)
summary: キット更新後に /doc-check full を掛け、規範との不整合8件を自動修正して SSOT 64 ファイルを再認証し、人間判断が要る4件を起票した
---

# 2026-08-06 キット更新後の `/doc-check full` による全体再認証

## 変更理由

`.claude/` 一式(`CLAUDE.md` / `directions/` / `templates/` / `scripts/` / `tools-readme.md`)が
2026-08-06 10:38 に更新された一方、`docs/` は 2026-08-05 で止まっていた。
**新しい規範に対する仕様ドキュメントの検査が一度も行われていない**状態だったため、
人間が全体の保証を求めて `/doc-check full` を起動した(`/doc-check` §0 が定める full の
2トリガーのうち後者)。起点層は、見つかった不整合の多数が 02(`environments.md` の検査コマンド、
`system.md` の依存列)にあったため 02 とする。

## 変更内容の要約

- **キット更新に起因する不整合**を3件直した。
  1. `02-design/environments.md` の「ドキュメント整合検査コマンド」が `--out` を欠いていた。
     現行の `.claude/directions/callgraphs.md` §3.1 は生成先を
     `resolve-callgraph-out.py` に決めさせることを要求し、CLAUDE.md §9 は検査コマンドを
     environments.md の**厳密な文字列**で実行せよと定める。**この文書どおりに実行すると、
     進行中タスクがあるときに SSOT のコールグラフを上書きする(原則1違反)。**
  2. `03-impl/index.md` の鮮度検査コマンドも同じ欠落を持っていた。
  3. `03-impl/tests/` 全 31 ファイルの「未検証(テスト未実装)の全件」表の見出しが
     旧テンプレートの「閉じる予定」のままだった。現行テンプレートは「解消の条件」で、
     `.claude/directions/03-impl.md` 自身が「『いつやるか』は計画であり SSOT には書けない
     (CLAUDE.md 原則1)」と記録している。**セルの内容は既に条件文だったので、見出しだけを揃えた。**
- **層内・層間の不整合**を5件直した(下の表)。
- 生成物 2 件を再生成した(`feature-graph.md` が古かった / `tests/index.md` に差分)。
- 版を持つ **64 ファイル全件**の検証済み記録を再発行した。

## 更新したドキュメント

| ドキュメント | version 遷移 | 何を変えたか |
|---|---|---|
| docs/00-requests/decisions/sec.md | 1.1.1 → 1.1.2 | 冒頭コメントの「残る『中』(issue 005 の残存リスクが『既知の制限』に無い)」が 2026-08-05 に解消済みである事実を追記(削除はせず追記で訂正) |
| docs/01-requirements/functional.md | 1.6.0 → 1.7.0 | (a) `source` に `decisions/{auth,env,orch,sec}.md` を追加(`.claude/directions/01-requirements.md` が本文の引用元を source に持たせよと定めるのに 0 件だった)。(b) **FR-env-07 受入基準5 の compose 一意化を「起動ディレクトリ名で」から「起動ディレクトリの絶対パスを含めて」へ訂正** — 同一文書内の FR-env-01 受入基準19 および `D0-env-05`(2026-08-04 改め)と正面から食い違っていた |
| docs/01-requirements/non-functional.md | 1.3.0 → 1.3.1 | `source` に `decisions/orch.md` を追加 |
| docs/01-requirements/system.md | 1.0.0 → 1.0.1 | `source` に `decisions/{orch,sec}.md` を追加 |
| docs/02-design/system.md | 2.3.0 → 2.4.0 | モジュール分割定義の「依存」列に欠けていたモジュール境界越えの辺を2件追加(`MOD-cli-start` → `MOD-entrypoint` / `MOD-cli-orchestrate` → `MOD-cli-start`)。`.claude/directions/02-design.md:46` が「依存列は relations が宣言する境界越えの辺をすべて覆う」と定める |
| docs/02-design/environments.md | 1.0.0 → 1.1.0 | 検査コマンド表に手順0(`CG_OUT=$(resolve-callgraph-out.py)`)を追加し、1・2 と「コールグラフ抽出設定」の鮮度検査に `--out "$CG_OUT"` を付けた |
| docs/03-impl/index.md | 1.14.0 → 1.15.0 | 「82機能」を実測値「83機能」へ訂正(同一文書の「この層の状態」表は 83 と書いており内部で食い違っていた)。鮮度検査コマンドに `--out` を追加 |
| docs/03-impl/tests/*.md(31件) | 各 PATCH +1 | 「未検証(テスト未実装)の全件」表の見出しを「閉じる予定」→「解消の条件」へ |
| 上記以外の 版を持つ全ドキュメント(計 64 件) | 版は据え置き | `verified` を再発行(`at: 2026-08-06`、`against` を各 source の現在版へ更新) |

## 実装したもの

なし(ドキュメントのみ。コードは1行も変えていない)。

## 機能間連携仕様書の変化

なし(`MODULE-*` の追加・変更・削除は 0 件。`check-relations.py` は 83 ファイル / 83 ID で合格)。

## 副産物

| 種別 | 行き先 | 内容 |
|---|---|---|
| 起票 → 同一実行内で解消・削除 | docs/issues/069(削除) | AC-03 が根拠に挙げる「2026-08-03 の判断」に対応する決定記録が `decisions/` に無く、**独立レビューが検証のたびに「高」の矛盾として再検出していた**。人間が案A を選択し、`acceptances.md` の当該箇所を「`D0-sec-05` の委任範囲内で下した判断であり、独立した決定事項ではない」へ書き換えて解消した |
| 起票 → 同一実行内で解消・削除 | docs/issues/070(削除) | EARS の帰結節が SHALL でなく「してよい」の受入基準が2件(FR-env-07 #8 / FR-env-09 #10)。人間が案A を選択し、両方を SHALL へ改めて解消した。**実装はどちらも分岐を持たないので振る舞いは変わっていない** |
| 新規 issue | docs/issues/071 | 用語集 23 語のうち 17 語で「含む例」「含まない例」が両方とも空 |
| 新規 issue | docs/issues/072 | ドキュメント(03-impl を含む)のどこにも書かれておらず実装者が値か方針を発明するしかない箇所が5件。**人間が案C(5件とも据え置き)を選択**したので、issue のまま残る |
| 更新した issue | docs/issues/054 | `related` に、削除済み issue パスを参照している同型のファイル 13 件を追加(従来は 6 件しか挙がっておらず、054 の解消をもって全件解消と誤認する余地があった) |
| 独立レビュー | — | **Codex は利用上限で不可**(復旧予定 2026-08-11 12:56)。人間の常設承認に基づきサブエージェント5本で代替した(`lens: subagent` / model `sonnet`)。効果は Codex より弱い |

## 人間の裁定(2026-08-06 の決定シート 5 論点)

| 論点 | 回答 | 帰結 |
|---|---|---|
| 1. `docs/issues/060`(条項ID・分割可否・充足列)をタスクへ昇格するか | **昇格** | `/task-new 060` でフェーズ1へ。**この裁定より前に SSOT の修正をすべて反映した** — タスクが1件でも存在すると原則1により `/doc-check` が SSOT を直せなくなるため |
| 2. AC-03 の根拠の書き方 | **A** | `acceptances.md` の「2026-08-03 の判断」を「`D0-sec-05` の委任範囲内で下した判断であり、独立した決定事項ではない」へ書き換えた(1.1.0 → **1.2.0**) |
| 3. 「してよい」2件を SHALL へ上げるか | **A** | `functional.md` の FR-env-07 受入基準8 と FR-env-09 受入基準10 を SHALL へ改めた(1.7.0 → **1.8.0**)。実装は分岐を持たないので振る舞いは不変 |
| 4. `docs/issues/072` の #5(`/workspace` が git でないときの `orchestrate`)を先に直すか | **C(据え置き)** | 推奨していた案B は採らない。`CTR-cli-orchestrator` のエラーケース表に該当行が無い状態は `docs/issues/072` が追跡したまま残る |
| 5. Codex 復旧後(2026-08-11)に `/doc-check full` を掛け直すか | **B(掛け直さない)** | **本実行が発行した 64 件の検証済み記録は、サブエージェント代替のレビューに基づいたまま確定する。** 推奨は A(掛け直す)だった。理由は `/codex-audit` §2.5 が言うとおり、同系列モデルのレンズは盲点を共有し、Codex と同等の独立性を持たないため。**この弱点は補われないまま残る**ことを、ここに明記しておく。`03-impl/index.md` の 2026-08-04 のコメントが書いていた「2026-08-10 以降に `/doc-check full` を掛け直すこと」は、この裁定により実施しない |

## 機械検査の結果(修正後)

| スクリプト | 結果 |
|---|---|
| `build-callgraphs.py --out "$CG_OUT" --check` | 最新 |
| `cluster-features.py --out "$CG_OUT" --check` | 最新(再生成後) |
| `callgraph-check.py` | 高 0 / 中 6 / 低 21 / 参考 20 |
| `check-relations.py` | 合格(83 ファイル / 83 ID) |
| `check-contracts.py` | 合格 |
| `build-index.py --check` | 差分なし(再生成後) |
| `check-changeset.py --ssot docs` | 違反 31 件(CS8 = 8 / CS11 = 23)。**いずれも既知の2クラス**で、CS8 は `docs/pendings.md` P-002 / P-003 が追跡する「将来設定」、CS11 は `docs/issues/054` が追跡する削除済み issue パスである |
| 合格証テスト(version と各 against が MAJOR.MINOR で一致) | 64 / 64 合格 |

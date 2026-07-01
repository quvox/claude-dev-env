---
summary: オーケストレーター自己検証用のサンプルサブプロジェクト（テンプレート examples/orch-sample/）と、それを使い捨て作業コピーへ展開する scaffold（Makefile/スクリプト）、決定論的に介入・並行・中断再開を踏ませる seed plan、検証用 CLI affordance の実装仕様。
keywords: [ サンプルプロジェクト, scaffold, seed plan, 自己検証, Makefile, orchestrate, テンプレート ]
---

# 実装仕様: examples/orch-sample/（自己検証用サンプルサブプロジェクト）

> **この文書の役割**: [docs/07_self-verification.md](../07_self-verification.md) の設計を実装する成果物の仕様。オーケストレーター本体の正本は [60_orchestrator.md](60_orchestrator.md)。

## 要件（なぜ必要か）

オーケストレーターの不具合を、実プロジェクトを犠牲にせず**高速・再現可能・ユースケース準拠**で発見/修正したい（07 §1）。そのために、リポジトリ同梱の小さな開発対象（テンプレート）と、それを使い捨て作業コピーへ展開して `claude-dev orchestrate` を走らせる scaffold を用意する。

## カバーするコード

```
examples/orch-sample/             ← テンプレート（git 追跡・正本）
├── README.md                     サンプルの目的と使い方（利用者向け）
├── CLAUDE.md                     最小限のプロジェクト指示（本リポジトリの規約の縮約）
├── ORCHESTRATOR.md               プロジェクト固有の判断基準（60 §判断基準。worker/壁打ち/介入に前置される）
├── GOAL.md                       壁打ちを短縮するためのゴール記述（orchestrate のゴール引数に使う）
├── .gitignore                    Python キャッシュ等の無視（テンプレートを綺麗に保つ）
├── pytest.ini                    pytest 設定（pythonpath=src, testpaths=tests）
├── seed/plan.json                決定論的検証用の seed plan（Ready=true。--start-executing で使用）
├── src/mathkit/                  開発対象。各モジュールは NotImplementedError のスタブで、worker が実装する
│   ├── __init__.py
│   ├── stats.py                  スタブ（mean/median）
│   ├── strings.py                スタブ（slugify）
│   └── geometry.py               スタブ（rect_area/circle_area）
└── tests/                        期待仕様を表す pytest（worker はこれを通す）
    ├── test_stats.py
    ├── test_strings.py
    └── test_geometry.py

scripts/orch-sample.sh            scaffold スクリプト（テンプレート → workspace/orch-sample 作業コピー）
Makefile                          orch-sample / orch-sample-clean ターゲット（→ 20_makefile.md）
orchestrator/                     検証 affordance（--start-executing 等）の追加（→ 60_orchestrator.md / 10_cli.md）
```

`workspace/orch-sample/`（scaffold の出力）は `.gitignore` 済みの `workspace/` 配下に作られる使い捨ての**独立 git リポジトリ**であり、本書の追跡対象ではない（生成物）。

## サンプルの開発対象（mathkit）

小さな Python ユーティリティ `mathkit` を題材にする（外部依存なし・`pytest` のみ・worker が数分で完了する規模）。複数の**独立**モジュールで並行実行を踏み、テストで成果を機械検証する。

| モジュール | 内容 | 検証 |
|---|---|---|
| `src/mathkit/stats.py` | `mean(xs)` / `median(xs)` | `tests/test_stats.py` |
| `src/mathkit/strings.py` | `slugify(s)` | `tests/test_strings.py` |
| `src/mathkit/geometry.py` | `rect_area(w,h)` / `circle_area(r)` | `tests/test_geometry.py` |

テンプレートには **テスト（期待仕様）とスタブ**を置き、実装本体（関数の中身）は `NotImplementedError` のスタブにして worker に実装させる。各モジュールは互いに依存しないため、`max_workers` まで並行起動される。

## seed plan（決定論的に不具合を踏ませる）

`examples/orch-sample/seed/plan.json` は `Ready=true` のタスク計画で、各タスクに**タスク固有 `completion`**（60 §8.1）を持つ。検証シナリオ（07 §3）を再現性高く踏ませる構成：

| タスク | deps | irreversible | 目的（07 のシナリオ） |
|---|---|---|---|
| `t-stats` | — | false | 並行実行。`completion`=「`stats.py` に mean/median があり test_stats が通る。他モジュールは責務外」 |
| `t-strings` | — | false | 並行実行。`completion`=「`strings.py` の slugify が test_strings を通す。責務外明示」 |
| `t-geometry` | — | false | 並行実行。`completion`=「`geometry.py` が test_geometry を通す。責務外明示」 |
| `t-announce` | — | **true** | 依存なしの irreversible タスク → ディスパッチ前に trigger1 が必ず発火し `waiting_human` に。**他 3 タスクが走る間 1 件だけ待つ**ことを決定論的に再現（S1）。`[i]` 承認で `IrrevApproved`→完遂 |
| `t-release` | t-stats,t-strings,t-geometry,t-announce | **true** | 統合後の irreversible（タグ付け等）。S5（複数同時介入）用に第 2 の irreversible を提供 |

`irreversible` タスクは trigger1（pre-dispatch・worker 判断に非依存）で必ず発火するため、実 `claude -p` の出力揺れに影響されず介入挙動を検証できる（07 §2.3）。

## scaffold（テンプレート → 使い捨て作業コピー）

`scripts/orch-sample.sh`（`make orch-sample` から呼ぶ）の責務：

1. 出力先 `workspace/orch-sample/` が既存なら（`--force` 指定時に）削除し、テンプレート `examples/orch-sample/` を**コピー**する（`seed/` 以下を除く本体）。`make orch-sample FORCE=1` が `scripts/orch-sample.sh --force` に、`SEED=1` が `--seed` に対応する（Make 変数 → スクリプトフラグ）。
2. コピー先で `git init` ＋ 全ファイルを**初期コミット**（worktree のベースを作る）。
3. `--start-executing` で検証する場合のみ、`seed/plan.json` を作業コピーの `.orchestrator/plan.json` として配置する（通常の壁打ち検証では配置しない）。
4. 作業コピー直下に `.gitignore`（`/.orchestrator/`）を置く（運用状態は追跡しない。60 §状態ストア）。

scaffold は**冪等**（再実行でクリーンな初期状態に戻る）であること。これが「何度でもやり直せる」再現性（07 §1）の担保。

## 実行方法（2 系統。07 §2.2）

- **本番同等**：`claude-dev start` 後、`claude-dev orchestrate --workspace workspace/orch-sample`（ゴールは `GOAL.md` を渡すか壁打ちで決める）。
- **オーケストレーター開発の高速ループ**（イメージ再ビルド不要）：
  `make build-orchestrator` →
  `orchestrator/orchestrator --workspace workspace/orch-sample --instructions orchestrator/instructions [--start-executing] "$(cat examples/orch-sample/GOAL.md)"`
  - `--workspace` / `--instructions` は既存フラグ（60）。
  - `--start-executing`（**本改訂で追加する検証用 affordance**）：`.orchestrator/plan.json` が存在し `Ready=true` のとき、壁打ちを飛ばして直接 `executing` から開始する。**ready な seed plan が無ければ無効**（通常起動＝壁打ちにフォールバック）。決定論的な非対話検証（S1〜S5）のために用意する。通常運用の既定は従来どおり壁打ち開始（06 §5.1）であり、この affordance は検証専用と明記する。

## 検証手順（CLAUDE.md「動作確認」準拠）

07 §3 のシナリオを実行し、ダッシュボード（noVNC）・`workspace/orch-sample/.orchestrator/audit.jsonl`・`plan.json`・`git log` で合格条件を確認する。中断検証（S2/S3）は実行中に Ctrl-C し、再 orchestrate で `done` タスクが再ディスパッチされない（`audit.jsonl` の `dispatch` 重複なし）ことを確かめる。結果は `docs/reviews/` に記録する。

## Makefile ターゲット（正本は [20_makefile.md](20_makefile.md)）

| ターゲット | 内容 |
|---|---|
| `orch-sample` | `scripts/orch-sample.sh` を呼び使い捨て作業コピーを scaffold（`FORCE=1` で再生成、`SEED=1` で seed plan 配置） |
| `orch-sample-clean` | `workspace/orch-sample/` を削除 |

## テスト方針

- scaffold スクリプトは冪等性（再実行でクリーン初期化）と、seed plan 配置/非配置の分岐を確認する。
- サンプル自体の単体テスト（`pytest`）は worker の成果検証に使うものであり、オーケストレーターのテスト（`orchestrator/*_test.go`、60 §テスト方針）とは別系統。

## 関連ドキュメント

- [docs/07_self-verification.md](../07_self-verification.md)：本サンプルを使う検証の設計（正本）
- [60_orchestrator.md](60_orchestrator.md)：検証対象本体（`--start-executing` affordance・`--workspace`/`--instructions`）
- [10_cli.md](10_cli.md)：`orchestrate` の CLI 契約
- [20_makefile.md](20_makefile.md)：`orch-sample` ターゲット

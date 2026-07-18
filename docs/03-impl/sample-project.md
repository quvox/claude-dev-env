---
id: sample-project
layer: impl
title: sample-project 実装説明書
version: 1.0.0
updated: 2026-07-18
verified:
  at: 2026-07-18
  version: 1.0.0
  against:
    - doc: docs/02-design/system.md
      version: 1.0
summary: >
  オーケストレーター自己検証用のサンプル題材 examples/orch-sample/（外部依存なしの Python+pytest
  ユーティリティ mathkit）と、それを使い捨て作業コピー workspace/orch-sample へ独立 git リポジトリ
  として冪等に展開する scaffold scripts/orch-sample.sh の実装。決定論的検証用の seed plan を同梱する。
keywords: [sample-project, orch-sample, scaffold, seed-plan, 自己検証, mathkit, pytest]
depends_on: [orchestrator]
source:
  - docs/02-design/system.md
---

# 実装説明書:sample-project

## 概要

`orchestrator`（Go 製コントローラ）の振る舞いを、実プロジェクトを犠牲にせず再現性高く検証するための
題材モジュール。実体は 3 つ——(1) リポジトリ同梱テンプレート `examples/orch-sample/`（正本・git 追跡）、
(2) それを使い捨て作業コピー `workspace/orch-sample/` へ展開する scaffold `scripts/orch-sample.sh`、
(3) `make orch-sample` / `make orch-sample-clean` の入口（実体は `makefile` モジュールが持つ）。
題材は外部依存のない小さな Python ユーティリティ `mathkit`（独立 3 モジュール＋pytest）で、テンプレートには
**期待仕様のテストとスタブだけ**を置き、実装本体は worker に埋めさせる。上流: [全体設計](../02-design/system.md)
の分割定義 `sample-project` 行および要件 orchestration/20。

## ファイル構成

| パス | 役割 |
|---|---|
| examples/orch-sample/README.md | サンプルの目的と使い方（利用者向け） |
| examples/orch-sample/CLAUDE.md | 題材のプロジェクト指示（Python・外部依存なし・テストを全通し・変更最小） |
| examples/orch-sample/ORCHESTRATOR.md | プロジェクト固有の判断基準（後戻り不可はエスカレーション／軽微な判断は仮定して進む）。各プロンプトに前置される |
| examples/orch-sample/GOAL.md | ブレインストーミング短縮用のゴール記述（orchestrate のゴール引数に使う） |
| examples/orch-sample/.gitignore | `__pycache__/` `*.pyc` `.pytest_cache/` を無視（テンプレートを綺麗に保つ） |
| examples/orch-sample/pytest.ini | pytest 設定（`pythonpath = src` / `testpaths = tests`） |
| examples/orch-sample/seed/plan.json | 決定論的検証用の seed plan（`ready=true`。`--seed` 指定時のみ配置） |
| examples/orch-sample/src/mathkit/__init__.py | パッケージ定義（docstring のみ） |
| examples/orch-sample/src/mathkit/stats.py | スタブ `mean(xs)` / `median(xs)`（`NotImplementedError`） |
| examples/orch-sample/src/mathkit/strings.py | スタブ `slugify(s)`（`NotImplementedError`） |
| examples/orch-sample/src/mathkit/geometry.py | スタブ `rect_area(w,h)` / `circle_area(r)`（`NotImplementedError`） |
| examples/orch-sample/tests/test_stats.py | mean/median の期待仕様（5 ケース） |
| examples/orch-sample/tests/test_strings.py | slugify の期待仕様（3 ケース） |
| examples/orch-sample/tests/test_geometry.py | rect_area/circle_area の期待仕様（4 ケース。`pytest.approx` 使用） |
| scripts/orch-sample.sh | scaffold 本体（テンプレート → workspace/orch-sample 作業コピー） |
| Makefile（`orch-sample` / `orch-sample-clean` ターゲット） | 入口。正本は `makefile` モジュール（03-impl/makefile.md） |

`workspace/orch-sample/`（scaffold の出力）は `.gitignore` 済みの `workspace/` 配下に作られる使い捨ての
**独立 git リポジトリ**であり、本モジュールの追跡対象ではない（生成物）。

## モジュール別実装詳細

### 題材 mathkit（examples/orch-sample/src・tests）

- **責務:** worker が並行実装・機械検証できる、外部依存のない小さな開発対象を提供する（設計書 sample-project 行）。
- **公開インターフェース（スタブ関数。中身は worker が実装）:**

```
mathkit.stats.mean(xs)       -> 算術平均
mathkit.stats.median(xs)     -> 中央値（偶数個なら中央2要素の平均・ソートして判定）
mathkit.strings.slugify(s)   -> URL スラグ（小文字化・空白をハイフン連結・英数字とハイフン以外除去・端の余白/ハイフン除去）
mathkit.geometry.rect_area(w,h)  -> w*h
mathkit.geometry.circle_area(r)  -> math.pi * r**2
```

- **処理の要点:**
  - 3 モジュール（stats / strings / geometry）は互いに依存しないため、`max_workers` まで並行起動される。
  - テンプレートの src はすべて `raise NotImplementedError` のスタブで、docstring に期待挙動を書いてある。
  - tests/ は期待仕様であり worker は変更しない（CLAUDE.md の指示）。標準ライブラリのみ（`math`）を使う。

### seed plan（examples/orch-sample/seed/plan.json）

- **責務:** 検証シナリオ（並行・介入・中断再開）を決定論的に踏ませるタスク計画。`ready=true`。
- **タスク構成:**

| タスク | deps | irreversible | 目的 |
|---|---|---|---|
| `t-stats` | — | false | 並行実行。`completion`＝stats.py のみ担当・pytest test_stats 全通・他は責務外 |
| `t-strings` | — | false | 並行実行。`completion`＝strings.py のみ担当・pytest test_strings 全通・他は責務外 |
| `t-geometry` | — | false | 並行実行。`completion`＝geometry.py のみ担当・pytest test_geometry 全通・他は責務外 |
| `t-announce` | — | **true** | 依存なしの後戻り不可タスク。ディスパッチ前に発火し人間承認を待つ（他 3 タスクが走る間 1 件だけ待つことを決定論的に再現）。承認後 `ANNOUNCEMENT.md` を作成 |
| `t-release` | t-stats,t-strings,t-geometry,t-announce | **true** | 統合後の後戻り不可（`git tag v0.1.0`）。複数介入の再現用に第 2 の irreversible を提供 |

- **処理の要点:** 各タスクは**タスク固有 `completion`**（責務境界を明示）を持つ。`irreversible` タスクは
  worker の出力揺れに依存せず必ずエスカレーションに回るため、実 `claude -p` の非決定性に影響されずに
  介入挙動を検証できる。plan 全体の `goal` / `completion` も定義されている。

### scaffold（scripts/orch-sample.sh）

- **責務:** テンプレート `examples/orch-sample/` を使い捨て作業コピー `workspace/orch-sample/` へ展開し、
  独立 git リポジトリとして初期化する。冪等（`--force` で既存をクリーン初期化）。
- **公開インターフェース:**

```
scripts/orch-sample.sh [--force] [--seed]
  --force  出力先が既存なら削除して作り直す（未指定で既存ならエラー終了）
  --seed   seed/plan.json を作業コピーの .orchestrator/plan.json に配置する
```

- **処理の要点（実行順）:**
  1. スクリプト位置からリポジトリルートを解決（`scripts/` の親）。`set -euo pipefail`。
  2. 引数解析（`--force`→FORCE、`--seed`→SEED、その他は使い方を出して `exit 2`）。テンプレート不在なら `exit 1`。
  3. 出力先が既存なら、`--force` 指定時は `rm -rf` で削除、未指定ならエラー `exit 1`。
  4. テンプレート本体をコピー。`find . -mindepth 1 -maxdepth 1 ! -name 'seed' -exec cp -R` で
     ドットファイル含め全て複製し、**`seed/` ディレクトリだけ除外**する。
  5. 作業コピー直下の `.gitignore` に `/.orchestrator/` を追記（無ければ作成）。テンプレート同梱の
     `.gitignore`（Python キャッシュ除外）を保持しつつ、`grep -qxF` で重複追記を防ぐ。
  6. `git init` → `add -A` → 初期コミット（`-c user.name/user.email` を明示し未設定環境でも動く）。
  7. `--seed` 指定時のみ `.orchestrator/plan.json` へ seed plan をコピー。`.gitignore` 済みなので
     初期コミットには含まれない（運用状態は追跡しない）。
- **実装上の判断:** テンプレート内の `seed/` は「検証用の別入力」であり作業コピーの通常内容ではないため、
  コピー段階で除外し、`--seed` 時のみ `.orchestrator/` へ配置する二段構えにしている（設計書の scaffold 責務どおり）。

## データアクセス

| データ | 操作 | 実施モジュール | 備考 |
|---|---|---|---|
| examples/orch-sample/（テンプレート・正本） | 読み取り（コピー元） | scripts/orch-sample.sh | git 追跡。書き換えない |
| workspace/orch-sample/（作業コピー・独立 git リポジトリ） | 生成・削除・git init/commit | scripts/orch-sample.sh | `workspace/` 配下で `.gitignore` 済み（本リポジトリの追跡外） |
| workspace/orch-sample/.orchestrator/plan.json | 配置（`--seed` 時のみ） | scripts/orch-sample.sh | seed/plan.json のコピー。運用状態は `orchestrator` が読み書き（本モジュール外） |

## API実装詳細

外部公開 API なし（CLI/HTTP エンドポイントを持たない。scaffold スクリプトと題材ファイル群のみ）。

## 設定・環境変数

| 名前 | 用途 | デフォルト | 必須 |
|---|---|---|---|
| FORCE（Make 変数） | `make orch-sample FORCE=1` → `--force` に対応 | 未設定（既存ならエラー） | 否 |
| SEED（Make 変数） | `make orch-sample SEED=1` → `--seed` に対応 | 未設定（seed 非配置） | 否 |

環境変数は使用しない。git identity はスクリプト内で `-c` により固定注入する（`orch-sample` /
`orch-sample@example.invalid`）。

## エラーハンドリング実装

| 異常系 | 実装箇所 | 実際の振る舞い | 対応する要件 |
|---|---|---|---|
| テンプレート不在 | orch-sample.sh L37-40 | 日本語メッセージを stderr、`exit 1` | orchestration/20-1 |
| 出力先が既存かつ `--force` 未指定 | orch-sample.sh L47-50 | 「--force で再生成してください」を stderr、`exit 1`（誤上書き防止） | orchestration/20-1 |
| 不明な引数 | orch-sample.sh L29-34 | 使い方を stderr、`exit 2` | — |
| いずれかのコマンド失敗 | `set -euo pipefail`（L14） | 即時中断（未定義変数・パイプ失敗も検知） | — |

## テスト

| テスト（ファイル::ケース名） | レベル | 検証内容 | 対応する受け入れ基準/契約 |
|---|---|---|---|
| test_stats.py::test_mean_basic / test_mean_single | 単体 | mean の算術平均 | 題材の期待仕様（worker 成果を機械検証） |
| test_stats.py::test_median_odd / test_median_even / test_median_unsorted | 単体 | median（奇数/偶数/未ソート） | 同上 |
| test_strings.py::test_slugify_basic / test_slugify_lowercase / test_slugify_strips_edges | 単体 | slugify（基本/小文字化/端の余白除去） | 同上 |
| test_geometry.py::test_rect_area / test_rect_area_zero / test_circle_area / test_circle_area_unit | 単体 | 面積計算（`pytest.approx` で浮動小数比較） | 同上 |

- 上表の pytest は**題材自身のテスト**であり、worker が埋めた実装の成果を機械検証するもの。
  `orchestrator` の Go テストとは別系統。
- scaffold `scripts/orch-sample.sh` 自体の自動テストは無い（シェルスクリプトのため実機確認。設計書テスト戦略
  「シェル系は自動テストなし＝実機確認」に従う）。冪等性（再実行でクリーン初期化）・`--seed` の配置/非配置分岐は
  実行して確認する。
- **E2E 自己検証**は `make orch-sample` で作業コピーを scaffold した上で `orchestrator` を実走させて行う。
  この E2E シナリオ **E2E-4** は `docs/03-impl/e2e.md` の対応表が持つ（本表には載せない）。

**要件 orchestration/20 の基準マッピング:**

| 受け入れ基準 | 実装箇所 | 状態 |
|---|---|---|
| 20-1 `make orch-sample` でサンプルにオーケストレーターを実走 | Makefile `orch-sample` → scripts/orch-sample.sh（作業コピーを準備）＋ orchestrate 実走 | 実走部分は E2E-4（e2e.md）で検証 |
| 20-2 `make orch-sample-clean` で題材の作業コピーを初期化 | Makefile `orch-sample-clean`（`rm -rf workspace/orch-sample`） | 実機確認 |

実行方法:
- scaffold: `make orch-sample`（再生成は `make orch-sample FORCE=1`、seed 配置は `make orch-sample SEED=1`）／
  直接は `scripts/orch-sample.sh [--force] [--seed]`。
- 作業コピー削除: `make orch-sample-clean`。
- 題材の pytest: `cd examples/orch-sample && pytest`（`pytest.ini` で `pythonpath=src` 設定済み）。
- 自己検証実走: `make orch-sample` 後に `claude-dev orchestrate --workspace workspace/orch-sample`。

## 既知の制限・技術的負債

- `make orch-sample` の Makefile ターゲットは scaffold（作業コピー準備）までを行い、orchestrator の実走は
  別ステップ（`claude-dev orchestrate` または orchestrator バイナリ直接起動）で行う構成。要件 20-1 の
  「実走」全体は E2E-4 の実機シナリオでカバーする。ターゲットの正本仕様は `makefile` モジュール（03-impl/makefile.md）。
- scaffold は git identity をダミー値で固定注入する（作業コピーは使い捨てのため）。
- 題材の実装本体はテンプレートには存在しない（スタブのみ）＝ worker 未実行の作業コピーでは pytest は失敗する
  （これは意図した初期状態）。

## 運用メモ

- テンプレート `examples/orch-sample/` は正本。直接開発せず、常に scaffold して使い捨て作業コピーで走らせる。
- 検証後は `make orch-sample-clean` で作業コピーを掃除するか、`FORCE=1` で再生成してクリーンな初期状態へ戻す。
- 検証観点（並行実行・後戻り不可タスクの介入・中断再開）は seed plan の構成に埋め込まれており、
  `--seed` 起動＋オーケストレーターの `--start-executing` 相当で決定論的に踏める。

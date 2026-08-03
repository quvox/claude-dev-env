---
id: MODULE-sample-project-mathkit
module: MOD-sample-project
kind: function-call
sync: sync
impl: examples/orch-sample/src/mathkit/geometry.py::circle_area, examples/orch-sample/src/mathkit/geometry.py::rect_area, examples/orch-sample/src/mathkit/stats.py::mean, examples/orch-sample/src/mathkit/stats.py::median, examples/orch-sample/src/mathkit/strings.py::slugify
callers: EXTERNAL-pytest
callees: なし
contracts: なし
design: DSN-mod-01, DSN-test-01
requirements: FR-orch-09
tests: examples/orch-sample/tests/test_geometry.py, examples/orch-sample/tests/test_stats.py, examples/orch-sample/tests/test_strings.py
updated: 2026-08-02
summary: 自己検証で orchestrator が実装対象とする mathkit の関数群
---

# MODULE-sample-project-mathkit 自己検証題材のライブラリ

## 目的

orchestrator が実際にタスクを分解・実装・レビューできるかを確かめる(FR-orch-09)ための
**実装対象**。題材そのものに製品としての役割は無く、pytest で合否が機械判定できる小さな
ライブラリであることだけが要件である。

## 処理の流れ

1. `geometry.py::circle_area(r)` — 半径から円の面積を返す。
2. `geometry.py::rect_area(w, h)` — 幅と高さから長方形の面積を返す。
3. `stats.py::mean(xs)` — 数列の平均を返す。
4. `stats.py::median(xs)` — 数列の中央値を返す。
5. `strings.py::slugify(s)` — 文字列を URL に使える slug へ変換する。

## 呼び出され方

- 契機: `examples/orch-sample/tests/` の pytest から呼ばれる。製品コードからの呼び出しは無い。
- 前提条件: `pytest.ini` の設定で `src/` が import パスに入っていること。
- 引数: 各関数のシグネチャによる(上記)。

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `r` / `w` / `h` | 数値 | 必須 | `geometry` の各関数 |
| `xs` | 数値の並び | 必須 | `stats` の各関数 |
| `s` | 文字列 | 必須 | `slugify` |

- 認可: なし(ライブラリ関数)。

## 連携先と連携内容

連携先なし。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 各関数の計算結果 |
| 永続化 | なし(純粋関数) |
| 発火するイベント | なし |
| ログ | なし |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 空の数列を `mean` / `median` に渡す | Python の標準的な例外(`ZeroDivisionError` / `IndexError` 相当)が送出される | pytest が失敗として報告する |
| 負の半径を `circle_area` に渡す | 検証せず計算する(負の面積が返る) | 題材としての割り切り |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 関数単位ではなく mathkit 全体を1機能として扱う(関数ごとに割っても仕様として意味を持たないため) | D0-orch-08 |
| 2 | 題材の堅牢性(入力検証など)は追求しない。合否が pytest で機械判定できることだけを要件にする | D0-orch-08 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 製品コードからの呼び出しが無く、`kind: function-call` でありながら `callers` が pytest だけ | `check-relations.py` の「到達不能コードの疑い」に当たらないよう、`callers` に `EXTERNAL-pytest` を置いている | なし |
| 入力検証を持たない | 異常入力では Python の標準例外がそのまま出る | なし |

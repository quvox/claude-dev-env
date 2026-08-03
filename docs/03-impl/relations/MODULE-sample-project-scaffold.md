---
id: MODULE-sample-project-scaffold
module: MOD-sample-project
kind: tool
sync: sync
impl: scripts/orch-sample.sh::main
callers: なし
callees: なし
contracts: なし
design: DSN-mod-01, DSN-test-01
requirements: FR-orch-09
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: サンプルプロジェクトと seed plan を作業領域へ配置する
---

# MODULE-sample-project-scaffold 自己検証題材の配置

## 目的

orchestrator を実際に走らせて検証する(FR-orch-09)ための題材を、リポジトリ内の
`examples/orch-sample/` から作業領域 `workspace/orch-sample/` へ配置する。題材を毎回同じ状態から
始められるようにするのがこの機能の役割である。

## 処理の流れ

1. 配置先 `workspace/orch-sample/` が既に存在する場合、`--force` が無ければ既存を尊重して
   スキップする(メッセージを出して終わる)。
2. `--force` があれば既存を消してから配置し直す。
3. `examples/orch-sample/`(Python + pytest の題材。`src/mathkit/` と `tests/`、`GOAL.md`、
   `ORCHESTRATOR.md`、`CLAUDE.md`、`pytest.ini`)を作業領域へコピーする。
4. `--seed` が指定されていれば、決定論的な検証のために `seed/` の plan を
   `.orchestrator/plan.json` として配置する。
5. 配置結果を表示する。

## 呼び出され方

- 契機: 利用者が `scripts/orch-sample.sh [--force] [--seed]` を実行したとき。
  `MODULE-makefile-orch-sample` が `FORCE=1` / `SEED=1` を対応するフラグへ変換して呼ぶ。
- 前提条件: リポジトリのルートから実行できること。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `--force` | フラグ | 任意 | 既存の配置を作り直す |
| `--seed` | フラグ | 任意 | 決定論検証用の seed plan を併せて置く |

- 認可: リポジトリを操作できるホストユーザ。

## 連携先と連携内容

連携先なし(ファイルのコピーのみ)。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 0(コピーに失敗すれば非0) |
| 永続化 | **`workspace/orch-sample/`** 一式。`--seed` 指定時は **`workspace/orch-sample/.orchestrator/plan.json`**(この plan を `MODULE-orchestrator-state` の `LoadPlan` が読むため、書式はそちらと一致していなければならない) |
| 発火するイベント | なし |
| ログ | 標準出力へ配置結果 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 配置先が既存で `--force` が無い | スキップして 0 で終わる | 前回の作業内容が残ったまま検証を始めてしまう |
| コピー元 `examples/orch-sample/` が無い | コピーが失敗し非0で終わる | 検証が始められない |
| 書き込み権限が無い | 同上 | 同上 |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 既定では既存を上書きしない(検証途中の状態を誤って消さないため)。作り直しは `--force` の明示が要る | D0-scope-02 |
| 2 | seed plan の配置を任意にする(決定論的な検証と、ブレインストーミングから始める検証の両方を回せるようにする) | D0-orch-08 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 配置先が `workspace/orch-sample` に固定 | 複数の題材を並べて検証できない | なし |

---
id: MODULE-makefile-orch-sample
module: MOD-makefile
kind: tool
sync: sync
impl: Makefile::orch-sample
callers: なし
callees: なし
contracts: なし
design: DSN-mod-01
requirements: FR-orch-09
tests: なし(未実装。Makefile のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: orchestrator 自己検証用のサンプルプロジェクトを配置する
---

# MODULE-makefile-orch-sample make orch-sample

## 目的

自己検証(FR-orch-09)の題材を作業領域へ配置する入口。実体は `MODULE-sample-project-scaffold`。

## 処理の流れ

1. `<BASE_DIR>/scripts/orch-sample.sh` を実行する。
2. `FORCE=1` が指定されていれば `--force` を、`SEED=1` なら `--seed` を渡す。

## 呼び出され方

- 契機: 利用者が `make orch-sample` を実行したとき。
- 前提条件: リポジトリのルートで実行すること(`BASE_DIR` は Makefile の位置から解決する)。
- 引数: なし(変数で調整する場合は下表)。

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| (なし) | - | - | - |

- 認可: リポジトリを操作できるホストユーザ。

## 連携先と連携内容

連携先なし。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | `scripts/orch-sample.sh` の終了ステータス |
| 永続化 | `workspace/orch-sample/`(スクリプト側の副作用) |
| 発火するイベント | なし |
| ログ | スクリプトの出力 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 配置先が既存で `FORCE` 未指定 | スクリプトが既存を尊重してスキップする | 再生成には `FORCE=1` が要る |
| スクリプトが失敗する | make が非0で停止する | サンプルが配置されない |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | Makefile はホスト側の開発者向け入口に限定し、日常操作は `claude-dev` CLI に寄せる | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 自動テストが無い | 回帰検出は実機実行に依存する | なし |

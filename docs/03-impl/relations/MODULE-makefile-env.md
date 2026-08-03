---
id: MODULE-makefile-env
module: MOD-makefile
kind: tool
sync: sync
impl: Makefile::env
callers: MODULE-makefile-setup
callees: なし
contracts: なし
design: DSN-mod-01
requirements: FR-env-01
tests: なし(未実装。Makefile のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: .env を雛形から作成する
---

# MODULE-makefile-env make env

## 目的

CLI が起動時に読む `.env` を用意する(FR-env-01)。既存設定を壊さないことが要件。

## 処理の流れ

1. `<BASE_DIR>/.env` が無ければ `.env.example` をコピーして作成し、編集を促すメッセージを出す。
2. 既にあれば「ℹ️ .env は既に存在します」と表示して何もしない。

## 呼び出され方

- 契機: 利用者が `make env` を実行したとき。
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
| 戻り値 | 0 |
| 永続化 | `<BASE_DIR>/.env`(既存なら変更しない) |
| 発火するイベント | なし |
| ログ | 作成結果 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| `.env.example` が無い | `cp` が失敗し make が非0で停止する | `setup` が中断する |
| `.env` が既存 | 上書きせずメッセージだけ出す | 利用者の設定が保たれる |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | Makefile はホスト側の開発者向け入口に限定し、日常操作は `claude-dev` CLI に寄せる | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 自動テストが無い | 回帰検出は実機実行に依存する | なし |

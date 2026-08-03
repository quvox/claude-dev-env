---
id: MODULE-makefile-login
module: MOD-makefile
kind: tool
sync: sync
impl: Makefile::login
callers: なし
callees: なし
contracts: なし
design: DSN-mod-01, DSN-auth-01
requirements: FR-env-03
tests: なし(未実装。Makefile のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: Claude の OAuth ログインを実行する
---

# MODULE-makefile-login make login

## 目的

`claude-dev login` への薄い委譲(FR-env-03)。`make setup` の直後に案内される導線として置いてある。

## 処理の流れ

1. `$(CLI) login` を実行する(`CLI` は OS 判定で `claude-dev` / `claude-dev-mac`)。
2. 以降の処理は CLI 側の `MODULE-cli-login` が担う。

## 呼び出され方

- 契機: 利用者が `make login` を実行したとき。
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
| 戻り値 | CLI の終了ステータス |
| 永続化 | 共有ボリューム `claude-dev-auth` の認証(CLI 側の副作用) |
| 発火するイベント | なし |
| ログ | CLI の出力 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| CLI が非0で終わる | make が非0で停止する | 認証は取得されない |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | Makefile はホスト側の開発者向け入口に限定し、日常操作は `claude-dev` CLI に寄せる | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 自動テストが無い | 回帰検出は実機実行に依存する | なし |

---
target: docs/03-impl/relations/MODULE-makefile-build-orchestrator.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
id: MODULE-makefile-build-orchestrator
module: MOD-makefile
kind: tool
sync: sync
impl: Makefile::build-orchestrator
callers: なし
callees: なし
contracts: なし
design: DSN-mod-01
requirements: FR-orch-01
tests: なし(未実装。Makefile のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: orchestrator をローカルでビルドしテストする
---

# MODULE-makefile-build-orchestrator make build-orchestrator

## 目的

コンテナイメージへ同梱される orchestrator(FR-orch-01)を、ホスト側で素早くビルド・検証するための入口。イメージ用のビルドは `build-claude` に同梱される。

## 処理の流れ

1. `cd <BASE_DIR>/orchestrator` へ移動する。
2. `go build -o orchestrator .` でバイナリを明示的に出力する
   (`go build ./...` はバイナリを残さないため。自己検証の高速ループが直接起動する)。
3. `go vet ./...` を実行する。
4. `go test ./...` を実行する。

## 呼び出され方

- 契機: 利用者が `make build-orchestrator` を実行したとき。
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
| 戻り値 | 0(build / vet / test のいずれかが失敗すれば非0) |
| 永続化 | `orchestrator/orchestrator`(ローカルバイナリ) |
| 発火するイベント | なし |
| ログ | go の出力 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| コンパイルエラー | `go build` が失敗し make が非0で停止する | バイナリは更新されない |
| `go vet` の指摘 | 非0で停止する(テストまで進まない) | 同上 |
| テスト失敗 | 非0で停止する | バイナリは生成済みだが検証は未通過 |
| Go ツールチェインが無い | `go: command not found` で失敗する | ホストに Go の導入が必要 |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | Makefile はホスト側の開発者向け入口に限定し、日常操作は `claude-dev` CLI に寄せる | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 自動テストが無い | 回帰検出は実機実行に依存する | なし |

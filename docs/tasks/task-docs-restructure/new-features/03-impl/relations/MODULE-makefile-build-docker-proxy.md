---
target: docs/03-impl/relations/MODULE-makefile-build-docker-proxy.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
id: MODULE-makefile-build-docker-proxy
module: MOD-makefile
kind: tool
sync: sync
impl: Makefile::build-docker-proxy
callers: MODULE-makefile-build
callees: なし
contracts: なし
design: DSN-mod-01
requirements: FR-env-07, FR-env-09
tests: なし(未実装。Makefile のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: Docker Socket Proxy のイメージをビルドする
---

# MODULE-makefile-build-docker-proxy make build-docker-proxy

## 目的

コンテナからの Docker アクセスを検査するプロキシ(FR-env-07)のイメージを作る。

## 処理の流れ

1. `docker build -t claude-dev-docker-proxy -f .devcontainer/Dockerfile.docker-proxy <BASE_DIR>`
   を実行する(build-arg は渡さない)。

## 呼び出され方

- 契機: 利用者が `make build-docker-proxy` を実行したとき。
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
| 戻り値 | 0(失敗時は非0) |
| 永続化 | イメージ `claude-dev-docker-proxy` |
| 発火するイベント | なし |
| ログ | docker build の出力 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| ビルドが失敗する | docker のログを出して非0で停止する | 前のイメージが残る |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | Makefile はホスト側の開発者向け入口に限定し、日常操作は `claude-dev` CLI に寄せる | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 自動テストが無い | 回帰検出は実機実行に依存する | なし |

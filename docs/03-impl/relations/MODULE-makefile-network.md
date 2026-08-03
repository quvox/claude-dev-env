---
id: MODULE-makefile-network
module: MOD-makefile
kind: tool
sync: sync
impl: Makefile::network
callers: MODULE-makefile-setup
callees: なし
contracts: なし
design: DSN-mod-01
requirements: FR-env-01
tests: なし(未実装。Makefile のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: 専用 docker network を作成する
---

# MODULE-makefile-network make network

## 目的

コンテナ間通信に使う専用ネットワークを用意する(FR-env-01)。CLI 側の `ensure_infrastructure` と同じ資源を作る。

## 処理の流れ

1. `docker network create claude-dev-net` を実行する。
2. 既存などで失敗しても `2>/dev/null || true` で握りつぶす。
3. 「✅ ネットワーク: claude-dev-net」と表示する。

## 呼び出され方

- 契機: 利用者が `make network` を実行したとき。
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
| 戻り値 | 0(常に成功扱い) |
| 永続化 | docker network `claude-dev-net` |
| 発火するイベント | なし |
| ログ | 作成結果 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 既に存在する | エラーを破棄して成功メッセージを出す | なし |
| Docker デーモンに接続できない | 同じく握りつぶし、成功メッセージを出す(**誤った成功表示**) | 後続のビルド/起動で失敗する |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | Makefile はホスト側の開発者向け入口に限定し、日常操作は `claude-dev` CLI に寄せる | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 自動テストが無い | 回帰検出は実機実行に依存する | なし |

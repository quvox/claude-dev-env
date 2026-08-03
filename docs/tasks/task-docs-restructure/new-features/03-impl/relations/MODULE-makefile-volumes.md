---
target: docs/03-impl/relations/MODULE-makefile-volumes.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
id: MODULE-makefile-volumes
module: MOD-makefile
kind: tool
sync: sync
impl: Makefile::volumes
callers: MODULE-makefile-setup
callees: なし
contracts: なし
design: DSN-mod-01, DSN-auth-01
requirements: FR-env-01, FR-env-03
tests: なし(未実装。Makefile のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: 認証情報などの共有ボリュームを作成する
---

# MODULE-makefile-volumes make volumes

## 目的

認証共有(FR-env-03)と履歴・設定の永続化に使うボリュームを用意する(FR-env-01)。

## 処理の流れ

1. `claude-dev-auth` / `claude-dev-history` / `claude-dev-config` / `claude-dev-chrome-data` を
   `docker volume create` する。
2. いずれも `>/dev/null 2>&1 || true` で握りつぶす。
3. 作成したボリューム名を一覧表示する。

## 呼び出され方

- 契機: 利用者が `make volumes` を実行したとき。
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
| 永続化 | docker volume `claude-dev-auth`(claude 認証と `codex/auth.json`)、`claude-dev-history`、`claude-dev-config`、`claude-dev-chrome-data` |
| 発火するイベント | なし |
| ログ | 作成結果 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 既に存在する | エラーを破棄して成功メッセージを出す | なし |
| Docker デーモンに接続できない | 握りつぶして成功メッセージを出す | 後続で失敗する |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | Makefile はホスト側の開発者向け入口に限定し、日常操作は `claude-dev` CLI に寄せる | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 自動テストが無い | 回帰検出は実機実行に依存する | なし |

---
target: docs/03-impl/relations/MODULE-makefile-status.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
id: MODULE-makefile-status
module: MOD-makefile
kind: tool
sync: sync
impl: Makefile::status
callers: なし
callees: なし
contracts: なし
design: DSN-mod-01
requirements: FR-env-01
tests: なし(未実装。Makefile のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: イメージ・コンテナ・ボリュームの状態を表示する
---

# MODULE-makefile-status make status

## 目的

ホスト側から現在の状態を1コマンドで俯瞰する(FR-env-01)。

## 処理の流れ

1. `docker images` を3イメージの `reference` フィルタで絞って表示する。
2. `docker ps` を `ancestor` フィルタで絞り、実行中の Claude セッションを表示する。
3. `docker ps --filter "name=^claude-dev-docker-proxy$"` で proxy の状態を表示する。
4. `docker volume ls --filter "name=claude-dev"` でボリュームを表示する。
5. いずれも `2>/dev/null || true` を付けており、失敗しても停止しない。

## 呼び出され方

- 契機: 利用者が `make status` を実行したとき。
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
| 永続化 | なし(読み取りのみ) |
| 発火するイベント | なし |
| ログ | 標準出力へ4つの表 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| Docker デーモンに接続できない | 各コマンドが失敗するが握りつぶされ、見出しだけが並ぶ | 状態が空に見える |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | Makefile はホスト側の開発者向け入口に限定し、日常操作は `claude-dev` CLI に寄せる | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 自動テストが無い | 回帰検出は実機実行に依存する | なし |

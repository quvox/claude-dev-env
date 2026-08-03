---
target: docs/03-impl/relations/MODULE-makefile-orch-sample-clean.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
id: MODULE-makefile-orch-sample-clean
module: MOD-makefile
kind: tool
sync: sync
impl: Makefile::orch-sample-clean
callers: なし
callees: なし
contracts: なし
design: DSN-mod-01
requirements: FR-orch-09
tests: なし(未実装。Makefile のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: サンプルプロジェクトの生成物を削除する
---

# MODULE-makefile-orch-sample-clean make orch-sample-clean

## 目的

自己検証(FR-orch-09)の作業コピーを消して、次の実行を素の状態から始められるようにする。

## 処理の流れ

1. `rm -rf <BASE_DIR>/workspace/orch-sample` を実行する。
2. 「🧹 removed workspace/orch-sample」と表示する。

## 呼び出され方

- 契機: 利用者が `make orch-sample-clean` を実行したとき。
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
| 永続化 | `workspace/orch-sample/` の削除 |
| 発火するイベント | なし |
| ログ | 削除メッセージ |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 対象が存在しない | `rm -rf` は成功扱いになり、削除メッセージが出る | なし |
| 権限が無い | `rm` が失敗し make が非0で停止する | 残骸が残る |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | Makefile はホスト側の開発者向け入口に限定し、日常操作は `claude-dev` CLI に寄せる | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 自動テストが無い | 回帰検出は実機実行に依存する | なし |

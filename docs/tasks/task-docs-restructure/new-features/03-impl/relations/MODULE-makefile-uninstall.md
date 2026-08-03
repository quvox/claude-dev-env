---
target: docs/03-impl/relations/MODULE-makefile-uninstall.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
id: MODULE-makefile-uninstall
module: MOD-makefile
kind: tool
sync: sync
impl: Makefile::uninstall
callers: なし
callees: なし
contracts: なし
design: DSN-mod-01
requirements: FR-env-01, FR-env-10
tests: なし(未実装。Makefile のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: CLI のシンボリックリンクを削除する
---

# MODULE-makefile-uninstall make uninstall

## 目的

`install` の対で、PATH 登録を取り消す(FR-env-10)。イメージやボリュームは消さない。

## 処理の流れ

1. `/usr/local/bin/claude-dev` が symlink または実体として存在するかを調べる。
2. 存在すれば `rm -f` を試み、失敗したら `sudo rm -f` で再試行する。
3. 存在しなければ「ℹ️ ... は存在しません」と表示する。

## 呼び出され方

- 契機: 利用者が `make uninstall` を実行したとき。
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
| 永続化 | `/usr/local/bin/claude-dev` の削除 |
| 発火するイベント | なし |
| ログ | 削除結果 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 権限が無い | `rm -f` の失敗を受けて `sudo rm -f` を実行する。それも失敗すれば make が非0で停止する | symlink が残る |
| 既に存在しない | メッセージだけ出して 0 で終わる | なし |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | Makefile はホスト側の開発者向け入口に限定し、日常操作は `claude-dev` CLI に寄せる | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 自動テストが無い | 回帰検出は実機実行に依存する | なし |

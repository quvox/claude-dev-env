---
id: MODULE-makefile-clean
module: MOD-makefile
kind: tool
sync: sync
impl: Makefile::clean
callers: なし
callees: なし
contracts: なし
design: DSN-mod-01
requirements: FR-env-01, FR-env-03
tests: なし(未実装。Makefile のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: コンテナ・ボリューム・イメージを削除して初期化する
---

# MODULE-makefile-clean make clean

## 目的

ホスト側からの全リセット(FR-env-01)。認証ボリュームも消えるため再ログインが要る(FR-env-03)。

## 処理の流れ

1. 削除対象を列挙して表示し、`read -p "実行しますか？ (y/N) "` で確認する。`y` 以外なら
   「キャンセル」と表示して `exit 1`。
2. `ancestor` フィルタで全 Claude コンテナ(停止中を含む)を `docker rm -f` する。
3. `claude-dev-docker-proxy` を `docker rm -f` する。
4. `claude-dev-auth` / `claude-dev-history` / `claude-dev-config` / `claude-dev-chrome-data` を
   `docker volume rm -f` する。
5. docker network `claude-dev-net` を削除する。
6. 3イメージを `docker rmi -f` する。
7. 手順2〜6 はすべて `2>/dev/null || true` で握りつぶす。

## 呼び出され方

- 契機: 利用者が `make clean` を実行したとき。
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
| 戻り値 | 0(キャンセル時は 1) |
| 永続化 | **破壊的**: 全 Claude コンテナ・docker-proxy・共有4ボリューム(認証を含む)・docker network・3イメージの削除 |
| 発火するイベント | なし |
| ログ | 削除対象の一覧と完了メッセージ |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 確認に `y` 以外を入力 | 「キャンセル」と表示して `exit 1` | 何も削除されない |
| 削除が失敗する(使用中など) | 握りつぶして次へ進み、最後に「✅ 全リセット完了」と表示する(**誤った成功表示**) | 残骸が残る |
| `fwd-*` の中継コンテナ | `ancestor` フィルタに合致するため削除される | なし |
| コンテナ別 Chrome ボリューム `claude-dev-chrome-<name>` | **削除対象に含まれない**(消すのは `claude-dev-chrome-data` のみ) | 残骸が残る |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | Makefile はホスト側の開発者向け入口に限定し、日常操作は `claude-dev` CLI に寄せる | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 自動テストが無い | 回帰検出は実機実行に依存する | なし |

---
id: MODULE-cli-unforward
module: MOD-cli-unforward
kind: tool
sync: sync
impl: claude-dev::main#unforward, claude-dev-mac::main#unforward
callers: なし
callees: MODULE-cli-common-container-exists, MODULE-cli-common-container-name
contracts: なし
design: DSN-mod-01, DSN-mod-02
requirements: FR-env-06
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: 指定ポートのフォワードを解除する
---

# MODULE-cli-unforward ポートフォワードの解除

## 目的

`MODULE-cli-forward` が作った中継コンテナを個別に取り消す(FR-env-06)。ホスト側ポートを
開けっぱなしにしないための対の操作である。

## 処理の流れ

1. `MODULE-cli-common-container-name` で対象コンテナ名を決める(引数 `NAME` 優先)。
2. `MODULE-cli-common-container-exists` で `fwd-<name>-<cport>` の存在を確認する。
3. 存在すれば `docker rm -f fwd-<name>-<cport>` で削除し、結果を表示する。存在しなければ
   その旨を表示する。

## 呼び出され方

- 契機: 利用者が `claude-dev unforward <cport> [NAME]` を実行したとき。
- 前提条件: なし(本体コンテナが停止していても中継コンテナは消せる)。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `<cport>` | 整数 | 必須 | 解除するコンテナ側ポート番号 |
| `NAME` | 文字列 | 任意 | 省略時はカレントディレクトリ由来のコンテナ名 |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

### MODULE-cli-common-container-name

- 何のために呼ぶか: 中継コンテナ名の決定。 / 何を渡すか: なし。 / 何を受け取るか: コンテナ名。
- **失敗したときどうなるか**: 想定されない。

### MODULE-cli-common-container-exists

- 何のために呼ぶか: 削除対象の有無を判定するため。 / 何を渡すか: `fwd-<name>-<cport>`。 / 何を受け取るか: 終了ステータス。
- **失敗したときどうなるか**: 「無い」と判定され、削除せずメッセージだけ出す。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 0 |
| 永続化 | コンテナ `fwd-<name>-<cport>` の削除(占有していたホストポートが解放される) |
| 発火するイベント | なし |
| ログ | 標準出力へ解除結果 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 対象のフォワードが無い | 「見つかりません」旨を表示して 0 で終わる | なし |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 存在しない場合もエラーにしない(冪等に何度でも呼べるようにする) | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| ポート単位でしか解除できない | まとめて解除したい場合は `stop` を使う | なし |

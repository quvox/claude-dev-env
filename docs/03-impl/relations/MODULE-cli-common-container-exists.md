---
id: MODULE-cli-common-container-exists
module: MOD-cli-common
kind: function-call
sync: sync
impl: claude-dev::container_exists, claude-dev-mac::container_exists
callers: MODULE-cli-forward, MODULE-cli-logout, MODULE-cli-reset, MODULE-cli-start, MODULE-cli-stop, MODULE-cli-unforward
callees: なし
contracts: なし
design: DSN-mod-01, DSN-mod-02
requirements: FR-env-01
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-04
summary: 指定名のコンテナが存在するか(停止中を含む)を判定する
---

# MODULE-cli-common-container-exists コンテナ存在判定(停止中を含む)

## 目的

稼働判定(`MODULE-cli-common-is-running`)とは別に「停止した残骸があるか」を知る必要がある。
`start` は残骸を消してから作り直し、`stop` / `logout` / `forward` / `unforward` は残骸も削除対象に
含める(FR-env-01)。両者は別概念なので別機能として立てている。

## 処理の流れ

1. `docker ps -aq -f "name=^<name>$" 2>/dev/null` を実行する(`-a` で停止中も対象にする)。
2. 出力が1行以上あれば終了ステータス 0、無ければ 1 を返す。

## 呼び出され方

- 契機: コンテナを作り直す前、または削除対象を決めるとき。
- 前提条件: `docker` コマンドが実行できること。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `$1` | 文字列 | 必須 | コンテナ名。完全一致 |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

連携先なし。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 終了ステータス。0 = 存在する(停止中を含む) / 1 = 存在しない |
| 永続化 | なし |
| 発火するイベント | なし |
| ログ | なし |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| Docker デーモンに接続できない | stderr を捨てて空出力となり 1(=存在しない)を返す | 呼び出し元は「残骸なし」として進み、後続の `docker` 実行で失敗する |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | `is_running` と統合せず別関数のまま扱う(判定の意味が違い、`start` は両方を別々に使う) | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| デーモン不在を「存在しない」に丸める | 呼び出し元が誤った分岐へ進む | なし |

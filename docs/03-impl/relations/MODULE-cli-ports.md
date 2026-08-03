---
id: MODULE-cli-ports
module: MOD-cli-ports
kind: tool
sync: sync
impl: claude-dev::main#ports, claude-dev-mac::main#ports
callers: なし
callees: MODULE-cli-common-container-name, MODULE-cli-common-get-novnc-url, MODULE-cli-common-is-running
contracts: なし
design: DSN-mod-01, DSN-mod-02
requirements: FR-env-06, FR-env-11
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: コンテナのポートフォワード一覧と noVNC URL を表示する
---

# MODULE-cli-ports ポート一覧の表示

## 目的

いま何が外から見えているのかを一覧できるようにする(FR-env-06)。noVNC の URL も併せて
出すことで、ブラウザ確認(FR-env-11)への導線を兼ねる。

## 処理の流れ

1. `MODULE-cli-common-container-name` で対象コンテナ名を決める(引数 `NAME` 優先)。
2. `MODULE-cli-common-is-running` で稼働を確認する。未起動なら日本語エラーで `exit 1`。
3. `fwd-<name>-*` に一致するコンテナを列挙し、`host:<h> → <name>:<c>` の形式で表示する。
4. `MODULE-cli-common-get-novnc-url` の結果が空でなければ noVNC URL を表示する。

## 呼び出され方

- 契機: 利用者が `claude-dev ports [NAME]` を実行したとき。
- 前提条件: 対象コンテナが稼働中であること。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `NAME` | 文字列 | 任意 | 省略時はカレントディレクトリ由来のコンテナ名 |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

### MODULE-cli-common-container-name

- 何のために呼ぶか: 列挙対象の絞り込み。 / 何を渡すか: なし。 / 何を受け取るか: コンテナ名。
- **失敗したときどうなるか**: 想定されない。

### MODULE-cli-common-is-running

- 何のために呼ぶか: 未起動時に一覧を出さないため。 / 何を渡すか: コンテナ名。 / 何を受け取るか: 終了ステータス。
- **失敗したときどうなるか**: 日本語エラーを出して `exit 1`。

### MODULE-cli-common-get-novnc-url

- 何のために呼ぶか: noVNC の接続先を提示するため。 / 何を渡すか: コンテナ名。 / 何を受け取るか: URL または空。
- **失敗したときどうなるか**: 空が返り URL 行を出さない(`--no-vnc` 起動時の正常な結果)。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 0(未起動時は 1) |
| 永続化 | なし(読み取りのみ) |
| 発火するイベント | なし |
| ログ | 標準出力へ一覧 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| コンテナが未起動 | 日本語エラーを出して `exit 1` | 利用者は `start` する |
| フォワードが1件も無い | 一覧が空のまま noVNC URL だけを出す | なし |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 表示だけを行い、状態を変えない(読み取り専用のサブコマンド) | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 中継コンテナ以外の公開ポートは列挙しない | `docker run -p` で直接開けたポートは表示されない | なし |

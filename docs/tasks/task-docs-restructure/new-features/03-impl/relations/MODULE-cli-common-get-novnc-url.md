---
target: docs/03-impl/relations/MODULE-cli-common-get-novnc-url.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
id: MODULE-cli-common-get-novnc-url
module: MOD-cli-common
kind: function-call
sync: sync
impl: claude-dev::get_novnc_url, claude-dev-mac::get_novnc_url
callers: MODULE-cli-list, MODULE-cli-ports, MODULE-cli-start
callees: なし
contracts: なし
design: DSN-mod-01, DSN-mod-02, DSN-ui-01
requirements: FR-env-11
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: 公開中の noVNC ポートから接続 URL を組み立てる
---

# MODULE-cli-common-get-novnc-url noVNC 接続 URL の組み立て

## 目的

利用者がブラウザで画面確認するための URL 表記を1か所で決める(FR-env-11)。`start` /
`list` / `ports` の3機能が同じ URL を表示するので、表記規則を共有基盤として切り出している。

## 処理の流れ

1. `docker port "<container>" 6080` を実行し、1行目をポート部分だけに切り出す
   (`head -1 | sed 's/.*://'`)。
2. 取得できた場合だけ `http://localhost:<port>/vnc.html?autoconnect=true` を標準出力へ出す。
3. 取得できなければ何も出力しない(空文字)。

## 呼び出され方

- 契機: 稼働中コンテナの接続情報を利用者へ提示するとき。
- 前提条件: 対象コンテナが 6080 を公開していること(VNC 有効で起動していること)。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `$1` | 文字列 | 必須 | コンテナ名 |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

連携先なし。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 標準出力へ URL 1行、または空 |
| 永続化 | なし |
| 発火するイベント | なし |
| ログ | なし |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| `--no-vnc` で起動していて 6080 が非公開 | `docker port` が空を返し、本機能も空文字を返す | 呼び出し元は URL 行を表示しない |
| コンテナが存在しない | `docker port` の stderr を破棄し空文字を返す | 同上 |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | ホスト名は常に `localhost` 固定(リモートホスト運用は SSH ポートフォワード前提) | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| `localhost` 固定 | リモートの docker ホストで起動した場合、表示 URL では接続できない | なし |

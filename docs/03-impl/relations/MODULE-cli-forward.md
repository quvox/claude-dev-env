---
id: MODULE-cli-forward
module: MOD-cli-forward
kind: tool
sync: sync
impl: claude-dev::main#forward, claude-dev-mac::main#forward
callers: なし
callees: MODULE-cli-common-container-exists, MODULE-cli-common-container-name, MODULE-cli-common-is-running
contracts: なし
design: DSN-mod-01, DSN-mod-02
requirements: FR-env-06
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: 指定コンテナポートのホスト側フォワードを動的に追加する
---

# MODULE-cli-forward ポートフォワードの追加

## 目的

`start` の時点では Web アプリ用のポートを公開せず(noVNC の 6080 だけを公開する)、必要に
なった時点で明示的に開ける(FR-env-06)。既に稼働中のコンテナを再作成せずにポートを足せる
ようにするため、socat の使い捨てコンテナを中継に使う。

## 処理の流れ

1. `MODULE-cli-common-container-name` で対象コンテナ名を決める(引数 `NAME` 優先)。
2. `MODULE-cli-common-is-running` で稼働を確認する。未起動なら日本語エラーで `exit 1`。
3. `MODULE-cli-common-container-exists` で `fwd-<name>-<cport>` の有無を調べ、既にあれば現在の
   ホストポートを表示して終わる。
4. `find_available_host_port`(本機能に畳み込み)で 8100〜8999 の空きポートを探す。
5. `docker run -d --rm -p <hport>:<cport> --network claude-dev-net --name fwd-<name>-<cport>
   --entrypoint socat <IMG_CLAUDE> TCP-LISTEN:<cport>,fork,reuseaddr TCP:<name>:<cport>` で
   中継コンテナを起動する。
6. Linux 版は SSH トンネルの例を、macOS 版は `http://localhost:<host-port>` の直結案内を表示する。

## 呼び出され方

- 契機: 利用者が `claude-dev forward <cport> [NAME]` を実行したとき。
- 前提条件: 対象コンテナが稼働中であること。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `<cport>` | 整数 | 必須 | コンテナ側のポート番号 |
| `NAME` | 文字列 | 任意 | 省略時はカレントディレクトリ由来のコンテナ名 |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

### MODULE-cli-common-container-name

- 何のために呼ぶか: 中継コンテナ名 `fwd-<name>-<cport>` と接続先ホスト名の決定。
- 何を渡すか: なし。 / 何を受け取るか: コンテナ名。
- **失敗したときどうなるか**: 想定されない。

### MODULE-cli-common-is-running

- 何のために呼ぶか: 未起動のコンテナへ中継を張らないため。 / 何を渡すか: コンテナ名。 / 何を受け取るか: 終了ステータス。
- **失敗したときどうなるか**: 日本語エラーを出して `exit 1`。

### MODULE-cli-common-container-exists

- 何のために呼ぶか: 同じポートのフォワードが既にあるかを判定するため。
- 何を渡すか: `fwd-<name>-<cport>`。 / 何を受け取るか: 終了ステータス。
- **失敗したときどうなるか**: 「無い」と判定して `docker run` し、名前衝突で失敗する。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 0(未起動時は 1) |
| 永続化 | コンテナ `fwd-<name>-<cport>`(`--rm` なので停止と同時に消える)。ホスト側ポート 8100〜8999 の1つを占有する |
| 発火するイベント | なし |
| ログ | 標準出力へ割り当てたホストポートと接続方法の案内 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| コンテナが未起動 | 日本語エラーを出して `exit 1` | 利用者は `start` する |
| 同じポートのフォワードが既存 | 現在のホストポートを表示して 0 で終わる(二重に作らない) | なし |
| 8100〜8999 に空きが無い | `find_available_host_port` が基準値 8100 を返し、`docker run` がポート衝突で失敗する | 非0終了する |
| コンテナ側でそのポートが待ち受けていない | 中継コンテナは起動するが接続時に socat が接続拒否を返す | ブラウザ側で接続エラーになる |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | コンテナを再作成せずに socat 中継コンテナで足す(稼働中セッションを壊さないため) | D0-scope-02 |
| 2 | 中継コンテナは `--rm` で作る(残骸を残さない。`stop` も `fwd-<name>-*` を掃除する) | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 空きポート探索から `docker run` までが非アトミック | 同時実行で衝突しうる(`start` と違いリトライは無い) | なし |

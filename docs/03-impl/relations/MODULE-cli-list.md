---
id: MODULE-cli-list
module: MOD-cli-list
kind: tool
sync: sync
impl: claude-dev::main#list, claude-dev-mac::main#list
callers: なし
callees: MODULE-cli-common-get-novnc-url, MODULE-cli-common-is-running
contracts: なし
design: DSN-mod-01, DSN-mod-02
requirements: FR-env-01, FR-env-11
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: 実行中セッションの一覧と noVNC URL を表示する
---

# MODULE-cli-list セッション一覧の表示

## 目的

複数プロジェクトを同時に開けるため、どのセッションが動いているかを横断的に見られるように
する(FR-env-01)。各セッションの noVNC URL も出す(FR-env-11)。

## 処理の流れ

1. `docker ps` を `--filter ancestor=claude-dev-claude` / `--filter ancestor=claude-dev-claude-vnc`
   で絞り、全 Claude コンテナを列挙する。
2. 各コンテナについて NAME / STATUS / WORKSPACE(マウント元)を表示する。
3. `MODULE-cli-common-get-novnc-url` で noVNC URL を求めて表示する。
4. `fwd-<name>-*` のフォワードを併記する。
5. 最後に `MODULE-cli-common-is-running` で `claude-dev-docker-proxy` の稼働状態を確認して表示する。

## 呼び出され方

- 契機: 利用者が `claude-dev list` を実行したとき。
- 前提条件: なし(カレントディレクトリに依存しない)。
- 引数: なし。

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| (なし) | - | - | - |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

### MODULE-cli-common-get-novnc-url

- 何のために呼ぶか: 各セッションの接続先を提示するため。 / 何を渡すか: コンテナ名。 / 何を受け取るか: URL または空。
- **失敗したときどうなるか**: 空が返り、そのセッションの URL 行を出さない。

### MODULE-cli-common-is-running

- 何のために呼ぶか: 共有 docker-proxy の稼働状態を表示するため。 / 何を渡すか: `claude-dev-docker-proxy`。 / 何を受け取るか: 終了ステータス。
- **失敗したときどうなるか**: 非稼働と表示される。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 0 |
| 永続化 | なし(読み取りのみ) |
| 発火するイベント | なし |
| ログ | 標準出力へ一覧 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 稼働中のセッションが0件 | 一覧が空で、proxy の状態だけを表示する | なし |
| GHCR 版とローカルビルド版でイメージ名が同じ | `ancestor` フィルタは名前一致なので両方列挙される | なし |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 列挙条件を `ancestor`(イメージ由来)にする。コンテナ名の接頭辞では判定できない(コンテナ名 = ディレクトリ名のため) | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| `ancestor` フィルタのため、別イメージから起動したセッションは列挙されない | GHCR 版と同名 retag 運用が前提 | なし |

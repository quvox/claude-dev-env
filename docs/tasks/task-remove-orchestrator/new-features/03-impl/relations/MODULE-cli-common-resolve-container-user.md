---
target: docs/03-impl/relations/MODULE-cli-common-resolve-container-user.md
change: replace
version_bump: patch
reason: 'オーケストレーターの全面削除にともなう `callers` の修正(決定シート 概念1)。`MODULE-cli-orchestrate` を削除するので、この機能の `callers` から同 ID を外す。**外さないと `check-relations.py` の対称性検査と `CS2` が実在しない ID を指して落ちる**。 呼び出し元は 4 → 3 になる。あわせて `## 呼び出され方` の契機の列挙から `orchestrate` を外す。。**`## 実装上の判断` を再掲する**: `.claude/directions/delegation.md` §3.1 に従って既存の判断行を1件ずつ読み直した結果、**すべて継続**である(オーケストレーターの削除で見直す条件が発火した行は1件も無い)。`CS19` はこの節が変更のたびに読み直されることを要求するので、変更が無い場合も再掲する'
id: MODULE-cli-common-resolve-container-user
module: MOD-cli-common
kind: function-call
sync: sync
impl: claude-dev::resolve_container_user, claude-dev-mac::resolve_container_user
callers: MODULE-cli-attach, MODULE-cli-code, MODULE-cli-start
callees: なし
contracts: なし
design: DSN-mod-01, DSN-mod-02, DSN-dist-01
requirements: FR-env-01, FR-env-02, FR-env-09
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: docker exec に渡す実行ユーザを稼働中コンテナ自身の env から決定する
reflected: 2026-08-10
---

# MODULE-cli-common-resolve-container-user exec 実行ユーザの解決

## 目的

`docker exec -u` に渡すユーザ名を、ローカルイメージのタグではなく**そのコンテナ自身に
焼き込まれた `CONTAINER_USER`** から解決する(FR-env-02)。GHCR の generic user イメージ
(`CONTAINER_USER=dev`)とローカルビルド(`whoami`)が混在しても、別イメージ由来で稼働中の
コンテナへ正しい `-u` で入れるようにするための機能である(FR-env-09)。

## 処理の流れ

1. `docker inspect "<container>" --format '{{range .Config.Env}}{{println .}}{{end}}'` を実行する。
2. `sed -n 's/^CONTAINER_USER=//p' | head -1` で `CONTAINER_USER` の値を取り出す。
3. 空なら、スクリプト先頭でイメージから解決済みの `CUSER` にフォールバックする。
4. 解決した値を改行なしで標準出力へ返す(`printf '%s'`)。

## 呼び出され方

- 契機: 稼働中コンテナへ `docker exec` する直前(`start` の再接続経路 / `code` / `attach`)。
  いずれも `is_running` の確認後に `CUSER="$(resolve_container_user "$NAME")"` と
  上書きしてから使う。
- 前提条件: 対象コンテナが存在すること。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `$1` | 文字列 | 必須 | コンテナ名または ID |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

連携先なし。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 標準出力へユーザ名(改行なし) |
| 永続化 | なし |
| 発火するイベント | なし |
| ログ | なし |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| コンテナが存在しない | `docker inspect` が失敗し stderr は破棄。空文字となり `CUSER` へフォールバックする | 呼び出し元は `is_running` で先に弾いているため実質発生しない |
| コンテナに `CONTAINER_USER` が無い(旧イメージ) | `CUSER` へフォールバックする | 旧来どおりの挙動 |
| フォールバック先の `CUSER` もコンテナに存在しない | `docker exec -u` が `unable to find user ...: no matching entries in passwd file` で失敗する | サブコマンドが非0で終了する |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 新規コンテナ作成(create)経路と `firewall`(`-u` 無し)はこの上書きの対象外にする | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| コンテナ内 `/etc/passwd` の実在までは検証しない | `CONTAINER_USER` が誤っているイメージでは exec が失敗する | なし |

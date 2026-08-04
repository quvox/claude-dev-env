---
id: MODULE-cli-common-image-exists
module: MOD-cli-common
kind: function-call
sync: sync
impl: claude-dev::image_exists, claude-dev-mac::image_exists
callers: MODULE-cli-common-require-setup, MODULE-cli-reset, MODULE-cli-start
callees: なし
contracts: なし
design: DSN-mod-01, DSN-mod-02
requirements: FR-env-01, FR-env-09
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-04
summary: 指定イメージがローカルに存在するかを判定する
---

# MODULE-cli-common-image-exists イメージ存在判定

## 目的

イメージが無ければ自動ビルドする、という前提条件ゲートの判定部(FR-env-01)。GHCR から
`pull` したイメージを `latest` へ retag する運用(FR-env-09)でも、ビルドの要否はこの判定だけで
決まる。

## 処理の流れ

1. `docker image inspect "<ref>" >/dev/null 2>&1` を実行する。
2. `docker image inspect` の終了ステータスをそのまま返す(0 = 存在)。

## 呼び出され方

- 契機: `require_setup` と `ensure_docker_proxy_container` がビルド要否を決めるとき。
- 前提条件: `docker` コマンドが実行できること。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `$1` | 文字列 | 必須 | イメージ参照(名前またはイメージ ID) |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

連携先なし。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 終了ステータス。0 = 存在する / 非0 = 存在しない |
| 永続化 | なし |
| 発火するイベント | なし |
| ログ | なし(stdout/stderr とも破棄する) |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| Docker デーモンに接続できない | 非0 を返す | 呼び出し元がビルドを試み、`docker build` 側で失敗して `set -e` により終了する |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | イメージの新旧(ダイジェスト・ラベル)は見ない。存在の有無だけで判定する | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 古いイメージでも「存在する」と判定する | 更新は `pull` / `upgrade` を明示実行するまで行われない | なし(意図した設計) |

---
id: MODULE-makefile-build-claude
module: MOD-makefile
kind: tool
sync: sync
impl: Makefile::build-claude
callers: MODULE-makefile-build, MODULE-makefile-build-claude-vnc
callees: なし
contracts: なし
design: DSN-mod-01, DSN-dist-01
requirements: FR-env-01, FR-env-09, FR-env-12
tests: なし(未実装。Makefile のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: Claude ベースイメージをビルドする
---

# MODULE-makefile-build-claude make build-claude

## 目的

開発コンテナの土台となるイメージを作る(FR-env-01・FR-env-09)。エージェント CLI は配布ステージの終端レイヤーで導入される(FR-env-12)。

## 処理の流れ

1. `docker build -t claude-dev-claude --target claude-cli` を実行する。
2. build-arg として `USERNAME=$(whoami)`・`USER_UID=$(id -u)`・`USER_GID=$(id -g)` を渡す
   (コンテナ内ユーザをホストへ合わせる)。
3. Dockerfile は `.devcontainer/Dockerfile.claude`、コンテキストは `BASE_DIR`。
4. Claude Code のバージョンは Dockerfile 既定の `latest` を使う(固定しない)。

## 呼び出され方

- 契機: 利用者が `make build-claude` を実行したとき。
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
| 戻り値 | 0(失敗時は非0) |
| 永続化 | イメージ `claude-dev-claude` |
| 発火するイベント | なし |
| ログ | docker build の出力 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| ビルドが失敗する | docker のログを出して make が非0で停止する | 前のイメージが残る |
| ネットワーク不通 | パッケージ取得に失敗してビルドが失敗する | 同上 |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | Makefile はホスト側の開発者向け入口に限定し、日常操作は `claude-dev` CLI に寄せる | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 自動テストが無い | 回帰検出は実機実行に依存する | なし |

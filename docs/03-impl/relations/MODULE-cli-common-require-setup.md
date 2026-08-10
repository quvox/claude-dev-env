---
id: MODULE-cli-common-require-setup
updated: 2026-08-10
module: MOD-cli-common
kind: function-call
sync: sync
impl: claude-dev::require_setup, claude-dev-mac::require_setup
callers: MODULE-cli-attach, MODULE-cli-code, MODULE-cli-login, MODULE-cli-login-codex, MODULE-cli-logout, MODULE-cli-start
callees: MODULE-cli-common-image-exists
contracts: なし
design: DSN-mod-01, DSN-mod-02
requirements: FR-env-01, FR-env-09
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
summary: セットアップ未実施なら必要なイメージを自動ビルドする事前条件ゲート
---

# MODULE-cli-common-require-setup セットアップ事前条件ゲート

## 目的

利用者に `setup` を強制せず、必要になった時点で不足イメージを自動ビルドする(FR-env-01)。
7つのサブコマンドが共通で通る事前条件ゲートであり、「イメージが無い」という理由での失敗を
このモジュールに集約している。

## 処理の流れ

1. `MODULE-cli-common-image-exists` で `claude-dev-claude`(`IMG_CLAUDE`)の有無を判定する。
2. 無ければ `docker build -t claude-dev-claude --target claude-cli
   --build-arg USERNAME=$CUSER --build-arg USER_UID=$(id -u) --build-arg USER_GID=$(id -g)
   -f <BASE_DIR>/.devcontainer/Dockerfile.claude <BASE_DIR>` を実行する。
3. 同じく `claude-dev-claude-vnc`(`IMG_CLAUDE_VNC`)の有無を判定し、無ければ
   `--target claude-vnc` で同様にビルドする。
4. どちらも存在すれば何もしない(冪等)。

## 呼び出され方

- 契機: `setup` 以外のサブコマンドが処理の先頭で呼ぶ(`start` / `login` / `login-codex` /
  `logout` / `attach` / `code`)。
- 前提条件: `docker` が実行でき、`<BASE_DIR>/.devcontainer/Dockerfile.claude` が存在すること。
- 引数: なし。

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| (なし) | - | - | 参照するのは定数 `IMG_CLAUDE` / `IMG_CLAUDE_VNC` と `BASE_DIR` |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

### MODULE-cli-common-image-exists

- 何のために呼ぶか: ビルドが要るかどうかを決めるため。
- 何を渡すか: イメージ名(`claude-dev-claude` / `claude-dev-claude-vnc`)。
- 何を受け取るか: 終了ステータス(0 = 存在する)。
- **失敗したときどうなるか**: 「存在しない」と判定されビルドへ進む。既に存在していれば
  `docker build` はキャッシュで即座に完了するため、誤判定でも観測可能な破壊は起きない。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | なし(失敗時は `set -e` により呼び出し元ごと終了する) |
| 永続化 | ローカル Docker イメージ `claude-dev-claude` / `claude-dev-claude-vnc` |
| 発火するイベント | なし |
| ログ | 標準出力へ「📦 Claude ベースイメージが見つかりません。ビルドします...」等 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| `docker build` が失敗する | `set -e` によりスクリプト全体が非0で終了する。docker のビルドログがそのまま端末に出る | サブコマンドは処理に入らず終了する |
| `Dockerfile.claude` が無い | `docker build` が「failed to read dockerfile」で失敗し、上と同じ経路で終了する | 同上 |
| ビルド中に中断(Ctrl-C) | 中間イメージが残り、次回呼び出しで再びビルドが走る | なし |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | ビルドの build-arg にホストの UID/GID を渡す(コンテナ内ユーザをホストに合わせる。FR-env-02 の一部) | D0-scope-02 |
| 2 | `IMG_DOCKER_PROXY` はここでは作らない(Docker ソケットがある環境でだけ必要なので `ensure_docker_proxy_container` 側に置く) | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| イメージが古くても再ビルドしない | 更新は `claude-dev pull` / `claude-dev upgrade` の明示実行が必要 | なし |

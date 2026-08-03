---
id: MODULE-cli-setup
module: MOD-cli-setup
kind: tool
sync: sync
impl: claude-dev::main#setup, claude-dev-mac::main#setup
callers: なし
callees: なし
contracts: なし
design: DSN-mod-01, DSN-mod-02
requirements: FR-env-01, FR-env-09
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: イメージをビルドし docker network と共有ボリュームを作る初回セットアップ
---

# MODULE-cli-setup 初回セットアップ

## 目的

利用開始に必要なホスト側の資源(`.env`・docker network・共有ボリューム・3イメージ)を一度に
そろえる(FR-env-01)。以降のサブコマンドは `MODULE-cli-common-require-setup` が不足分を補うため、
本機能は「明示的に全部そろえたいとき」の入口である。

## 処理の流れ

1. `<BASE_DIR>/.env` が無ければ `.env.example` から生成する。
2. docker network `claude-dev-net` と共有ボリューム `claude-dev-auth` / `claude-dev-history` /
   `claude-dev-config` を作成する。
3. `Dockerfile.claude` の `--target claude-cli` を `claude-dev-claude` としてビルドする。
4. 同じく `--target claude-vnc` を `claude-dev-claude-vnc` としてビルドする。
5. `Dockerfile.docker-proxy` を `claude-dev-docker-proxy` としてビルドする。
6. 次の手順と、PATH へ登録する symlink コマンド
   (`sudo ln -sf <BASE_DIR>/claude-dev /usr/local/bin/claude-dev`)を案内する。

## 呼び出され方

- 契機: 利用者が `claude-dev setup` を実行したとき。
- 前提条件: `docker` が実行でき、リポジトリの `.devcontainer/` が存在すること。
- 引数: なし。

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| (なし) | - | - | - |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

連携先なし。ネットワーク/ボリューム作成は `ensure_infrastructure` と同等の処理を本分岐が直接
書いており、共有関数としては呼んでいない(コールグラフにも辺が無い)。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 終了ステータス 0(ビルド失敗時は `set -e` により非0) |
| 永続化 | `<BASE_DIR>/.env`、docker network `claude-dev-net`、docker volume `claude-dev-auth` / `claude-dev-history` / `claude-dev-config`、イメージ `claude-dev-claude` / `claude-dev-claude-vnc` / `claude-dev-docker-proxy` |
| 発火するイベント | なし |
| ログ | 標準出力へ進捗と次手順の案内 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| `docker build` の失敗 | docker のログをそのまま出し `set -e` で非0終了する | セットアップは未完了のまま。再実行で続きから作られる(冪等) |
| ネットワーク/ボリュームが既存 | エラーを破棄して続行する | なし |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | `setup` は必須ではない(他のサブコマンドが `require_setup` で自動ビルドする)。明示実行の入口としてだけ残す | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| PATH 登録(symlink)は自動化せず案内にとどめる | `sudo` を CLI から実行しない方針の帰結 | なし |

---
id: MODULE-cli-upgrade
module: MOD-cli-upgrade
kind: tool
sync: sync
impl: claude-dev::main#upgrade, claude-dev-mac::main#upgrade
callers: なし
callees: なし
contracts: なし
design: DSN-mod-01, DSN-mod-02
requirements: FR-env-01, FR-env-09
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: 全イメージを --no-cache で再ビルドして更新する
---

# MODULE-cli-upgrade イメージの完全再ビルド

## 目的

`MODULE-cli-common-image-exists` が「存在すれば再ビルドしない」判定であるため、内容を更新する
明示的な手段が要る(FR-env-01・FR-env-09)。本機能はキャッシュを使わずに作り直す。

## 処理の流れ

1. `docker build --no-cache -t claude-dev-claude --target claude-cli`
   (`USERNAME` / `USER_UID` / `USER_GID` を build-arg で渡す)を実行する。
2. 同じく `--no-cache -t claude-dev-claude-vnc --target claude-vnc` を実行する。
3. `docker build --no-cache -t claude-dev-docker-proxy -f Dockerfile.docker-proxy` を実行する。
4. 「実行中のコンテナは stop → start で反映されます」と案内する。

## 呼び出され方

- 契機: 利用者が `claude-dev upgrade` を実行したとき。
- 前提条件: `docker` が実行でき、`.devcontainer/` が存在すること。ネットワークが到達可能であること
  (`--no-cache` のため全レイヤを取得し直す)。
- 引数: なし。

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| (なし) | - | - | - |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

連携先なし(`require_setup` を経由せず直接 `docker build` する)。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 0(ビルド失敗時は `set -e` で非0) |
| 永続化 | イメージ `claude-dev-claude` / `claude-dev-claude-vnc` / `claude-dev-docker-proxy` を作り直す |
| 発火するイベント | なし |
| ログ | 標準出力へ進捗と反映方法の案内 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| ビルドが失敗する | docker のログを出して `set -e` で非0終了する。途中まで作られたイメージは前の版のまま残る | 稼働中のセッションには影響しない |
| 稼働中のコンテナがある | 停止せずビルドだけ行う。新イメージは `stop` → `start` まで反映されない | 明示的な再起動が要る |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 稼働中コンテナを自動で入れ替えない(作業中のセッションを勝手に落とさない) | D0-scope-02 |
| 2 | GHCR から取り直す `pull` と使い分ける(`upgrade` はローカルビルド運用向け) | D0-dist-01 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| `--no-cache` のため所要時間が長い | 部分更新の手段は `make update-claude` 側にある | なし |

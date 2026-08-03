---
id: MODULE-cli-pull
module: MOD-cli-pull
kind: tool
sync: sync
impl: claude-dev::main#pull, claude-dev-mac::main#pull
callers: なし
callees: なし
contracts: なし
design: DSN-mod-01, DSN-mod-02, DSN-arch-04
requirements: FR-env-09
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: GHCR からビルド済みイメージを取得して latest へ retag する
---

# MODULE-cli-pull 配布イメージの取得

## 目的

ローカルビルドを避け、GHCR に日次で publish されたマルチアーキイメージを取得して使えるように
する(FR-env-09)。取得後に `latest` へ retag することで、以降の `start` /
`MODULE-cli-common-require-setup` がビルドを走らせずに済む。

## 処理の流れ

1. `.env` の `CLAUDE_DEV_REGISTRY`(既定 `ghcr.io/quvox`)と `CLAUDE_DEV_IMAGE_TAG`(既定 `latest`。
   引数 `TAG` があれば上書き)から参照を組み立てる。
2. `claude-dev-claude` / `claude-dev-claude-vnc` / `claude-dev-docker-proxy` の3イメージを
   `docker pull` する。manifest によりホストのアーキが自動選択される。
3. 取得できたものを `${name}:latest` へ `docker tag` する。
4. 1つでも成功すれば完了メッセージを出す。全部失敗した場合は `docker login ghcr.io` を案内して
   `exit 1` する。

## 呼び出され方

- 契機: 利用者が `claude-dev pull [TAG]` を実行したとき。
- 前提条件: ネットワークが到達可能であること。private パッケージなら `docker login ghcr.io` 済み。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `TAG` | 文字列 | 任意 | 取得タグ。省略時は `CLAUDE_DEV_IMAGE_TAG`(既定 `latest`) |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

連携先なし(GHCR への `docker pull` は外部コマンド実行であり機能間の辺には現れない)。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 1つ以上成功で 0、全失敗で 1 |
| 永続化 | ローカルイメージ `claude-dev-claude` / `claude-dev-claude-vnc` / `claude-dev-docker-proxy`(いずれも `:latest` タグ) |
| 発火するイベント | なし |
| ログ | 標準出力へ取得結果。失敗時は stderr へ `docker login ghcr.io` の案内 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 一部のイメージだけ取得できた | 取得できたものだけ retag し、完了扱い(0)にする | 残りは `require_setup` がローカルビルドする |
| 全イメージの取得に失敗 | `docker login ghcr.io` を案内して `exit 1` | 利用者はログインするかローカルビルドへ切り替える |
| 存在しないタグを指定 | `docker pull` が manifest unknown で失敗し、全失敗と同じ経路になる | 同上 |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 取得後に `:latest` へ retag する(以降の存在判定を1本の名前に集約し、`require_setup` を変えずに済ませる) | D0-dist-01 |
| 2 | 部分成功を成功として扱う(不足分は自動ビルドで補われるため) | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| retag のためローカルビルド版と GHCR 版が同名で混在しうる | 稼働中コンテナのユーザ差異は `MODULE-cli-common-resolve-container-user` が吸収する | なし |

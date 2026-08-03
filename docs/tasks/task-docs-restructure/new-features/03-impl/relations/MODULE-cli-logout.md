---
target: docs/03-impl/relations/MODULE-cli-logout.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
id: MODULE-cli-logout
module: MOD-cli-logout
kind: tool
sync: sync
impl: claude-dev::main#logout, claude-dev-mac::main#logout
callers: なし
callees: MODULE-cli-common-container-exists, MODULE-cli-common-require-setup
contracts: なし
design: DSN-mod-01, DSN-mod-02, DSN-auth-01
requirements: FR-env-03
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: Claude と Codex の認証情報を共有ボリュームごと削除する
---

# MODULE-cli-logout 認証の削除

## 目的

共有ボリュームに残っている認証を消し、以後のコンテナが未ログイン状態で起動するようにする
(FR-env-03)。claude と codex の認証が同じボリュームに同居しているため、両方が同時に消える。

## 処理の流れ

1. `MODULE-cli-common-require-setup` でイメージをそろえる。
2. 稼働中の Claude コンテナと docker-proxy コンテナを `docker rm -f` で削除する
   (`MODULE-cli-common-container-exists` で存在を確認してから消す)。
3. `claude-dev-auth` をマウントした一時コンテナで `rm -rf /auth/* /auth/.*` を実行し、
   ボリュームの中身を空にする。

## 呼び出され方

- 契機: 利用者が `claude-dev logout` を実行したとき。
- 前提条件: なし。
- 引数: なし。

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| (なし) | - | - | - |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

### MODULE-cli-common-require-setup

- 何のために呼ぶか: 削除用の一時コンテナに使うイメージを保証するため。
- 何を渡すか: なし。
- 何を受け取るか: なし。
- **失敗したときどうなるか**: `set -e` で非0終了し、認証は消えない。

### MODULE-cli-common-container-exists

- 何のために呼ぶか: 削除対象のコンテナ(停止中を含む)を特定するため。
- 何を渡すか: コンテナ名。
- 何を受け取るか: 終了ステータス。
- **失敗したときどうなるか**: 「存在しない」と判定され、削除がスキップされる。残骸が残るが後続の
  `rm -rf` は共有ボリュームを空にするので認証は消える。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 0 |
| 永続化 | 共有ボリューム `claude-dev-auth` の中身(claude の `.credentials.json` / `.claude.json` と codex の `codex/auth.json`)を削除する |
| 発火するイベント | なし |
| ログ | 標準出力へ削除結果 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 稼働中コンテナがある | 先に `rm -f` で強制削除してから認証を消す(作業中のセッションは失われる) | 利用者のセッションが切れる |
| ボリュームが存在しない | `docker run` がボリュームを自動作成し、空のまま終わる | なし |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | claude と codex を個別に消す分岐を作らない(同一ボリュームに同居させた D0-auth-01 の帰結) | D0-auth-01 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| codex だけ・claude だけのログアウトができない | 片方だけ消したい場合は手作業になる | なし |

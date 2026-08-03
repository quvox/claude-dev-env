---
target: docs/03-impl/relations/MODULE-cli-attach.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
id: MODULE-cli-attach
module: MOD-cli-attach
kind: tool
sync: sync
impl: claude-dev::main#attach, claude-dev-mac::main#attach
callers: なし
callees: MODULE-cli-common-container-name, MODULE-cli-common-is-running, MODULE-cli-common-require-setup, MODULE-cli-common-resolve-container-user
contracts: なし
design: DSN-mod-01, DSN-mod-02
requirements: FR-env-01
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: 実行中コンテナの tmux セッションに接続する
---

# MODULE-cli-attach セッションへの再接続

## 目的

起動済みのセッションへ入り直す最短経路を提供する(FR-env-01)。`start` の再接続経路と違い、
コンテナの作成・設定は一切行わない。

## 処理の流れ

1. `MODULE-cli-common-require-setup` でイメージをそろえる。
2. `MODULE-cli-common-container-name` で対象コンテナ名を決める(引数 `NAME` があればそちらを使う)。
3. `MODULE-cli-common-is-running` で稼働を確認する。未起動なら日本語エラーを出して `exit 1`。
4. `MODULE-cli-common-resolve-container-user` で exec に使うユーザを解決する。
5. `docker exec -it -u <user> <name> tmux attach -t main` を実行する。

## 呼び出され方

- 契機: 利用者が `claude-dev attach [NAME]` を実行したとき。
- 前提条件: 対象コンテナが稼働中で、`main` tmux セッションが存在すること。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `NAME` | 文字列 | 任意 | 省略時はカレントディレクトリ由来のコンテナ名 |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

### MODULE-cli-common-require-setup

- 何のために呼ぶか: イメージ前提を満たすため。
- 何を渡すか: なし。 / 何を受け取るか: なし。
- **失敗したときどうなるか**: `set -e` で非0終了し、attach しない。

### MODULE-cli-common-container-name

- 何のために呼ぶか: 対象コンテナ名を決めるため。
- 何を渡すか: なし(カレントディレクトリ)。 / 何を受け取るか: コンテナ名。
- **失敗したときどうなるか**: 想定されない(純粋な文字列変換)。

### MODULE-cli-common-is-running

- 何のために呼ぶか: 未起動での exec を避けるため。
- 何を渡すか: コンテナ名。 / 何を受け取るか: 終了ステータス。
- **失敗したときどうなるか**: 非稼働と判定され、日本語エラーを出して `exit 1` する。

### MODULE-cli-common-resolve-container-user

- 何のために呼ぶか: `docker exec -u` に渡すユーザを決めるため。
- 何を渡すか: コンテナ名。 / 何を受け取るか: ユーザ名。
- **失敗したときどうなるか**: `CUSER` にフォールバックする。それも合わなければ `docker exec` が
  `unable to find user` で失敗し非0終了する。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | `tmux attach` の終了ステータス |
| 永続化 | なし |
| 発火するイベント | なし |
| ログ | なし(tmux の画面がそのまま端末に出る) |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| コンテナが未起動 | 「コンテナが起動していません」旨の日本語メッセージを出し `exit 1` | 利用者は `claude-dev start` を実行する |
| `main` セッションが無い | `tmux attach` が「no sessions」で失敗し非0終了する | `start` 経由なら自動生成される |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | セッション不在時に自動生成しない(生成は `start` の責務。attach は読み取り専用の入口に保つ) | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| `main` セッションが無いと失敗する | `start` を経由しない起動をした場合に手当てが要る | なし |

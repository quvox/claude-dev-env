---
id: MODULE-cli-ssh-keys-select
module: MOD-cli-ssh-keys
kind: tool
sync: sync
impl: claude-dev::main#ssh-keys.select, claude-dev-mac::main#ssh-keys.select
callers: なし
callees: MODULE-cli-common-select-ssh-keys
contracts: なし
design: DSN-mod-01, DSN-mod-02
requirements: FR-env-04
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: 使う SSH 鍵を対話選択して .claude-dev.yaml に保存する
---

# MODULE-cli-ssh-keys-select SSH 鍵の選択

## 目的

このプロジェクトでコンテナへ見せる鍵を選び直す(FR-env-04)。`start` の初回にも同じ選択 UI が
呼ばれるが、こちらは任意のタイミングでやり直すための入口である。

## 処理の流れ

1. `MODULE-cli-common-select-ssh-keys` を呼ぶ。
2. 以上(この分岐は選択 UI の呼び出しだけを行う)。

## 呼び出され方

- 契機: 利用者が `claude-dev ssh-keys` または `claude-dev ssh-keys select` を実行したとき。
- 前提条件: 標準入力が対話可能であること(非 TTY では 0 件選択になる)。
- 引数: なし。

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| (なし) | - | - | 対象は `$(pwd)/.claude-dev.yaml` |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

### MODULE-cli-common-select-ssh-keys

- 何のために呼ぶか: 鍵の列挙・対話選択・保存をまとめて行うため。
- 何を渡すか: なし(カレントディレクトリと `~/.ssh` を見る)。
- 何を受け取るか: なし(`.claude-dev.yaml` が更新され、`SSH_KEY_LIST` が設定される)。
- **失敗したときどうなるか**: 書き込み失敗は `set -e` で伝播し、非0終了する。鍵が0件のときは
  警告を出して空の `ssh_keys:` を書き、正常終了する。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 0 |
| 永続化 | `$(pwd)/.claude-dev.yaml`(`MODULE-cli-common-write-project-ssh-keys` が全面上書きする) |
| 発火するイベント | なし |
| ログ | 鍵一覧と保存結果(連携先が出力する) |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| `~/.ssh` に鍵が無い | 警告を出し空の `ssh_keys:` を保存して 0 で終わる | SSH 転送なしになる |
| 稼働中のコンテナがある | 選択結果は次回 `start` から反映される(稼働中セッションには影響しない) | 反映には `stop` → `start` が要る |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 選択後に稼働中コンテナへ再適用しない(agent の入れ替えはコンテナ再作成が要るため) | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 変更が稼働中セッションへ即時反映されない | `stop` → `start` が必要 | なし |

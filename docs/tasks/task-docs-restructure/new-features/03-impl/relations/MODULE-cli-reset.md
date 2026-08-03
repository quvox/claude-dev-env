---
target: docs/03-impl/relations/MODULE-cli-reset.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
id: MODULE-cli-reset
module: MOD-cli-reset
kind: tool
sync: sync
impl: claude-dev::main#reset, claude-dev-mac::main#reset
callers: なし
callees: なし
contracts: なし
design: DSN-mod-01, DSN-mod-02
requirements: FR-env-01, FR-env-03
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: コンテナ・ボリューム・イメージを全削除して初期状態へ戻す
---

# MODULE-cli-reset 全リセット

## 目的

環境を作り直したいときに、本システムが作った Docker 資源をまとめて消す(FR-env-01)。
認証も共有ボリュームごと消える(FR-env-03)。

## 処理の流れ

1. 削除対象を列挙して表示し、確認プロンプトを出す(同意しなければ何もしない)。
2. 全 Claude コンテナ・全 `fwd-*` コンテナ・`claude-dev-docker-proxy` を `docker rm -f` する。
3. 共有ボリューム `claude-dev-auth` / `claude-dev-history` / `claude-dev-config` と、
   `claude-dev-chrome-*` をすべて削除する。
4. docker network `claude-dev-net` を削除する。
5. イメージ `claude-dev-claude` / `claude-dev-claude-vnc` / `claude-dev-docker-proxy` を削除する。

## 呼び出され方

- 契機: 利用者が `claude-dev reset` を実行したとき。
- 前提条件: なし。
- 引数: なし。

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| (なし) | - | - | 確認プロンプトへの同意が必要 |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

連携先なし(削除処理を本分岐が直接書いており、共有関数を呼んでいない)。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 0 |
| 永続化 | **破壊的**: 全 Claude コンテナ・`fwd-*`・`claude-dev-docker-proxy` の削除、docker volume `claude-dev-auth` / `claude-dev-history` / `claude-dev-config` / `claude-dev-chrome-*` の削除、docker network `claude-dev-net` の削除、3イメージの削除 |
| 発火するイベント | なし |
| ログ | 標準出力へ削除対象の一覧と結果 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 確認プロンプトで同意しない | 何も削除せずに終了する | なし |
| 一部の削除が失敗する(使用中など) | 失敗を表示して次へ進む | 残骸が残る |
| VM モードのボリューム `claude-dev-vm-<name>` | **削除対象に含まれない** | ゲストディスクは残る |
| macOS の専用 agent / ブリッジ | **削除対象に含まれない**(掃除は `ssh-keys reset` が担う) | 残骸が残る |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 破壊的操作なので確認プロンプトを必須にする | D0-scope-02 |
| 2 | プロジェクト側の `.claude/` `.codex/` `.claude-dev.yaml` は消さない(利用者のリポジトリを触らない) | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| VM ボリュームと macOS の agent 残骸を消さない | 完全な初期化にはならない | なし |

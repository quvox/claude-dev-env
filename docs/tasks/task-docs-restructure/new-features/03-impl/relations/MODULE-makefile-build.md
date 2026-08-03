---
target: docs/03-impl/relations/MODULE-makefile-build.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
id: MODULE-makefile-build
module: MOD-makefile
kind: tool
sync: sync
impl: Makefile::build
callers: MODULE-makefile-setup
callees: MODULE-makefile-build-claude, MODULE-makefile-build-claude-vnc, MODULE-makefile-build-docker-proxy
contracts: なし
design: DSN-mod-01, DSN-dist-01
requirements: FR-env-01, FR-env-09, FR-env-12
tests: なし(未実装。Makefile のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: claude / claude-vnc / docker-proxy の全イメージをビルドする
---

# MODULE-makefile-build make build

## 目的

配布に必要な3イメージをまとめて作る(FR-env-09)。エージェント CLI の同梱もこの経路で行われる(FR-env-12)。

## 処理の流れ

1. Make の依存関係として `build-claude` `build-claude-vnc` `build-docker-proxy` を実行する
   (レシピ本体は空)。
2. `build-claude-vnc` 自身が `build-claude` に依存するため、ベース層は一度しかビルドされない。

## 呼び出され方

- 契機: 利用者が `make build` を実行したとき。
- 前提条件: リポジトリのルートで実行すること(`BASE_DIR` は Makefile の位置から解決する)。
- 引数: なし(変数で調整する場合は下表)。

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| (なし) | - | - | - |

- 認可: リポジトリを操作できるホストユーザ。

## 連携先と連携内容

### MODULE-makefile-build-claude

- 何のために呼ぶか: ベースイメージ(配布ステージ `claude-cli`)を作るため。 / 何を渡すか: なし。 / 何を受け取るか: なし。
- **失敗したときどうなるか**: make が停止し、残りのビルドは実行されない。

### MODULE-makefile-build-claude-vnc

- 何のために呼ぶか: VNC/Chrome 層を重ねたイメージを作るため。 / 何を渡すか: なし。 / 何を受け取るか: なし。
- **失敗したときどうなるか**: 同上。

### MODULE-makefile-build-docker-proxy

- 何のために呼ぶか: Docker Socket Proxy のイメージを作るため。 / 何を渡すか: なし。 / 何を受け取るか: なし。
- **失敗したときどうなるか**: 同上。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 0(前提が失敗すれば非0) |
| 永続化 | イメージ `claude-dev-claude` / `claude-dev-claude-vnc` / `claude-dev-docker-proxy` |
| 発火するイベント | なし |
| ログ | 各前提ターゲットの出力 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| いずれかのビルドが失敗 | make が停止し非0で終わる | `setup` も中断する |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | Makefile はホスト側の開発者向け入口に限定し、日常操作は `claude-dev` CLI に寄せる | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 自動テストが無い | 回帰検出は実機実行に依存する | なし |

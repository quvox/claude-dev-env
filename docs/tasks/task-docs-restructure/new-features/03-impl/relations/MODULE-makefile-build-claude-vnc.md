---
target: docs/03-impl/relations/MODULE-makefile-build-claude-vnc.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
id: MODULE-makefile-build-claude-vnc
module: MOD-makefile
kind: tool
sync: sync
impl: Makefile::build-claude-vnc
callers: MODULE-makefile-build
callees: MODULE-makefile-build-claude
contracts: なし
design: DSN-mod-01, DSN-dist-01
requirements: FR-env-01, FR-env-09, FR-env-11
tests: なし(未実装。Makefile のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: ベースイメージの上に VNC/Chrome 層を重ねてビルドする
---

# MODULE-makefile-build-claude-vnc make build-claude-vnc

## 目的

ブラウザ確認(FR-env-11)に使う VNC/noVNC/Chrome を載せたイメージを作る。

## 処理の流れ

1. 依存として `build-claude` を先に実行する(base / vnc-base 層を共有するため)。
2. `docker build -t claude-dev-claude-vnc --target claude-vnc` を同じ build-arg で実行する。

## 呼び出され方

- 契機: 利用者が `make build-claude-vnc` を実行したとき。
- 前提条件: リポジトリのルートで実行すること(`BASE_DIR` は Makefile の位置から解決する)。
- 引数: なし(変数で調整する場合は下表)。

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| (なし) | - | - | - |

- 認可: リポジトリを操作できるホストユーザ。

## 連携先と連携内容

### MODULE-makefile-build-claude

- 何のために呼ぶか: 共有する base / vnc-base 層を先に作るため(Make の依存関係)。
- 何を渡すか: なし。 / 何を受け取るか: なし。
- **失敗したときどうなるか**: make が停止し、VNC イメージはビルドされない。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 0(失敗時は非0) |
| 永続化 | イメージ `claude-dev-claude-vnc` |
| 発火するイベント | なし |
| ログ | docker build の出力 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| `build-claude` が失敗 | make が停止し VNC 層はビルドされない | `build` も中断する |
| ビルドが失敗する | docker のログを出して非0で停止する | 前のイメージが残る |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | Makefile はホスト側の開発者向け入口に限定し、日常操作は `claude-dev` CLI に寄せる | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 自動テストが無い | 回帰検出は実機実行に依存する | なし |

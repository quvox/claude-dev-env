---
target: docs/03-impl/relations/MODULE-makefile-upgrade.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
id: MODULE-makefile-upgrade
module: MOD-makefile
kind: tool
sync: sync
impl: Makefile::upgrade
callers: なし
callees: なし
contracts: なし
design: DSN-mod-01
requirements: FR-env-01, FR-env-09
tests: なし(未実装。Makefile のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: 全イメージを --no-cache で完全再ビルドする
---

# MODULE-makefile-upgrade make upgrade

## 目的

キャッシュを使わず全部作り直す(FR-env-09)。CLI 側の `MODULE-cli-upgrade` と同じ内容をホストの Make からも実行できるようにしてある。

## 処理の流れ

1. `docker build --no-cache -t claude-dev-claude --target claude-cli` を build-arg 付きで実行する。
2. 同じく `--no-cache -t claude-dev-claude-vnc --target claude-vnc` を実行する。
3. `--no-cache -t claude-dev-docker-proxy` を実行する。
4. 「実行中のコンテナは claude-dev stop → claude-dev start で反映」と案内する。

## 呼び出され方

- 契機: 利用者が `make upgrade` を実行したとき。
- 前提条件: リポジトリのルートで実行すること(`BASE_DIR` は Makefile の位置から解決する)。
- 引数: なし(変数で調整する場合は下表)。

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| (なし) | - | - | - |

- 認可: リポジトリを操作できるホストユーザ。

## 連携先と連携内容

連携先なし。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 0(ビルド失敗は非0) |
| 永続化 | 3イメージを作り直す |
| 発火するイベント | なし |
| ログ | docker build の出力 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| ビルドが失敗する | docker のログを出して make が非0で停止する | 前のイメージが残る |
| 稼働中のコンテナがある | 停止せずビルドだけ行う | `stop` → `start` まで反映されない |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | Makefile はホスト側の開発者向け入口に限定し、日常操作は `claude-dev` CLI に寄せる | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 自動テストが無い | 回帰検出は実機実行に依存する | なし |

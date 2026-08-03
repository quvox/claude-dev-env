---
target: docs/03-impl/relations/MODULE-makefile-help.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
id: MODULE-makefile-help
module: MOD-makefile
kind: tool
sync: sync
impl: Makefile::help
callers: なし
callees: なし
contracts: なし
design: DSN-mod-01
requirements: FR-env-01
tests: なし(未実装。Makefile のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: 利用可能なターゲットの一覧を表示する
---

# MODULE-makefile-help make help

## 目的

`make` の既定ターゲット。何ができるかを一覧で示す(FR-env-01 の運用補助)。

## 処理の流れ

1. `@echo` を並べてセットアップ・ビルド・メンテナンスの各ターゲットと、日常の使い方
   (`cd ~/repos/my-project && claude-dev start`)を表示する。
2. 他のターゲットは**一切実行しない**(レシピは `echo` だけで構成されている)。

## 呼び出され方

- 契機: 利用者が `make help` を実行したとき。
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
| 戻り値 | 0 |
| 永続化 | なし |
| 発火するイベント | なし |
| ログ | 標準出力へヘルプ本文 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| (異常系なし) | `echo` だけなので失敗経路が無い | - |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | Makefile はホスト側の開発者向け入口に限定し、日常操作は `claude-dev` CLI に寄せる | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 自動テストが無い | 回帰検出は実機実行に依存する | なし |
| **コールグラフに実在しない辺が出る**(この機能から `build` `setup` `clean` など12本) | make 抽出器がレシピ行の `make <target>` 文字列を再帰 make とみなすため、`@echo "  make setup ..."` という**案内文からも辺が立つ**(`.claude/scripts/cgx/make_regex.py`)。`help` のレシピは `echo` だけで他ターゲットを実行しないので、12本すべてを**棄却**した。`callgraph-check.py` の CG4 に「取りこぼし」として現れるが誤検知である | 抽出器の修正は `/kit-improve` 案件(memo.md 申し送り事項) |

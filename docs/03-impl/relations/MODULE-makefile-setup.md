---
id: MODULE-makefile-setup
module: MOD-makefile
kind: tool
sync: sync
impl: Makefile::setup
callers: なし
callees: MODULE-makefile-build, MODULE-makefile-env, MODULE-makefile-install, MODULE-makefile-network, MODULE-makefile-volumes
contracts: なし
design: DSN-mod-01
requirements: FR-env-01, FR-env-09
tests: なし(未実装。Makefile のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: env→network→volumes→build→install を順に実行する初回セットアップ
---

# MODULE-makefile-setup make setup

## 目的

初回導入の手順をひとまとめにする(FR-env-01)。個別に叩く必要をなくすのが目的。

## 処理の流れ

1. 前提ターゲット `env` `network` `volumes` `build` `install` を **Make の依存関係として**この順に実行する。
2. 完了後、次のステップ(`make login` → プロジェクトへ移動 → `claude-dev start`)を表示する。

## 呼び出され方

- 契機: 利用者が `make setup` を実行したとき。
- 前提条件: リポジトリのルートで実行すること(`BASE_DIR` は Makefile の位置から解決する)。
- 引数: なし(変数で調整する場合は下表)。

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| (なし) | - | - | - |

- 認可: リポジトリを操作できるホストユーザ。

## 連携先と連携内容

### MODULE-makefile-env

- 何のために呼ぶか: `.env` を用意するため。 / 何を渡すか: なし。 / 何を受け取るか: なし。
- **失敗したときどうなるか**: make が停止し、以降の手順は実行されない。

### MODULE-makefile-network

- 何のために呼ぶか: docker network を作るため。 / 何を渡すか: なし。 / 何を受け取るか: なし。
- **失敗したときどうなるか**: 失敗は `|| true` で握りつぶされるため停止しない。

### MODULE-makefile-volumes

- 何のために呼ぶか: 共有ボリュームを作るため。 / 何を渡すか: なし。 / 何を受け取るか: なし。
- **失敗したときどうなるか**: 同上(握りつぶす)。

### MODULE-makefile-build

- 何のために呼ぶか: 3イメージをビルドするため。 / 何を渡すか: なし。 / 何を受け取るか: なし。
- **失敗したときどうなるか**: make が停止し `install` は実行されない。

### MODULE-makefile-install

- 何のために呼ぶか: `claude-dev` を PATH へ登録するため。 / 何を渡すか: なし。 / 何を受け取るか: なし。
- **失敗したときどうなるか**: make が非0で終わる。イメージは作られたままになる。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 0(いずれかの前提が失敗すれば make が非0で中断する) |
| 永続化 | 前提ターゲットの副作用(`.env`・docker network・共有ボリューム・3イメージ・`/usr/local/bin/claude-dev` の symlink) |
| 発火するイベント | なし |
| ログ | 各前提ターゲットの出力と完了メッセージ |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| いずれかの前提が失敗 | make がそこで停止し非0で終わる。それまでの副作用は残る | 再実行すると完了済みの手順は冪等に通過する |
| `install` の `sudo` が拒否される | symlink が作られず非0終了する | `claude-dev` コマンドが PATH に入らない |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | Makefile はホスト側の開発者向け入口に限定し、日常操作は `claude-dev` CLI に寄せる | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 自動テストが無い | 回帰検出は実機実行に依存する | なし |
| **コールグラフに実在しない辺が1本出る**(`MODULE-makefile-login`) | `setup` の前提は `env network volumes build install` の5つで `login` を含まない。レシピの `@echo "  1. make login"` という案内文を make 抽出器が再帰 make とみなしたための誤検知なので**棄却**した | 抽出器の修正は `/kit-improve` 案件(memo.md 申し送り事項) |

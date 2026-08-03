---
id: MODULE-makefile-install
module: MOD-makefile
kind: tool
sync: sync
impl: Makefile::install
callers: MODULE-makefile-setup
callees: なし
contracts: なし
design: DSN-mod-01
requirements: FR-env-01, FR-env-10
tests: なし(未実装。Makefile のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: claude-dev CLI のシンボリックリンクを PATH へ登録する
---

# MODULE-makefile-install make install

## 目的

利用者コマンド名を OS によらず `claude-dev` に統一する(FR-env-10)。macOS では実体が `claude-dev-mac` になる。

## 処理の流れ

1. `chmod +x "$(CLI)"` で実行権限を付ける。`CLI` は `uname -s` が `Darwin` なら
   `claude-dev-mac`、それ以外は `claude-dev`。
2. `sudo ln -sf "$(CLI)" /usr/local/bin/claude-dev` で symlink を張る。
3. 「どの OS でも claude-dev コマンドで実行」と案内する。

## 呼び出され方

- 契機: 利用者が `make install` を実行したとき。
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
| 永続化 | `/usr/local/bin/claude-dev` の symlink(既存があれば `-f` で置き換える) |
| 発火するイベント | なし |
| ログ | インストール結果 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| `sudo` が使えない/拒否される | `ln` が失敗し make が非0で停止する | 手動で symlink を張る必要がある |
| `/usr/local/bin` が無い | `ln` が失敗する | 同上 |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | Makefile はホスト側の開発者向け入口に限定し、日常操作は `claude-dev` CLI に寄せる | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 自動テストが無い | 回帰検出は実機実行に依存する | なし |

---
id: MODULE-cli-login
module: MOD-cli-login
kind: tool
sync: sync
impl: claude-dev::main#login, claude-dev-mac::main#login
callers: なし
callees: MODULE-cli-common-ensure-infrastructure, MODULE-cli-common-require-setup
contracts: CTR-cli-container
design: DSN-mod-01, DSN-mod-02, DSN-auth-01
requirements: FR-env-03
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: Claude の OAuth ログインをコンテナ内で実行し共有ボリュームへ保存する
---

# MODULE-cli-login Claude 認証の取得

## 目的

ホストのクレデンシャルをコンテナへ渡す経路を作らずに Claude の認証を得る(FR-env-03)。
認証は使い捨ての一時コンテナ内で取得し、共有ボリューム `claude-dev-auth` にだけ残す
(DSN-auth-01)。

## 処理の流れ

1. `MODULE-cli-common-require-setup` でイメージをそろえる。
2. `MODULE-cli-common-ensure-infrastructure` でネットワークと共有ボリュームを用意する。
3. `docker run --rm -it --entrypoint bash` で一時コンテナを起動し、`claude-dev-auth` を
   `~/.claude-shared` へマウントする(`TERM` / `LANG` も渡す)。
4. コンテナ内 root が `settings.json` 未存在時に
   `{"permissions":{"defaultMode":"bypassPermissions"},"model":"sonnet"}` を生成して `chown` する
   (この設定は共有しない)。
5. `su` でコンテナユーザへ切り替え、共有ボリュームの `.credentials.json` / `.claude.json` を
   `~/.claude/` へコピーし、`~/.claude.json` をリンクする。
6. `claude` を対話起動する(利用者がブラウザで OAuth を完了させる)。
7. 終了後、`~/.claude/` の認証を `~/.claude-shared/` へ書き戻す。

## 呼び出され方

- 契機: 利用者が `claude-dev login` を実行したとき。
- 前提条件: 端末が対話可能(`-it`)であること。
- 引数: なし。

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| (なし) | - | - | - |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

### MODULE-cli-common-require-setup

- 何のために呼ぶか: 一時コンテナに使うイメージが存在することを保証するため。
- 何を渡すか: なし(定数を参照する)。
- 何を受け取るか: なし(不足時はビルドされる)。
- **失敗したときどうなるか**: `docker build` の失敗が `set -e` で伝播し、ログインは行われず非0終了する。

### MODULE-cli-common-ensure-infrastructure

- 何のために呼ぶか: マウント元の共有ボリューム `claude-dev-auth` を確実に存在させるため。
- 何を渡すか: なし。
- 何を受け取るか: なし(常に 0)。
- **失敗したときどうなるか**: 失敗は握りつぶされる。ボリュームが無いまま進むと `docker run` が
  ボリュームを自動作成するため、観測される破壊は無い。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | `claude` の対話終了後 0 |
| 永続化 | 共有ボリューム `claude-dev-auth` 直下の `.credentials.json` / `.claude.json` |
| 発火するイベント | なし |
| ログ | 標準出力へ手順案内。`claude` の対話出力はそのまま端末に出る |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| OAuth を完了せず終了 | 書き戻す認証が無く、共有ボリュームは変化しない | 次回の `start` は未ログイン状態で起動する |
| 非 TTY で実行 | `docker run -it` が「the input device is not a TTY」で失敗し非0終了する | ログインできない |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | `-c '...'` の内側でシングルクォートが使えないため、JSON は root 部で `\"` エスケープした二重引用符で生成する | D0-scope-02 |
| 2 | ホストの `~/.claude/.credentials.json` は読み込まない(ホストのクレデンシャルをコンテナへ渡す経路を作らない) | D0-auth-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| ホストでログイン済みでも初回一度は本コマンドが必要 | 手間が増えるが、意図した安全側の設計 | なし |

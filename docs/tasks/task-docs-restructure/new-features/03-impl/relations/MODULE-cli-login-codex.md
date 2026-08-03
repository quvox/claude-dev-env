---
target: docs/03-impl/relations/MODULE-cli-login-codex.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
id: MODULE-cli-login-codex
module: MOD-cli-login-codex
kind: tool
sync: sync
impl: claude-dev::main#login-codex, claude-dev-mac::main#login-codex
callers: なし
callees: MODULE-cli-common-ensure-infrastructure, MODULE-cli-common-require-setup
contracts: CTR-cli-container
design: DSN-mod-01, DSN-mod-02, DSN-auth-01, DSN-dist-02
requirements: FR-env-03, FR-env-12
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: Codex のデバイス認証を実行し認証情報を共有ボリュームの codex/ へ置く
---

# MODULE-cli-login-codex Codex 認証の取得

## 目的

同梱の Codex CLI を使えるようにするための認証を、Claude と同じ「一時コンテナで取得して
共有ボリュームへ置く」方式で得る(FR-env-03・FR-env-12)。Codex 認証は専用ボリュームを
作らず `claude-dev-auth` の `codex/` サブディレクトリへ相乗りさせる(DSN-auth-01)。

## 処理の流れ

1. `MODULE-cli-common-require-setup` → `MODULE-cli-common-ensure-infrastructure`。
2. `login` と同型の一時コンテナ(`--rm -it --entrypoint bash`、`claude-dev-auth` を
   `~/.claude-shared` へ)を起動する。
3. root が `~/.claude-shared/codex/` を `mkdir -p` し、**`chown -R` で所有権をコンテナユーザへ戻す**
   (entrypoint の同期ループが root で書き戻すため共有側が root 所有になりうる。戻さないと後続の
   ユーザー権限コピーが失敗する)。
4. コンテナ内の `~/.codex` を作り直す。
5. `su` でユーザへ切り替え、共有側に `codex/auth.json` があれば `~/.codex/` へコピーする(`chmod 600`)。
6. `codex login --device-auth` を対話起動する。表示された URL と認証コードを利用者がブラウザで開く
   (Linux 版は「手元の PC」と案内、mac 版はローカルブラウザ前提の文言)。
7. 終了後、`~/.codex/auth.json` を `~/.claude-shared/codex/` へ書き戻す(`chmod 600`)。

## 呼び出され方

- 契機: 利用者が `claude-dev login-codex` を実行したとき。
- 前提条件: 端末が対話可能であること。
- 引数: なし。

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| (なし) | - | - | - |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

### MODULE-cli-common-require-setup

- 何のために呼ぶか: 一時コンテナのイメージを保証するため。
- 何を渡すか: なし。
- 何を受け取るか: なし。
- **失敗したときどうなるか**: `set -e` で非0終了し、認証は行われない。

### MODULE-cli-common-ensure-infrastructure

- 何のために呼ぶか: `claude-dev-auth` を存在させるため。
- 何を渡すか: なし。
- 何を受け取るか: なし。
- **失敗したときどうなるか**: 握りつぶされ、`docker run` のボリューム自動作成で吸収される。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | `codex` の対話終了後 0 |
| 永続化 | 共有ボリューム `claude-dev-auth` の `codex/auth.json`(`chmod 600`)。所有権をコンテナユーザへ戻す `chown -R` も行う |
| 発火するイベント | なし |
| ログ | 標準出力へ手順案内。`codex login --device-auth` の URL と認証コードが端末に出る |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| デバイス認証を完了せず終了 | 書き戻す `auth.json` が無く、共有ボリュームは変化しない | 未ログインのまま。`start` は codex 認証をコピーせずに起動する |
| 共有側 `codex/` が root 所有のまま | 手順3の `chown -R` で修復してから進む | なし |
| 非 TTY で実行 | `docker run -it` が失敗し非0終了する | 認証できない |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | codex 認証を専用ボリュームにせず `claude-dev-auth` の `codex/` へ相乗りさせる(`logout` / `reset` の分岐を増やさない) | D0-auth-01 |
| 2 | `-c '...'` の内側でシングルクォートを使わない(`login` と同じクォート制約) | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| デバイス認証の対話はブラウザ操作を伴うため無人化できない | 自動テスト不可。`start` によるコピー経路と同期は `scripts/e2e6-codex.sh` が判定する | なし |

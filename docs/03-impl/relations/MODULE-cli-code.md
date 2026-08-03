---
id: MODULE-cli-code
module: MOD-cli-code
kind: tool
sync: sync
impl: claude-dev::main#code, claude-dev-mac::main#code
callers: なし
callees: MODULE-cli-common-container-name, MODULE-cli-common-is-running, MODULE-cli-common-require-setup, MODULE-cli-common-resolve-container-user
contracts: なし
design: DSN-mod-01, DSN-mod-02
requirements: FR-env-01, FR-env-08, FR-env-12
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: 新しい tmux ウィンドウで Claude Code を起動する
---

# MODULE-cli-code 追加ウィンドウでの Claude Code 起動

## 目的

稼働中セッションに Claude Code をもう1つ立てる(FR-env-01・FR-env-12)。VM モードで
起動しているときは、ゲスト Docker を使うための導線をシステムプロンプトで注入する(FR-env-08)。

## 処理の流れ

1. `MODULE-cli-common-require-setup` → `MODULE-cli-common-container-name` →
   `MODULE-cli-common-is-running`(未起動なら日本語エラーで `exit 1`)。
2. `MODULE-cli-common-resolve-container-user` で exec ユーザを解決する。
3. **Linux 版のみ**: コンテナ内の `CLAUDE_DEV_VM` を `printenv` で確認し、`1` なら
   `claude --append-system-prompt "..."` を起動コマンドにする(docker はゲスト daemon 指定・
   bind source は `/workspace` 配下のみ・`/workspace/VM_DEV.md` 参照、という VM 導線)。
   `1` でなければ `claude` をそのまま使う。
4. **macOS 版**: VM モード非対応のため判定も注入も行わず、常に `claude` を使う。
5. `docker exec -it -u <user> <name> tmux new-window -t main "<claude cmd>"` を実行し、続けて
   `tmux attach -t main` する。

## 呼び出され方

- 契機: 利用者が `claude-dev code` を実行したとき。
- 前提条件: 対象コンテナが稼働中であること。
- 引数: なし。

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| (なし) | - | - | 対象はカレントディレクトリ由来のコンテナ |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

### MODULE-cli-common-require-setup

- 何のために呼ぶか: イメージ前提を満たすため。 / 何を渡すか: なし。 / 何を受け取るか: なし。
- **失敗したときどうなるか**: `set -e` で非0終了する。

### MODULE-cli-common-container-name

- 何のために呼ぶか: 対象コンテナ名の決定。 / 何を渡すか: なし。 / 何を受け取るか: コンテナ名。
- **失敗したときどうなるか**: 想定されない。

### MODULE-cli-common-is-running

- 何のために呼ぶか: 未起動での exec を避けるため。 / 何を渡すか: コンテナ名。 / 何を受け取るか: 終了ステータス。
- **失敗したときどうなるか**: 日本語エラーを出して `exit 1`。

### MODULE-cli-common-resolve-container-user

- 何のために呼ぶか: exec ユーザの決定。 / 何を渡すか: コンテナ名。 / 何を受け取るか: ユーザ名。
- **失敗したときどうなるか**: `CUSER` へフォールバックし、合わなければ exec が失敗する。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | `tmux attach` の終了ステータス |
| 永続化 | なし(tmux ウィンドウはコンテナ内の揮発状態) |
| 発火するイベント | なし |
| ログ | なし |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| コンテナが未起動 | 日本語エラーを出して `exit 1` | 利用者は `start` する |
| `main` セッションが無い | `tmux new-window -t main` が失敗し非0終了する | `start` 経由での起動が必要 |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | VM 導線をシステムプロンプト注入で渡す(コンテナ内の設定ファイルを書き換えない) | D0-scope-02 |
| 2 | macOS 版は VM 判定を持たない(VM モード自体が非対応) | D0-scope-03 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| VM 導線の文面がスクリプトに直書き | 文面変更に CLI の改修が要る | なし |

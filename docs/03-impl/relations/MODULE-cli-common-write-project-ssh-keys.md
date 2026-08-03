---
id: MODULE-cli-common-write-project-ssh-keys
module: MOD-cli-common
kind: function-call
sync: sync
impl: claude-dev::write_project_ssh_keys, claude-dev-mac::write_project_ssh_keys
callers: MODULE-cli-common-select-ssh-keys, MODULE-cli-start
callees: なし
contracts: なし
design: DSN-mod-01, DSN-mod-02
requirements: FR-env-04
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: 選択した鍵を .claude-dev.yaml へ書き出す
---

# MODULE-cli-common-write-project-ssh-keys プロジェクト設定の書き出し

## 目的

「このプロジェクトで転送する鍵」の唯一の記録先である `.claude-dev.yaml` を生成する
(FR-env-04)。書式を決めているのはこの機能であり、読み取り側(`_parse_ssh_keys_yaml`)は
ここが出す書式に依存している。

## 処理の流れ

1. 第1引数を書き出し先パスとして受け取り、残りの引数を鍵パスの並びとして扱う。
2. 次の内容を**上書き**で書き出す(`> "$file"`):
   - `# claude-dev プロジェクト設定(このプロジェクトで使う SSH 鍵。claude-dev が管理します)`
   - `# 再選択は 'claude-dev ssh-keys'、初期化は 'claude-dev ssh-keys reset'`
   - `ssh_keys:`
   - 各鍵について `  - <パス>`(0 件なら行を出さない = 空のセクション)

## 呼び出され方

- 契機: 鍵選択の確定時(`MODULE-cli-common-select-ssh-keys`)、および非 TTY で
  `.claude-dev.yaml` を空作成するとき(`ensure_project_config`。`MODULE-cli-start` に畳み込み)。
- 前提条件: 書き出し先ディレクトリに書き込み権限があること。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `$1` | 文字列 | 必須 | 書き出し先のファイルパス |
| `$2...` | 文字列の並び | 任意 | 鍵の絶対パス。0 件可 |

- 認可: CLI を実行できるホストユーザ。

## 連携先と連携内容

連携先なし。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | なし |
| 永続化 | プロジェクト直下の `.claude-dev.yaml` を**全面上書き**する。書式(`ssh_keys:` と `  - <path>`)はこの機能が決め、`_parse_ssh_keys_yaml` がそれに依存する |
| 発火するイベント | なし |
| ログ | なし(メッセージは呼び出し元が出す) |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 書き込み権限が無い | リダイレクトが失敗し `set -e` でスクリプト全体が非0終了する | サブコマンドが中断する |
| 既存の `.claude-dev.yaml` に他のキーがある | **全面上書きで失われる**(このファイルは CLI の所有物という前提) | 他キーを足す運用は現状できない |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 追記ではなく全面上書きにする(`.claude-dev.yaml` は CLI が所有し `ssh_keys` しか持たない前提) | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| `ssh_keys` 以外のキーを保持できない | 将来キーを増やすなら本機能と `_parse_ssh_keys_yaml`、`ssh-keys reset` の行削除処理を同時に直す必要がある | `docs/issues/002-modify-claude-dev-yaml-is-overwritten-wholesale.md` |

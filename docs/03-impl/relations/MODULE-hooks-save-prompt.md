---
id: MODULE-hooks-save-prompt
module: MOD-hooks
kind: tool
sync: sync
impl: scripts/save_prompt.sh::main
callers: なし
callees: なし
contracts: なし
design: DSN-mod-01, DSN-mod-03
requirements: FR-orch-07, NFR-ops-01
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: Claude Code フックから渡されたプロンプトを一時ファイルへ保存する
---

# MODULE-hooks-save-prompt プロンプトの保存

## 目的

Slack 通知(FR-orch-07)の本文に「直前にユーザが入力したプロンプト」を含められるようにする。
hook の入力からプロンプト先頭を取り出し、セッション別の一時ファイルへ置くのがこの機能の役割で、
通知側(`MODULE-hooks-send-slack-message`)とはファイル経由で疎結合にしてある。

## 処理の流れ

1. `cat` で標準入力(hook が渡す JSON)を全部読む。
2. `python3` で JSON をパースし、`session_id`(既定 `unknown`)と `prompt` の先頭30文字を取り出す。
   パースに失敗したら `session_id=unknown` / プロンプト空文字へフォールバックする
   (`2>/dev/null || echo`)。
3. `/tmp/claude_prompt_<session_id>.txt` へ `echo` で**上書き**保存する(追記ではない)。

## 呼び出され方

- 契機: Claude Code の hook 機構から呼ばれたとき(どのイベントで呼ぶかはコンテナ内
  `settings.json` の `hooks` が決める。配線は `MODULE-cli-start` がホストの
  `~/.claude/settings.json` から抽出し、entrypoint がマージする)。
- 前提条件: イメージに同梱され `/usr/local/bin/save_prompt.sh` として実行できること。
- 引数: なし(入力は標準入力の JSON)。

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| stdin | JSON | 必須 | `{"session_id": <str>, "prompt": <str>, ...}` |

- 認可: コンテナ内のユーザ(Claude Code のプロセス)。

## 連携先と連携内容

連携先なし。`MODULE-hooks-send-slack-message` との受け渡しは一時ファイル経由で、呼び出し関係は無い。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 0 |
| 永続化 | **`/tmp/claude_prompt_<session_id>.txt`**(プロンプト先頭30文字。上書き)。**この書式をこの機能が決め、`MODULE-hooks-send-slack-message` が読んで依存する** |
| 発火するイベント | なし |
| ログ | なし |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| JSON のパースに失敗 | `session_id=unknown` / プロンプト空文字で続行し、ファイルは作られる | 通知本文が `(no prompt)` になる |
| `session_id` が無い | `unknown` を使う | 複数セッションで同じファイルを共有してしまう |
| `/tmp` へ書けない | `echo` のリダイレクトが失敗する | 通知本文が `(no prompt)` になる |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 通知側とプロセス間で状態を共有せず、`session_id` をキーにした一時ファイルで疎結合にする | D0-scope-02 |
| 2 | 保存するのは先頭30文字だけにする(通知本文の識別用途に限る) | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 一時ファイルを削除しない | セッションごとに増える(`/tmp` 上なので無害) | なし |
| 抽出ツールが `python3`(通知側は `jq`)で統一されていない | 保守上の一貫性が無い | なし |

---
target: docs/03-impl/relations/MODULE-hooks-send-slack-message.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
id: MODULE-hooks-send-slack-message
module: MOD-hooks
kind: tool
sync: sync
impl: scripts/sendslackmsg.sh::main
callers: なし
callees: なし
contracts: なし
design: DSN-mod-01, DSN-mod-03
requirements: FR-orch-07, NFR-ops-01
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: Claude Code フックの通知をプロンプト文脈つきで Slack へ送る
---

# MODULE-hooks-send-slack-message Slack 通知(フック)

## 目的

Claude Code の節目(停止・通知イベント)を Slack へ知らせる(FR-orch-07)。
`MODULE-hooks-save-prompt` が置いたプロンプト文脈を本文に添えることで、どのセッションの
通知かが分かるようにしている。

## 処理の流れ

1. `SLACK_BOT_TOKEN` が未設定なら何もせず `exit 0`(これが通知の無効化手段になる)。
2. 標準入力の JSON が**サブエージェント由来**なら何もせず `exit 0`。判定は `jq` で
   `agent_id` が非空、または `hook_event_name == "SubagentStop"` のいずれか。本体エージェントは
   `Stop`、サブエージェントは `SubagentStop` で発火し、サブエージェント文脈では stdin JSON に
   `agent_id` が入る。これにより `Stop` / `Notification` のどちらから呼ばれてもサブエージェント
   由来の通知は送らない。
3. 通知先は `SLACK_CHANNEL`(未設定時は既定 `U5SJG0XEK`)。
4. 第1引数 `$1` を本文の接頭辞 `MSG` とする(未指定なら空)。
5. 標準入力の JSON から `jq -r '.session_id // "unknown"'` で `session_id` を取り出す。
6. `/tmp/claude_prompt_<session_id>.txt` を読む。無い、または空なら `(no prompt)` とする。
7. `jq -n` で `{channel, text: "<MSG> 「<PROMPT>...」"}` を組み立て、
   `Authorization: Bearer <TOKEN>` と `Content-Type: application/json; charset=utf-8` を付けて
   `https://slack.com/api/chat.postMessage` へ `curl -sS -X POST` する。
8. POST の失敗・API エラーは握りつぶす(`|| true`。標準出力/エラーは破棄)。

## 呼び出され方

- 契機: Claude Code の hook 機構から呼ばれたとき(`Stop` / `Notification` など。配線は
  コンテナ内 `settings.json` の `hooks`)。
- 前提条件: `SLACK_BOT_TOKEN` が `settings.json` の `env` 経由で渡っていること。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `$1` | 文字列 | 任意 | 通知本文の接頭辞。未指定なら空 |
| stdin | JSON | 必須 | `{"session_id": <str>, "agent_id"?: <str>, "hook_event_name"?: <str>}` |

- 認可: コンテナ内のユーザ(Claude Code のプロセス)。

## 連携先と連携内容

連携先なし。Slack API への POST は外部システムへの呼び出しで、機能間の辺には現れない。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 常に 0(失敗も握りつぶす) |
| 永続化 | なし。**読む資源は `/tmp/claude_prompt_<session_id>.txt`**(書式の持ち主は `MODULE-hooks-save-prompt`。先頭30文字のプレーンテキストという前提に依存している) |
| 発火するイベント | Slack チャンネルへのメッセージ投稿 |
| ログ | なし(POST の出力は破棄する) |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| `SLACK_BOT_TOKEN` 未設定 | 何もせず `exit 0` | 通知が無効になる(意図した無効化手段) |
| サブエージェント由来の発火 | 何もせず `exit 0` | 通知が二重に飛ばない |
| プロンプト一時ファイルが無い / 空 | 本文を `(no prompt)` として通知を続ける | 文脈なしで届く |
| Slack への POST 失敗 / API エラー | 握りつぶす。ログも残さない | Claude の本処理は妨げない。**失敗に気づけない** |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 通知失敗を非致命として握りつぶす(hook の失敗が Claude の作業を止めないようにする) | D0-orch-07 |
| 2 | サブエージェント由来を除外する(1回の作業で通知が何度も飛ぶのを防ぐ) | D0-orch-07 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| POST 失敗をログに残さない | 届かないときの切り分けが難しい(コンテナ `settings.json` のマージ・トークン権限・一時ファイルの有無を順に見るしかない) | なし |
| 既定チャンネル ID がスクリプトに直書き | 設定漏れのとき意図しない宛先へ送りうる | なし |
| 本文に載るプロンプトは先頭30文字のみ | 識別用途に限られる | なし |

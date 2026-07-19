---
id: hooks
layer: impl
title: hooks 実装説明書
version: 1.1.0
updated: 2026-07-20
verified:
  at: 2026-07-20
  version: 1.1.0
  against:
    - doc: docs/02-design/system.md
      version: 1.2.0
summary: >
  Claude Code のフックスクリプト2種。save_prompt.sh が hook 入力 JSON から直近プロンプトを
  一時ファイルへ保存し、sendslackmsg.sh がそれを本文に添えて Slack へ通知する。両者はイメージに
  焼き込まれ、cli 経由でホスト settings の hooks/env がコンテナの settings.json へ配線される。
keywords: [hooks, Claude Code フック, Slack通知, save_prompt, sendslackmsg, settings.json]
depends_on: []
source:
  - docs/02-design/system.md
---

# 実装説明書:hooks

## 概要

Claude Code の hook 機構から呼ばれる 2 つのシェルスクリプトで構成する（上流: [全体設計](../02-design/system.md) の分割定義 `hooks` 行、orchestration/18）。`save_prompt.sh` は Claude Code が hook に渡す JSON を標準入力で受け、`session_id` とプロンプト先頭を `/tmp/claude_prompt_<session_id>.txt` に保存する。`sendslackmsg.sh` は同ファイルを読み、引数のメッセージとプロンプト文脈を添えて Slack へ POST する。両スクリプトはイメージビルド時に `/usr/local/bin/` へ焼き込まれ、どの hook イベントで何を実行するか（`hooks`）と Slack 認証（`env`）の登録は、ホストの `~/.claude/settings.json` を `cli`（`claude-dev start`）が抽出しコンテナの `settings.json` へ配線することで行う。

## ファイル構成

| パス | 役割 |
|---|---|
| scripts/save_prompt.sh | Claude Code hook: 直近プロンプトを一時ファイルへ保存 |
| scripts/sendslackmsg.sh | Claude Code hook: プロンプト文脈つき Slack 通知 |

いずれもイメージに焼き込まれ、コンテナ内では `/usr/local/bin/save_prompt.sh` / `/usr/local/bin/sendslackmsg.sh` として実行可能（`.devcontainer/Dockerfile.claude`。詳細は [03-impl/devcontainer.md](devcontainer.md)）。

## モジュール別実装詳細

### save_prompt.sh（scripts/save_prompt.sh）

- **責務:** Slack 通知が「直前にユーザーが入力したプロンプト」を本文に含められるよう、hook 入力からプロンプト先頭をセッション別の一時ファイルに保存する。
- **公開インターフェース:**

```
save_prompt.sh            # 引数なし。hook の JSON を標準入力から受ける
  stdin:  {"session_id": <str>, "prompt": <str>, ...}
  出力:   /tmp/claude_prompt_<session_id>.txt（プロンプト先頭30文字を上書き）
```

- **処理の要点:**
  - `cat` で標準入力を全読み。
  - `python3` で JSON をパースし、`session_id`（既定 `unknown`）と `prompt` の先頭 30 文字を抽出。パース失敗時は `session_id=unknown` / プロンプト空文字へフォールバック（`2>/dev/null || echo`）。
  - `/tmp/claude_prompt_<session_id>.txt` へ `echo` で上書き保存（追記ではない）。
- **実装上の判断:** JSON 抽出に `python3` を用いる（`sendslackmsg.sh` 側は `jq`。両ツールともイメージに導入済み）。

### sendslackmsg.sh（scripts/sendslackmsg.sh）

- **責務:** Claude Code の特定 hook イベント発生時に、`save_prompt.sh` が保存したプロンプト文脈を添えて Slack へ通知する。ただし通知するのは本体（メイン）エージェント由来の発火に限り、サブエージェント（Task＝バックグラウンド）由来では通知しない。
- **公開インターフェース:**

```
sendslackmsg.sh "<MSG>"   # $1: 通知本文の接頭辞。hook の JSON を標準入力から受ける
  stdin:  {"session_id": <str>, ...}
  副作用: Slack chat.postMessage へ POST
```

- **処理の要点:**
  - `SLACK_BOT_TOKEN` が未設定なら何もせず `exit 0`（通知を無効化できる）。
  - 標準入力の JSON がサブエージェント（Task＝バックグラウンド）由来なら何もせず `exit 0`。判定は `jq` で `agent_id` が非空、または `hook_event_name == "SubagentStop"` のいずれか。本体エージェントは `Stop`、サブエージェントは `SubagentStop` で発火し、サブエージェント文脈では stdin JSON に `agent_id` が入る。これにより `Stop`/`Notification` いずれのフックから呼ばれても、サブエージェント由来の通知は送らない。
  - 通知先チャンネルは `SLACK_CHANNEL`（未設定時は既定 `U5SJG0XEK`）。
  - 第 1 引数 `$1` を本文接頭辞 `MSG` とする（未指定時は空）。
  - 標準入力の JSON から `jq -r '.session_id // "unknown"'` で `session_id` を抽出。
  - `/tmp/claude_prompt_<session_id>.txt` を読む。無ければ／空なら `(no prompt)`。
  - `jq -n` で `{channel, text: "<MSG> 「<PROMPT>...」"}` を組み立て、`Authorization: Bearer <TOKEN>` と `Content-Type: application/json; charset=utf-8` を付けて `https://slack.com/api/chat.postMessage` へ `curl -sS -X POST`。
  - 通知は非致命扱い：POST の失敗・API エラーは握りつぶす（`|| true`、標準出力/エラーは破棄）。
- **実装上の判断:** `save_prompt.sh` と `sendslackmsg.sh` の連携は `session_id` をキーにした一時ファイル受け渡しで疎結合にしている（プロセス間で状態を共有しない）。

## データアクセス

| データ | 操作 | 実施モジュール | 備考 |
|---|---|---|---|
| /tmp/claude_prompt_<session_id>.txt | 書込（上書き） | save_prompt.sh | セッション別。プロンプト先頭30文字 |
| /tmp/claude_prompt_<session_id>.txt | 読取 | sendslackmsg.sh | 不在/空なら `(no prompt)` |

## 設定・環境変数

| 名前 | 用途 | デフォルト | 必須 |
|---|---|---|---|
| SLACK_BOT_TOKEN | Slack Bot トークン。未設定なら sendslackmsg.sh は何もせず終了 | （なし） | 必須（Slack 通知を使う場合） |
| SLACK_CHANNEL | 通知先チャンネル/ユーザー ID | U5SJG0XEK | 任意 |

配線経路：ホストの `~/.claude/settings.json` の `env`（Slack 認証）と `hooks`（どのイベントで `sendslackmsg.sh`/`save_prompt.sh` を実行するか）を、`claude-dev start` が `jq` で抽出しプロジェクトの `.claude/host-hooks.json` として書き出す（ファイル名は歴史的経緯。`env` も含む）。entrypoint がコンテナ内 `settings.json` へ `jq '. * $overlay[0]'` でマージする（[03-impl/cli.md](cli.md) / [03-impl/entrypoint.md](entrypoint.md)）。hook スクリプト本体はイメージ焼き込み済みのため `~/.local/bin` 経由でのコピー対象外。

## エラーハンドリング実装

| 異常系 | 実装箇所 | 実際の振る舞い | 対応する要件 |
|---|---|---|---|
| hook JSON のパース失敗 | save_prompt.sh | `session_id=unknown` / プロンプト空でフォールバック継続 | orchestration/18 |
| プロンプト一時ファイル不在/空 | sendslackmsg.sh | 本文を `(no prompt)` として通知継続 | orchestration/18 |
| SLACK_BOT_TOKEN 未設定 | sendslackmsg.sh | 何もせず `exit 0`（通知無効化） | orchestration/18 |
| Slack POST 失敗/API エラー | sendslackmsg.sh | 握りつぶし（`|| true`）。Claude 本処理は妨げない | orchestration/18 |

## テスト

シェルスクリプトのため自動テストは持たない（[全体設計](../02-design/system.md) テスト戦略：シェル系は実機確認）。実機での確認観点：

| 確認項目 | レベル | 検証内容 | 対応する受け入れ基準/契約 |
|---|---|---|---|
| プロンプト保存 | 実機確認 | hook JSON を stdin に与え `/tmp/claude_prompt_<session>.txt` が先頭30文字で作られる | orchestration/18 |
| Slack 通知 | 実機確認 | `SLACK_BOT_TOKEN`/`SLACK_CHANNEL` 設定下で `sendslackmsg.sh "msg"` が該当チャンネルへ投稿（本文にプロンプト文脈） | orchestration/18・契約: orchestrator→hooks(Slack通知) |
| トークン未設定 | 実機確認 | `SLACK_BOT_TOKEN` 未設定で無害に `exit 0` | orchestration/18 |

実行方法：自動テストなし。実機（`claude-dev start` 後のコンテナ）で該当 hook イベントを発生させ、Slack 投稿と一時ファイルを目視確認する。

## 既知の制限・技術的負債

- 一時ファイル `/tmp/claude_prompt_<session_id>.txt` の削除は行わない（セッションごとに増えるが `/tmp` 上で無害）。
- 抽出ツールが save_prompt.sh は `python3`、sendslackmsg.sh は `jq` と分かれている（統一されていない）。
- 抽出/保存するプロンプトは先頭 30 文字のみ（通知本文の識別用途に限定）。
- ホスト設定を運ぶファイル名が実体（`env` も含む）と食い違う `host-hooks.json`（歴史的経緯）。

## 運用メモ

- Slack 通知を止めたいときはホスト `~/.claude/settings.json` の `env.SLACK_BOT_TOKEN` を外す（未設定なら sendslackmsg.sh は無害に終了）。
- 投稿されない場合の切り分け：(1) コンテナ `settings.json` の `hooks`/`env` にマージされているか、(2) `SLACK_BOT_TOKEN` の権限・チャンネル ID、(3) `/tmp/claude_prompt_<session>.txt` の有無。POST 失敗はログを残さず握りつぶす点に注意。

---
slug: slack-hook-subagent-suppress
layer: history
title: Slack 通知フックのサブエージェント由来抑制
date: 2026-07-20
trigger: 実装上の判断（通知ノイズ削減）
origin_layer: impl
affected:
  - doc: docs/03-impl/hooks.md
    version: 1.0.0 -> 1.1.0
---

# 変更記録:Slack 通知フックのサブエージェント由来抑制

## 変更理由・背景

`Stop`/`Notification` フックから `sendslackmsg.sh` が Slack 通知を送るが、サブエージェント
（Task＝バックグラウンド）由来の発火でも通知が飛びうるため、本体（メイン）エージェント由来に
限定して通知したいという要望。上流（00/01/02）に `Stop`/`Notification` フック通知の発火条件を
規定する受入基準・契約は存在せず、hooks モジュールの通知ロジックに閉じる実装詳細のため起点は
03-impl とした。

## 変更内容の要約

- `docs/03-impl/hooks.md`（1.0.0→1.1.0）：`sendslackmsg.sh` の責務を「本体エージェント由来の
  発火に限り通知する」と明記。処理の要点に、標準入力 JSON がサブエージェント由来
  （`agent_id` が非空、または `hook_event_name == "SubagentStop"`）なら何もせず `exit 0` する
  ステップを追加。

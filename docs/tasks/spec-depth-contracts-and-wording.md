---
slug: spec-depth-contracts-and-wording
layer: task
title: モジュール間契約の深度と orchestration 要件の判定語を実装可能な粒度にする
date: 2026-07-31
updated: 2026-07-31
phase: ドキュメント
source:
  - docs/01-requirements/orchestration.md
  - docs/02-design/system.md
history: []
---

# タスク:契約の深度と判定語を実装可能な粒度にする

## 目的

既に実装済みの領域について、**ドキュメントが実装を導けるだけの深さを持っていない**箇所を埋める。
機能を変えるのではなく、既存の振る舞いを検証可能な形に書き下ろす作業である。

## 起票の経緯

`/doc-check full`（2026-07-31）の独立監査（Codex の 02 レンズ・readiness レンズ）が D11/C6/C7 として
検出した残存指摘のうち、本作業の対象は次の 2 系統。いずれも重大度 中 で PASS はブロックしなかったため
`02-design/system.md` と `01-requirements/orchestration.md` は合格証を維持しているが、指摘自体は未解決。
人間判断（決定シート #5 = 案A: 別作業として起票）により本作業へ切り出した。

## 対象の指摘

| # | 分類 | 箇所 | 内容 |
|---|---|---|---|
| 1 | D11 | system.md「モジュール間インターフェース(契約)」5 契約 | 環境変数名とコマンド例はあるが、型・必須/任意・値域・不正値・タイムアウト・部分失敗時のエラーと伝播・並行アクセス時の所有権が定義されていない。とくに `cli(orchestrate)→orchestrator` の設定値（`max_workers`/`stuck_limit`/`max_review_rounds` 等）の型と範囲、`cli→コンテナ/entrypoint` のマウント元不在・認証ファイル破損時の扱い |
| 2 | D11 | system.md「UI設計」画面一覧の状態列 | `cli-commands`＝「起動中/未セットアップ/エラー案内」、`orch-brainstorming`＝「対話中」、`orch-intervention`＝「回答待ち」など一部状態のみ。初期・空・入力不正・処理中・復旧不能の各状態と、その表示・操作可否が未定義 |
| 3 | C6/C7 | orchestration.md 13-3 / 15-4 / 非機能:性能 | 「必要な文脈だけを再構成して」「軽微な判断ならば最も妥当な仮定を置いて」「意味のあるまとまりで割り当て」の判定条件が本文にない。とくに 15-4 は「軽微」の分類・許容されない仮定・候補競合時の優先規則が未定義で、実装者（および worker）に方針の発明を強いる |
| 4 | D12 | entrypoint.md 認証同期 | 複数のプロジェクトコンテナが同じ共有 `auth.json` へ 30 秒ごとに書き戻す構成だが、同時更新時の排他・競合判定・どちらを正とするかが未定義（実装は last-writer-wins だが文書に無い） |
| 5 | D12 | entrypoint.md 起動シーケンス | `/workspace/CLAUDE.md`・`.mcp.json`・`.claude/.claude.json` を順次書き換える際の途中失敗時の扱い、同一 workspace への二重起動時の並行更新規則が未定義。`set -e` と個別の `\|\| true` が混在しており、どの部分状態を許容するかが網羅されていない |
| 6 | D12 | entrypoint.md VNC 起動 | Xvnc/websockify/Chrome/D-Bus/IBus をバックグラウンド起動した後、ready 確認をせず「✅ Ready」へ進む。個別起動失敗時に再試行するのか、起動失敗扱いにするのか、警告だけかが未定義 |

## 未決点

| # | 対象 | 未決点 | 帰着 | 状態 |
|---|---|---|---|---|
| 1 | 全体 | 「実装済みの振る舞いをそのまま書き下ろす」のか「この機会に振る舞い自体を決め直す」のか（前者なら 03 起点、後者なら 01/02 起点で影響が広がる） | フェーズ1 の決定シート | 未closure |
| 2 | 指摘3 | 15-4「軽微な判断」は本質的に worker（LLM）の裁量で、閾値の数値化になじまない。分類の**例示**と「許容されない仮定」の列挙で足りるとするか、機械判定可能な条件まで求めるか | フェーズ1 の決定シート | 未closure |

## 調査メモ

| # | 調べたこと | 判明した事実(根拠) | 使いどころ |
|---|---|---|---|
| 1 | 設定値の実際の既定と型 | `03-impl/orchestrator.md`「設定・環境変数」表に `max_workers`=5 / `stuck_limit`=3 / `max_review_rounds`=10 / `review_format_error_limit`=2 / `worker_grace_seconds`=10 / `merge_strategy`=merge / `worker_permission_mode`=bypassPermissions が既定つきで載っている。**範囲・不正値時の挙動だけが未記載** | 指摘1 の埋め先 |
| 2 | config のマージ順 | 組込既定 → `~/.config/claude-dev.yaml` の `orchestrator:` → `/workspace/.orchestrator/config.yaml`（`orchestrator/config.go`、stdlib のみの簡易パーサ） | 指摘1 |
| 3 | 認証同期の実装 | `scripts/entrypoint-claude.sh:293-312`。`cmp` で差分検出 → `cp`。排他なし＝last-writer-wins | 指摘4 |

## 質問キュー

なし（未決点はフェーズ1 の決定シートで一括提示する）

## タスク

（フェーズ1 未着手。決定シートの回答後に分解する）

## Definition of Done

- [ ] 上表の指摘 1〜6 がすべて解消している（または「対象外(理由)」として明示されている）
- [ ] 各契約が型・必須性・値域・エラー時の振る舞いを持つ
- [ ] 画面一覧の状態列が、到達可能な状態と各状態での表示・操作可否を列挙している
- [ ] 曖昧な判定語が、判定条件・例示・禁止事項のいずれかで置き換わっている
- [ ] 機能・振る舞いを変えていない（変える必要が出たら 00 起点へ戻す）
- [ ] `/doc-check` が PASS する
- [ ] 本作業の 質問/修正/委任判断 が `docs/feedback/log.md` に記録されている

## 進捗メモ

- 2026-07-31: `/doc-check full` の残存指摘（重大度 中）を、決定シート #5 の回答（案A: 別作業として起票）
  により切り出して起票。未着手。**次は `/change` でフェーズ1（決定シート）を回す。**

---
id: glossary
layer: request
title: claude-dev-env 用語集
version: 1.0.0
updated: 2026-07-18
verified:
  at: 2026-07-18
  version: 1.0.0
  against: []
summary: >
  claude-dev-env 固有の用語定義。下流の誤読・表記ゆれを潰す。
keywords: [用語集, オーケストレーター, worker, DooD, VMモード, docker-proxy]
source: null
---

# 用語集:claude-dev-env

## 用語定義

| 用語 | 定義 | 別名・禁止表記 |
|---|---|---|
| claude-dev | ホスト側 CLI。コンテナのライフサイクル・認証・ポート・SSH鍵を操作する。Linux は `claude-dev`、macOS は `claude-dev-mac`（installで symlink 統一） | 「CLIツール」単独表記は避け claude-dev と書く |
| Claude コンテナ | プロジェクトごとに起動する開発用コンテナ。VNC あり(`claude-dev-claude-vnc`)/なし(`claude-dev-claude`) | プロジェクトコンテナ（同義。文脈で使い分け） |
| docker-proxy | Docker Socket Proxy。生ソケットを直接使わせず、危険な Docker API を拒否する Go 製リバースプロキシ。全 Claude コンテナで共有 | 「プロキシ」単独は forward の socat プロキシと紛らわしいので docker-proxy と書く |
| forward プロキシ | `claude-dev forward` が立てる `fwd-<name>-<port>` の socat コンテナ。Webアプリのポート中継用 | docker-proxy と混同しない |
| DooD | Docker-outside-of-Docker。コンテナがホストの Docker デーモンを（proxy 経由で）使う既定方式 | DinD（Docker-in-Docker、本構成では非採用）と区別 |
| VM モード | オプトイン（`--vm`）。ゲスト VM(QEMU+virtiofs)内でネイティブ Docker を動かす層構成 | — |
| オーケストレーター | プロジェクトに1体立てる AIオーケストレーター（コントローラ）。ブレインストーミング/実行の2モードを持つ「1実体」 | リードエージェント（旧称。本体系ではオーケストレーターに統一） |
| コントローラ | オーケストレーターの外部制御ループ本体（Go, `orchestrate` で起動、tmux 常駐） | オーケストレーターの実装実体を指すときに使う |
| worker | 実装/レビューを行うコーディングエージェント（`claude -p`）。git worktree で分離 | ワーカー、コーディングエージェント（同義） |
| ブレインストーミングモード | 人間×対話Claudeでゴール/仕様を固める検討モード（自動化しない） | ブレスト（本文では正式名を優先） |
| 実行モード | plan の各タスクを worker へ並行ディスパッチして自律実装するモード | — |
| 介入 | 実行中に要判断が出たタスク1件を保留し、その worker ウィンドウで対話Claudeに諮ること | ストップ・ザ・ワールド（旧廃止方式。使わない） |
| 介入トリガー | 人間の判断を仰ぐ5条件（重大判断/曖昧さ/行き詰まり/方針分岐/前提崩れ） | — |
| plan.json / control.json / state.json | `.orchestrator/` の運用状態。機械が読み書きし、人間は直接編集しない | — |
| ORCHESTRATOR.md | リポジトリルートに置く任意のプロジェクト固有方針（コミット対象。`.orchestrator/` とは別） | — |

## 紛らわしい概念の区別

| 概念A | 概念B | 違い |
|---|---|---|
| docker-proxy | forward プロキシ(socat) | 前者は Docker API を検査・制限する共有プロキシ。後者は Webアプリのポートを中継する使い捨てコンテナ |
| DooD（既定） | VM モード | DooD はホスト daemon を proxy 経由で使う軽量既定。VM モードは VM 内ネイティブ Docker（bind/compose/privileged 可）でオプトイン |
| ブレインストーミングモード | 実行モード | 前者は人間主導・同期・自動化しない検討。後者は自律・並列の実装。境界は実装仕様ドキュメント |
| 仕様（docs/） | 運用状態（.orchestrator/） | 固まった仕様は docs/ に、進捗・仮定・plan 等の運用状態は `.orchestrator/` に置く |

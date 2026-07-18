---
id: e2e
layer: impl
title: E2Eテスト実装説明書
version: 1.0.0
updated: 2026-07-18
verified:
  at: 2026-07-18
  version: 1.0.0
  against:
    - doc: docs/02-design/system.md
      version: 1.0
summary: >
  02-design のE2Eシナリオ一覧(E2E-1〜5)に対応するE2E検証の実装説明。専用E2Eフレームワークは持たず、
  実機操作(claude-dev)とオーケストレーター自己検証(make orch-sample)で担保する。
keywords: [e2e, 実機確認, 自己検証, orch-sample, docker-proxy, orchestrate]
depends_on: [cli, entrypoint, docker-proxy, portsync, orchestrator, sample-project]
source:
  - docs/02-design/system.md
---

# E2Eテスト実装説明書

## 概要

本システムのE2Eは、[全体設計のテスト戦略](../02-design/system.md)「E2Eシナリオ一覧」（E2E-1〜5）に従う。
Web アプリのような自動E2Eフレームワーク（Playwright 等）は導入していない。E2E は
**(a) ホスト CLI の実機操作**（コンテナ起動・フォワード・docker-proxy 挙動）と、**(b) オーケストレーターの
自己検証**（バンドル題材に対する `make orch-sample` の実走、[sample-project](sample-project.md)）で担保する。
したがって多くのシナリオは自動化されておらず**実機確認**である点を明記する。

## テスト環境・実行方法

| 項目 | 内容 |
|---|---|
| ツール | ホスト CLI `claude-dev`（実機操作）＋ `make orch-sample`（オーケストレーター自己検証題材の scaffold・実走） |
| 実行環境(構成) | Linux サーバ + Docker Engine 24+（macOS は Docker Desktop）。VNC あり/なしイメージ、docker-proxy 共有コンテナ |
| テストデータ方針 | 自己検証題材は `examples/orch-sample/`（正本）を `workspace/orch-sample/` へ scaffold（冪等・`--force` で再初期化）。実機確認は使い捨てのプロジェクトで行う |
| 実行コマンド | 実機: `claude-dev start` / `forward` / コンテナ内 `docker run` 等。自己検証: `make orch-sample`（題材を scaffold）→ `claude-dev orchestrate`（実走）、後始末は `make orch-sample-clean` |

## ファイル構成

| パス | 役割 |
|---|---|
| scripts/orch-sample.sh | 自己検証題材の scaffold（[sample-project](sample-project.md) が正本） |
| examples/orch-sample/ | オーケストレーター自己検証の題材（Python+pytest、seed/plan.json 等） |
| （専用E2Eテストコードなし） | CLI/コンテナ系は自動E2Eを持たず実機確認 |

## テスト対応表

| テスト(ファイル::ケース名) | 対応シナリオID | 対応ユースケース | 検証内容 |
|---|---|---|---|
| 実機確認(手動): `claude-dev start`（VNC/`--no-vnc`）→ claude 起動・再接続 | E2E-1 | UC-1 | /workspace マウント・認証・FW・tmux が整い Claude Code が動く。自動化なし＝**未検証(自動化なし・実機確認)** |
| 実機確認(手動): `claude-dev forward` → SSH トンネル → ブラウザ表示・`ports` 確認 | E2E-2 | UC-2 | 8100〜割当・クライアントから到達・start 時は非公開。自動化なし＝**未検証(自動化なし・実機確認)** |
| 実機確認(手動): コンテナ内 `docker run -v /:/host` 等 → 拒否／`/workspace` bind 許可／通常許可 | E2E-3 | UC-3 | docker-proxy の許可/拒否/書換（契約は [docker-proxy](docker-proxy.md) の結合テストが機械検証、E2E としては実機確認）＝**部分自動(結合テスト)＋実機確認** |
| 自己検証: `make orch-sample`（scaffold）→ `claude-dev orchestrate`（実走） | E2E-4 | UC-4 | ブレスト→plan→worker 並列→要判断タスク単位待機→回答復帰→完了。題材に対し実走で確認＝**半自動(自己検証題材で実走・観測)** |
| 実機確認(手動): 実行中に端末全終了 → `claude-dev orchestrate` 再実行 | E2E-5 | UC-5 | attach/resume・完了済み非再実行・plan/履歴保持。自動化なし＝**未検証(自動化なし・実機確認)** |

## 既知の制限・技術的負債

- CLI/コンテナ系（E2E-1,2,3,5）の**自動E2Eは未整備**で、実機確認に依存する。回帰検出は手動。
- E2E-4 は自己検証題材での実走・観測であり、合否を機械判定する厳密なアサーションは持たない（人間/助言的検証が確認する）。
- docker-proxy の契約は結合テスト（`docker-proxy/*_test.go`）で機械検証されるため、E2E-3 の中核ロジックはそちらでカバーされる。

## 運用メモ

- 自己検証は変更時に `make orch-sample` を実行して観測する（[tech steering](../_steering/tech.md)）。
- 実機E2Eは、リリース前・オーケストレーター/CLI 変更後に主要シナリオ（特に E2E-1/E2E-4）を手動で一巡することを推奨。

---
id: tech
layer: steering
title: 技術スタックと標準コマンド（tech steering）
updated: 2026-07-18
summary: >
  言語・ビルド・テストの標準。テスト/ lint コマンドはここが唯一の正（DoD 検証で使用）。
keywords: [bash, Go, Docker, Makefile, go-test, pytest, ビルドコマンド]
---

# 技術スタックと標準コマンド

## 言語・ランタイム

| 領域 | 技術 |
|---|---|
| ホスト CLI / スクリプト | Bash（`claude-dev`, `claude-dev-mac`, `scripts/*.sh`, `scripts/vm`） |
| docker-proxy | Go 1.22（HTTP リバースプロキシ） |
| orchestrator | Go 1.24（bubbletea/lipgloss TUI、`vendor/` 同梱） |
| コンテナ | Docker マルチステージビルド（ubuntu:24.04 ベース）、GitHub Actions で GHCR 配布 |
| サンプル題材 | Python + pytest（`examples/orch-sample/` のみ） |

## ビルド（Makefile）

- `make setup` — 初期セットアップ
- `make build` — claude（VNC なし）+ claude-vnc + docker-proxy を一括ビルド
- `make build-claude` / `make build-claude-vnc` — 個別ビルド（vnc は base に続けてビルド）
- `make build-docker-proxy` / `make build-orchestrator`
- `make install` / `make uninstall` — CLI を PATH へ配置/除去
- `make login` — 認証（一時コンテナ）
- `make orch-sample` / `make orch-sample-clean` — オーケストレーター自己検証題材
- 補助: `make status` / `make clean` / `make network` / `make volumes` / `make env` / `make update-claude` / `make upgrade`

## テスト / lint（DoD で使用する唯一の正）

| レベル | コマンド | 対象 |
|---|---|---|
| 単体（Go: docker-proxy） | `cd docker-proxy && go test ./...` | プロキシの検査ロジック |
| 単体（Go: orchestrator） | `cd orchestrator && go test -mod=vendor ./...` | コントローラ/状態/レビュー等（17 テストファイル） |
| 単体（Python サンプル） | `cd examples/orch-sample && pytest` | 題材プロジェクト（オーケストレーター題材） |
| lint | `go vet ./...`（各 Go モジュール）。Bash には自動 lint を設けていない | — |
| E2E | オーケストレーター自己検証（`make orch-sample` で題材に対し実走） | 下記 |

- Bash スクリプトに自動テストランナーはない。動作確認は実機（コンテナ起動）で行う。
- E2E は「バンドルしたサンプルサブプロジェクトに対してオーケストレーターを実走させる」自己検証方式。

## 横断的な技術判断（詳細は 02-design）

- Docker 生ソケットはコンテナにマウントしない。`docker-proxy` 経由で制限付き Docker API を使う。
- 認証共有は symlink ではなく「コピー＋30秒ごとのバックグラウンド同期」で行う（アトミック書き込み対策）。
- 重い Docker 案件はオプトインの **VM モード**（QEMU+virtiofs、VM 内ネイティブ Docker）を使う。

---
id: structure
layer: steering
title: リポジトリ構造と規約（structure steering）
updated: 2026-07-18
summary: >
  コード配置とモジュール境界の共通前提。02-design の分割定義はこの物理構造に対応する。
keywords: [ディレクトリ構成, モジュール境界, 命名規約, リポジトリレイアウト]
---

# リポジトリ構造と規約

## トップレベル構成

```
claude-dev-env/
├── claude-dev              # ホスト CLI（Linux、bash）
├── claude-dev-mac          # ホスト CLI（macOS、bash）
├── Makefile                # ビルド・セットアップ・管理タスク
├── docker-proxy/           # Go: Docker API リバースプロキシ（main.go, *_test.go）
├── orchestrator/           # Go: AIオーケストレーター（controller/state/mode/session/
│                           #   worker/review/trigger/slack/dashboard 等 + vendor/ + instructions/）
├── scripts/                # entrypoint / firewall / vm 系 / portsync / slack / tmux.conf 等
├── .devcontainer/          # Dockerfile.claude, Dockerfile.docker-proxy, tmux.conf
├── .github/workflows/      # ghcr-images.yml（GHCR マルチアーキ配布）
├── examples/orch-sample/   # オーケストレーター自己検証の題材（Python + pytest）
├── workspace/orch-sample/  # 題材の使い捨て作業コピー
├── CLAUDE.md               # プロジェクト運用規範（4層仕様体系）
├── INDEX.md                # 全ドキュメントの索引（最初に見る地図）
└── docs/                   # 仕様ドキュメント（4層）＋ steering / templates / knowledge 等
```

## docs/ の構造（4層仕様体系）

`00-requests/`（要求・WHY）→ `01-requirements/`（要件・WHAT）→ `02-design/`（設計・分割定義）→
`03-impl/`（実装説明書・モジュール1ファイル）。補助: `_steering/` `_templates/` `histories/`
`tasks/` `knowledge/`（`feedback/log.md` は最初のエントリ時に作成）。詳細は `docs/README.md`。

## モジュール境界の規約

- 02-design の **モジュール分割定義** が 03-impl と実装のファンアウト単位。物理配置（上記）に対応する。
- 命名: ホスト CLI は `claude-dev`(Linux) / `claude-dev-mac`(macOS)。OS 依存はホスト CLI に閉じ、
  コンテナ内資産（イメージ・entrypoint・firewall・docker-proxy）は OS 非依存に保つ。
- Docker リソースは `claude-dev-` 接頭辞（ネットワーク `claude-dev-net`、ボリューム `claude-dev-auth` 等）。
- Go モジュールは各ディレクトリ独立（`docker-proxy/`, `orchestrator/`）。orchestrator は vendored。

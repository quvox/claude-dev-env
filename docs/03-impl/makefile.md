---
id: makefile
layer: impl
title: makefile 実装説明書
version: 1.0.0
updated: 2026-07-18
verified:
  at: 2026-07-18
  version: 1.0.0
  against:
    - doc: docs/02-design/system.md
      version: 1.0
summary: >
  ビルド・初回セットアップ・install/uninstall・login・upgrade・orch-sample 等の入口を
  `make <target>` の統一インタフェースで提供する Makefile。イメージビルドはマルチステージ
  （base→vnc）でキャッシュ共有し、OS 判定で使用する CLI を切り替える。
keywords: [Makefile, ビルド, セットアップ, install, upgrade, マルチステージ, orch-sample]
depends_on: [devcontainer, docker-proxy, orchestrator, sample-project]
source:
  - docs/02-design/system.md
---

# 実装説明書:makefile

## 概要

`Makefile`（リポジトリ直下）は、環境構築・保守操作を `make <target>` の統一インタフェースで
提供する入口である。担当は主に「セットアップ系」——イメージビルド（devcontainer の
Dockerfile 群を使用）、Docker リソース作成、CLI の PATH 登録、更新、全リセット——であり、
日常のコンテナ操作は `claude-dev` CLI が担う。orchestrator のローカル build/test と、自己検証用
サンプル（sample-project）の scaffold もここから起動する。上流: [全体設計](../02-design/system.md)
（makefile 行 / 要件 core/9 build）。

## ファイル構成

| パス | 役割 |
|---|---|
| Makefile | 全ターゲット定義。変数・OS 判定・Docker リソース名・各ターゲット |

Makefile 単体で完結し、実処理は `docker build` / `docker network|volume` / `$(CLI)` 委譲 /
`scripts/orch-sample.sh` 呼び出しに帰着する。

## モジュール別実装詳細

### 変数・OS 判定

- **責務:** ビルド/操作に使う共通値の定義と OS 分岐。
- **処理の要点:**
  - `SHELL := /bin/bash`。
  - `BASE_DIR := $(shell cd "$(dir $(lastword $(MAKEFILE_LIST)))" && pwd)`（Makefile 所在の絶対パス）。
  - `UNAME_S := $(shell uname -s)`。`Darwin`（macOS）なら `CLI := $(BASE_DIR)/claude-dev-mac`、
    それ以外は `CLI := $(BASE_DIR)/claude-dev`。**この OS 分岐は `CLI` 変数の選択のみに使う**
    （install/login 等が委譲する CLI 実体を切り替える）。利用者コマンド名はどの OS でも
    `claude-dev`（`INSTALL_PATH := /usr/local/bin/claude-dev`）。
  - macOS でもビルドはネイティブアーキ（Apple Silicon=arm64 / Intel=amd64）。
    `DOCKER_DEFAULT_PLATFORM` は固定しない（共有 Dockerfile がアーキ別対応済み）。
  - Docker リソース名は CLI と同一命名（`claude-dev-` 接頭辞）:
    `IMG_CLAUDE=claude-dev-claude`, `IMG_CLAUDE_VNC=claude-dev-claude-vnc`,
    `IMG_DOCKER_PROXY=claude-dev-docker-proxy`, `DOCKER_PROXY_CONTAINER=claude-dev-docker-proxy`,
    `NETWORK=claude-dev-net`, `VOL_AUTH=claude-dev-auth`, `VOL_HISTORY=claude-dev-history`,
    `VOL_CONFIG=claude-dev-config`, `VOL_CHROME=claude-dev-chrome-data`。
  - `CUSER := $(shell whoami)`（build-arg `USERNAME` に使用）。

### ターゲット一覧

| ターゲット | 依存 | 何をするか / 前提 |
|---|---|---|
| `help`（デフォルト） | — | セットアップ/ビルド/メンテナンス/日常の使い方のコマンド一覧を `echo` 表示 |
| `setup` | `env network volumes build install` | 初回セットアップ一括実行。完了後に次手順（login → プロジェクトへ cd → `claude-dev start`）を案内 |
| `env` | — | `$(BASE_DIR)/.env` が無ければ `.env.example` からコピー。既存ならその旨のみ表示 |
| `install` | — | `chmod +x "$(CLI)"` の後、`sudo ln -sf "$(CLI)" "$(INSTALL_PATH)"` で symlink を張る。**常に `sudo ln -sf`**（OS 分岐なし） |
| `uninstall` | — | `INSTALL_PATH` が symlink/存在すれば `rm -f`（失敗時 `sudo rm -f`）で削除。無ければその旨表示 |
| `network` | — | `docker network create $(NETWORK) 2>/dev/null || true` で冪等作成 |
| `volumes` | — | 4 ボリューム（AUTH/HISTORY/CONFIG/CHROME）を `docker volume create ... || true` で冪等作成 |
| `build` | `build-claude build-claude-vnc build-docker-proxy` | 全イメージビルド |
| `build-claude` | — | `.devcontainer/Dockerfile.claude` の `--target base` を `IMG_CLAUDE` としてビルド。build-arg に `USERNAME=$(CUSER)`, `USER_UID=$$(id -u)`, `USER_GID=$$(id -g)` |
| `build-claude-vnc` | `build-claude` | 同 Dockerfile の `--target vnc` を `IMG_CLAUDE_VNC` としてビルド（build-arg 同上）。base レイヤーをキャッシュ共有 |
| `build-docker-proxy` | — | `.devcontainer/Dockerfile.docker-proxy` を `IMG_DOCKER_PROXY` としてビルド |
| `build-orchestrator` | — | `cd orchestrator && go build -o orchestrator . && go vet ./... && go test ./...`。実行ファイル `orchestrator/orchestrator` を生成（`-o` で明示。自己検証の高速ループが直接起動する）。イメージ用バイナリは `build-claude`(base) に同梱されるため独立イメージは作らない |
| `orch-sample` | — | `scripts/orch-sample.sh` を呼び、`examples/orch-sample/` テンプレを `workspace/orch-sample/` へ scaffold。`FORCE=1`→`--force`、`SEED=1`→`--seed` を引数化 |
| `orch-sample-clean` | — | `rm -rf $(BASE_DIR)/workspace/orch-sample`（作業コピー削除） |
| `login` | — | `$(CLI) login` に委譲（OAuth ログイン） |
| `update-claude` | — | Claude Code のみ高速更新。`IMG_CLAUDE`(base) と `IMG_CLAUDE_VNC`(vnc) を、build-arg `CLAUDE_CACHE_BUST=$$(date +%s)` を付けて再ビルド（`--no-cache` ではなくキャッシュ利用。Claude Code 導入レイヤー以降のみ無効化）。反映は `stop`→`start` を案内 |
| `upgrade` | — | 3 イメージ（base/vnc/docker-proxy）を `--no-cache` で完全再ビルド。反映は `stop`→`start` を案内 |
| `status` | — | イメージ一覧・稼働中 Claude セッション・プロキシコンテナ・`claude-dev` ボリュームを `docker images/ps/volume ls` のフィルタ表示 |
| `clean` | — | 確認プロンプト（`y` 以外はキャンセル）後、全 Claude/プロキシコンテナ削除・4 ボリューム・ネットワーク・3 イメージを削除。※`fwd-*` フォワードコンテナは対象外（CLI `reset` は網羅的） |

### ビルド構成（重要）

`Dockerfile.claude` はマルチステージ（`base` → `vnc`）。`build-claude` が `base` を、
`build-claude-vnc`（`build-claude` に依存）が `vnc` をビルドし、ベースレイヤーを Docker
キャッシュで共有する。これにより VNC イメージの追加ディスクは GUI/Chrome 分のみ。
`update-claude` は同 2 段を `CLAUDE_CACHE_BUST` 付きでキャッシュ利用再ビルドし、Claude Code
導入レイヤー以降だけを無効化して高速更新する。

### 冪等性・CLI との関係

- `network`/`volumes` は `docker ... create ... 2>/dev/null || true` で冪等。
- `clean`（Makefile）と `reset`（CLI）はほぼ同義だが、`clean` は `fwd-*` フォワードコンテナを
  明示削除しない点が異なる。全消去時は CLI `reset` がより網羅的。

## 設定・環境変数

| 名前 | 用途 | デフォルト | 必須 |
|---|---|---|---|
| `.env`（ファイル） | 環境設定。`env` ターゲットが `.env.example` からコピー | .env.example 由来 | ビルド前に用意 |
| `FORCE`（make 変数） | `orch-sample` に `--force` を渡し作業コピーを再生成 | 未設定 | 任意 |
| `SEED`（make 変数） | `orch-sample` に `--seed` を渡し決定論検証用 seed plan を配置 | 未設定 | 任意 |
| `USERNAME`/`USER_UID`/`USER_GID`（build-arg） | イメージ内ユーザを実行者に合わせる | whoami / id -u / id -g | ビルド時自動 |
| `CLAUDE_CACHE_BUST`（build-arg） | `update-claude` で Claude 導入レイヤーのキャッシュ無効化 | date +%s | 自動 |
| `INSTALL_PATH` | CLI symlink 先 | /usr/local/bin/claude-dev | 固定 |

OS 判定（`uname -s`）は `CLI` 変数の選択（`claude-dev` / `claude-dev-mac`）にのみ用いる。
`install` は OS を問わず常に `sudo ln -sf` を実行する。

## テスト

Makefile 自体に対する自動テストは無い（シェル/ビルド系のため、02 テスト戦略でも「自動テスト
なし＝実機確認」）。`build-orchestrator` は内部で `go vet` / `go test ./...` を実行するが、
これは orchestrator モジュールのテストであり Makefile のテストではない。

| テスト(ファイル::ケース名) | レベル | 検証内容 | 対応する受け入れ基準/契約 |
|---|---|---|---|
| （自動テストなし。実機確認） | — | `make setup`→`build`→`install` が成功し `claude-dev` が起動できること、`make orch-sample` で `make orch-sample`（E2E-4 の実走）ができること | core/9 build / E2E-4 実走の入口 |

実行方法: 実機で `make setup` / `make build` / `make status` 等を実行して確認する。

## 既知の制限・技術的負債

- `install` は OS に関わらず常に `sudo` を要求する（`/usr/local/bin` の書込可否を判定して
  非 sudo 経路にフォールバックする実装にはなっていない）。
- `env` ターゲットは `.PHONY` 宣言に含まれていない（`env` という同名ファイルが存在すれば
  実行されない可能性がある。実害は極めて小さい）。

## 運用メモ

- イメージ更新後、稼働中コンテナへの反映は `claude-dev stop` → `claude-dev start` が必要
  （`update-claude`/`upgrade` が案内を表示する）。
- `clean` は破壊的操作。確認プロンプトで `y` 以外はキャンセルされる。

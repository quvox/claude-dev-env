# =============================================================================
# Claude Code 安全開発環境 - Makefile
# =============================================================================
# make setup    初回セットアップ（ビルド + PATH 登録）
# make login    OAuth ログイン
# make status   状態確認
# make upgrade  Claude Code 更新
# make clean    全リセット
# =============================================================================

SHELL := /bin/bash

# --- 設定 ---
BASE_DIR := $(shell cd "$(dir $(lastword $(MAKEFILE_LIST)))" && pwd)
# OS を判定し、macOS では macOS 版 CLI（claude-dev-mac）を使う。
# 利用者コマンド名はどの OS でも claude-dev（INSTALL_PATH）。
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
CLI := $(BASE_DIR)/claude-dev-mac
# macOS はネイティブアーキでビルド（Apple Silicon=arm64 / Intel=amd64）。
# 共有 Dockerfile はアーキ別対応済み（arm64 は Playwright Chromium・gcloud は arm 写像）。
else
CLI := $(BASE_DIR)/claude-dev
endif
INSTALL_PATH := /usr/local/bin/claude-dev

# --- Docker リソース名 ---
IMG_CLAUDE := claude-dev-claude
IMG_CLAUDE_VNC := claude-dev-claude-vnc
IMG_DOCKER_PROXY := claude-dev-docker-proxy
DOCKER_PROXY_CONTAINER := claude-dev-docker-proxy
CUSER := $(shell whoami)
NETWORK := claude-dev-net
VOL_AUTH := claude-dev-auth
VOL_HISTORY := claude-dev-history
VOL_CONFIG := claude-dev-config
VOL_CHROME := claude-dev-chrome-data


# =============================================================================
# メインターゲット
# =============================================================================

.PHONY: help setup install login build network volumes \
        upgrade update-claude status clean uninstall build-claude build-claude-vnc build-docker-proxy build-orchestrator \
        orch-sample orch-sample-clean

## デフォルト: ヘルプ表示
help:
	@echo "Claude Code 安全開発環境"
	@echo ""
	@echo "セットアップ:"
	@echo "  make setup        初回セットアップ（ビルド + PATH 登録）"
	@echo "  make login        OAuth ログイン"
	@echo ""
	@echo "ビルド:"
	@echo "  make build              全イメージをビルド"
	@echo "  make build-claude       Claude ベースイメージをビルド"
	@echo "  make build-claude-vnc   Claude VNC イメージをビルド"
	@echo "  make build-docker-proxy Docker Socket Proxy イメージをビルド"
	@echo "  make build-orchestrator orchestrator をローカルビルド/テスト（イメージ用は build-claude に同梱）"
	@echo ""
	@echo "メンテナンス:"
	@echo "  make update-claude  Claude Code のみ高速更新（Go/Rust 等はキャッシュ利用）"
	@echo "  make upgrade        全イメージを完全再ビルドで更新（--no-cache）"
	@echo "  make status         状態確認"
	@echo "  make clean        全リセット（コンテナ・ボリューム・イメージ削除）"
	@echo "  make uninstall    CLI のシンボリックリンクを削除"
	@echo ""
	@echo "日常の使い方:"
	@echo "  cd ~/repos/my-project && claude-dev start"

# =============================================================================
# セットアップ
# =============================================================================

## 初回セットアップ（すべて実行）
setup: env network volumes build install
	@echo ""
	@echo "============================================"
	@echo "✅ セットアップ完了！"
	@echo ""
	@echo "次のステップ:"
	@echo "  1. make login"
	@echo "  2. cd /path/to/your/project"
	@echo "  3. claude-dev start"
	@echo "============================================"

## .env ファイル作成
env:
	@if [ ! -f "$(BASE_DIR)/.env" ]; then \
		cp "$(BASE_DIR)/.env.example" "$(BASE_DIR)/.env"; \
		echo "✅ .env を作成しました（$(BASE_DIR)/.env を編集してください）"; \
	else \
		echo "ℹ️  .env は既に存在します"; \
	fi

## CLI を PATH に登録（$(INSTALL_PATH) → $(CLI) への symlink）
##  macOS: /usr/local/bin が root 所有のことが多いため sudo ln -sf で symlink。
##  Linux: 書込可能なら ln -sf、不可なら sudo ln -sf を案内。
install:
	@chmod +x "$(CLI)"
	@sudo ln -sf "$(CLI)" "$(INSTALL_PATH)"
	@echo "✅ $(INSTALL_PATH) にインストールしました（どの OS でも claude-dev コマンドで実行）"

## CLI の PATH 登録を解除
uninstall:
	@if [ -L "$(INSTALL_PATH)" ] || [ -e "$(INSTALL_PATH)" ]; then \
		rm -f "$(INSTALL_PATH)" 2>/dev/null || sudo rm -f "$(INSTALL_PATH)"; \
		echo "✅ $(INSTALL_PATH) を削除しました"; \
	else \
		echo "ℹ️  $(INSTALL_PATH) は存在しません"; \
	fi

# =============================================================================
# Docker リソース
# =============================================================================

## Docker ネットワーク作成
network:
	@docker network create $(NETWORK) 2>/dev/null || true
	@echo "✅ ネットワーク: $(NETWORK)"

## Docker ボリューム作成
volumes:
	@docker volume create $(VOL_AUTH) >/dev/null 2>&1 || true
	@docker volume create $(VOL_HISTORY) >/dev/null 2>&1 || true
	@docker volume create $(VOL_CONFIG) >/dev/null 2>&1 || true
	@docker volume create $(VOL_CHROME) >/dev/null 2>&1 || true
	@echo "✅ ボリューム: $(VOL_AUTH), $(VOL_HISTORY), $(VOL_CONFIG), $(VOL_CHROME)"

# =============================================================================
# ビルド
# =============================================================================

## 全イメージビルド
build: build-claude build-claude-vnc build-docker-proxy

## Claude ベースイメージ
build-claude:
	@echo "📦 Claude ベースイメージをビルド中..."
	@docker build -t $(IMG_CLAUDE) \
		--target base \
		--build-arg USERNAME=$(CUSER) \
		--build-arg USER_UID=$$(id -u) \
		--build-arg USER_GID=$$(id -g) \
		-f $(BASE_DIR)/.devcontainer/Dockerfile.claude $(BASE_DIR)
	@echo "✅ $(IMG_CLAUDE)"

## Claude VNC イメージ
build-claude-vnc: build-claude
	@echo "📦 Claude VNC イメージをビルド中..."
	@docker build -t $(IMG_CLAUDE_VNC) \
		--target vnc \
		--build-arg USERNAME=$(CUSER) \
		--build-arg USER_UID=$$(id -u) \
		--build-arg USER_GID=$$(id -g) \
		-f $(BASE_DIR)/.devcontainer/Dockerfile.claude $(BASE_DIR)
	@echo "✅ $(IMG_CLAUDE_VNC)"

## Docker Socket Proxy イメージ
build-docker-proxy:
	@echo "📦 Docker Socket Proxy イメージをビルド中..."
	@docker build -t $(IMG_DOCKER_PROXY) \
		-f $(BASE_DIR)/.devcontainer/Dockerfile.docker-proxy $(BASE_DIR)
	@echo "✅ $(IMG_DOCKER_PROXY)"

## orchestrator（ローカル build/test。イメージ用は build-claude に同梱される）
## go build ./... はバイナリを残さないため -o で明示（自己検証の高速ループが直接起動する）
build-orchestrator:
	@echo "🔧 orchestrator をローカルビルド/テスト中..."
	@cd $(BASE_DIR)/orchestrator && go build -o orchestrator . && go vet ./... && go test ./...
	@echo "✅ orchestrator (local build/test) -> orchestrator/orchestrator"

## 自己検証用サンプルサブプロジェクトの scaffold（examples/orch-sample -> workspace/orch-sample）
## FORCE=1 で再生成、SEED=1 で決定論検証用 seed plan を配置（docs/07_self-verification.md）
orch-sample:
	@$(BASE_DIR)/scripts/orch-sample.sh $(if $(FORCE),--force,) $(if $(SEED),--seed,)

## 自己検証用サンプルの作業コピーを削除
orch-sample-clean:
	@rm -rf $(BASE_DIR)/workspace/orch-sample && echo "🧹 removed workspace/orch-sample"

# =============================================================================
# 認証
# =============================================================================

## OAuth ログイン
login:
	@$(CLI) login

# =============================================================================
# メンテナンス
# =============================================================================

## Claude Code のみ高速更新（Go/Rust/Playwright 等はキャッシュ利用）
update-claude:
	@echo "📦 Claude Code を更新中（キャッシュ利用で高速ビルド）..."
	@docker build -t $(IMG_CLAUDE) \
		--target base \
		--build-arg USERNAME=$(CUSER) \
		--build-arg USER_UID=$$(id -u) \
		--build-arg USER_GID=$$(id -g) \
		--build-arg CLAUDE_CACHE_BUST=$$(date +%s) \
		-f $(BASE_DIR)/.devcontainer/Dockerfile.claude $(BASE_DIR)
	@echo "✅ Claude ベースイメージ更新完了"
	@echo ""
	@echo "📦 Claude VNC イメージを更新中..."
	@docker build -t $(IMG_CLAUDE_VNC) \
		--target vnc \
		--build-arg USERNAME=$(CUSER) \
		--build-arg USER_UID=$$(id -u) \
		--build-arg USER_GID=$$(id -g) \
		--build-arg CLAUDE_CACHE_BUST=$$(date +%s) \
		-f $(BASE_DIR)/.devcontainer/Dockerfile.claude $(BASE_DIR)
	@echo "✅ Claude VNC イメージ更新完了"
	@echo ""
	@echo "   実行中のコンテナは claude-dev stop → claude-dev start で反映"

## 全イメージを最新版に更新
upgrade:
	@echo "📦 Claude ベースイメージを更新中..."
	@docker build --no-cache -t $(IMG_CLAUDE) \
		--target base \
		--build-arg USERNAME=$(CUSER) \
		--build-arg USER_UID=$$(id -u) \
		--build-arg USER_GID=$$(id -g) \
		-f $(BASE_DIR)/.devcontainer/Dockerfile.claude $(BASE_DIR)
	@echo "✅ Claude ベースイメージ更新完了"
	@echo ""
	@echo "📦 Claude VNC イメージを更新中..."
	@docker build --no-cache -t $(IMG_CLAUDE_VNC) \
		--target vnc \
		--build-arg USERNAME=$(CUSER) \
		--build-arg USER_UID=$$(id -u) \
		--build-arg USER_GID=$$(id -g) \
		-f $(BASE_DIR)/.devcontainer/Dockerfile.claude $(BASE_DIR)
	@echo "✅ Claude VNC イメージ更新完了"
	@echo ""
	@echo "📦 Docker Socket Proxy イメージを更新中..."
	@docker build --no-cache -t $(IMG_DOCKER_PROXY) \
		-f $(BASE_DIR)/.devcontainer/Dockerfile.docker-proxy $(BASE_DIR)
	@echo "✅ Docker Socket Proxy イメージ更新完了"
	@echo ""
	@echo "   実行中のコンテナは claude-dev stop → claude-dev start で反映"

## 状態確認
status:
	@echo "=== Docker イメージ ==="
	@docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" \
		--filter "reference=$(IMG_CLAUDE)" --filter "reference=$(IMG_CLAUDE_VNC)" --filter "reference=$(IMG_DOCKER_PROXY)" 2>/dev/null || true
	@echo ""
	@echo "=== 実行中の Claude Code セッション ==="
	@docker ps --filter "ancestor=$(IMG_CLAUDE)" --filter "ancestor=$(IMG_CLAUDE_VNC)" \
		--format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || true
	@echo ""
	@echo "=== Docker Socket Proxy コンテナ ==="
	@docker ps --filter "name=^$(DOCKER_PROXY_CONTAINER)$$" \
		--format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || true
	@echo ""
	@echo "=== ボリューム ==="
	@docker volume ls --filter "name=claude-dev" --format "table {{.Name}}\t{{.Driver}}" 2>/dev/null || true

## 全リセット
clean:
	@echo "⚠️  以下を全て削除します:"
	@echo "   - 全 Claude Code コンテナ"
	@echo "   - Chrome/VNC コンテナ"
	@echo "   - 認証情報・履歴ボリューム"
	@echo "   - Docker イメージ"
	@echo ""
	@read -p "実行しますか？ (y/N) " ans && [ "$$ans" = "y" ] || { echo "キャンセル"; exit 1; }
	@# プロジェクトコンテナ停止
	@docker ps -a --filter "ancestor=$(IMG_CLAUDE)" --filter "ancestor=$(IMG_CLAUDE_VNC)" -q | xargs -r docker rm -f 2>/dev/null || true
	@# Docker Socket Proxy コンテナ停止
	@docker rm -f $(DOCKER_PROXY_CONTAINER) 2>/dev/null || true
	@# ボリューム削除
	@docker volume rm -f $(VOL_AUTH) $(VOL_HISTORY) $(VOL_CONFIG) $(VOL_CHROME) 2>/dev/null || true
	@# ネットワーク削除
	@docker network rm $(NETWORK) 2>/dev/null || true
	@# イメージ削除
	@docker rmi -f $(IMG_CLAUDE) $(IMG_CLAUDE_VNC) $(IMG_DOCKER_PROXY) 2>/dev/null || true
	@echo "✅ 全リセット完了"

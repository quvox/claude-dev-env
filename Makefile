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
CLI := $(BASE_DIR)/claude-dev
INSTALL_PATH := /usr/local/bin/claude-dev

# --- Docker リソース名 ---
IMG_CLAUDE := claude-dev-claude
IMG_CHROME := claude-dev-chrome
IMG_DOCKER_PROXY := claude-dev-docker-proxy
CHROME_CONTAINER := claude-dev-chrome
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
        upgrade status clean uninstall build-claude build-chrome build-docker-proxy sync-zrt-tools

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
	@echo "  make build-claude       Claude イメージをビルド"
	@echo "  make build-chrome       Chrome/VNC イメージをビルド"
	@echo "  make build-docker-proxy Docker Socket Proxy イメージをビルド"
	@echo ""
	@echo "メンテナンス:"
	@echo "  make upgrade      Claude Code + Chrome を最新版に更新"
	@echo "  make status       状態確認"
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

## CLI を PATH に登録
install:
	@chmod +x "$(CLI)"
	@if [ -w "$(dir $(INSTALL_PATH))" ]; then \
		ln -sf "$(CLI)" "$(INSTALL_PATH)"; \
		echo "✅ $(INSTALL_PATH) にインストールしました"; \
	else \
		echo "⚠️  $(INSTALL_PATH) への書き込み権限がありません"; \
		echo "   実行してください: sudo ln -sf $(CLI) $(INSTALL_PATH)"; \
	fi

## CLI の PATH 登録を解除
uninstall:
	@if [ -L "$(INSTALL_PATH)" ]; then \
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
build: build-claude build-chrome build-docker-proxy

## Claude Code イメージ
build-claude: sync-zrt-tools
	@echo "📦 Claude イメージをビルド中..."
	@docker build -t $(IMG_CLAUDE) \
		--build-arg USERNAME=$(CUSER) \
		--build-arg USER_UID=$$(id -u) \
		--build-arg USER_GID=$$(id -g) \
		-f $(BASE_DIR)/.devcontainer/Dockerfile.claude $(BASE_DIR)
	@echo "✅ $(IMG_CLAUDE)"

## Chrome/VNC イメージ
build-chrome:
	@echo "📦 Chrome/VNC イメージをビルド中..."
	@docker build -t $(IMG_CHROME) \
		--build-arg USERNAME=$(CUSER) \
		--build-arg USER_UID=$$(id -u) \
		--build-arg USER_GID=$$(id -g) \
		-f $(BASE_DIR)/.devcontainer/Dockerfile.chrome $(BASE_DIR)
	@echo "✅ $(IMG_CHROME)"

## Docker Socket Proxy イメージ
build-docker-proxy:
	@echo "📦 Docker Socket Proxy イメージをビルド中..."
	@docker build -t $(IMG_DOCKER_PROXY) \
		-f $(BASE_DIR)/.devcontainer/Dockerfile.docker-proxy $(BASE_DIR)
	@echo "✅ $(IMG_DOCKER_PROXY)"

## zrt-tools の取得・更新
ZRT_REPO := https://github.com/zettant/zrt-tools.git
ZRT_DIR := $(BASE_DIR)/zrt-tools
sync-zrt-tools:
	@if [ -d "$(ZRT_DIR)/.git" ]; then \
		echo "📥 zrt-tools を更新中..."; \
		cd "$(ZRT_DIR)" && git fetch origin && git checkout develop && git pull origin develop; \
	else \
		echo "📥 zrt-tools をクローン中..."; \
		git clone --branch develop "$(ZRT_REPO)" "$(ZRT_DIR)"; \
	fi

# =============================================================================
# 認証
# =============================================================================

## OAuth ログイン
login:
	@$(CLI) login

# =============================================================================
# メンテナンス
# =============================================================================

## Claude Code + Chrome を最新版に更新
upgrade:
	@echo "📦 Claude イメージを更新中..."
	@docker build --no-cache -t $(IMG_CLAUDE) \
		--build-arg USERNAME=$(CUSER) \
		--build-arg USER_UID=$$(id -u) \
		--build-arg USER_GID=$$(id -g) \
		-f $(BASE_DIR)/.devcontainer/Dockerfile.claude $(BASE_DIR)
	@echo "✅ Claude イメージ更新完了"
	@echo ""
	@echo "📦 Chrome/VNC イメージを更新中..."
	@docker build --no-cache -t $(IMG_CHROME) \
		--build-arg USERNAME=$(CUSER) \
		--build-arg USER_UID=$$(id -u) \
		--build-arg USER_GID=$$(id -g) \
		-f $(BASE_DIR)/.devcontainer/Dockerfile.chrome $(BASE_DIR)
	@echo "✅ Chrome/VNC イメージ更新完了"
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
		--filter "reference=$(IMG_CLAUDE)" --filter "reference=$(IMG_CHROME)" 2>/dev/null || true
	@echo ""
	@echo "=== 実行中の Claude Code セッション ==="
	@docker ps --filter "ancestor=$(IMG_CLAUDE)" \
		--format "table {{.Names}}\t{{.Status}}" 2>/dev/null || true
	@echo ""
	@echo "=== Chrome/VNC コンテナ ==="
	@docker ps --filter "name=^$(CHROME_CONTAINER)$$" \
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
	@docker ps -a --filter "ancestor=$(IMG_CLAUDE)" -q | xargs -r docker rm -f 2>/dev/null || true
	@# Chrome/VNC コンテナ停止
	@docker rm -f $(CHROME_CONTAINER) 2>/dev/null || true
	@# Docker Socket Proxy コンテナ停止
	@docker rm -f $(DOCKER_PROXY_CONTAINER) 2>/dev/null || true
	@# ボリューム削除
	@docker volume rm -f $(VOL_AUTH) $(VOL_HISTORY) $(VOL_CONFIG) $(VOL_CHROME) 2>/dev/null || true
	@# ネットワーク削除
	@docker network rm $(NETWORK) 2>/dev/null || true
	@# イメージ削除
	@docker rmi -f $(IMG_CLAUDE) $(IMG_CHROME) $(IMG_DOCKER_PROXY) 2>/dev/null || true
	@echo "✅ 全リセット完了"

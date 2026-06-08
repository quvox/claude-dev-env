# 実装仕様: Makefile

> **この文書の役割**: 初回セットアップ・イメージビルド・メンテナンスを担う `Makefile` のターゲット仕様。日常操作は `claude-dev` CLI（[10_cli.md](10_cli.md)）が担い、Makefile は主にビルドと PATH 登録など「セットアップ系」を担当する。

## 要件（なぜ必要か）

イメージのビルド、Docker リソースの作成、CLI の PATH 登録、全リセットといった「環境構築・保守」操作を、`make <target>` の統一インタフェースで提供する必要がある。CLI の `setup`/`upgrade`/`reset` と機能が重なる部分があるが、Makefile は個別ターゲット（特定イメージのみビルド等）への分解を提供する。

## カバーするコード

```
Makefile
```

## 変数

- `SHELL := /bin/bash`
- `BASE_DIR`: Makefile の所在ディレクトリの絶対パス
- `CLI := $(BASE_DIR)/claude-dev`, `INSTALL_PATH := /usr/local/bin/claude-dev`
- イメージ/コンテナ/ネットワーク/ボリューム名は CLI と同一（`IMG_CLAUDE`, `IMG_CLAUDE_VNC`, `IMG_DOCKER_PROXY`, `DOCKER_PROXY_CONTAINER`, `NETWORK`, `VOL_AUTH`, `VOL_HISTORY`, `VOL_CONFIG`, `VOL_CHROME`）
- `CUSER := $(shell whoami)`

## ターゲット仕様

| ターゲット | 依存 | 内容 |
|-----------|------|------|
| `help`（デフォルト） | — | セットアップ/ビルド/メンテナンスのコマンド一覧を表示 |
| `setup` | `env network volumes build install` | 初回セットアップ一括実行。完了後に次手順を案内 |
| `env` | — | `.env` が無ければ `.env.example` からコピー |
| `install` | — | `CLI` に実行権限を付与し `INSTALL_PATH` へ symlink。書込権限が無ければ `sudo` 実行を案内 |
| `uninstall` | — | `INSTALL_PATH` の symlink を削除 |
| `network` | — | `claude-dev-net` を冪等作成 |
| `volumes` | — | 4 ボリュームを冪等作成 |
| `build` | `build-claude build-claude-vnc build-docker-proxy` | 全イメージビルド |
| `build-claude` | — | `Dockerfile.claude` の `--target base` を `IMG_CLAUDE` としてビルド（`USERNAME`/`USER_UID`/`USER_GID` を build-arg で付与） |
| `build-claude-vnc` | `build-claude` | `--target vnc` を `IMG_CLAUDE_VNC` としてビルド |
| `build-docker-proxy` | — | `Dockerfile.docker-proxy` を `IMG_DOCKER_PROXY` としてビルド |
| `login` | — | `$(CLI) login` に委譲 |
| `upgrade` | — | 3 イメージを `--no-cache` で再ビルド。反映は `stop`→`start` を案内 |
| `status` | — | イメージ一覧・稼働中 Claude セッション・プロキシコンテナ・ボリュームを表示 |
| `clean` | — | 確認プロンプト後、全 Claude コンテナ・プロキシコンテナを削除、4 ボリューム・ネットワーク・3 イメージを削除 |

`.PHONY` には上記のうちファイルを生成しないターゲットを列挙する。

## ビルド構成（重要）

`Dockerfile.claude` はマルチステージ（`base` → `vnc`）。`build-claude` が `base` を、`build-claude-vnc`（`build-claude` に依存）が `vnc` をビルドし、ベースレイヤーを Docker キャッシュで共有する。これにより VNC イメージの追加ディスクは GUI/Chrome 分のみ。

## CLI との関係・冪等性

- `network`/`volumes` は `docker ... create ... 2>/dev/null || true` で冪等。
- `clean`（Makefile）と `reset`（CLI）はほぼ同義だが、`clean` はフォワードコンテナ（`fwd-*`）を明示的には削除しない点が異なる（CLI `reset` は `fwd-*` も削除する）。全消去時は CLI `reset` がより網羅的。

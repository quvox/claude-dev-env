---
summary: コンテナイメージを GitHub Container Registry(GHCR) へ GitHub Actions から定期(毎日)・マルチアーキ(amd64/arm64)で push し、YYYYMMDDHHmm タグでバージョン識別する仕組みの設計。pull して使う運用（generic user イメージ＋CLI の CONTAINER_USER 解決）も定める。
keywords: [ GHCR, GitHubActions, マルチアーキ, イメージ配布, pull, タグ, buildx ]
---

# GHCR イメージ配布設計

> **この文書の役割**: `claude-dev-claude` / `claude-dev-claude-vnc` / `claude-dev-docker-proxy` の各イメージを **GitHub Container Registry (GHCR)** へ **GitHub Actions から毎日**・**マルチアーキ(amd64/arm64)** で push し、`YYYYMMDDHHmm` タグでバージョンを識別できるようにする。あわせて GHCR から **pull して使う運用**を可能にする。実装仕様はワークフロー [docs/impl/90_ghcr-workflow.md](impl/90_ghcr-workflow.md)、CLI 側 [docs/impl/10_cli.md](impl/10_cli.md) / [docs/impl/11_cli-mac.md](impl/11_cli-mac.md)。

## 要件（なぜ必要か）

現状はユーザーが手元で `make build` してローカルにイメージを保存する運用。これは維持しつつ、次を追加する:

1. **配布**: ビルド済みイメージを GHCR に置き、各マシンで長いビルドをせずに `pull` して使えるようにする。
2. **自動更新**: GitHub Actions で**毎日**ビルドして push し、Claude Code や apt パッケージの更新を取り込む。
3. **バージョン識別**: タグに `YYYYMMDDHHmm`（分単位）を付け、`latest` と併用して任意時点のイメージへ固定できるようにする。
4. **マルチアーキ**: amd64（Linux サーバ）と arm64（Apple Silicon）の両方で pull・実行できる。

## レジストリと命名

- レジストリ: `ghcr.io`。オーナーはリポジトリ所有者（既定 `quvox`）。
- イメージ:
  - `ghcr.io/<owner>/claude-dev-claude`（base）
  - `ghcr.io/<owner>/claude-dev-claude-vnc`（vnc）
  - `ghcr.io/<owner>/claude-dev-docker-proxy`
- タグ: 毎回 **`YYYYMMDDHHmm`**（Asia/Tokyo）と **`latest`** の 2 つを付与。`latest` は常に最新、`YYYYMMDDHHmm` で特定ビルドに固定できる。
- 各イメージは **マルチアーキ manifest list**（linux/amd64 + linux/arm64）。

## GitHub Actions ワークフロー

`.github/workflows/ghcr-images.yml`。トリガーは **`schedule`（毎日）** と **`workflow_dispatch`（手動）**。`GITHUB_TOKEN` に `packages: write` を与え GHCR へ push する。

### ジョブ構成（3 段）

重い（CPython ソースビルド・rust cargo・playwright 等）イメージを arm64 で高速にビルドするため、**アーキごとにネイティブ runner** で並行ビルドし、あとで manifest を統合する（QEMU エミュレーションを避ける）。

1. **prepare**: タグ `YYYYMMDDHHmm`（Asia/Tokyo）と小文字オーナー名を算出し outputs に出す（後続で一貫利用）。
2. **build**（matrix: 3 イメージ × 2 アーキ = 6 ジョブ）:
   - amd64 は `ubuntu-latest`、arm64 は `ubuntu-24.04-arm`（ネイティブ）。
   - `docker/build-push-action` で該当アーキだけをビルドし、**push-by-digest**（タグを付けずダイジェストで push）。ダイジェストを artifact に保存。
   - **generic user でビルド**: `--build-arg USERNAME=dev USER_UID=1000 USER_GID=1000`（特定ユーザーに紐づけない。UID/GID は実行時に entrypoint が `/workspace` 所有者へ追従させる。§pull 運用）。
3. **merge**（matrix: 3 イメージ）:
   - 各イメージの amd64/arm64 ダイジェストを `docker buildx imagetools create` で 1 つの manifest list にまとめ、`:YYYYMMDDHHmm` と `:latest` の両タグで push。

> **runner について**: `ubuntu-24.04-arm`（GitHub ホスト arm64 runner）は public リポジトリでは無料。private リポジトリでは利用可否・課金が異なるため、必要なら arm64 を QEMU エミュレーション（単一 runner で `--platform linux/amd64,linux/arm64`）に切り替える。ただしエミュレーションは本イメージでは非常に遅くなる点に注意（実装仕様に代替案を記載）。

### スケジュール

- 既定 `cron: '30 18 * * *'`（UTC）＝ **03:30 JST 毎日**（オフピーク）。頻度は cron 行の変更で調整可能。

## pull して使う運用

### 課題: ユーザー名/UID/GID の焼き込み

ローカルの `make build` はホストの `whoami`/`id -u`/`id -g` をイメージへ焼き込む（`CONTAINER_USER` env・`/home/<user>`）。GHCR の共有イメージは特定ユーザーに紐づけられないため、**generic user（`dev`/1000/1000）** で焼く。UID/GID は entrypoint が起動時に `/workspace` 所有者へ追従させるため、実ファイル所有権の齟齬は起きない。残る差は **ユーザー名（＝ホームパス `/home/dev`）** で、ここを CLI が吸収する。

### CLI 側の解決（CONTAINER_USER 解決）

CLI はコンテナ内ユーザー名を **実行するイメージの `CONTAINER_USER` env から解決**する（イメージが無ければ従来どおり `whoami`）。

- ローカルビルド image → `CONTAINER_USER=<whoami>` → 従来と同一挙動（後方互換）。
- GHCR pull image → `CONTAINER_USER=dev` → マウント先 `/home/dev`・`docker exec -u dev` に自動追従。

この 1 点の変更で、ボリュームマウント（`${CHOME}/...`）・`exec -u` はすべて解決済みユーザーに従うため、他のロジックは不変。entrypoint も既存の `CONTAINER_USER` 参照・UID/GID 追従のまま変更不要。

### `pull` サブコマンド

`claude-dev pull [TAG]`:

- `.env` の `CLAUDE_DEV_REGISTRY`（既定 `ghcr.io/<owner>`）と `CLAUDE_DEV_IMAGE_TAG`（既定 `latest`、引数 `TAG` で上書き）から、3 イメージを `docker pull`。
- pull 後、**ローカル名へ retag**（`ghcr.io/<owner>/claude-dev-claude:TAG` → `claude-dev-claude`）。以降の CLI は従来のローカル名を参照するため、`start` 等は自動ビルドせずに pull 済みイメージを使う。
- Docker が対象アーキの manifest を自動選択するため、Apple Silicon では arm64、Linux amd64 では amd64 が pull される。

`.env` に登録できる設定:

| 変数 | 既定 | 用途 |
|------|------|------|
| `CLAUDE_DEV_REGISTRY` | `ghcr.io/quvox` | pull 元レジストリ/オーナー |
| `CLAUDE_DEV_IMAGE_TAG` | `latest` | pull するタグ（`YYYYMMDDHHmm` で固定可） |

## 設計原則・不変条件

- **ローカル build 運用は不変**: `make build` / `setup` / `upgrade` の挙動は従来どおり（whoami で焼く）。GHCR は追加経路。
- **共有イメージ定義は不変**: `Dockerfile.claude` / `Dockerfile.docker-proxy` は変更しない。generic user はビルド時の `--build-arg` で与える（Dockerfile 既定値の範囲）。
- **CLI 変更は最小**: ユーザー名解決（`CONTAINER_USER`）と `pull` サブコマンドの追加のみ。`claude-dev`（Linux）/`claude-dev-mac`（macOS）両方に同じ変更を入れる。
- **認証**: push は `GITHUB_TOKEN`。pull は public なら不要、private なら `docker login ghcr.io`（PAT）が必要。

## 関連文書

- ワークフロー実装仕様: [docs/impl/90_ghcr-workflow.md](impl/90_ghcr-workflow.md)
- CLI 実装仕様: [docs/impl/10_cli.md](impl/10_cli.md)（Linux）/ [docs/impl/11_cli-mac.md](impl/11_cli-mac.md)（macOS）
- イメージビルド仕様: [docs/impl/40_devcontainer.md](impl/40_devcontainer.md)
- macOS 対応（arm64・Chromium 等）: [docs/09_macos-support.md](09_macos-support.md)

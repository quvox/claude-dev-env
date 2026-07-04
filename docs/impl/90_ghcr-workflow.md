---
summary: GHCR へイメージ(claude/claude-vnc/docker-proxy)を毎日・マルチアーキ(amd64/arm64)で push する GitHub Actions ワークフロー(.github/workflows/ghcr-images.yml)の実装仕様。prepare→build(matrix, push-by-digest)→merge(imagetools) の3ジョブと YYYYMMDDHHmm+latest タグを定める。
keywords: [ GitHubActions, GHCR, buildx, マルチアーキ, push-by-digest, imagetools, タグ ]
---

# 実装仕様: GHCR イメージ配布ワークフロー

> **この文書の役割**: `.github/workflows/ghcr-images.yml` の成果物仕様。設計意図は [../10_ghcr-images.md](../10_ghcr-images.md)。CLI 側の `pull`/ユーザー解決は [10_cli.md](10_cli.md) / [11_cli-mac.md](11_cli-mac.md)。

## 要件（なぜ必要か）

3 イメージを GHCR へ毎日・マルチアーキで push し、`YYYYMMDDHHmm` タグでバージョン識別する（設計 [../10_ghcr-images.md](../10_ghcr-images.md)）。重いイメージ（CPython ソースビルド等）を arm64 でエミュレーションせず高速にビルドするため、アーキごとにネイティブ runner で並行ビルドし manifest を統合する。

## カバーするコード

```
.github/workflows/ghcr-images.yml
```

## トリガー・権限

- `on`: `schedule`（`cron: '30 18 * * *'` = 03:30 JST 毎日）と `workflow_dispatch`（手動）。
- `permissions`: `contents: read`, `packages: write`（GHCR push に必要）。
- `concurrency`: group `ghcr-images`、`cancel-in-progress: false`（多重起動を直列化）。
- `env.REGISTRY`: `ghcr.io`。

## ジョブ

### `prepare`
`runs-on: ubuntu-latest`。outputs:
- `tag`: `TZ=Asia/Tokyo date +%Y%m%d%H%M`。
- `owner`: `github.repository_owner` を小文字化（GHCR はパスに小文字を要求）。

### `build`（matrix）
`needs: prepare`。matrix は **image（3）× platform（2）= 6 ジョブ**、`fail-fast: false`。

- `image`: `{name, dockerfile, target}` の 3 要素。
  - `claude`: `.devcontainer/Dockerfile.claude` / target `base`
  - `claude-vnc`: `.devcontainer/Dockerfile.claude` / target `vnc`
  - `docker-proxy`: `.devcontainer/Dockerfile.docker-proxy` / target `""`（空＝target 指定なし）
- `platform`: `{arch, runner, docker}` の 2 要素。
  - `amd64`: runner `ubuntu-latest` / `linux/amd64`
  - `arm64`: runner `ubuntu-24.04-arm`（ネイティブ arm64） / `linux/arm64`
- `runs-on: ${{ matrix.platform.runner }}`。

手順: checkout → `docker/setup-buildx-action` → `docker/login-action`（ghcr.io、`github.actor`＋`GITHUB_TOKEN`）→ `docker/build-push-action@v7`:
- `context: .`、`file: matrix.image.dockerfile`、`target: matrix.image.target`、`platforms: matrix.platform.docker`（単一アーキ）。
- `build-args`: `USERNAME=dev` / `USER_UID=1000` / `USER_GID=1000`（generic user）、および **`IMAGE_VERSION=${tag}`**（＝`YYYYMMDDHHmm`。Dockerfile がこれを `io.github.quvox.claude-dev.version`／`org.opencontainers.image.version` ラベルに焼き込み、`claude-dev start` がバージョン表示に使う）。docker-proxy は `USERNAME` 系 ARG を宣言しないため無視＝警告のみ（`IMAGE_VERSION` は宣言済み）。
- `provenance: false`（余分な attestation manifest を作らず manifest list をクリーンに保つ）。
- `outputs: type=image,name=${REGISTRY}/${owner}/claude-dev-${name},push-by-digest=true,name-canonical=true,push=true`（**タグを付けずダイジェストで push**）。
- `cache-from`/`cache-to`: `type=gha,scope=${name}-${arch}`（アーキ・イメージ別キャッシュ）。

その後、`steps.build.outputs.digest` を `${runner.temp}/digests/<digest-without-sha256:>` に空ファイルとして書き出し、`actions/upload-artifact@v7`（name `digests-${name}-${arch}`、`if-no-files-found: error`、`retention-days: 1`）で保存。

### `merge`（matrix）
`needs: [prepare, build]`、`runs-on: ubuntu-latest`。matrix は `image_name`（`claude`/`claude-vnc`/`docker-proxy`）の 3 ジョブ。

手順: `actions/download-artifact@v8` を **exact 名で 2 回**（`digests-${image_name}-amd64` と `digests-${image_name}-arm64`）呼び、当該イメージの全アーキ分を 1 ディレクトリへ集約する（**パターン方式は使わない**。`digests-claude-*` が `digests-claude-vnc-*` を巻き込む前置一致バグを避けるため。イメージ名が別イメージ名の前置になり得る＝`claude`⊂`claude-vnc` 対策）→ buildx セットアップ → GHCR ログイン → `docker buildx imagetools create` で **manifest list を作成**:
- `-t ${IMAGE}:${tag}` と `-t ${IMAGE}:latest` の 2 タグ。
- ソースはダウンロードしたダイジェスト群（`${IMAGE}@sha256:<digest>` を各ファイル名から構成）。
- `IMAGE=${REGISTRY}/${owner}/claude-dev-${image_name}`。

最後に `docker buildx imagetools inspect ${IMAGE}:${tag}` で確認。

## 成果物（GHCR に現れるもの）

- `ghcr.io/<owner>/claude-dev-claude:{YYYYMMDDHHmm,latest}`（amd64+arm64 manifest list）
- `ghcr.io/<owner>/claude-dev-claude-vnc:{YYYYMMDDHHmm,latest}`
- `ghcr.io/<owner>/claude-dev-docker-proxy:{YYYYMMDDHHmm,latest}`

## 注意・代替

- **arm64 runner**: `ubuntu-24.04-arm` は public リポジトリでは無料。private で使えない場合は、build を単一 runner（`ubuntu-latest`）＋`docker/setup-qemu-action` に替え、`platforms: linux/amd64,linux/arm64` で 1 回ビルド（`push-by-digest` を使わず直接タグ push）に変更する。ただし本イメージの arm64 エミュレーションビルドは非常に遅いため既定は採らない。
- **タグ時刻**: `YYYYMMDDHHmm` は JST。`prepare` で 1 度だけ算出して全 merge ジョブへ配るため、イメージ間でタグがずれない。
- **公開範囲**: 初回 push 後、GHCR パッケージの可視性（public/private）は GitHub のパッケージ設定で調整する。private の場合、pull 側は `docker login ghcr.io` が必要（[10_ghcr-images.md](../10_ghcr-images.md)）。

---
id: ghcr-workflow
layer: impl
title: ghcr-workflow 実装説明書
version: 1.1.0
updated: 2026-07-18
verified:
  at: 2026-07-19
  version: 1.1.0
  against:
    - doc: docs/02-design/system.md
      version: 1.1
summary: >
  コンテナイメージ（claude / claude-vnc / docker-proxy）を GHCR へ毎日・マルチアーキ
  (amd64/arm64) で push する GitHub Actions ワークフロー。prepare→build(matrix, push-by-digest)
  →merge(imagetools) の3ジョブ構成で、YYYYMMDDHHmm(JST) と latest の2タグを付与する。
keywords: [GitHubActions, GHCR, buildx, マルチアーキ, push-by-digest, imagetools, タグ]
depends_on: [devcontainer]
source:
  - docs/02-design/system.md
---

# 実装説明書:ghcr-workflow

## 概要

`.github/workflows/ghcr-images.yml` は、devcontainer が定義する 3 イメージ
（`claude` / `claude-vnc` / `docker-proxy`）を GitHub Actions で毎日ビルドし、GHCR
（`ghcr.io`）へマルチアーキ（amd64 / arm64）で push するワークフロー（要件 core/9 配布）。
重いイメージ（CPython ソースビルド等）を arm64 で QEMU エミュレーションせず（エミュレーションは
ビルド時間が数倍に増えるため）、アーキごとにネイティブ runner で並行ビルドし、manifest list を統合する方式を採る。
`prepare`（タグ算出）→ `build`（matrix・push-by-digest）→ `merge`（imagetools でタグ付け）の
3 ジョブから成る。上流: [全体設計](../02-design/system.md)。

## ファイル構成

| パス | 役割 |
|---|---|
| .github/workflows/ghcr-images.yml | GHCR マルチアーキ日次配布ワークフロー本体（3ジョブ） |

ビルド対象の Dockerfile（`.devcontainer/Dockerfile.claude` の base/vnc ステージ、
`.devcontainer/Dockerfile.docker-proxy`）は devcontainer モジュールが所有する。

## モジュール別実装詳細

### prepare ジョブ

- **責務:** タグ（`YYYYMMDDHHmm`, JST）と小文字化したオーナー名を 1 度だけ算出し、後続ジョブへ配る。
- **処理の要点:**
  - `runs-on: ubuntu-latest`。
  - outputs `tag`: `TZ=Asia/Tokyo date +%Y%m%d%H%M`（JST の分精度タイムスタンプ）。
  - outputs `owner`: `github.repository_owner` を `tr '[:upper:]' '[:lower:]'` で小文字化
    （GHCR はパスに小文字を要求するため）。
- **実装上の判断:** タグを prepare で 1 度だけ算出することで、全 build/merge ジョブ間でタグがずれない。

### build ジョブ（matrix）

- **責務:** 3 イメージ × 2 アーキ = 6 ジョブを並行ビルドし、タグを付けずダイジェストで push する。
- **処理の要点:**
  - `needs: prepare`、`strategy.fail-fast: false`（1 ジョブ失敗でも他を継続）。
  - matrix `image`（`{name, dockerfile, target}`）:
    - `claude`: `.devcontainer/Dockerfile.claude` / target `base`
    - `claude-vnc`: `.devcontainer/Dockerfile.claude` / target `vnc`
    - `docker-proxy`: `.devcontainer/Dockerfile.docker-proxy` / target `""`（空＝target 指定なし）
  - matrix `platform`（`{arch, runner, docker}`）:
    - `amd64`: runner `ubuntu-latest` / `linux/amd64`
    - `arm64`: runner `ubuntu-24.04-arm`（ネイティブ arm64）/ `linux/arm64`
  - `runs-on: ${{ matrix.platform.runner }}`。
  - 手順: `actions/checkout@v7` → `docker/setup-buildx-action@v4` →
    `docker/login-action@v4`（`ghcr.io`、`github.actor` ＋ `secrets.GITHUB_TOKEN`）→
    `docker/build-push-action@v7`。
  - build-push-action の設定:
    - `context: .`、`file: matrix.image.dockerfile`、`target: matrix.image.target`、
      `platforms: matrix.platform.docker`（単一アーキ）。
    - `build-args`: `USERNAME=dev` / `USER_UID=1000` / `USER_GID=1000`（特定ユーザーに紐づけない
      generic user。UID/GID は実行時に entrypoint が /workspace 所有者へ追従）。
      docker-proxy は `USERNAME` 系 ARG を宣言しないため無視（警告のみ）。
      **`IMAGE_VERSION` は build-arg で渡さない**（後述のキャッシュ理由）。
    - `labels`: `io.github.quvox.claude-dev.version` / `org.opencontainers.image.version` =
      `${{ needs.prepare.outputs.tag }}`。**バージョン（日次で変わるタイムスタンプ）は build-arg=
      `IMAGE_VERSION` として Dockerfile の `LABEL` 経由でレイヤーチェーンに載せない**。載せると
      その層以降のレイヤーキャッシュが毎日失効し（`cache-from` が効かず）`docker pull` が毎回
      全レイヤー再取得になるため。`labels` 入力は最終イメージの config メタデータとして export 時に
      付与され、**レイヤーキャッシュ／レイヤーダイジェストに影響しない**（＝日次 pull が増分になる）。
      Dockerfile 側の `ARG IMAGE_VERSION=local`＋`LABEL` は据え置き（CI では既定 `local` の定数となり
      キャッシュを失効させない。ローカルビルドのバージョン表示に使う。pushed イメージは本 `labels` が上書き）。
    - `provenance: false`（余分な attestation manifest を作らず manifest list をクリーンに保つ）。
    - `outputs: type=image,name=${REGISTRY}/${owner}/claude-dev-${name},push-by-digest=true,name-canonical=true,push=true`
      （タグを付けずダイジェストで push）。
    - `cache-from`/`cache-to`: `type=gha,scope=${name}-${arch}`（`cache-to` は `mode=max`。
      アーキ・イメージ別キャッシュ）。上記のとおり、日次で変わる値をレイヤーチェーンに入れないことで
      このキャッシュが実効化し、変更のない層は再ビルド／再 push／再 pull されない。
  - Export digest: `steps.build.outputs.digest` から `sha256:` を除いた名前で
    `${runner.temp}/digests/<digest>` に空ファイルを `touch`。
  - Upload digest: `actions/upload-artifact@v7`（name `digests-${name}-${arch}`、
    `if-no-files-found: error`、`retention-days: 1`）。

### merge ジョブ（matrix）

- **責務:** 各イメージの amd64/arm64 ダイジェストを manifest list に統合し、タグ付けして push する。
- **処理の要点:**
  - `needs: [prepare, build]`、`runs-on: ubuntu-latest`、`strategy.fail-fast: false`。
  - matrix `image_name`: `[claude, claude-vnc, docker-proxy]`（3 ジョブ）。
  - 手順: `actions/download-artifact@v8` を **exact 名で 2 回**
    （`digests-${image_name}-amd64` と `digests-${image_name}-arm64`）呼び、当該イメージの
    全アーキ分を `${runner.temp}/digests` へ集約 → `docker/setup-buildx-action@v4` →
    `docker/login-action@v4`（GHCR ログイン）→ manifest list 作成 → inspect。
  - manifest list 作成: `docker buildx imagetools create -t ${IMAGE}:${tag} -t ${IMAGE}:latest`
    に、ダウンロードしたダイジェスト群（`printf "${IMAGE}@sha256:%s " *`）をソースとして渡す。
    `IMAGE=${REGISTRY}/${owner}/claude-dev-${image_name}`。
  - 確認: `docker buildx imagetools inspect ${IMAGE}:${tag}`。
- **実装上の判断:** ダウンロードは download-artifact のパターン方式を使わず exact 名で 2 回呼ぶ。
  `claude` が `claude-vnc` の前置（`claude`⊂`claude-vnc`）になり得るため、パターン `digests-claude-*`
  が `digests-claude-vnc-*` を巻き込む前置一致バグを避ける。

## データアクセス

該当なし（永続データストアを持たない。ジョブ間受け渡しは GITHUB_OUTPUT と Actions Artifact）。

## API実装詳細

外部公開 API なし（GitHub Actions ワークフロー。成果物は GHCR 上のイメージ）。

成果物（GHCR に現れるもの）:

- `ghcr.io/<owner>/claude-dev-claude:{YYYYMMDDHHmm,latest}`（amd64+arm64 manifest list）
- `ghcr.io/<owner>/claude-dev-claude-vnc:{YYYYMMDDHHmm,latest}`
- `ghcr.io/<owner>/claude-dev-docker-proxy:{YYYYMMDDHHmm,latest}`

## 設定・環境変数

| 名前 | 用途 | デフォルト | 必須 |
|---|---|---|---|
| env.REGISTRY | push 先レジストリ | `ghcr.io` | ○（定義済み） |
| secrets.GITHUB_TOKEN | GHCR ログインのパスワード（Actions 既定トークン） | Actions 自動発行 | ○ |
| github.actor | GHCR ログインのユーザー名 | 実行者 | ○（自動） |
| github.repository_owner | イメージパスのオーナー（小文字化して使用） | リポジトリ所有者 | ○（自動） |

トリガー・権限:

- `on`: `schedule`（`cron: '30 18 * * *'` = UTC 18:30 = 03:30 JST 毎日）と `workflow_dispatch`（手動）。
  push トリガーは無し。
- `permissions`: `contents: read`, `packages: write`（GHCR push に必要）。
- `concurrency`: group `ghcr-images`、`cancel-in-progress: false`（多重起動を直列化）。

## エラーハンドリング実装

| 異常系 | 実装箇所 | 実際の振る舞い | 対応する要件 |
|---|---|---|---|
| ダイジェストファイルが無い | build: Upload digest | `if-no-files-found: error` でジョブ失敗 | core/9 |
| 一部アーキ/イメージのビルド失敗 | build/merge: strategy | `fail-fast: false` で他ジョブは継続 | core/9 |
| ワークフロー多重起動 | concurrency | 同一 group を直列化（進行中はキャンセルしない） | core/9 |

## テスト

単体テストなし（GitHub Actions ワークフロー。シェル系は自動テストなし＝実機確認、
[テスト戦略](../02-design/system.md)）。

| テスト(ファイル::ケース名) | レベル | 検証内容 | 対応する受け入れ基準/契約 |
|---|---|---|---|
| CI 実機（`workflow_dispatch` 手動実行 → GHCR 確認） | 実機 | 3 イメージ × amd64/arm64 の manifest list が `YYYYMMDDHHmm` と `latest` で push される | core/9 配布 |

実行方法: GitHub 上で本ワークフローを手動実行（Actions タブ → workflow_dispatch）するか、
日次スケジュール（03:30 JST）で自動実行。GHCR パッケージ一覧と `imagetools inspect` の出力で確認する。

## 既知の制限・技術的負債

- arm64 ネイティブ runner `ubuntu-24.04-arm` は public リポジトリでは無料。private で使えない場合は、
  build を単一 runner（`ubuntu-latest`）＋ `docker/setup-qemu-action` に替え、
  `platforms: linux/amd64,linux/arm64` で 1 回ビルド（push-by-digest を使わず直接タグ push）に
  変更する必要がある。ただし arm64 エミュレーションビルドは非常に遅いため既定は採らない。
- GHCR パッケージの可視性（public/private）はワークフロー外（GitHub のパッケージ設定）で調整する。

## 運用メモ

- タグ時刻 `YYYYMMDDHHmm` は JST。`prepare` で 1 度だけ算出して全 merge ジョブへ配るため、
  イメージ間でタグがずれない。
- private 公開の場合、pull 側は `docker login ghcr.io` が必要。
- Dockerfile の base/vnc ステージや ARG を変更した際は、本ワークフローの build-args / target 指定
  との整合を確認する（devcontainer モジュールと連動）。
- **日次で変わる値を新たに build-arg / ENV / LABEL でレイヤーチェーンへ入れない**こと（`IMAGE_VERSION`
  を `labels` に移した理由と同じ）。入れると `cache-from` が実効しなくなり pull が全再取得に戻る。
  バージョン等のメタデータは build-push-action の `labels` 入力で最終イメージへ付与する。

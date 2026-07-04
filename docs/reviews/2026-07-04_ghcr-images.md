# レビュー: GHCR イメージ配布（GitHub Actions 定期 push ＋ pull 運用）

対象: `.github/workflows/ghcr-images.yml`（新規）、`claude-dev` / `claude-dev-mac`（`pull` サブコマンド・`CONTAINER_USER` 解決）、`.env.example`、設計 `docs/10_ghcr-images.md`、実装仕様 `docs/impl/90_ghcr-workflow.md`、および 10_cli/11_cli-mac/INDEX/README/04 の更新
日付: 2026-07-04
ブランチ: feature/v2-orchestration

## 背景・要件

ローカル `make build` 運用は維持しつつ、3 イメージ（claude / claude-vnc / docker-proxy）を GHCR へ GitHub Actions から**毎日・マルチアーキ(amd64/arm64)**で push し、`YYYYMMDDHHmm`(JST)＋`latest` タグで識別。GHCR から `pull` して使う運用も可能にする。方針は AskUserQuestion で確認（pull 運用込み / multi-arch / 3 イメージ / 毎日）。

## 観点別所見

### 1. 要件・ユースケースに合致
- ワークフロー: `schedule`(03:30 JST 毎日)＋`workflow_dispatch`、3 イメージ×2 アーキ、`YYYYMMDDHHmm`＋`latest`。要件充足。
- pull 運用: `claude-dev pull [TAG]` で GHCR から取得しローカル名へ retag → `start` は再ビルドせず使用。generic user イメージのユーザー名差は CLI の `CONTAINER_USER` 解決で吸収。

### 2. 無駄な処理
- arm64 をネイティブ runner（`ubuntu-24.04-arm`）でビルドし、遅い QEMU エミュレーションを回避。`cache-from/to: gha`（image×arch scope）で日次差分ビルドを高速化。
- CUSER 解決は起動時に `docker image inspect` 1 回。ローカル既存イメージでは従来と同一値（t-kubo）に解決＝後方互換で無駄な変更なし。

### 3. 処理時間
- push-by-digest＋imagetools merge の並行ビルドで wall-clock を短縮。`provenance: false` で余分な attestation を作らない。

### 4. セキュリティ
- push は `GITHUB_TOKEN`（`packages: write` のみ付与、`contents: read`）。追加の PAT 不要。
- generic user（`dev`/1000/1000）で焼くため特定ユーザーの UID/GID・ユーザー名を配布物に含めない。UID/GID は実行時に entrypoint が `/workspace` 所有者へ追従。
- private パッケージ時の pull は `docker login ghcr.io`（PAT）が必要である旨を明記。
- 共有 Dockerfile は不変（generic user はビルド時 build-arg で付与）。

## 検証結果（本環境で実施可能な範囲）

- `bash -n`：`claude-dev` / `claude-dev-mac` とも構文 OK。
- CUSER 解決：現行ローカルイメージ（`CONTAINER_USER=t-kubo`）から `t-kubo` を解決＝**後方互換**を確認。
- ワークフロー YAML：Ruby(psych) でパースし構造を確認（jobs=prepare/build/merge、triggers=schedule+workflow_dispatch、build matrix=3×2=6、merge=3、permissions=contents:read/packages:write、cron=`30 18 * * *`、generic user=dev/1000/1000、tag=`date +%Y%m%d%H%M` JST）。
- `pull` 失敗パス：存在しないタグで 3 イメージを試行→各警告→`❌ すべての pull に失敗`→`exit 1`、private 用 `docker login` 案内を確認。
- 整合性：`ghcr.io/quvox` が設計/`.env.example`/両 CLI 既定で一致。新規 docs の相対リンク宛先すべて実在。

## 未検証・要実機確認（本環境の制約）

- **GHCR への実 push（GitHub Actions 実行）**：本環境から Actions は動かせないため未実行。初回は `workflow_dispatch` で手動起動し、6 build ジョブ＋3 merge ジョブの成功と、GHCR に `:YYYYMMDDHHmm`/`:latest` の manifest list（amd64+arm64）が現れることを確認する必要がある。
- **`ubuntu-24.04-arm` runner の可用性**：public リポジトリは無料。private の場合は利用可否/課金を確認し、不可なら QEMU 単一 runner へ切替（90_ghcr-workflow.md に代替手順を記載）。
- **pull→start の実イメージでの疎通**：GHCR に push 後、`claude-dev pull` で generic(dev) イメージを取得し `start` で UID/GID 追従・マウント（/home/dev）が正しく動くことを実機確認する。ロジック（CUSER=dev 解決、retag、entrypoint の UID/GID 追従）はレビュー済みだが実イメージでの通し確認は push 後に行う。

## 結論

設計・実装仕様・実装は整合し、本環境で可能な静的検証・失敗パス・後方互換は確認済み。GHCR への実 push と pull→start の通し確認は、初回 `workflow_dispatch` 実行後に実機で行う（上記「未検証」）。ローカル `make build` 運用への影響はなく後方互換。

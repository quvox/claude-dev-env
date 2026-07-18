---
title: 配布イメージは generic user で焼き、UID/GID は実行時に追従させる
summary: 特定ユーザーの UID/GID・名前をイメージに埋めず dev/1000/1000 で焼く。実行時 entrypoint が /workspace 所有者へ UID/GID を追従し、CLI が CONTAINER_USER を image inspect で吸収。arm64 は QEMU でなくネイティブ runner でビルド
---

## 状況

3 イメージ（claude / claude-vnc / docker-proxy）を GitHub Actions から毎日・マルチアーキ
（amd64/arm64）で GHCR へ push し、`claude-dev pull` で取得して使う配布運用を追加した。ローカル
`make build` 運用（特定ユーザー名 t-kubo で焼く）とは後方互換を保つ必要があった。

## 判断

- **generic user（`dev`/1000/1000）でイメージを焼く**。特定ユーザーの UID/GID・ユーザー名を配布物に
  含めない。UID/GID は実行時に entrypoint が `/workspace` の所有者へ追従する。CLI 側は起動時に
  `docker image inspect` 1 回で `CONTAINER_USER` を解決し、ローカル既存イメージでは従来と同一値
  （t-kubo）に解決＝後方互換。共有 Dockerfile は不変（generic user はビルド時 build-arg で付与）。
- **arm64 はネイティブ runner（`ubuntu-24.04-arm`）でビルド**し、遅い QEMU エミュレーションを回避。
  `cache-from/to: gha`（image×arch scope）で日次差分を高速化、push-by-digest＋imagetools merge の
  並行ビルドで wall-clock を短縮、`provenance: false` で余分な attestation を作らない。
- push は `GITHUB_TOKEN`（`packages: write` のみ、追加 PAT 不要）。private パッケージの pull 時のみ
  `docker login ghcr.io`（PAT）が要る旨を明記。

## 一般化した教訓（今後どう活かすか）

- **配布イメージにビルド者固有のアイデンティティ（ユーザー名・UID/GID）を埋め込まない**。generic user
  で焼き、**UID/GID はマウント先の所有者へ実行時追従**、名前差は CLI が inspect で吸収する。これで
  同じイメージが誰の環境でも動き、ローカルビルド運用とも後方互換になる。
- **マルチアーキ CI は QEMU エミュレーションでなくネイティブ runner を第一候補にする**（public は無料。
  private は可用性/課金を要確認、不可なら QEMU 単一 runner へ切替の代替手順を用意）。gha キャッシュ・
  push-by-digest＋imagetools merge・`provenance:false` が定番の高速化。
- push の権限は `GITHUB_TOKEN` の `packages: write` で足り、追加 PAT を要求しない。

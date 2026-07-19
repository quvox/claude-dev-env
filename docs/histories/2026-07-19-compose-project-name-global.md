---
slug: compose-project-name-global
layer: history
title: docker compose プロジェクト名の一意化を全シェルへ（-e で付与）
date: 2026-07-19
trigger: バグ起因の仕様修正＋要件明記（複数プロジェクト同時起動時の compose 衝突）
origin_layer: requirements
affected:
  - doc: docs/00-requests/decisions.md
    version: 1.0.0 -> 1.1.0
  - doc: docs/01-requirements/core.md
    version: 1.0.0 -> 1.1.0
  - doc: docs/02-design/system.md
    version: 1.0.1 -> 1.1.0
  - doc: docs/03-impl/entrypoint.md
    version: 1.0.0 -> 1.1.0
  - doc: docs/03-impl/cli.md
    version: 1.1.0 -> 1.2.0
  - doc: docs/03-impl/cli-mac.md
    version: 1.0.0 -> 1.1.0
---

# 変更記録:docker compose プロジェクト名の一意化を全シェルへ

## 変更理由・背景

異なる 2 プロジェクト（`../ct_matchsupport` と `../mockup-kousoku`）で `claude-dev` を同時起動し、
各コンテナ内で `docker compose` を動かすとコンテナ名・ネットワーク名（`workspace_default`,
`workspace-<svc>-1`）が衝突して正しく動作しなかった。全プロジェクトがコンテナ内で `/workspace` に
マウントされるため compose の既定プロジェクト名が `workspace` に固定されるのが原因。

衝突防止のための `COMPOSE_PROJECT_NAME` 一意化は元々 entrypoint が rc（`/etc/zsh/zshrc`・
`/etc/bash.bashrc`）へ追記していたが、rc は対話シェルしか読まないため、Claude Code が実行する
非対話シェル（`bash -c "docker compose ..."`）では未設定となり衝突が再発していた。既存の意図
（衝突防止）は正しく、その実装が不十分だった（対称にある `DOCKER_HOST` は `-e` で全シェルに効く）。

なお `claude-dev-net`（claude コンテナ ↔ docker-proxy）は共有 proxy を前提とした意図的な共有
ネットワークであり、本件とは無関係（変更しない）。

さらに利用者がこの分離を「要求事項」と明言したため、実装詳細に留めず要件として明記する
（compose 層の分離で十分・claude-dev-net は共有維持、と利用者確認済み）。

## 変更内容の要約

- 00-requests/decisions.md: 決定 D-24（compose リソースのプロジェクト間分離を必須化＝
  `COMPOSE_PROJECT_NAME` 一意化。claude-dev-net は共有維持）を追加。決定数を19に更新。
- 01-requirements/core.md: 要件7 に受入基準5（複数プロジェクト同時 `docker compose` 時の
  ネットワーク名・コンテナ名の非衝突）を追加。
- 02-design/system.md: 要件カバレッジ確認表の core/7 行に cli/cli-mac（7-5）を追記し、
  テスト戦略に compose 一意化の実機確認備考を追加。
- 03-impl/cli・cli-mac: `start` の `docker run` に `-e COMPOSE_PROJECT_NAME=<compose互換名>` を
  付与（`NAME` を小文字・`[a-z0-9_-]` のみへ正規化）。`DOCKER_HOST` と同じく `-e` 方式のため、
  対話・非対話シェルと `docker exec` の全てで一意化が効く。
- 03-impl/entrypoint: COMPOSE_PROJECT_NAME を rc へ追記していたブロックを撤去（`-e` が全シェルに
  効くため冗長かつ値ズレの温床）。手順一覧の項目7を「entrypoint は関与せず CLI が `-e` で渡す」旨に更新。
- 実装（`claude-dev`・`claude-dev-mac`・`scripts/entrypoint-claude.sh`）を上記に同期。

---
slug: cli-attach-user-resolution
layer: history
title: 起動中コンテナへの attach 時のユーザー解決をコンテナ由来に修正
date: 2026-07-18
trigger: バグ起因の仕様修正（make build 後に既存コンテナへ attach 不能）
origin_layer: impl
affected:
  - doc: docs/03-impl/cli.md
    version: 1.0.0 -> 1.1.0
---

# 変更記録:起動中コンテナへの attach 時のユーザー解決をコンテナ由来に修正

## 変更理由・背景

`make build` でローカルイメージ（`claude-dev-claude:latest`）のユーザーがローカルビルド版
（`CONTAINER_USER=<whoami>`＝例 `t-kubo`）に置き換わると、GHCR の generic user イメージ
（`CONTAINER_USER=dev`）由来で**既に起動中のコンテナ**へ `claude-dev start`/`attach` すると
`docker exec -u t-kubo` が失敗し `unable to find user t-kubo: no matching entries in passwd file`
になった。原因は、exec 時のユーザー `CUSER` を**イメージのタグ**から解決していたため、稼働中
コンテナ（別イメージ由来）と食い違ったこと。

## 変更内容の要約

- コード（`claude-dev` / `claude-dev-mac`、いずれも generic）: `resolve_container_user()` を追加し、
  起動中コンテナへ exec する分岐（`start` 再接続／`code`／`orchestrate`／`attach`）で、`is_running`
  確認後に **そのコンテナ自身の `CONTAINER_USER`** から `CUSER` を解決するよう上書き。新規作成
  （create パス）とイメージビルドは従来どおりイメージ由来の `CUSER` を使用。firewall は `-u` 無しのため対象外。
- `docs/03-impl/cli.md`（1.0.0→1.1.0）: 「設定・環境変数」に `resolve_container_user` の役割と
  適用分岐、回帰（passwd エラー）の防止意図を追記し、実コードへ同期。
- `docs/03-impl/cli-mac.md`: 共有ロジックのため差分記述の変更なし（cli.md に委譲）。

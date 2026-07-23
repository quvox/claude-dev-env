---
slug: container-env-marker
layer: history
title: claude コンテナに container=docker 判定マーカーを追加
date: 2026-07-23
trigger: 要望（コンテナ内動作をプロセスが判定できるようにしたい）
origin_layer: request
affected:
  - doc: docs/00-requests/decisions.md
    version: 1.2.0 -> 1.3.0
  - doc: docs/03-impl/devcontainer.md
    version: 1.0.0 -> 1.1.0
---

# 変更記録:claude コンテナに container=docker 判定マーカーを追加

## 変更理由・背景

claude コンテナ内で動作するプロセス（entrypoint・各スクリプト・オーケストレーター等）が、
「自分がコンテナ内で動作しているか」を判定できるようにしたいという要望。判定手段として、
コンテナに環境変数 `container=docker` を持たせ、プロセスはこの変数の有無・値で判定する。

名前・値は独自に決めず、systemd/podman が採用する業界標準慣習（`container=<runtime>`）に
合わせることとした（外部ツールとの互換も同時に得られる）。全起動経路で必ず存在させたいため、
起動時 `-e` 付与（経路依存で漏れうる）ではなくイメージ焼き込み（`Dockerfile.claude` の base
ステージ `ENV`）で常時保証する。VNC 版は `FROM base` 継承で同値を持つ。

既存のイメージ焼き込み env マーカー（`CLAUDE_DEV_VNC=1` 等）と同種の実装詳細だが、
「全 claude コンテナに標準慣習の判定マーカーを持たせる」という横断的方針であるため、
利用者判断で 00-requests の決定台帳にも決定として残す（起点＝request 層）。

## 変更内容の要約

- 00-requests/decisions.md: 決定 D-25（全 claude コンテナに `container=docker` を焼き込み、
  コンテナ内動作の判定マーカーとする。systemd/podman 標準慣習に準拠。イメージ側で常時保証）を
  追加。決定数を 20 に更新。
- 03-impl/devcontainer.md: base ステージの「ビルド引数/環境」に `ENV container=docker`（D-25）を
  追記し、「設定・環境変数」表に同行を追加。
- 実コードへの反映（`.devcontainer/Dockerfile.claude` への `ENV container=docker` 追加）は
  本 /change の対象外。関係ドキュメントが検証済みになったのち `/implement` で行う。

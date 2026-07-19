---
slug: stop-compose-teardown
layer: history
title: claude-dev stop 時に compose コンテナ群も片付ける
date: 2026-07-19
trigger: 振る舞い変更(利用者要望)
origin_layer: request
affected:
  - doc: docs/00-requests/decisions.md
    version: 1.1 -> 1.2
  - doc: docs/01-requirements/core.md
    version: 1.1 -> 1.2
  - doc: docs/02-design/system.md
    version: 1.1 -> 1.2
  - doc: docs/03-impl/cli.md
    version: 1.2 -> 1.3
  - doc: docs/03-impl/cli-mac.md
    version: 1.1 -> 1.2
---

# 変更記録:claude-dev stop 時に compose コンテナ群も片付ける

## 変更理由・背景

`claude-dev stop` は当該 claude コンテナと `fwd-*` を削除するが、そのコンテナ内から
`docker compose` で起動されたコンテナ群（docker-proxy 経由でホスト daemon 上に作られ、
`com.docker.compose.project=<正規化NAME>` ラベルを持つ）は残り、孤児化していた。stop で
これらも一緒に片付けたい、という利用者要望。compose の起動側分離（D-24）に対する停止側の
ライフサイクル判断であり、要件レベルの判断のため 00（decisions.md）を起点に反映する。

片付け範囲は利用者確認により「`docker compose down` 相当」に決定: コンテナ＋当該プロジェクトの
compose デフォルトネットワークを削除し、名前付きボリューム（データ）は非破壊のため保持、共有の
`claude-dev-net`・docker-proxy も他プロジェクトが使用中のため残す。

## 変更内容の要約

- **00 decisions.md**: D-24 を「compose リソース分離**とライフサイクル**」に拡張。stop 時に
  ラベルで compose コンテナを特定して削除・デフォルトネットワーク削除・ボリューム保持・共有リソース
  温存・VM モード対象外の判断を追記。
- **01 core.md**: 要件1 受入基準6 に、当該コンテナ内から起動された compose コンテナ群と compose
  デフォルトネットワークの削除（`docker compose down` 相当・ボリューム保持・DooD 既定モード対象）を追記。
- **02 system.md**: テスト戦略に stop 時 compose 片付けの実機確認手順（core/1-6）を追記。
- **03 cli.md / cli-mac.md**: `stop` の処理説明に compose コンテナ群・デフォルトネットワークの
  削除を追記（cli.md を正本、cli-mac.md は同一挙動）。

---
slug: ghcr-version-label-cache
layer: history
title: バージョンラベルを build-arg から labels 入力へ移しレイヤーキャッシュを実効化
date: 2026-07-18
trigger: バグ起因の仕様修正（claude-dev pull が毎回全レイヤー再取得で遅い）
origin_layer: impl
affected:
  - doc: docs/03-impl/ghcr-workflow.md
    version: 1.0.0 -> 1.1.0
---

# 変更記録:バージョンラベルを build-arg から labels 入力へ移しレイヤーキャッシュを実効化

## 変更理由・背景

`claude-dev pull` が毎回、全レイヤーを再ダウンロードして遅い。原因は、日次で変わる
`IMAGE_VERSION`（タイムスタンプ）を build-arg で渡し、`Dockerfile.claude` 前段の `LABEL` へ
焼いていたこと。レイヤーチェーンの前段で cache key が毎日変わるため、以降の高コスト層が
すべて cache-miss→新ダイジェスト→pull 全再取得となり、CI の `cache-from: type=gha` が無効化されていた。

## 変更内容の要約

- コード（`.github/workflows/ghcr-images.yml`＝ghcr-workflow モジュール）: build-push-action の
  build-args から `IMAGE_VERSION` を削除し、`labels`（`io.github.quvox.claude-dev.version` /
  `org.opencontainers.image.version` = タグ）入力へ移動。バージョンは最終イメージの config
  メタデータとして export 時に付与され、レイヤーキャッシュ／ダイジェストに影響しなくなった。
- Dockerfile（devcontainer モジュール）は変更なし（CI が `IMAGE_VERSION` を渡さなくなり、既定
  `local` の定数となってキャッシュを失効させない。ローカルビルドのバージョン表示に引き続き使用）。
- `docs/03-impl/ghcr-workflow.md`（1.0.0→1.1.0）: build-args / labels / cache の記述を実装へ同期し、
  「日次で変わる値をレイヤーチェーンに入れない」運用注意を追記。
- `docs/knowledge/changing-label-busts-layer-cache.md` を追加（一般化した教訓）。

## 補足（効果の現れ方）

次回以降の CI ビルドから gha キャッシュが実効し、変更のない層は再ビルド／再 push されない。
利用者側の `docker pull` は、修正後の最初の1回は差分が大きいが、以降の日次 pull は tiny な
config と実際に変わった層だけの増分取得になる。レイヤー総数（base 62 / vnc 85）は据え置き
（適切に順序付けされた層は増分 pull で skip されるため、統合はむしろ変更時の再取得量を増やす）。

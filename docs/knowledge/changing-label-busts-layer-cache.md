---
title: 日次で変わる値をレイヤーチェーンに入れると pull が全再取得になる
summary: バージョン等の毎回変わる値を build-arg/LABEL でイメージ前段に入れると cache が失効し、docker pull が全レイヤー再取得になる。メタデータは labels 入力で最終イメージに付与する。
---

# 日次で変わる値をレイヤーチェーンに入れると pull が全再取得になる

## 状況

`claude-dev pull`（GHCR イメージの `docker pull`）が毎回、全レイヤーを再ダウンロードして遅い、
との指摘。base 62 / vnc 85 レイヤーと多いことも問題視された。調べると `Dockerfile.claude` の
先頭付近（base ステージの上部）に、日次で変わるタイムスタンプ `IMAGE_VERSION` を焼く
`LABEL io.github.quvox.claude-dev.version="${IMAGE_VERSION}"` が置かれ、CI が毎日異なる
`IMAGE_VERSION` を build-arg で渡していた。

## 判断（原因と対処）

- **原因**: BuildKit のキャッシュはチェーン。ある命令の cache key が変わると、それ以降の全命令が
  cache-miss になる。バージョンラベルがレイヤーチェーンの前段にあり、値が日次で変わるため、
  以降の高コスト層（apt 1.68GB・go/rust/pyenv/node 等）がすべて再ビルド→新しいレイヤーダイジェスト
  →`docker pull` が全再取得。CI は `cache-from: type=gha` を持っていたが、この失効で無効化されていた。
- **対処**: バージョンは build-arg/LABEL でレイヤーチェーンに載せず、**build-push-action の `labels`
  入力**で最終イメージの config メタデータとして付与する（export 時に適用され、レイヤーキャッシュ・
  レイヤーダイジェストに影響しない）。CI から `IMAGE_VERSION` build-arg を外し、`labels` を追加した。
  Dockerfile の `ARG IMAGE_VERSION=local`＋`LABEL` は据え置き（CI では定数 `local` になりキャッシュを
  失効させない。ローカルビルドのバージョン表示に使用。pushed イメージは `labels` が上書き）。

## 一般化した教訓（今後どう活かすか）

- **毎回変わる値（タイムスタンプ・ビルド番号・コミットハッシュ等）を build-arg / ENV / LABEL で
  レイヤーチェーンの前段に入れない**。入れるとキャッシュが実効せず、増分ビルド／増分 push／増分 pull
  がすべて崩れる。メタデータは最終イメージへ export 時に付与する（buildx/`build-push-action` の
  `labels`、または最終段の LABEL）。変えたい ARG はできるだけ後段に置く。
- **「レイヤーが多い」より「キャッシュが失効している」方が本質**なことが多い。適切に順序付けされた
  多数の層は増分 pull で skip されるので害は小さく、むしろ層を統合すると変更時の再取得量が増える
  （キャッシュ粒度が粗くなる）。まずキャッシュ失効の有無を疑う。
- 症状「毎回すべて再ダウンロード」を見たら、`docker history` で前段に日次可変な入力が無いか、
  CI が cache-from/to を持ちつつそれが効いているかを確認する。

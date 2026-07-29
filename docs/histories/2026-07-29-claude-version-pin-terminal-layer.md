---
slug: claude-version-pin-terminal-layer
layer: history
title: 同梱 Claude Code を latest ピン留めし、導入を配布ステージの終端レイヤーへ移す
date: 2026-07-29
trigger: バグ起因の仕様修正（GHCR 日次ビルドが更新されているのにコンテナ内 claude が古い）
origin_layer: request
affected:
  - doc: docs/00-requests/decisions.md
    version: 1.3.0 -> 1.4.0
  - doc: docs/01-requirements/core.md
    version: 1.2.0 -> 1.3.0
  - doc: docs/02-design/system.md
    version: 1.2.0 -> 1.3.0
  - doc: docs/03-impl/devcontainer.md
    version: 1.1.0 -> 1.2.0 -> 1.3.0     # 1.3.0 は実装反映時の同期（終端ステージの ARG 再宣言）
  - doc: docs/03-impl/ghcr-workflow.md
    version: 1.1.0 -> 1.2.0              # 実装反映時の同期不要（記述と実装が一致）
  - doc: docs/03-impl/makefile.md
    version: 1.0.0 -> 1.1.0 -> 1.3.0     # 1.2.0 は別エントリ（doc-check 指摘修正）、1.3.0 が実装反映の同期
  - doc: docs/03-impl/cli.md
    version: 1.3.0 -> 1.4.0 -> 1.5.0     # 1.5.0 は実装反映時の同期（setup/upgrade の配布ステージ名）
---

# 変更記録:同梱 Claude Code を latest ピン留めし、導入を配布ステージの終端レイヤーへ移す

## 変更理由・背景

「毎日 GitHub Actions でイメージを更新しているのに、コンテナ内の Claude Code が最新にならない」
という利用者の指摘から調査したところ、**日次ビルドは成功しているが中身が更新されていなかった**。

- 直近8回の日次実行はいずれも約1分で完了し、ログ上 `RUN curl -fsSL https://claude.ai/install.sh
  | bash` が毎回 `CACHED`。実ビルド時（4分43秒）と明確に差がある。
- 配布イメージに焼かれていた Claude Code は **2.1.214**（2026-07-19 ビルド時点）で凍結。
  ホスト側は 2.1.220（`latest`）。
- 原因は `2026-07-18-ghcr-version-label-cache` の副作用。当時「pull が毎回全レイヤー再取得」を
  直すため日次タイムスタンプを build-arg から `labels` へ移した結果、**レイヤーチェーンから
  日々変わる値が完全に消え**、claude 導入層が永久にキャッシュヒットするようになった。ラベル
  （＝バージョン表示とダイジェスト）だけが日次で変わるため、外から見ると更新されているように見える。
- キャッシュを落とす仕組み（`ARG CLAUDE_CACHE_BUST`）は存在したが、渡していたのは Makefile の
  `update-claude` だけで、CI は渡していなかった。
- 要件側にも穴があった。core/9 の受け入れ基準は「イメージにタイムスタンプタグを付与し、日次で
  更新しなければならない」で、**タグだけ変われば文字上は充足**してしまい、同梱 Claude Code の
  鮮度を要求していなかった。加えて 2026-07-18 に得た「pull は増分に保つ」という不変条件は 03 に
  しか書かれておらず、要件として保護されていなかったため、今回の退行が仕様上検出されなかった。

チャネル選択は D-11 に規定がなく該当する委任もないため人間に確認し、「`latest` を追随し、不良版を
引いた場合のみ手動でバージョンをピンする」方針が決定した（`stable` は段階的公開のため観測時点で
2.1.212 と、現に焼かれている 2.1.214 より古く、追随するとダウングレードになる）。

## 変更内容の要約

- **00-requests/decisions.md（1.3.0→1.4.0）**: D-26 を新規追加——①同梱 Claude Code は `latest`
  チャネルを CI で具体バージョンへ解決してピン留め（`install.sh` 引数なし既定＝`stable` は使わない）、
  ②`workflow_dispatch` 入力による手動ピンを逃げ道として用意、③バージョン文字列自体をキャッシュキー
  とし時刻由来の `CLAUDE_CACHE_BUST` は廃止、④「日次で更新」は同梱 claude が `latest` に追随する
  ことを含む。D-11 の証跡列に D-26 への参照を追記。
- **01-requirements/core.md（1.2.0→1.3.0）**: 要件9 の受け入れ基準を書き換え。曖昧な「日次で更新」を
  4項目（タグ付与／同梱 claude が `latest` に一致／手動指定時はその版／ラベルで版を参照可能）に
  具体化。非機能要件（性能・拡張性）に「日次更新後も `docker pull` は増分取得に留める」を追加し、
  2026-07-18 の不変条件を要件として保護。
- **02-design/system.md（1.2.0→1.3.0）**: 分割定義の devcontainer 行を 2ステージ→4ステージ
  （`base` / `vnc-base` / `claude-cli` / `claude-vnc`）に更新。設計判断4「Claude Code 導入は内容由来
  キーで配布ステージの終端レイヤーに置く」を追加し、却下した代替案3つと一般原則（レイヤーチェーンに
  入れてよいのは内容由来の値のみ、かつ失効の波及が最小になる終端に置く）を明記。
- **03-impl/devcontainer.md（1.1.0→1.2.0）**: ステージ表を追加し、`base`/`vnc-base` から Claude Code
  を除去。終端ステージ `claude-cli`/`claude-vnc` の節を新設（`ARG CLAUDE_VERSION=latest`、
  ユーザー権限での実行理由、`USER root` への復帰、2ステージへの意図的な重複記述）。環境変数表の
  `CLAUDE_CACHE_BUST` を `CLAUDE_VERSION` に差し替え。
- **03-impl/ghcr-workflow.md（1.1.0→1.2.0）**: prepare に outputs `claude_version`（`workflow_dispatch`
  入力優先、既定は `latest` チャネル取得、形式不一致は失敗）を追加。build の matrix target を
  `claude-cli`/`claude-vnc` に変更し build-args に `CLAUDE_VERSION` を追加。運用メモを「時刻由来の値は
  入れない／内容由来の値は必要で、終端レイヤーに置く」の対比に書き換え、凍結事例を記録。
- **03-impl/makefile.md（1.0.0→1.1.0）**: `--target` を新ステージ名に更新。`update-claude` を
  `CLAUDE_CACHE_BUST=$(date +%s)` から「`latest` を具体バージョンへ解決して `CLAUDE_VERSION` で渡す」
  方式へ変更（解決失敗時はフォールバックせずエラー中断——`latest` 文字列へ退避すると CI と同型の
  「更新したつもりで何も変わらない」状態になるため）。
- **03-impl/cli.md（1.3.0→1.4.0）**: `require_setup` の自動ビルドが使う `--target` を新ステージ名に更新。

## 補足（実装時の対象コード）

本エントリはドキュメント変更の記録であり、コード反映は `/implement` で行う。対象は
`.devcontainer/Dockerfile.claude`、`.github/workflows/ghcr-images.yml`、`Makefile`（`--target` 6箇所と
`update-claude`）、`claude-dev`／`claude-dev-mac`（`--target` 各6箇所。cli-mac.md はステージ名を
記載していないため文書更新は不要）。

## 実装反映（2026-07-29 追記）

上記コード反映を `/implement` で実施し、それに伴う 03-impl の同期を行った（affected の 3 段目）。
文書が先に更新され**コードが未反映のまま合格証が付いていた**状態は、同日の `/doc-check full` が
検出した（4 文書の合格証を剥落）。

- `.devcontainer/Dockerfile.claude`: `base` から claude 導入ブロック（`CLAUDE_CACHE_BUST` 付き）を削除、
  `vnc`→`vnc-base` へ改名、終端ステージ `claude-cli`(`FROM base`)／`claude-vnc`(`FROM vnc-base`) を追加。
- `.github/workflows/ghcr-images.yml`: `workflow_dispatch` 入力 `claude_version`、prepare の
  outputs `claude_version`（入力優先／`latest` 解決／形式不一致は失敗）、matrix target と
  build-arg `CLAUDE_VERSION` を追加。
- `Makefile`: `--target` 6箇所を配布ステージ名へ、`update-claude` を版解決方式へ。
- `claude-dev` / `claude-dev-mac`: `--target` 各6箇所を配布ステージ名へ。
- 03-impl の同期差分: **devcontainer.md 1.3.0** — 終端ステージで `ARG USERNAME` を再宣言する
  必要（ARG はステージスコープで `FROM` 継承されず、`USER $USERNAME` が空になる）を明記。
  **makefile.md 1.3.0** — 取得値の体裁検査と、1 レシピ行にまとめた理由（make は行ごとに別シェル）を明記。
  **cli.md 1.5.0** — `setup`／`upgrade` の説明に残っていた旧ステージ名 `base`/`vnc` を配布ステージ名へ修正。
  ghcr-workflow.md は記述と実装が一致したため同期不要（1.2.0 据置）。
- **未了（人間/CI 側の実機確認事項）**: 実イメージのビルドと、配布イメージ内 `claude --version` が
  ビルド時点の `latest` と一致することの突合（要件 core/9 受入基準3 の成果物検証）。
  緑ランプではなく成果物の中身で確かめる（`docs/knowledge/verify-automation-by-artifact-not-by-green-run.md`）。

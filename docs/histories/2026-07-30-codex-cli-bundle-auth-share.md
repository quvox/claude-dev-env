---
slug: codex-cli-bundle-auth-share
layer: history
title: Codex CLI をコンテナへ同梱し、認証情報をホストと共有する（D-27）
date: 2026-07-30
trigger: 要件追加(利用者要望)
origin_layer: request
affected:
  - doc: docs/00-requests/request.md
    version: 1.0 -> 1.1
  - doc: docs/00-requests/decisions.md
    version: 1.4 -> 1.5
  - doc: docs/00-requests/glossary.md
    version: 1.0 -> 1.1
  - doc: docs/00-requests/acceptance.md
    version: 1.0 -> 1.1
  - doc: docs/01-requirements/core.md
    version: 1.5 -> 1.6
  - doc: docs/02-design/system.md
    version: 1.4 -> 1.5
  - doc: docs/03-impl/devcontainer.md
    version: 1.3 -> 1.5          # 1.4=仕様更新 / 1.5=実装同期（ランチャー方式）
  - doc: docs/03-impl/entrypoint.md
    version: 1.1 -> 1.3          # 1.2=仕様更新 / 1.3=実装同期
  - doc: docs/03-impl/cli.md
    version: 1.5 -> 1.7          # 1.6=仕様更新 / 1.7=実装同期
  - doc: docs/03-impl/ghcr-workflow.md
    version: 1.2 -> 1.4          # 1.3=仕様更新 / 1.4=実装同期
  - doc: docs/03-impl/e2e.md
    version: 1.0 -> 1.2          # 1.1=仕様更新 / 1.2=実装同期
---

# 変更記録:Codex CLI をコンテナへ同梱し、認証情報をホストと共有する（D-27）

## 変更理由・背景

利用者から「claude コンテナで codex（OpenAI Codex CLI）も使えるようにしたい。codex は頻繁に更新される。
`codex login --device-auth` でログインする前提で、credential 情報をホストと共有できるようにしたい
（claude と同じ要件）」という要求があった。

従来の要求定義は Claude Code のみを前提としており、①コンテナに同梱するエージェント CLI が 1 つである
こと、②認証前提が Claude Pro/Max（OAuth）に限られること、の 2 点で現状の要求と食い違っていた。
そのため起点は 00-requests とした。

なお 00 層には「異種ベンダー worker（Codex 等）の常用可否」が要確認 D-22 として残っている。本変更の
スコープは**開発者がコンテナ内で codex を対話的に使える状態まで**であり、オーケストレーターが
worker/レビューアーとして codex を常用するかは D-22 のまま未決とした（利用者確認済み）。D-22 の論点欄に
その線引きを明記した。

バージョン方針は D-26（同梱 Claude Code の latest ピン留め）で得た教訓——`latest` を文字列のまま
build-arg に渡すとレイヤーキャッシュが永久ヒットし、ラベルだけ日次で変わって中身が凍結する——を
そのまま横展開し、CI で具体バージョンへ解決してピン留めする方式を採った。

## 変更内容の要約

- **00-requests/request.md**: §5 やること に「エージェント CLI の同梱（Claude Code + Codex CLI）と
  認証共有」を追加。§6 制約の認証行に OpenAI 側アカウント（デバイス認証）を追記。§7 の Should に
  「Codex CLI の同梱と認証共有」を追加し、Could の記述を「worker/レビューアーとしての常用」に限定して
  CLI 同梱と区別。
- **00-requests/decisions.md**: **D-27 を新規追加**（①同梱＝配布 2 イメージの終端レイヤーで
  `npm install -g @openai/codex@<具体バージョン>`、②バージョン＝CI prepare で npm registry の最新版を
  解決しピン留め・`workflow_dispatch` で手動指定可、③認証＝`auth.json` のみを既存 `claude-dev-auth`
  ボリュームの `codex/` 経由で共有・方式は D-3 と同じコピー＋30 秒書き戻し・`config.toml`/セッションは
  コンテナ固有、④導線＝独立サブコマンド `claude-dev login-codex`・`logout` は現状挙動維持、
  ⑤スコープ＝worker 常用は D-22 のまま未決）。D-22 の論点欄に D-27 との線引きを追記。
- **00-requests/glossary.md**: 用語「Codex CLI」を追加。紛らわしい概念の表に「Codex CLI の同梱（D-27）
  ⇔ 異種ベンダー worker の常用（D-22）」を追加。
- **00-requests/acceptance.md**: **AS-6**（Codex CLI をコンテナで使い、認証をホストと共有する）を追加。
- **01-requirements/core.md**: **UC-6** を追加（AS-6 対応）。要件3 に受け入れ基準 6〜9 を追加
  （`login-codex` によるデバイス認証と保存／起動時コピー／30 秒書き戻し／設定・履歴はコンテナ固有）、
  基準5 に「claude・codex 双方が消える」旨を明記。要件9 に受け入れ基準 6〜7（同梱 codex の版の鮮度・
  手動指定）を追加。**要件12「同梱エージェント CLI」を新規追加**（両 CLI の同梱・PATH 解決・ビルド時
  ピン留め・worker 常用は対象外）。非機能のシステム環境に OpenAI 側アカウントを追記、性能の pull 増分性を
  「同梱エージェント CLI」表現へ一般化。UC-1 の代替フローと関連要件、シナリオ外要件の注記を更新。
- **02-design/system.md**: 分割定義の cli（`login-codex`）・entrypoint（codex 認証コピー/同期）・
  devcontainer（両 CLI を終端で導入、core/12 追加）の各行を更新。契約「cli → コンテナ/entrypoint」に
  認証受け渡しの経路（claude / codex）を明記。データモデルに codex 認証ファイルを追加。設計判断3 に
  「codex はその場書き換えだが方式を 2 つ持たない」判断理由を追記、設計判断4 を「エージェント CLI の
  導入」へ一般化。要件カバレッジに core/12 を追加。テスト戦略に core/12 の実機確認備考、E2E シナリオ
  一覧に **E2E-6** を追加。UI設計の cli-commands に `login-codex` を追加。
- **03-impl/devcontainer.md**: ステージ表と概要を「エージェント CLI」表現へ更新。終端ステージ節に
  `ARG CODEX_VERSION` と `npm install -g @openai/codex@...`、`/usr/local/bin/codex` への symlink
  （非対話シェルからの解決保証）、実行時に Node を要する点を追記。環境変数表・テスト表・既知の制限・
  運用メモを更新。
- **03-impl/entrypoint.md**: 起動シーケンス9 に `~/.codex → /workspace/.codex` の symlink 化と
  `auth.json` の権限整備、13 の同期ループに codex 認証の書き戻しを追記。実装上の判断・データアクセス表・
  テスト表を更新。
- **03-impl/cli.md**: サブコマンド **`login-codex`** を追記（一時コンテナで `codex login --device-auth`
  →共有ボリューム `codex/` へ書き戻し）。`logout` の説明に codex 認証も消える旨、`start` の認証コピーに
  codex 分、`.gitignore` 追記対象に `.codex` を追加。テスト表を更新。
- **03-impl/ghcr-workflow.md**: prepare の outputs に `codex_version`（npm registry から解決、形式検証で
  早期失敗）、build-args に `CODEX_VERSION`、`workflow_dispatch` 入力 `codex_version`、エラー
  ハンドリング表・テスト表・運用メモを追加/更新。
- **03-impl/e2e.md**: **E2E-6** の実機確認手順をテスト対応表に追加（デバイス認証はブラウザ操作を伴い
  無人自動化できない点を既知の制限に明記）。
- **変更しなかったドキュメント**: `03-impl/cli-mac.md`（`login-codex` は OS 差分ではなく cli.md が正本。
  実装は `claude-dev-mac` にも反映が必要）、`03-impl/makefile.md`（`make login-codex` は追加せず
  `claude-dev login-codex` を直接使う）。

## 実装（コード反映）で確定した差分

`/implement`（作業 slug `codex-cli-bundle-auth-share`）でコードへ反映した際、03-impl を実装結果へ
同期して次の点を書き改めた。

- **devcontainer**: `/usr/local/bin/codex` は当初「symlink」と記述していたが、**ランチャースクリプト**に
  変更した。codex の実体が `#!/usr/bin/env node` の JS ランチャーであり、fnm 初期化のないシェル
  （`bash -c` / `docker exec`）では `node` が解決できず単純な symlink では起動しないため（実測で確認）。
  `${USER_HOME}/.local/share/fnm/aliases/default/bin` を PATH に前置して実体を `exec` する方式とし、
  `chromium-browser`／`claude-dev-chrome` の共通ランチャーと同じ流儀に揃えた。副作用として `codex` は
  素の PATH でも解決できる（`claude` は従来どおり rc の PATH 追記に依存）。
- **entrypoint**: 共有側（`~/.claude-shared/codex`）を認証段より前に `mkdir -p`＋`chown` で用意する点、
  イメージにはビルド時 `codex --version` が作る実 `~/.codex` が必ず存在し退避経路を必ず通る点、
  同期ループが root で走るため共有側ファイルが root 所有になる点を明記した。
- **cli**: `login-codex` は書き込み前に共有ディレクトリを `chown -R` する（上記の root 所有対策）。
  `start` の認証コピーは同一の一時コンテナに `/target-codex` を追加マウントして 1 回の `chown -R` に
  含める。`.gitignore` は `.claude`/`.codex` をループで冪等追記する。
- **ghcr-workflow**: `codex_version` は claude と同じ `steps.meta` 内で連続算出し、入力は env
  （`CODEX_VERSION_INPUT`）で受ける。`jq` が `null` を返すケースも同じ形式検証で落ちる。

## 検証結果

- 自動検証（AI 実行）: `go vet`（docker-proxy / orchestrator）・単体テスト（両 Go モジュール）・
  変更したシェル資産の `bash -n`・ワークフローの YAML パース、いずれも通過。Go コードは無変更。
- ビルド実測（AI 実行）: `--target claude-cli` のビルド成功、`codex --version`=0.146.0、素の PATH
  （`env -i PATH=...`）でも解決（core/12-1,2）。`CODEX_VERSION=0.144.6` を指定したビルドで指定版が
  入ることを確認（core/9-7・core/12-3）。
- コンテナ実測（AI 実行）: `~/.codex → /workspace/.codex` の symlink 化、イメージ内の実 `~/.codex` の
  退避、`auth.json` の `chmod 600`、共有ボリューム `codex/` の作成、`auth.json` 更新の書き戻し伝播、
  entrypoint の `✅ Ready` 到達（core/3-7,8,9）。
- **実機確認（利用者実行、2026-07-30 完了）: E2E-6（`login-codex` → 別プロジェクトで `start` →
  `codex` が再ログイン不要で起動）および E2E-1 の起動回帰。** これによりタスクの Definition of Done を
  全項目充足し、作業用タスクドキュメントを削除した。

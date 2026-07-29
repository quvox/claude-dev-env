---
slug: claude-version-pin-terminal-layer
layer: task
title: 同梱 Claude Code の latest ピン留めと配布ステージ終端レイヤー化をコードへ反映
date: 2026-07-29
source:
  - docs/03-impl/devcontainer.md
  - docs/03-impl/ghcr-workflow.md
  - docs/03-impl/makefile.md
  - docs/03-impl/cli.md
history: docs/histories/2026-07-29-claude-version-pin-terminal-layer.md
---

# タスク:同梱 Claude Code の latest ピン留めと配布ステージ終端レイヤー化をコードへ反映

## 目的

D-26（要件 core/9 受入基準3・4／02-design 判断4）を実装コードへ反映する。`Dockerfile.claude` の
Claude Code 導入を `base` 途中から配布ステージの終端レイヤー（`claude-cli`/`claude-vnc`）へ移し、
キャッシュキーを時刻由来（`CLAUDE_CACHE_BUST`）から内容由来（`CLAUDE_VERSION`）へ変える。
ステージ名変更は全呼び出し元（CI ワークフロー・Makefile・ホスト CLI）を同時に直さないとビルドが
壊れるため、D-26 の affected 4 モジュール（devcontainer / ghcr-workflow / makefile / cli(+cli-mac)）を
1 つの作業単位として扱う。

## 前提（ゲート状況の記録）

上流チェーン（00-requests/decisions.md 1.4.0・01-requirements/core.md 1.4.0・02-design/system.md 1.4.0）は
すべて verified。対象 03-impl 4 件は本日の `/doc-check full` で**「コードに未反映」を唯一の理由として**
合格証を剥がされた状態（循環: コードを直さないと再検証できない）。上流が全て verified であり、
剥落理由が本作業の対象そのものであるため、ゲートの趣旨は満たすと判断して着手する。
完了後に `/doc-check`（できれば新規セッションで `full`）で再検証する。

## タスク

- [x] 1. `Dockerfile.claude` を 5 ステージ化し Claude Code 導入を終端レイヤーへ移す
      _要件: core/9-3,9-4_ _Boundary: .devcontainer/Dockerfile.claude_ _Depends: なし_
  - [x] 1.1 `base` から Claude Code 導入ブロック（`ARG CLAUDE_CACHE_BUST` / `WORKDIR /tmp` /
        `RUN curl … install.sh | bash`）を削除する
  - [x] 1.2 `FROM base AS vnc` を `FROM base AS vnc-base` へ改名する（非配布の中間ステージ）
  - [x] 1.3 終端ステージ `claude-cli`(`FROM base`) / `claude-vnc`(`FROM vnc-base`) を追加。
        `ARG CLAUDE_VERSION=latest`、`USER $USERNAME`＋`WORKDIR /tmp` で
        `curl -fsSL https://claude.ai/install.sh | bash -s -- "$CLAUDE_VERSION"`、
        その後 `WORKDIR /workspace`＋`USER root` へ戻す（`base` 末尾と同じ状態にする）
- [x] 2. `ghcr-images.yml`：prepare で Claude Code の版を解決し build へピン留めする
      _要件: core/9-3,9-4_ _Boundary: .github/workflows/ghcr-images.yml_ _Depends: 1_
  - [x] 2.1 `workflow_dispatch` に入力 `claude_version` を追加
  - [x] 2.2 prepare に output `claude_version`（入力優先、空なら `latest` チャネルを curl 解決、
        `MAJOR.MINOR.PATCH` 形式でなければジョブ失敗）を追加
  - [x] 2.3 build matrix の target を `claude-cli`/`claude-vnc` へ、build-args に
        `CLAUDE_VERSION=${{ needs.prepare.outputs.claude_version }}` を追加
- [x] 3. `Makefile`：ビルド target 変更と `update-claude` の版解決
      _要件: core/9-3_ _Boundary: Makefile_ _Depends: 1_
  - [x] 3.1 `build-claude`→`--target claude-cli`、`build-claude-vnc`→`--target claude-vnc`、
        `upgrade` も同様に変更
  - [x] 3.2 `update-claude` を `CLAUDE_CACHE_BUST=$(date +%s)` から
        「`latest` チャネルを具体バージョンへ解決し `CLAUDE_VERSION` で渡す（解決失敗はエラー中断・
        フォールバックしない）」へ変更
- [x] 4. ホスト CLI（`claude-dev` / `claude-dev-mac`）の `--target` を配布ステージ名へ追随
      _要件: core/9-3, core/10_ _Boundary: claude-dev, claude-dev-mac_ _Depends: 1_ (P)
  - [x] 4.1 `require_setup` / `setup` / `upgrade` の 3 箇所 × 2 ファイルを
        `claude-cli`/`claude-vnc` へ変更

## Definition of Done

以下がすべて満たされたときに完了とする。**ビルドが通っただけでは完了ではない。**

- [x] 上記タスクの全チェックが完了している
- [x] `go vet ./...`（docker-proxy / orchestrator の各 Go モジュール）がエラーなしで通る
- [x] `cd docker-proxy && go test ./...` と `cd orchestrator && go test -mod=vendor ./...` が全パスする
- [x] 今回対象の受け入れ基準（core/9-3, 9-4）に対応する検証：Bash/Dockerfile/ワークフローに
      自動テストランナーは存在しない（tech steering）ため、静的検証で代替する——
      `docker buildx build --check`（`claude-cli`/`claude-vnc` 両 target）・ワークフロー YAML の
      パース・`bash -n`（Makefile は `make -n`）がすべて通る。**実イメージのビルドと
      `claude --version` 突合（受入基準3の成果物検証）は CI/実機で人間が確認する事項として残す**
- [x] 影響するE2Eシナリオ: E2E-1（`claude-dev start`）が本変更を横断するが、自動E2Eは未整備
      （e2e.md のとおり実機確認）＝**自動実行は対象外(自動E2Eなし)**、実機確認事項として引き継ぐ
- [x] 対象モジュールの 03-impl（devcontainer / ghcr-workflow / makefile / cli）が実装結果と
      一致するよう更新されている（テスト対応表含む。E2Eテストの追加・変更はなし＝e2e.md 更新不要）
- [x] 対応する history エントリ（2026-07-29-claude-version-pin-terminal-layer.md）の affected に
      今回更新した全ドキュメントの version 遷移が記録されている
- [x] この作業中に発生した 質問/修正/委任判断 がすべて `docs/feedback/log.md` に記録されている

## 進捗メモ

- 2026-07-29 着手。`/doc-check full` の指摘1（D-26 が文書のみでコード未反映）への対応。
- 事実確認済みの現状コード: Dockerfile は `orch-builder`/`base`/`vnc` の 3 ステージ、claude 導入は
  base の L200-206（`CLAUDE_CACHE_BUST` 付き）、workflow の target は `base`/`vnc`、
  Makefile と claude-dev/claude-dev-mac も `--target base`/`vnc`（各 3 箇所）。
- `base` は L126 `USER $USERNAME` → L211 `USER root` の区間があり、claude 導入は現状ユーザー権限で
  走っている。終端ステージでも同じ（`USER $USERNAME`＋`ARG USERNAME` 再宣言）にする。

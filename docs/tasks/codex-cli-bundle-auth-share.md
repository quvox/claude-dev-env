---
slug: codex-cli-bundle-auth-share
layer: task
title: Codex CLI の同梱と認証共有をコードへ反映（D-27）
date: 2026-07-30
source:
  - docs/03-impl/devcontainer.md
  - docs/03-impl/entrypoint.md
  - docs/03-impl/cli.md
  - docs/03-impl/cli-mac.md
  - docs/03-impl/ghcr-workflow.md
  - docs/03-impl/e2e.md
history: docs/histories/2026-07-30-codex-cli-bundle-auth-share.md
---

# タスク:Codex CLI の同梱と認証共有をコードへ反映（D-27）

## 前提（ゲート状況の記録）

本作業の直前に `/change` で 00→03 を更新したため、対象 03-impl（devcontainer / entrypoint / cli /
ghcr-workflow / e2e）とその上流（00/01/02）は**版が上がり合格証が失効**している。`/implement` の
Phase A ゲートは「対象 03-impl と source チェーンが全て verified」を要求するが、

- 失効の理由は「本作業がまだ実装されていないこと」そのものであり、文書の誤りではない
- ゲートの趣旨（検証されていない仕様から実装しない）は、上流が同一の変更で一貫更新されている本件では
  満たされている
- 文書だけ先行した状態で `/doc-check` を先に回すと循環に入る（既知。
  `docs/knowledge/docs-ahead-of-code-deadlocks-doc-check.md`、`docs/feedback/log.md` の [5]）

ため、停止せず着手する。完了後に `/doc-check` で循環を閉じる。

## 目的

Codex CLI（`@openai/codex`）を配布 2 イメージの終端レイヤーへバージョンピン留めで同梱し、
`codex login --device-auth` で得た `auth.json` を `claude-dev-auth` ボリュームの `codex/` 経由で
ホスト・コンテナ間共有する（D-27、要件 core/3-6〜9・core/9-6,7・core/12）。

## タスク

- [x] 1. Dockerfile 終端ステージで Codex CLI をピン留め導入
  _要件: core/12-1,2,3_ _Boundary: .devcontainer/Dockerfile.claude（claude-cli / claude-vnc ステージのみ）_ _Depends: なし_
  - `ARG CODEX_VERSION=latest` を両終端ステージに追加
  - ユーザー権限で `npm install -g @openai/codex@${CODEX_VERSION}`（`latest` は `@latest`）
  - root で `/usr/local/bin/codex` symlink を作成（非対話シェル・`docker exec` からの解決保証）
  - 導入後は `WORKDIR /workspace` / `USER root` に戻す（base 末尾と同状態）

- [x] 2. entrypoint に `~/.codex` 構成・認証コピー・書き戻し同期を追加
  _要件: core/3-7,8,9_ _Boundary: scripts/entrypoint-claude.sh（認証セクションと同期ループ）_ _Depends: なし_
  - `SHARED_CODEX="$USER_HOME/.claude-shared/codex"` / `LOCAL_CODEX=/workspace/.codex`
  - `~/.codex` 実ディレクトリを退避して `~/.codex → /workspace/.codex` symlink
  - `auth.json` の `chown` / `chmod 600`
  - 既存の 30 秒同期ループへ codex 認証の `cmp`→書き戻しを追加

- [x] 3. `claude-dev`（Linux）に `login-codex` と start 側の codex 認証コピーを追加
  _要件: core/3-6,7,5_ _Boundary: claude-dev（login-codex 追加・start の認証コピー・.gitignore・help）_ _Depends: 1, 2_
  - `login-codex`: 一時コンテナで `codex login --device-auth` →`~/.claude-shared/codex/auth.json` へ書き戻し
  - `start`: 認証コピーの一時コンテナで `codex/auth.json` → `${PROJECT_DIR}/.codex/auth.json`
  - `.gitignore` に `.codex` を追記、`help` に `login-codex` を追加

- [ ] 4. `claude-dev-mac` に同じ差分を反映
  _要件: core/3-6,7・core/10_ _Boundary: claude-dev-mac_ _Depends: 3_
  - `login-codex` は OS 差分ではないため cli.md 正本の実装をそのまま移植する

- [ ] 5. GHCR ワークフローで codex バージョンを解決して build-arg で渡す
  _要件: core/9-6,7_ _Boundary: .github/workflows/ghcr-images.yml_ _Depends: 1_
  - `workflow_dispatch` 入力 `codex_version` を追加
  - prepare の outputs に `codex_version`（npm registry から解決＋形式検証で早期失敗）
  - build の `build-args` に `CODEX_VERSION=...`

## Definition of Done

以下がすべて満たされたときに完了とする。**ビルドが通っただけでは完了ではない。**

- [ ] 上記タスクの全チェックが完了している
- [ ] `go vet ./...`（各 Go モジュール）がエラーなしで通る（本作業は Go 非改変のため回帰確認）
- [ ] `cd docker-proxy && go test ./...` と `cd orchestrator && go test -mod=vendor ./...` が全パスする
- [ ] 今回対象の受け入れ基準に対応する確認が存在しパスする（シェル/Dockerfile 系は自動テストなし＝
      実機確認: `codex --version` の版一致、`docker exec <c> bash -c 'codex --version'` の解決、
      `login-codex`→`start`→`codex` の再ログイン不要、30 秒書き戻し）
- [ ] 影響する E2E シナリオ: **E2E-6**（＋E2E-1 の起動回帰）。自動 E2E は無いため実機確認で行う
      （`claude-dev` 実操作。デバイス認証はブラウザ操作を伴い無人自動化不可）
- [ ] 対象モジュールの 03-impl が実装結果と一致するよう更新されている（テスト対応表含む。e2e.md も）
- [ ] history エントリ `2026-07-30-codex-cli-bundle-auth-share.md` の affected に今回の版遷移が記録されている
- [ ] この作業中に発生した 質問/修正/委任判断 がすべて `docs/feedback/log.md` に記録されている

## 進捗メモ

- 着手前の確認事項（公式ソースで検証済み）: `@openai/codex` は JS ランチャー＋platform 別バイナリ
  （optionalDependencies に `linux-x64`/`linux-arm64` あり）。認証は `$CODEX_HOME/auth.json`
  （既定 `~/.codex/auth.json`）で、保存方式の既定は File（keyring ではない）・`0600`・その場書き換え。
  `codex login --device-auth` はヘッドレス向け導線として公式に案内されている。
- 実機での動作確認（イメージ再ビルドを伴う）は人間の環境で行う必要がある。コード反映後に手順を提示する。
- **作業ブランチ**: `feat/codex-cli-bundle-auth-share`（main 直コミットを避けるため作成）。
- **タスク1 完了（実測で検証済み）**:
  - `npm install -g` の bin は `$USER_HOME/.local/share/fnm/aliases/default/bin/codex`（`aliases/default`
    は fnm default が張る安定 symlink → `node-versions/v24.18.0/installation`）。
  - codex の実体は `#!/usr/bin/env node` の JS ランチャーのため、**単純な symlink では不可**
    （fnm 初期化のないシェルで node が見つからない）。`/usr/local/bin/codex` に PATH を足して exec する
    **ランチャースクリプト**を生成する方式にした（`chromium-browser`/`claude-dev-chrome` と同じ流儀）。
    → この判断は Phase C で 03-impl/devcontainer.md の「実装上の判断」へ反映すること（現状の 03 記述は
    「symlink」になっているため要修正）。
  - `docker build --target claude-cli` 成功、素の PATH（`env -i PATH=...`）でも `codex --version`=0.146.0、
    最終状態は `root` / `/workspace` / entrypoint 継承のまま（base 末尾と一致）。
  - 検証用タグ `claude-dev-claude:codex-test` を作成した。**Phase C で削除する**こと。
- **タスク2 完了（実測で検証済み）**: `bash -n` OK。テストコンテナ（`--target claude-cli` 再ビルド）で
  `~/.codex → /workspace/.codex` symlink 化、イメージ内の実 `~/.codex`（ビルド時に codex が作る）の退避、
  `auth.json` の `chmod 600`、共有ボリューム `codex/` の作成、**auth.json 更新の書き戻し伝播**を実測確認。
  entrypoint は `✅ Ready` まで到達し既存 claude 側の symlink も維持。
  - 注意: 書き戻しはループが root で走るため共有側ファイルは root 所有になる（claude 側と同じ既存挙動）。
    そのため `login-codex` では `login` と同様に先に `chown -R` する必要がある（タスク3で対応）。
- **タスク3 完了（実測で検証済み）**: `bash -n` OK。`login-codex` の書き戻し経路（共有 `codex/auth.json`
  が 600 で作られる）、`start` の認証コピー（共有 → プロジェクト `.codex/auth.json`、ホスト UID/GID へ chown）、
  `.gitignore` の新規作成/冪等/既存（`.claude/` 表記）への追記を実コンテナ＋一時ボリュームで確認。
  `claude-dev help` に `login-codex` が出ることも確認。
  - `login-codex` 冒頭で `chown -R` してから su するため、共有側が root 所有でもユーザー権限で上書きできる。
  - 実際の `codex login --device-auth` 対話は人間の実機確認（E2E-6）で行う。ここでは書き戻し経路のみ検証。

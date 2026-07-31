---
id: tech
layer: steering
title: 技術スタックと標準コマンド（tech steering）
updated: 2026-07-31
summary: >
  言語・ビルド・テストの標準。テスト/ lint コマンドはここが唯一の正（DoD 検証で使用）。
  Codex 実行設定（監査は添付方式に固定）もここ。
keywords: [bash, Go, Docker, Makefile, go-test, pytest, ビルドコマンド, Codex, 添付方式]
---

# 技術スタックと標準コマンド

## 言語・ランタイム

| 領域 | 技術 |
|---|---|
| ホスト CLI / スクリプト | Bash（`claude-dev`, `claude-dev-mac`, `scripts/*.sh`, `scripts/vm`） |
| docker-proxy | Go 1.22（HTTP リバースプロキシ） |
| orchestrator | Go 1.24（bubbletea/lipgloss TUI、`vendor/` 同梱） |
| コンテナ | Docker マルチステージビルド（ubuntu:24.04 ベース）、GitHub Actions で GHCR 配布 |
| サンプル題材 | Python + pytest（`examples/orch-sample/` のみ） |

## ビルド（Makefile）

- `make setup` — 初期セットアップ
- `make build` — claude（VNC なし）+ claude-vnc + docker-proxy を一括ビルド
- `make build-claude` / `make build-claude-vnc` — 個別ビルド（vnc は base に続けてビルド）
- `make build-docker-proxy` / `make build-orchestrator`
- `make install` / `make uninstall` — CLI を PATH へ配置/除去
- `make login` — 認証（一時コンテナ）
- `make orch-sample` / `make orch-sample-clean` — オーケストレーター自己検証題材
- 補助: `make status` / `make clean` / `make network` / `make volumes` / `make env` / `make update-claude` / `make upgrade`

## テスト / lint（DoD で使用する唯一の正）

| レベル | コマンド | 対象 |
|---|---|---|
| 単体（Go: docker-proxy） | `cd docker-proxy && go test ./...` | プロキシの検査ロジック |
| 単体（Go: orchestrator） | `cd orchestrator && go test -mod=vendor ./...` | コントローラ/状態/レビュー等（17 テストファイル） |
| 単体（Python サンプル） | `cd examples/orch-sample && pytest` | 題材プロジェクト（オーケストレーター題材） |
| lint | `go vet ./...`（各 Go モジュール）。Bash には自動 lint を設けていない | — |
| E2E | オーケストレーター自己検証（`make orch-sample` で題材に対し実走） | 下記 |

- Bash スクリプトに自動テストランナーはない。動作確認は実機（コンテナ起動）で行う。
- E2E は「バンドルしたサンプルサブプロジェクトに対してオーケストレーターを実走させる」自己検証方式。

## 横断的な技術判断（詳細は 02-design）

- Docker 生ソケットはコンテナにマウントしない。`docker-proxy` 経由で制限付き Docker API を使う。
- 認証共有は symlink ではなく「コピー＋30秒ごとのバックグラウンド同期」で行う（アトミック書き込み対策）。
- 重い Docker 案件はオプトインの **VM モード**（QEMU+virtiofs、VM 内ネイティブ Docker）を使う。

## Codex実行設定 ※節名固定(/codex-audit・/codex-qa が参照)

- Codex連携: 有効（claude コンテナに同梱、`codex` は PATH 上。認証は共有ボリューム経由。D-27）
- フロントエンド: CLI（`codex exec`）。MCP サーバは登録していない
- **必須フラグ: 監査・QA で codex を呼ぶときは常に `-c features.use_legacy_landlock=true` を付ける。**
  このコンテナでは codex 既定の bubblewrap サンドボックスが起動できない（seccomp が `CLONE_NEWUSER` を
  拒否、AppArmor が `mount --make-rslave /` を拒否。D-27 ⑥ /
  `docs/knowledge/nested-agent-sandbox-blocked-by-container-confinement.md`）。この legacy landlock
  バックエンドは user namespace を使わないため、コンテナの confinement を緩めずに動く。
  **付け忘れると読み取りコマンドが全て失敗するが `codex exec` の終了コードは 0 のまま**なので、
  成否は終了コードではなく最終メッセージと成果物で判定する。
- 監査の実行方式: **スコープ渡し（上記フラグ付き）を既定とする**。添付方式は予備
  （フラグが将来の codex で撤去された場合の退避先。/codex-audit §6.1）。
- サンドボックス疎通確認: `codex sandbox --enable use_legacy_landlock -- /bin/true` が exit 0、
  かつ `codex sandbox --enable use_legacy_landlock -- /bin/sh -c 'touch /tmp/x'` が失敗すること。
  フラグ無しの `codex sandbox -- /bin/true` は exit 1（bwrap）で、これは既知・正常。
  `codex doctor` はこの故障を検知しない。
- 実測（2026-07-31、`claude-dev-claude` 上の codex-cli 0.146.0）:
  - read-only（landlock）: 読み取り成功、`/tmp` と `/workspace` への書き込みは拒否、
    ネットワークも遮断（名前解決不可）＝ 読み取り専用が実効的に強制されている。
  - `diff` モード（`codex exec review --uncommitted -c sandbox_mode="read-only"`）: フラグ付きで
    差分を読み P1 指摘を返す。フラグ無しの対照実行は bwrap エラーで無指摘。
  - **QA（`--sandbox workspace-write`）は landlock 経路でも書き込みが失敗する** → **QA は
    `-c sandbox_mode="danger-full-access"`（＝コンテナの既定）で走らせる**（2026-07-31 の人間判断。
    理由「コンテナ自体が隔離空間だから、これ以上の隔離は不要」＝ D-1 の一貫適用。D-27 ⑥）。
    これは CLAUDE.md 不変条件5「監査・QA でサンドボックス迂回を使わない」からの**意図的な逸脱**で、
    コンテナ内で実行する場合に限る。QA の他の制約（専用 seed・ブラウザ排他・テスト成果物ディレクトリ
    以外を書かない・終了時に reset）はそのまま守る。判断の経緯は
    `docs/knowledge/container-is-the-only-isolation-boundary-for-agent-qa.md`。
- コンテナ側の seccomp/AppArmor は緩めない（要件 core/12-7）。
- **監査（`docs`/`readiness`/`diff`）では `--dangerously-bypass-approvals-and-sandbox` /
  `--sandbox danger-full-access` を使わない**（read-only + landlock で足りるため。CLAUDE.md 不変条件5）。
  **QA レーンのみ上記の例外**（`sandbox_mode="danger-full-access"`。理由・範囲・維持する制約は上の QA 行）。
  開発者の対話利用向けには `config.toml` 既定で別途無効化済み（要件 core/12-5）。
- git 未初期化のリポジトリでは `--skip-git-repo-check` を付ける（承認・サンドボックスの迂回ではない）。
- **イメージ更新時の注意**: `use_legacy_landlock` は codex 0.146.0 時点で deprecated（起動時に
  「will be removed soon」と警告）。`CODEX_VERSION` は build 時に latest を解決するため、イメージを
  更新したら上記の疎通確認を再実行する。撤去された場合の退避先は添付方式。
- プロファイル名: 未定（`docs-audit` / `qa` は未作成。codex 既定設定で走らせる）
- 実行種別ごとのモデル・推論強度: 未定（codex 既定。固定値を決めたらここに書く）
- タイムアウト: 監査 900 秒 / QA 未定
- テスト成果物ディレクトリ・seed/reset コマンド・ブラウザ排他方式: 未定（QA レーンは未運用）
- CDP エンドポイント: `http://localhost:9222`（コンテナ内 `claude-dev-chrome`）
- ロールアウトフェーズ: 1 観測モード

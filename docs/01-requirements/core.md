---
id: core
layer: requirements
title: 開発環境基盤 要件定義書
version: 1.9.0
updated: 2026-07-31
verified:
  at: 2026-07-31
  version: 1.9.0
  against:
    - doc: docs/00-requests/request.md
      version: 1.1
    - doc: docs/00-requests/decisions.md
      version: 1.7
    - doc: docs/00-requests/glossary.md
      version: 1.3
    - doc: docs/00-requests/acceptance.md
      version: 1.3
summary: >
  Claude Code を隔離Dockerコンテナで動かす開発環境基盤の要件。コンテナ管理・認証・SSH鍵・
  ネットワーク/FW・ブラウザ確認・ポートフォワード・Dockerアクセス制限・VMモード・配布/プラットフォーム・
  同梱エージェント CLI（Codex CLI。サンドボックス方針を含む）。
keywords: [コンテナ, 認証, SSH, ファイアウォール, docker-proxy, ポートフォワード, VMモード, GHCR, CodexCLI, Codexサンドボックス]
depends_on: []
source:
  - docs/00-requests/request.md
  - docs/00-requests/decisions.md
  - docs/00-requests/glossary.md
  - docs/00-requests/acceptance.md
---

# 要件定義書:開発環境基盤

## 概要

本領域は、Claude Code を安全な Docker コンテナ内で動かす開発環境基盤の要件を定める。上流:
[要求定義](../00-requests/request.md)・[決定台帳](../00-requests/decisions.md)。オーケストレーターの要件は
[orchestration.md](orchestration.md) に分離する（本領域に依存する）。

## 用語定義

用語は [glossary.md](../00-requests/glossary.md) に従う（claude-dev / Claude コンテナ / docker-proxy /
forward プロキシ / DooD / VM モード 等）。

## ユースケース

### UC-1:プロジェクトを隔離コンテナで開発開始（AS-1）

- **アクター:** 社内の開発者
- **目的:** 自分のリポジトリを隔離環境で Claude Code 開発する
- **事前条件:** `make setup` と OAuth ログイン済み
- **基本フロー:**
  1. 開発者がプロジェクトディレクトリで `claude-dev start` を実行する
  2. システムはカレントディレクトリを `/workspace` にマウントしたコンテナを起動し、認証・ファイアウォール・
     （VNC ありなら）ブラウザ環境を設定し、tmux セッションを開始する
  3. 開発者は tmux 内で `claude` を実行する
- **代替・例外フロー:**
  - `--no-vnc` 指定時: Chrome/VNC を起動せず軽量コンテナを使う
  - 同一ディレクトリで再実行時: 既存コンテナに再接続する（tmux が無ければ再作成）
  - Codex CLI を使う場合: 基本フロー3 で `claude` の代わりに（または並行して）`codex` を実行する（UC-6）
- **事後条件(成功時):** プロジェクト専用コンテナで Claude Code が動作している
- **関連要件:** 要件1、要件2、要件4、要件5（基本フロー2 のファイアウォール設定）、要件11（同 VNC ありのブラウザ環境）、要件12（代替フローの `codex` 実行）

### UC-2:Webアプリをクライアントのブラウザで確認（AS-2）

- **アクター:** 社内の開発者（Linux + SSH 運用）
- **目的:** コンテナ内 Webアプリを手元のブラウザで確認する
- **事前条件:** コンテナ内で Webアプリが `0.0.0.0` で待ち受けている
- **基本フロー:**
  1. サーバ上で `claude-dev forward <port>` を実行する
  2. システムはホスト側ポート（8100〜）を割り当て、`fwd-<name>-<port>` プロキシを立て、クライアント用の
     `ssh -O forward` コマンドを表示する
  3. 開発者がクライアントで SSH トンネルを張り、`http://localhost:<host-port>` を開く
- **事後条件(成功時):** クライアントのブラウザにコンテナ内 Webアプリが表示される
- **関連要件:** 要件6

### UC-3:危険な Docker 操作が拒否される（AS-3）

- **アクター:** 社内の開発者（コンテナ内から Docker を使う）
- **目的:** ホストを危険に晒さずにコンテナ内から Docker を使う
- **事前条件:** 既定 DooD 構成（`DOCKER_HOST` が docker-proxy を指す）
- **基本フロー:**
  1. コンテナ内で `docker run` 等を実行する
  2. システム（docker-proxy）はエンドポイントとボディを検査する
- **代替・例外フロー:**
  - `/` 等ホストバインドマウント・privileged・host ネットワーク/PID → 拒否する
  - `/workspace` 配下の bind → 実ホストパスに書き換えて許可する（既定）
  - バインドを含まない通常操作 → 許可する
- **事後条件(成功時):** 危険操作が遮断され、安全な操作のみが Docker Engine に届く
- **関連要件:** 要件7

### UC-6:Codex CLI をコンテナで使う（AS-6）

- **アクター:** 社内の開発者
- **目的:** 一度のデバイス認証で、どのプロジェクトのコンテナでも codex を使う
- **事前条件:** `make setup` 済み。OpenAI 側アカウント（ChatGPT プラン等）を持っている
- **基本フロー:**
  1. 開発者がホストで `claude-dev login-codex` を実行する
  2. システムは一時コンテナで `codex login --device-auth` を起動し、認証 URL とコードを表示する
  3. 開発者がブラウザでデバイス認証を完了する
  4. システムは認証ファイル（`auth.json`）を共有ボリュームへ保存する
  5. 開発者がプロジェクトディレクトリで `claude-dev start` し、tmux 内で `codex` を実行する
  6. 開発者が codex に、ファイルの読み書きとコマンド実行を伴う作業を依頼する。システムは既定設定
     （要件12-5 の 3 鍵）のもとでシェルコマンドを実行し、`/workspace` のファイルを読み書きする
  7. 開発者が別の使い方として、サンドボックスを明示指定した読み取り専用（`--sandbox read-only`）で
     調査だけを依頼する。システムは landlock バックエンドで読み取りを成功させ、書き込みは拒否する
- **代替・例外フロー:**
  - 共有ボリュームに既に codex 認証がある場合: `login-codex` は不要（`start` 時にコピーされる）
  - デバイス認証を完了せず終了した場合: 認証は保存されず、次に `codex` を実行しても未認証のままとなる
  - `workspace-write` を明示指定した場合: landlock では書き込みが成立しないため本 UC の対象外
    （書き込みを伴う自動化は `danger-full-access` で実行する。要件12-9）
- **事後条件(成功時):** 別プロジェクトのコンテナでも再ログインなしで codex が使え、通常依頼では
  シェル実行と読み書きが成功し、読み取り専用指定では読み取り成功かつ書き込み拒否になる
- **関連要件:** 要件3（認証の共有）、要件12（同梱エージェント CLI。基本フロー6 が要件12-4、
  基本フロー7 が要件12-9、両者の前提となる既定設定が要件12-5,12-6）

### シナリオ外要件

- 認証ログイン（要件3）は独立した保守操作のため UC を持たない（AS では前提扱い）。ただし codex の
  デバイス認証は UC-6 の基本フローそのものであり、UC を持つ。
- イメージ配布（要件9）・macOS 対応（要件10）・VM モード（要件8）は横断的な提供形態であり、
  UC-1〜3 のフロー内で「どの環境でも同じ操作ができる」形で満たされる。
- ただし要件9 の受け入れ基準1〜4・6〜7（マルチアーキ push・タグ付与・同梱エージェント CLI の版・手動指定）は**ビルド時の
  性質**であり、UC のフロー中に現れない。これらは利用者操作ではなく CI 側の成果物検証で確認する
  （検証手段は 03-impl/ghcr-workflow.md のテスト表が持つ）。

## 機能要件

### 要件1:コンテナのライフサイクル管理

**ユーザーストーリー:** 開発者として、プロジェクトごとに隔離コンテナを起動・再接続・停止したい。
なぜなら複数案件を並行し、SSH 切断後も作業を維持したいから。

#### 受け入れ基準

1. WHEN `claude-dev start` を実行したとき、システムはカレントディレクトリを `/workspace` にマウントした
   コンテナ（既定=VNC あり `claude-dev-claude-vnc`）を起動し tmux にアタッチしなければならない
2. WHERE `--no-vnc` が指定された場合、システムは VNC/Chrome を持たない軽量イメージ `claude-dev-claude` を使わなければならない
3. WHILE コンテナが起動している間、SSH 切断や tmux デタッチ（`Ctrl-_ D`）が起きてもコンテナは動作を継続しなければならない
4. WHEN 同一ディレクトリで `claude-dev start` を再実行したとき、システムは既存コンテナに再接続しなければならない（tmux セッションが無ければ再作成する）
5. WHEN `claude-dev list` を実行したとき、システムは実行中セッション一覧（noVNC URL・フォワード状況を含む）を表示しなければならない
6. WHEN `claude-dev stop <name>` を実行したとき、システムは当該コンテナを削除し、さらに当該コンテナ内から起動された compose コンテナ群（ラベル `com.docker.compose.project=<正規化name>`）と当該プロジェクトの compose デフォルトネットワークを削除（`docker compose down` 相当。名前付きボリュームは保持）し、全 Claude コンテナ停止時には docker-proxy コンテナも停止しなければならない（compose の片付けは DooD 既定モードが対象。VM モードでは compose はゲスト内 Docker で完結する）

### 要件2:UID/GID 追従とホスト資産の共有

**ユーザーストーリー:** 開発者として、コンテナ内のファイル所有権がホストと一致し、git 設定を引き継ぎたい。

#### 受け入れ基準

1. WHEN コンテナを起動したとき、システムはユーザーの UID/GID をホスト（`/workspace`）に一致させなければならない
2. WHERE ホストに `~/.gitconfig` が存在する場合、システムはそれを読み取り専用でマウントしなければならない
3. システムはシェル設定（`~/.zshrc`）を `claude-dev-config` ボリュームでコンテナ間共有し、コマンド履歴を `claude-dev-history` ボリュームで永続化しなければならない

### 要件3:認証の共有とセッション分離

**ユーザーストーリー:** 開発者として、一度のログインで全コンテナが認証を共有し、かつセッションはコンテナごとに独立させたい。
これは同梱するエージェント CLI（Claude Code / Codex CLI）の双方について成り立ってほしい。

#### 受け入れ基準

1. WHEN `claude-dev login` を実行したとき、システムは一時コンテナで対話認証を行い、完了後に認証ファイル（`.credentials.json`/`.claude.json`）を `claude-dev-auth` ボリュームへ保存しなければならない
2. WHEN コンテナを起動したとき、システムは認証ファイルを共有ボリュームからコンテナローカル `~/.claude/` へコピーしなければならない（symlink は使わない）
3. WHILE コンテナが起動している間、システムは 30 秒ごとに認証ファイルの変更を検知し共有ボリュームへ書き戻さなければならない
4. システムはセッション・設定（`settings.json`/`projects/`/`sessions/`）をコンテナ固有に保たなければならない
5. WHEN `claude-dev logout` を実行したとき、システムは認証情報を削除し実行中コンテナを停止しなければならない（共有ボリューム全体を空にするため、Claude Code と Codex CLI 双方の認証が削除される）
6. WHEN `claude-dev login-codex` を実行したとき、システムは一時コンテナで `codex login --device-auth` によるデバイス認証を行い、完了後に codex の認証ファイル（`auth.json`）を `claude-dev-auth` ボリュームの `codex/` サブディレクトリへ保存しなければならない
7. WHEN コンテナを起動したとき、システムは codex の認証ファイルを共有ボリュームからコンテナローカルの `~/.codex/` へコピーしなければならない（symlink は使わない）
8. WHILE コンテナが起動している間、システムは 30 秒ごとに codex 認証ファイルの変更を検知し共有ボリュームへ書き戻さなければならない（トークンリフレッシュの伝播）
9. システムは codex の設定・セッション履歴（`config.toml`・セッションログ）をコンテナ固有に保たなければならない（共有ボリューム経由でコンテナ間に伝播させない。コンテナ起動時に置く既定設定〈要件12-5〉もコンテナ固有の実体として置かれるため本基準と両立する）

### 要件4:SSH 鍵の限定転送

**ユーザーストーリー:** 開発者として、プロジェクトごとに必要な SSH 鍵だけをコンテナへ渡したい。秘密鍵ファイルは露出させたくない。

#### 受け入れ基準

1. システムは SSH 秘密鍵ファイルをコンテナにマウントしてはならない（agent ソケット転送のみ）
2. WHERE プロジェクト直下 `.claude-dev.yaml` の `ssh_keys` が指定された場合、システムはプロジェクト専用 ssh-agent を起動しその鍵だけを登録・転送しなければならない
3. IF `.claude-dev.yaml` が無い、または `ssh_keys` が空ならば、システムは SSH 転送なしで起動し案内メッセージを表示しなければならない
4. WHEN `claude-dev ssh-keys` を実行したとき、システムは `~/.ssh` の鍵を対話選択して `.claude-dev.yaml` を生成しなければならない

### 要件5:ネットワーク隔離とファイアウォール

**ユーザーストーリー:** 開発者として、レビュー前コードの外部通信を制御したい。

#### 受け入れ基準

1. WHEN コンテナを起動したとき、システムはコンテナ内で iptables ファイアウォールを設定しなければならない
2. システムはコンテナ間通信を専用ネットワーク `claude-dev-net` 上で行わなければならない
3. IF ファイアウォールの適用に失敗したならば、システムはコンテナの起動を中止してはならず、警告を起動ログへ
   出力したうえで起動を継続しなければならない。適用の成否は起動ログのファイアウォールサマリと、その直後の
   到達性スモークテストの結果（ブロック対象ドメインへ到達できてしまった場合と、Anthropic API へ到達できない
   場合に出る警告行）で判別できなければならない

### 要件6:ポートフォワード

**ユーザーストーリー:** 開発者として、必要なときだけコンテナ内 Webアプリのポートを公開したい。

#### 受け入れ基準

1. WHEN `claude-dev start` したとき、システムは Webアプリ用のポートマッピングを行ってはならない（VNC ありの noVNC ポートを除く）
2. WHEN `claude-dev forward <port> [name]` を実行したとき、システムはホスト側ポートを 8100〜 から動的割当し `fwd-<name>-<port>` プロキシを立てなければならない
3. WHEN `claude-dev unforward <port> [name]` を実行したとき、システムは当該フォワードを解除しなければならない
4. WHEN `claude-dev ports [name]` を実行したとき、システムはアクティブなフォワードと noVNC URL を表示しなければならない

### 要件7:Docker アクセスの制限（docker-proxy）

**ユーザーストーリー:** 開発者として、コンテナ内から Docker を使いたいが、ホストを危険に晒したくない。

#### 受け入れ基準

1. システムはコンテナに Docker 生ソケットをマウントしてはならず、`DOCKER_HOST=tcp://claude-dev-docker-proxy:2375` 経由で使わせなければならない
2. IF リクエストがホストバインドマウント（`/workspace` 配下を除く）・privileged・host ネットワーク/PID モードを含むならば、システムはそれを拒否しなければならない
3. WHERE 呼び出し元の `/workspace` 配下の bind の場合、システムは実ホストパスへ書き換えて許可しなければならない（既定有効、`CLAUDE_DEV_ALLOW_WORKSPACE_BINDS` で切替）
4. システムは docker-proxy をホストに公開せず `claude-dev-net` 内でのみアクセス可能にしなければならない
5. WHEN 複数プロジェクトのコンテナで同時に `docker compose` を実行したとき、システムは各プロジェクトの compose プロジェクト名を起動ディレクトリ名で一意化し、生成されるネットワーク名・コンテナ名がプロジェクト間で衝突しないようにしなければならない

### 要件8:VM モード（オプトイン）

**ユーザーストーリー:** 開発者として、bind/compose/privileged が要る重い Docker 案件を安全に扱いたい。

#### 受け入れ基準

1. WHERE `claude-dev start --vm` が指定された場合、システムは QEMU+virtiofs のゲスト VM を起動し、その中でネイティブ Docker を利用可能にしなければならない
2. システムは VM モードでも `/workspace` を virtiofs で同一パス共有（ライブ反映）し、claude コンテナを privileged 化してはならない
3. WHILE VM モードでない間、システムは既定の軽量構成（DooD + docker-proxy）で動作しなければならない

### 要件9:イメージ配布（GHCR）

**ユーザーストーリー:** 開発者として、ビルドせずに同一構成のイメージを取得したい。

#### 受け入れ基準

1. システムは GitHub Actions によりイメージを GHCR へマルチアーキ（amd64/arm64）で push しなければならない
2. WHEN 日次ビルド（03:30 JST）が実行されたとき、システムはイメージに `YYYYMMDDHHmm`（JST）形式のタイムスタンプタグと `latest` タグを付与して push しなければならない
3. WHEN 日次ビルドが実行されたとき、システムは配布イメージに同梱する Claude Code のバージョンを、その時点の `latest` チャネル公開バージョンに一致させなければならない（[D-26](../00-requests/decisions.md)）
4. WHERE Claude Code の特定バージョンが手動で指定された場合、システムは同梱する Claude Code をその指定バージョンにしなければならない（不良版を引いた際の切り戻し手段）
5. WHEN 利用者が配布イメージを取得したとき、システムはイメージのラベルとして同梱バージョン（タイムスタンプ）を参照可能にしなければならない
6. WHEN 日次ビルドが実行されたとき、システムは配布イメージに同梱する Codex CLI のバージョンを、その時点の npm registry における最新公開バージョンに一致させなければならない（[D-27](../00-requests/decisions.md)）
7. WHERE Codex CLI の特定バージョンが手動で指定された場合、システムは同梱する Codex CLI をその指定バージョンにしなければならない（不良版を引いた際の切り戻し手段）

### 要件10:macOS 対応

**ユーザーストーリー:** macOS 開発者として、Linux と同じ `claude-dev` コマンドで開発したい。

#### 受け入れ基準

1. WHEN `make install` を実行したとき、システムは `uname -s` で OS を判定し、`/usr/local/bin/claude-dev` を Linux では `claude-dev`、macOS（`Darwin`）では `claude-dev-mac` への symlink にしなければならない
2. WHERE macOS の場合、システムは SSH agent を TCP ブリッジで転送し、ポートは直結（SSH トンネル不要）とし、VM/KVM は非対応としなければならない
3. WHERE Apple Silicon の場合、システムは arm64 ネイティブで動作しなければならない

### 要件11:ブラウザ確認（VNC/noVNC/Chrome MCP）

**ユーザーストーリー:** 開発者として、コンテナ内 Chrome の画面をリアルタイムに確認しながら Claude に操作させたい。

#### 受け入れ基準

1. WHERE VNC ありイメージの場合、システムは Xvnc（`:99`/VNC 5999、ホスト非公開）→ openbox → Chrome（`--remote-debugging-port=9222`）→ noVNC を起動し、noVNC ポートを 6080〜 から動的割当しなければならない
2. システムは chrome-devtools MCP を entrypoint が自動設定し（`.mcp.json`/`.claude.json`）、既存 `.mcp.json` の他エントリを保持しなければならない
3. システムは日本語入力（IBus-Mozc、`Super+Space` 切替）を提供しなければならない

### 要件12:同梱エージェント CLI（Claude Code / Codex CLI）

**ユーザーストーリー:** 開発者として、コンテナ内で Claude Code だけでなく Codex CLI も使いたい。
なぜなら案件や検証内容に応じてベンダーを使い分けたいから。

#### 受け入れ基準

1. システムは配布イメージ（VNC あり/なしの両方）に Claude Code と Codex CLI の双方を同梱しなければならない
2. WHEN コンテナ内で `codex` を実行したとき、システムは同梱した Codex CLI を起動しなければならない。コマンドは対話シェル・非対話シェル（`bash -c`）・`docker exec` のいずれからも解決できなければならない
3. システムは Codex CLI をイメージビルド時に具体バージョンでピン留めして導入しなければならず、起動時や実行時のダウンロードに依存してはならない
4. WHEN codex がシェルコマンドを実行したとき、そのコマンドはコンテナ内で成功しなければならない（Codex サンドボックスの起動失敗を理由に失敗してはならない）
5. システムは次の 3 鍵からなる Codex サンドボックスの既定設定をコンテナ起動時に置かなければならない（[D-27](../00-requests/decisions.md) ⑥）——`sandbox_mode = "danger-full-access"`、`approval_policy = "never"`、`[features] use_legacy_landlock = true`（前 2 鍵は既定でのサンドボックス無効化、3 番目は読み取り専用を明示要求された場合に使う landlock バックエンドの有効化）
6. IF 起動時に codex の `config.toml` が既に存在するならば、システムは既に書かれている鍵とその値を書き換えてはならず、受け入れ基準5 の 3 鍵のうち**書かれていない鍵だけを追記**しなければならない（利用者が書いた設定を保持しつつ不足既定を補完する。同じ設定で何度起動しても結果が変わらないこと）
7. システムは Codex サンドボックスを動作させるためにコンテナの seccomp/AppArmor プロファイルを緩めてはならない
8. 本要件の対象は開発者が対話的に codex を使うことであり、オーケストレーターが worker/レビューアーとして codex を常用することは対象外とする（[D-22](../00-requests/decisions.md) 未決）
9. WHEN codex が `--sandbox read-only` のようにサンドボックスを明示指定して起動されたとき、システムはそのコマンド実行を成功させなければならない（読み取りは成功し、書き込みは拒否されること。受け入れ基準5 の landlock 有効化がこれを満たす）。WHERE `workspace-write` が指定された場合は landlock バックエンドでは書き込みが成立しないため本基準の対象外とし、書き込みを伴う自動化は `danger-full-access` で実行する（[D-27](../00-requests/decisions.md) ⑥）

## 非機能要件

| 分類 | 要件 |
|---|---|
| セキュリティ | 生 Docker ソケット・SSH 秘密鍵ファイルをコンテナへ渡さない。API キー/トークンをイメージに焼き込まない。docker-proxy をホスト非公開にする |
| 性能・拡張性 | VNC ありイメージは VNC なしイメージのベースレイヤーを共有し、追加ディスクを Chrome/VNC 分に限定する。noVNC ポートはプロジェクト間で衝突しない。日次ビルドの更新後も利用者の `docker pull` は増分取得に留め、実際に内容が変わった層以外を再取得させない（同梱エージェント CLI〈Claude Code / Codex CLI〉の更新時に再取得させる層は、その導入層以降のみ） |
| 運用・保守性 | OS 依存はホスト CLI（`claude-dev`/`claude-dev-mac`）に閉じ、コンテナ内資産は OS 非依存に保つ。全ターゲットを `make help` で確認できる |
| システム環境 | Linux（Ubuntu 22.04+ / Debian 12+ 推奨）または macOS + Docker Desktop、Docker Engine 24+、`jq` 必須、Claude Pro/Max（OAuth）、Codex 利用時は OpenAI 側アカウント（デバイス認証） |

## 制約(上流から継承+具体化)

- 信頼できる社内開発用途に限定する（[request.md](../00-requests/request.md) §5）。
- コンテナ内 Webアプリは `0.0.0.0` にバインドする必要がある（`localhost` はコンテナ外から不可）。
- 外部 CLI・各ツールは変化が速く、採用/更新時に公式仕様を確認する（[decisions.md](../00-requests/decisions.md) 前提）。

## スコープ外

- 各エージェントの個別隔離、信頼できないコード・本番相当環境での利用、生ソケット直マウント運用
  （[request.md](../00-requests/request.md) §5「やらないこと」を継承）。
- MCP ツールの本格連携（D-23 要確認。stdio 方式優先で将来検討）。
- オーケストレーターが worker/レビューアーとして codex を常用すること（D-22 要確認。本領域は codex を
  「開発者が使える状態にする」までを担い、常用の可否は決めない）。

## 未解決事項(Open Questions)

- なし（要確認事項は decisions.md の D-21〜D-23 に集約。本要件の範囲では未解決論点はない）

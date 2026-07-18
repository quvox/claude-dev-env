---
id: core
layer: requirements
title: 開発環境基盤 要件定義書
version: 1.0.0
updated: 2026-07-18
verified:
  at: 2026-07-18
  version: 1.0.0
  against:
    - doc: docs/00-requests/request.md
      version: 1.0
    - doc: docs/00-requests/decisions.md
      version: 1.0
    - doc: docs/00-requests/glossary.md
      version: 1.0
    - doc: docs/00-requests/acceptance.md
      version: 1.0
summary: >
  Claude Code を隔離Dockerコンテナで動かす開発環境基盤の要件。コンテナ管理・認証・SSH鍵・
  ネットワーク/FW・ブラウザ確認・ポートフォワード・Dockerアクセス制限・VMモード・配布/プラットフォーム。
keywords: [コンテナ, 認証, SSH, ファイアウォール, docker-proxy, ポートフォワード, VMモード, GHCR]
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
- **事後条件(成功時):** プロジェクト専用コンテナで Claude Code が動作している
- **関連要件:** 要件1、要件2、要件4

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

### シナリオ外要件

- 認証ログイン（要件3）は独立した保守操作のため UC を持たない（AS では前提扱い）。
- イメージ配布（要件9）・macOS 対応（要件10）・VM モード（要件8）は横断的な提供形態であり、
  UC-1〜3 のフロー内で「どの環境でも同じ操作ができる」形で満たされる。

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
6. WHEN `claude-dev stop <name>` を実行したとき、システムは当該コンテナを削除し、全 Claude コンテナ停止時には docker-proxy コンテナも停止しなければならない

### 要件2:UID/GID 追従とホスト資産の共有

**ユーザーストーリー:** 開発者として、コンテナ内のファイル所有権がホストと一致し、git 設定を引き継ぎたい。

#### 受け入れ基準

1. WHEN コンテナを起動したとき、システムはユーザーの UID/GID をホスト（`/workspace`）に一致させなければならない
2. WHERE ホストに `~/.gitconfig` が存在する場合、システムはそれを読み取り専用でマウントしなければならない
3. システムはシェル設定（`~/.zshrc`）を `claude-dev-config` ボリュームでコンテナ間共有し、コマンド履歴を `claude-dev-history` ボリュームで永続化しなければならない

### 要件3:認証の共有とセッション分離

**ユーザーストーリー:** 開発者として、一度のログインで全コンテナが認証を共有し、かつセッションはコンテナごとに独立させたい。

#### 受け入れ基準

1. WHEN `claude-dev login` を実行したとき、システムは一時コンテナで対話認証を行い、完了後に認証ファイル（`.credentials.json`/`.claude.json`）を `claude-dev-auth` ボリュームへ保存しなければならない
2. WHEN コンテナを起動したとき、システムは認証ファイルを共有ボリュームからコンテナローカル `~/.claude/` へコピーしなければならない（symlink は使わない）
3. WHILE コンテナが起動している間、システムは 30 秒ごとに認証ファイルの変更を検知し共有ボリュームへ書き戻さなければならない
4. システムはセッション・設定（`settings.json`/`projects/`/`sessions/`）をコンテナ固有に保たなければならない
5. WHEN `claude-dev logout` を実行したとき、システムは認証情報を削除し実行中コンテナを停止しなければならない

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
2. システムはイメージにタイムスタンプタグを付与し、日次で更新しなければならない

### 要件10:macOS 対応

**ユーザーストーリー:** macOS 開発者として、Linux と同じ `claude-dev` コマンドで開発したい。

#### 受け入れ基準

1. WHEN `make install` を実行したとき、システムは OS を判定し `/usr/local/bin/claude-dev` を適切な実体（macOS は `claude-dev-mac`）への symlink にしなければならない
2. WHERE macOS の場合、システムは SSH agent を TCP ブリッジで転送し、ポートは直結（SSH トンネル不要）とし、VM/KVM は非対応としなければならない
3. WHERE Apple Silicon の場合、システムは arm64 ネイティブで動作しなければならない

### 要件11:ブラウザ確認（VNC/noVNC/Chrome MCP）

**ユーザーストーリー:** 開発者として、コンテナ内 Chrome の画面をリアルタイムに確認しながら Claude に操作させたい。

#### 受け入れ基準

1. WHERE VNC ありイメージの場合、システムは Xvnc（`:99`/VNC 5999、ホスト非公開）→ openbox → Chrome（`--remote-debugging-port=9222`）→ noVNC を起動し、noVNC ポートを 6080〜 から動的割当しなければならない
2. システムは chrome-devtools MCP を entrypoint が自動設定し（`.mcp.json`/`.claude.json`）、既存 `.mcp.json` の他エントリを保持しなければならない
3. システムは日本語入力（IBus-Mozc、`Super+Space` 切替）を提供しなければならない

## 非機能要件

| 分類 | 要件 |
|---|---|
| セキュリティ | 生 Docker ソケット・SSH 秘密鍵ファイルをコンテナへ渡さない。API キー/トークンをイメージに焼き込まない。docker-proxy をホスト非公開にする |
| 性能・拡張性 | VNC ありイメージは VNC なしイメージのベースレイヤーを共有し、追加ディスクを Chrome/VNC 分に限定する。noVNC ポートはプロジェクト間で衝突しない |
| 運用・保守性 | OS 依存はホスト CLI（`claude-dev`/`claude-dev-mac`）に閉じ、コンテナ内資産は OS 非依存に保つ。全ターゲットを `make help` で確認できる |
| システム環境 | Linux（Ubuntu 22.04+ / Debian 12+ 推奨）または macOS + Docker Desktop、Docker Engine 24+、`jq` 必須、Claude Pro/Max（OAuth） |

## 制約(上流から継承+具体化)

- 信頼できる社内開発用途に限定する（[request.md](../00-requests/request.md) §5）。
- コンテナ内 Webアプリは `0.0.0.0` にバインドする必要がある（`localhost` はコンテナ外から不可）。
- 外部 CLI・各ツールは変化が速く、採用/更新時に公式仕様を確認する（[decisions.md](../00-requests/decisions.md) 前提）。

## スコープ外

- 各エージェントの個別隔離、信頼できないコード・本番相当環境での利用、生ソケット直マウント運用
  （[request.md](../00-requests/request.md) §5「やらないこと」を継承）。
- MCP ツールの本格連携（D-23 要確認。stdio 方式優先で将来検討）。

## 未解決事項(Open Questions)

- なし（要確認事項は decisions.md の D-21〜D-23 に集約。本要件の範囲では未解決論点はない）

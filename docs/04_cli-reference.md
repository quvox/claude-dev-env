---
summary: claude-dev CLI と Makefile の全コマンド・オプションの利用者向けリファレンス。CLIの内部実装仕様は docs/impl/10_cli.md を参照。
keywords: [ CLI, コマンドリファレンス, claude-dev, orchestrate, ポートフォワード, セッション管理, VNC ]
---

# CLI リファレンス

> **この文書の役割**: `claude-dev` CLI の全コマンド・オプションの利用者向けリファレンス。CLI の内部実装仕様は [docs/impl/10_cli.md](impl/10_cli.md) を参照。

## 概要

操作は **Makefile**（セットアップ・ビルド・管理）と **claude-dev CLI**（日常の開発操作）の 2 系統で提供される。

> **macOS について**: macOS では CLI 本体は `claude-dev-mac`（`make install` が `claude-dev` として配置）を使う。コマンド名・サブコマンド体系は本リファレンスと同一。差分は VM/KVM 非対応（`--vm`/`--kvm` はエラー）と、`forward`/`ports`/`list` の案内が SSH トンネルではなく `http://localhost:<host-port>` 直結になる点のみ。詳細は [docs/09_macos-support.md](09_macos-support.md)。

### Makefile ターゲット一覧

インストールやビルドなどの管理タスクは Makefile で実行する。

| ターゲット | 内容 |
|-----------|------|
| `make setup` | 初回セットアップ一括実行（env + network + volumes + build + install） |
| `make login` | OAuth ログイン |
| `make build` | 全イメージビルド（ベース + VNC + Docker Socket Proxy） |
| `make build-claude` | Claude ベースイメージのみをビルド（`--target base`） |
| `make build-claude-vnc` | Claude VNC イメージをビルド（`build-claude` に続けて `--target vnc`） |
| `make build-docker-proxy` | Docker Socket Proxy イメージをビルド |
| `make upgrade` | 全イメージを最新版にリビルド（`--no-cache`） |
| `make status` | イメージ・コンテナ・ボリュームの状態確認 |
| `make install` | CLI を `/usr/local/bin/claude-dev` に登録（**Linux**: シンボリックリンク。**macOS**: `claude-dev-mac` を `install(1)`+`sudo` でコピー配置） |
| `make uninstall` | `/usr/local/bin/claude-dev` を削除（symlink・実ファイル双方に対応） |
| `make clean` | 全リセット（コンテナ・ボリューム・イメージ削除、確認あり） |
| `make help` | ヘルプ表示 |

### claude-dev CLI

`claude-dev` は日常の開発操作を行う CLI ツール。任意のディレクトリから実行できる。

## コマンド一覧

### セットアップ

#### `claude-dev setup`

初回セットアップ。以下を実行する:

1. `.env` ファイルを `.env.example` からコピー（未作成時）
2. Docker ネットワーク `claude-dev-net` を作成
3. Docker ボリューム `claude-dev-auth`, `claude-dev-history`, `claude-dev-config`, `claude-dev-chrome-data` を作成
4. Docker イメージをビルド（Claude ベース / Claude VNC / Docker Socket Proxy）

```bash
claude-dev setup
```

#### `claude-dev login`

OAuth 認証を実行する。Claude イメージを使った一時コンテナを起動し、Claude Code を対話的に起動する。`claude-dev-auth` ボリュームは `~/.claude-shared/` にマウントされ、起動時に既存の認証ファイル（`.credentials.json`, `.claude.json`）を `~/.claude/` にコピーして使う。`/exit` で終了すると、認証ファイルが `~/.claude-shared/`（= ボリューム）に書き戻されて永続化される。

ログイン完了後、`/exit` で Claude Code を終了する。

```bash
claude-dev login
```

トークンが期限切れになったら `logout` → `login` で再認証する。

#### `claude-dev pull [TAG]`

GHCR のビルド済みイメージを取得してローカルビルド（`setup`/`build`）を省く。`.env` の `CLAUDE_DEV_REGISTRY`（既定 `ghcr.io/quvox`）と `CLAUDE_DEV_IMAGE_TAG`（既定 `latest`）を参照し、`claude-dev-claude` / `claude-dev-claude-vnc` / `claude-dev-docker-proxy` の 3 イメージを pull してローカル名に retag する。以降 `claude-dev start` は pull 済みイメージを使い、再ビルドしない。

```bash
claude-dev pull                 # latest を取得
claude-dev pull 202607041830    # 特定バージョン(YYYYMMDDHHmm)に固定
```

- amd64/arm64 は Docker が実行環境に合わせて自動選択（Apple Silicon=arm64 / Linux=amd64）。
- private パッケージの場合は事前に `docker login ghcr.io`（PAT）が必要。
- GHCR への push は GitHub Actions が毎日実行する（設計 [docs/10_ghcr-images.md](10_ghcr-images.md)）。

#### `claude-dev logout`

認証情報を削除する。実行中の全プロジェクトコンテナと Docker Socket Proxy コンテナ（`claude-dev-docker-proxy`）を停止し、`claude-dev-auth` ボリューム内のファイルをすべて削除する。

```bash
claude-dev logout
```

---

### 開発

#### `claude-dev start`

カレントディレクトリをワークスペースとして Claude Code 環境を起動する。

```bash
cd ~/repos/my-project
claude-dev start            # Chrome + VNC 付き（デフォルト）
claude-dev start --no-vnc   # Chrome / VNC なし（軽量）
claude-dev start --kvm      # KVM/QEMU デバイスを渡す（VM を動かす時のみ）
claude-dev start --vm       # VM モード。ゲスト VM 内でネイティブ Docker を使う
claude-dev start --vm-fresh # VM モード＋ゲストを白紙 provision やり直し（要 stop 後）
```

`--no-vnc` と `--kvm` は併用可能。デバイス受け渡しはコンテナ作成時のみ行われるため、稼働中コンテナに後付けはできない（`stop` → `start --kvm` で再作成する）。

動作:
- コンテナ名: ディレクトリ名（例: `my-project`）
- 同名コンテナが実行中の場合は再接続する
- 停止中のコンテナがある場合は削除して新規起動
- イメージが存在しなければ自動ビルド
- 共有ボリュームに認証情報があれば `/workspace/.claude/` にコピーする（無い場合もコンテナは起動する。未ログインなら起動後の `claude` でログインを求められる）
- Web アプリのポートマッピングは行わない（`claude-dev forward` で必要なときに動的にフォワード）
- ssh-agent が未起動なら自動起動し、鍵が未登録なら `ssh-add` を実行（`~/.config/claude-dev.yaml` から鍵リストを読み込み）
- `~/.gitconfig` があればコンテナに共有（読み取り専用）
- SSH agent ソケット・`~/.ssh/known_hosts`・`~/.ssh/config` をコンテナに共有（読み取り専用。秘密鍵はマウントしない）
- Docker Socket Proxy コンテナ（`claude-dev-docker-proxy`）が未起動なら自動起動する
- `--kvm` 指定時のみ、ホストに存在する `/dev/kvm`（および `/dev/vhost-net` / `/dev/net/tun`）を `--device` でコンテナに渡す。既定では渡さない（通常は Chrome 操作のみで十分）。コンテナ内で VM を動かす時だけ `--kvm` を付ける（詳細・セキュリティ上の含意は [docs/03_security.md](03_security.md) を参照）
- `--vm`（**実装済み・要イメージ再ビルド反映**）は `--kvm` を含意し、Docker を多用するシステム開発向けに**ゲスト VM 内でネイティブ Docker**（bind mount・compose・privileged 可）を動かすモード。コード共有は virtiofs（`/workspace` 同一パス・ライブ反映）、Docker 接続は `DOCKER_HOST`。設計は [docs/08_vm-mode.md](08_vm-mode.md)、実装仕様は [docs/impl/80_vm-mode.md](impl/80_vm-mode.md)

VNC あり（デフォルト）:
- `claude-dev-claude-vnc` イメージを使用
- コンテナ内で Xvnc + noVNC + Google Chrome が起動
- noVNC ポート（HTTP/WebSocket）は起動時に 6080〜 から空きを動的に割り当て。VNC 生ポートはホストに公開しない
- 起動時に noVNC URL が表示される。あとから `claude-dev list` や `claude-dev ports` でも確認可能
- Claude Code が chrome-devtools MCP サーバー経由で Chrome を操作
- 日本語入力対応（IBus-Mozc、`Super+Space` で切替。`Ctrl+Shift+Space` / `Ctrl+\` / `F3` も予備として使えるが、ホストに横取りされやすいため `Super+Space` 推奨）

VNC なし（`--no-vnc`）:
- `claude-dev-claude` イメージを使用（軽量）
- Chrome / VNC は起動しない
- バックエンド開発、CLI ツール開発など、ブラウザ不要なプロジェクト向け

#### `claude-dev code`

実行中のコンテナで、新しい tmux ウィンドウに Claude Code を起動する。

```bash
cd ~/repos/my-project
claude-dev code
```

前提: `claude-dev start` でコンテナが起動済みであること。

#### `claude-dev orchestrate [<ゴール>] [--fresh]`

実行中のコンテナで、新しい tmux ウィンドウに AI オーケストレーターを起動する。オーケストレーターはまず人間とのブレインストーミング（検討）で仕様を固め、合意後に自律実行（worker への委譲・統合・レビュー）へ移る。人間はブレインストーミングと例外対応（介入）だけに関与する。

```bash
cd ~/repos/my-project
claude-dev orchestrate                       # ブレインストーミングから開始（中断した run があれば再開）
claude-dev orchestrate "ユーザー認証を実装"   # ゴールを与えて開始
claude-dev orchestrate --fresh                # 前回の実行状態を破棄してブレインストーミングから新規開始
```

- ゴール引数は任意。省略するとブレインストーミングから開始する。
- 起動時、**中断された run（実行中/介入中）があれば自動で再開**する。完了済み（done）や状態が無い場合はブレインストーミングから新規開始する（完了済みでも即終了しない）。
- `--fresh` は前回の実行状態（state/plan/control・worktree・`orch/*` ブランチ）を破棄し、中断された run の再開を上書きしてブレインストーミングから新規開始する。「ブレインストーミングを飛ばして実行モードに入ってしまった」状態のリセットに使う。
- 実行ダッシュボードのキー：`[d]` worker のライブ出力表示をトグル、`[p]` 一時停止、`[q]` 中断（状態を保存し再開可。離席だけなら tmux を detach する）。
- 前提: `claude-dev start` でコンテナが起動済みであること。
- 詳細・設計は [docs/06_orchestration.md](06_orchestration.md) を参照。

#### `claude-dev attach [NAME]`

既存セッションに接続する。

```bash
# カレントディレクトリのプロジェクトに接続
claude-dev attach

# プロジェクト名を指定して接続
claude-dev attach my-project
```

#### `claude-dev stop [NAME]`

プロジェクトのコンテナを停止・削除する。プロジェクトファイルには影響しない。フォワード用プロキシコンテナ（`fwd-<name>-*`）も自動的にクリーンアップされる。

```bash
# カレントディレクトリのプロジェクトを停止
claude-dev stop

# プロジェクト名を指定して停止
claude-dev stop my-project
```

#### `claude-dev forward <port> [NAME]`

コンテナ内のポートをホストに動的にフォワードする。軽量な socat プロキシコンテナ（`fwd-<name>-<port>`）を同じ Docker ネットワーク上に作成する。ホスト側ポートは 8100 番台から自動的に割り当てられる。

```bash
# カレントディレクトリのプロジェクト
claude-dev forward 3000

# プロジェクト名を指定
claude-dev forward 8080 backend
```

出力例:
```
✅ host:8100 → my-project:3000
   SSH: ssh -O forward -L 8100:localhost:8100 <server>
```

#### `claude-dev unforward <port> [NAME]`

フォワードを解除する。対応するプロキシコンテナ（`fwd-<name>-<port>`）を停止・削除する。

```bash
# カレントディレクトリのプロジェクト
claude-dev unforward 3000

# プロジェクト名を指定
claude-dev unforward 8080 backend
```

#### `claude-dev ports [NAME]`

アクティブなフォワードと noVNC URL を表示する。

```bash
# カレントディレクトリのプロジェクト
claude-dev ports

# プロジェクト名を指定
claude-dev ports my-project
```

出力例:
```
📡 my-project のポートフォワード:
   host:8100 → my-project:3000
   host:8101 → my-project:5173

🖥️  noVNC: http://localhost:6080/vnc.html?autoconnect=true
```

フォワードが 1 つもない場合は `   (なし — claude-dev forward <port> で追加)` と表示される。

#### `claude-dev list`

実行中の Claude Code セッションを表示する。アクティブなフォワードと noVNC URL も表示される。

```bash
claude-dev list
```

出力例:
```
=== 実行中の Claude Code セッション ===

  NAME:      my-project
  STATUS:    running
  WORKSPACE: /home/user/repos/my-project
  noVNC:     http://localhost:6080/vnc.html?autoconnect=true
  FORWARD:   host:8100 → my-project:3000
  FORWARD:   host:8101 → my-project:5173

  NAME:      api-server
  STATUS:    running
  WORKSPACE: /home/user/repos/api-server
  FORWARD:   host:8102 → api-server:8080

=== Docker Socket Proxy コンテナ ===
  STATUS:  running
```

VNC なしコンテナでは `noVNC:` 行は表示されない（`(VNC なし)` のような行は出力されない）。最後に Docker Socket Proxy コンテナの稼働状態が表示される。

---

### メンテナンス

#### `claude-dev upgrade`

全イメージ（Claude ベース / VNC / Docker Socket Proxy）を `--no-cache` でリビルドする。

```bash
claude-dev upgrade
```

更新後、実行中のコンテナには即座に反映されない。`stop` → `start` で新しいイメージが使われる。

#### `claude-dev firewall`

カレントディレクトリのプロジェクトコンテナのファイアウォールルールを表示する。

```bash
claude-dev firewall
```

#### `claude-dev reset`

すべてのコンテナ、ボリューム、ネットワーク、イメージを削除する。確認プロンプトあり。

```bash
claude-dev reset
```

削除対象:
- 全プロジェクトコンテナ
- Docker Socket Proxy コンテナ
- `claude-dev-auth`, `claude-dev-history`, `claude-dev-config`, `claude-dev-chrome-data` ボリューム
- `claude-dev-net` ネットワーク
- `claude-dev-claude`, `claude-dev-claude-vnc`, `claude-dev-docker-proxy` イメージ

---

## コンテナ命名規則

| 種類 | 命名パターン | 例 |
|------|-------------|-----|
| プロジェクト | `<ディレクトリ名>` | `my-project` |
| Docker Socket Proxy | `claude-dev-docker-proxy` | （固定） |

ディレクトリ名は小文字化され、英数字・ハイフン・ドット・アンダースコア以外は `-` に置換される。

## Makefile と claude-dev の使い分け

| やりたいこと | 使うもの |
|-------------|---------|
| 初回セットアップ | `make setup` |
| イメージビルド | `make build` |
| イメージ取得（ビルド省略・GHCR） | `claude-dev pull` |
| Claude Code 更新 | `make upgrade` |
| 状態確認（全体） | `make status` |
| PATH 登録 | `make install` |
| プロジェクトで開発開始 | `claude-dev start` |
| セッション接続/切断 | `claude-dev attach` / `claude-dev stop` |
| ポートフォワード | `claude-dev forward` / `claude-dev unforward` |
| フォワード状況確認 | `claude-dev ports` |
| セッション一覧 | `claude-dev list` |
| OAuth ログイン | `make login` または `claude-dev login` |
| 認証情報削除 | `claude-dev logout` |
| 全リセット | `make clean` または `claude-dev reset` |

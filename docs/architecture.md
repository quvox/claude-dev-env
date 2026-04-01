# アーキテクチャ設計

## 全体構成

```
Linux サーバ (SSH でアクセス)
│
├── Makefile          セットアップ・ビルド・管理タスク
├── claude-dev CLI    日常の開発操作（/usr/local/bin/claude-dev にシンボリックリンク）
│
├── プロジェクトコンテナ（都度起動）
│   ├── claude-project-a       ~/repos/project-a をマウント
│   ├── claude-project-b       ~/repos/project-b をマウント
│   └── ...
│
├── Chrome/VNC コンテナ（共有、自動管理）
│   └── claude-dev-chrome      全 Claude コンテナで共有
│
├── Docker Socket Proxy コンテナ（共有、自動管理）
│   └── claude-dev-docker-proxy   Docker API を制限付きで中継
│
├── Docker ネットワーク
│   └── claude-dev-net         コンテナ間通信
│
└── Docker ボリューム
    ├── claude-dev-auth        認証ファイル（.credentials.json, .claude.json）
    └── claude-dev-history     コマンド履歴
```

## コンテナ構成

### Claude コンテナ（プロジェクトごと）

プロジェクトディレクトリをマウントして Claude Code を実行する環境。

```
┌───────────────────────────────────────────────┐
│ claude-<project-name>  (ubuntu:24.04)         │
│                                               │
│  Node.js 24/22 (fnm) + pnpm + Claude Code    │
│  Python3 + venv                               │
│  Go, Rust                                     │
│  Chrome DevTools MCP（noVNC Chrome 操作）       │
│  Playwright Chromium（ヘッドレステスト用）       │
│  git, zsh, tmux, vim, make, gcc, curl, wget   │
│  iptables ファイアウォール                      │
│                                               │
│  /workspace      ← ホストのプロジェクト (RW)    │
│  ~/.claude-shared/ ← 認証ボリューム (RW)        │
│  ~/.claude/      ← コンテナローカル（認証はコピー）│
│  ~/.claude.json  ← symlink → ~/.claude/ 内     │
│  ~/.gitconfig    ← ホストから共有 (RO)           │
│  SSH agent       ← ソケット転送（鍵ファイルなし） │
│                                               │
│  ※ Docker ソケットなし（proxy 経由で Docker API を利用）│
│  ※ UID/GID はビルド時にホストと一致させる        │
└───────────────────────────────────────────────┘
```

- **イメージ**: `claude-dev-claude`
- **ベース**: `ubuntu:24.04`
- **言語**: Node.js 24/22 (fnm), Python3 (venv), Go, Rust
- **ツール**: git, zsh, tmux, vim, make, gcc, curl, wget, pnpm, Playwright Chromium（ヘッドレステスト用）, Chrome DevTools MCP, etc.
- **Docker**: 生ソケットはマウントしない。`DOCKER_HOST=tcp://claude-dev-docker-proxy:2375` 経由で制限付き Docker API を利用
- **Chrome DevTools MCP**: Chrome/VNC コンテナの Google Chrome に CDP 接続し、MCP ツール経由でページ遷移・スクリーンショット・クリック・入力等を実行。entrypoint が `claude mcp add` で `/workspace/.mcp.json` に登録
- **ユーザー**: ホストのカレントユーザーと同名 (UID/GID はビルド時にホストと一致。entrypoint でも競合を解消して追従)
- **git 設定**: ホストの `~/.gitconfig` を読み取り専用でマウント（存在する場合）
- **SSH**: SSH agent ソケットを転送。秘密鍵ファイルはマウントしない。`~/.ssh/known_hosts` と `~/.ssh/config` は読み取り専用でマウント
- **起動**: ssh-agent 準備 → Chrome コンテナ自動起動 → Claude コンテナ作成 → entrypoint が UID/GID 調整 → 認証 symlink → MCP 設定 → ファイアウォール → tmux → 待機

### Chrome/VNC コンテナ（共有）

全 Claude コンテナで共有される GUI 環境。`claude-dev start` 時に自動的に起動される。

```
┌───────────────────────────────────────────────┐
│ claude-dev-chrome  (ubuntu:24.04)             │
│                                               │
│  Google Chrome + 日本語入力（IBus-Mozc）         │
│  TigerVNC (Xvnc) + noVNC                     │
│  CDP ポート 9222（Chrome DevTools Protocol）    │
│  ポート 6080 で noVNC を公開                    │
│                                               │
│  ~/.claude-shared/ ← 認証ボリューム (RW)        │
│  ~/.claude/      ← コンテナローカル              │
│                                               │
│  ※ Ctrl+\\ または F3 で日本語入力切替            │
│  ※ 全 Claude コンテナ停止時に自動停止            │
└───────────────────────────────────────────────┘
```

- **イメージ**: `claude-dev-chrome`
- **ベース**: `ubuntu:24.04`
- **ツール**: Google Chrome, TigerVNC (Xvnc), noVNC (websockify), openbox, IBus-Mozc（日本語入力）
- **ポート**: 6080（noVNC、全コンテナ共有）、9222（CDP、Claude コンテナから操作用）
- **ボリューム**: `claude-dev-auth` を `~/.claude/` にマウント（Chrome の認証情報共有用）
- **ライフサイクル**: `claude-dev start` で自動起動、全 Claude コンテナ停止時に自動停止
- **CDP**: Chrome は `--remote-debugging-port=9222` で起動（127.0.0.1 のみ）。socat が 0.0.0.0:9223 → 127.0.0.1:9222 にリレーし、Claude コンテナから Chrome DevTools MCP 経由で操作可能

### Docker Socket Proxy コンテナ（共有）

Claude コンテナから Docker API を安全に利用するためのリバースプロキシ。全 Claude コンテナで共有される。

```
┌───────────────────────────────────────────────┐
│ claude-dev-docker-proxy                       │
│                                               │
│  Go 製の HTTP リバースプロキシ                  │
│  リクエストのエンドポイント + ボディを検査        │
│  危険な操作（ホストマウント、privileged 等）を拒否 │
│                                               │
│  /var/run/docker.sock ← ホストからマウント (RO)  │
│  TCP 2375 で Docker API を中継                  │
│                                               │
│  ※ Claude コンテナからのみアクセス可能            │
│  ※ 全 Claude コンテナ停止時に自動停止            │
└───────────────────────────────────────────────┘
```

- **イメージ**: `claude-dev-docker-proxy`
- **ポート**: 2375（Docker API、`claude-dev-net` 内でのみアクセス可能。ホストには公開しない）
- **ボリューム**: `/var/run/docker.sock` を読み取り専用でマウント
- **ライフサイクル**: `claude-dev start` で自動起動、全 Claude コンテナ停止時に自動停止
- **セキュリティ**: リクエストボディを検査し、ホストバインドマウント・privileged・`host` ネットワーク/PID モード等を拒否。詳細は [セキュリティ設計](security.md) を参照

```
Claude コンテナ                        Docker Socket Proxy               Docker Engine
┌──────────────┐                      ┌─────────────────────┐           ┌──────────┐
│ docker ps    │─── HTTP GET ────────→│ GET /containers/json │──────────→│          │
│              │                      │ → 許可               │           │          │
│ docker run   │─── HTTP POST ───────→│ POST /containers/    │           │          │
│  -v /:/host  │                      │  create              │           │ docker   │
│              │                      │ → Binds 検出 → 拒否  │    ×      │ daemon   │
│              │                      │                      │           │          │
│ docker run   │─── HTTP POST ───────→│ POST /containers/    │──────────→│          │
│  myapp       │                      │  create              │           │          │
│              │                      │ → Binds なし → 許可   │           │          │
└──────────────┘                      └─────────────────────┘           └──────────┘
```

## Chrome DevTools MCP 連携

Claude Code が noVNC の Chrome を直接操作して Web アプリの動作確認を行う仕組み。

### CDP 接続経路

Chrome 128 以降、`--remote-debugging-address=0.0.0.0` はセキュリティ上の理由でサイレントに無効化されており、CDP は `127.0.0.1` にのみバインドされる。また、Chrome は CDP リクエストの `Host` ヘッダーが IP アドレスまたは `localhost` でない場合にリクエストを拒否する。

この 2 つの制約を回避するため、socat による二段リレーで接続する:

```
┌─ ユーザーの PC ─────────────────┐
│  ブラウザ → noVNC (port 6080)  │  ← リアルタイムで操作を確認
└──────────────────────────────┘
        │
        ▼
┌─ Chrome/VNC コンテナ (claude-dev-chrome) ─────────────────────┐
│  Google Chrome                                                │
│    ├── noVNC (port 6080)         ← ユーザーが閲覧             │
│    └── CDP  (127.0.0.1:9222)    ← Chrome 128+ で強制          │
│                                                               │
│  socat (0.0.0.0:9223 → 127.0.0.1:9222)                       │
│    └── CDP を外部に公開                                        │
└───────────────────────────────────────────────────────────────┘
        ▲ TCP 9223 (claude-dev-net)
        │
┌─ Claude コンテナ ─────────────────────────────────────────────┐
│  socat (127.0.0.1:9222 → claude-dev-chrome:9223)              │
│    └── MCP が localhost に接続 → Host ヘッダーが IP → Chrome 許可│
│                                                               │
│  Chrome DevTools MCP サーバー                                  │
│    └── browserUrl=http://127.0.0.1:9222                       │
│                                                               │
│  /workspace/.mcp.json ← claude mcp add で登録                 │
└───────────────────────────────────────────────────────────────┘
```

**なぜ二段リレーが必要か:**

1. **Chrome 側 socat** (0.0.0.0:9223 → 127.0.0.1:9222): Chrome の CDP が 127.0.0.1 にしかバインドされないため、外部からアクセス可能にする
2. **Claude 側 socat** (127.0.0.1:9222 → claude-dev-chrome:9223): MCP が `http://127.0.0.1:9222` に接続することで、HTTP の `Host` ヘッダーが IP アドレスになり、Chrome の Host ヘッダー検証を通過する

### MCP サーバーの登録

entrypoint が以下の 2 段階で Chrome DevTools MCP サーバーを登録する。

**ステップ 1: `claude mcp add` で `.mcp.json` を作成**

```bash
claude mcp add --transport stdio chrome-devtools --scope project \
    -- chrome-devtools-mcp --browserUrl=http://127.0.0.1:9222
```

- `/workspace/.mcp.json`（プロジェクトルート直下）に `chrome-devtools` エントリを作成
- Claude Code が読む MCP 設定ファイルは `~/.claude/mcp.json` ではなく `.mcp.json`（プロジェクトルート直下）
- entrypoint は起動のたびにエントリの存在と接続先を確認し、不足・不一致があれば再登録する
- `su` 経由で実行する際は `cd /workspace` しないとホームディレクトリに `.mcp.json` が作られるため、スクリプトファイル経由で実行する

**ステップ 2: `.claude.json` の `enabledMcpjsonServers` に直接追加**

```bash
jq '.projects["/workspace"].enabledMcpjsonServers |= (. // [] + ["chrome-devtools"] | unique)' \
    /workspace/.claude/.claude.json
```

- `claude mcp add` は `.mcp.json` を作成するだけで、`enabledMcpjsonServers` への追加は行わない
- Claude Code は `.mcp.json` に定義があっても、`.claude.json` の `enabledMcpjsonServers` に含まれていないサーバーのツールを有効化しない
- 通常は Claude Code 起動時の trust ダイアログで承認すると追加されるが、`--dangerously-skip-permissions` のコンテナ環境では trust ダイアログが表示されない
- `bypassPermissions` / `--dangerously-skip-permissions` は MCP サーバーの承認には影響しない（ファイル操作等の権限とは別のセキュリティ機構）
- そのため、entrypoint で jq を使って直接 `enabledMcpjsonServers` に追加する

### 動作フロー

1. `claude-dev start` 時に Chrome/VNC コンテナが起動。entrypoint が Chrome を起動後、socat で CDP をリレー (0.0.0.0:9223)
2. Claude コンテナの entrypoint が socat でローカルリレーを起動 (127.0.0.1:9222 → claude-dev-chrome:9223)
3. entrypoint が `claude mcp add` で `/workspace/.mcp.json` に MCP サーバーを登録（未登録 or 接続先変更時のみ）
4. entrypoint が `.claude.json` の `enabledMcpjsonServers` に `chrome-devtools` を追加（未追加時のみ）
4. Claude Code が MCP ツール（`navigate_page`, `take_screenshot`, `click` 等）を呼び出すと、Chrome DevTools MCP サーバーが socat 経由で CDP に接続し Chrome を操作
5. ユーザーは noVNC で Chrome の画面をリアルタイムに確認できる

### 主要な MCP ツール

| ツール | 用途 |
|--------|------|
| `navigate_page` | URL に遷移 |
| `take_screenshot` | スクリーンショット撮影 |
| `take_snapshot` | DOM スナップショット取得 |
| `click` | 要素をクリック |
| `fill` | テキスト入力 |
| `fill_form` | フォーム一括入力 |
| `press_key` | キーボード操作 |
| `evaluate_script` | JavaScript 実行 |
| `list_console_messages` | コンソール出力取得 |
| `list_network_requests` | ネットワークリクエスト確認 |

## 認証の仕組み

Claude Code は認証情報を以下の場所に保存する：

- `~/.claude/.credentials.json` — OAuth トークン（リフレッシュトークン含む）
- `~/.claude/.claude.json` / `~/.claude.json` — アカウント情報

### 認証共有 + セッション分離

**設計原則:**
- 認証ファイル（`.credentials.json`, `.claude.json`）だけをコンテナ間で共有
- セッション・メモリ・設定（`settings.json`, `projects/`, `sessions/` 等）はコンテナごとに独立

**方式: コピー + バックグラウンド同期（symlink は使わない）**

symlink は Claude Code のアトミック書き込み（tmp → rename）で壊れるため、
実体ファイルのコピーとバックグラウンド同期で認証を共有する。

```
Docker ボリューム: claude-dev-auth （認証ファイル専用）
    │
    ├── .credentials.json   ← OAuth トークン
    └── .claude.json        ← アカウント情報

コンテナ内:
    ~/.claude-shared/       ← auth ボリュームのマウントポイント（認証ファイルのみ）
    ~/.claude/              ← コンテナローカル（overlay FS）
        ├── .credentials.json   ← 起動時に ~/.claude-shared/ からコピー
        ├── .claude.json        ← 起動時に ~/.claude-shared/ からコピー
        ├── settings.json       ← コンテナ固有（bypassPermissions）
        ├── projects/           ← コンテナ固有
        └── sessions/           ← コンテナ固有
    ~/.claude.json          ← symlink → ~/.claude/.claude.json
```

**バックグラウンド同期:**
entrypoint が 30 秒ごとに認証ファイルの変更を検知し、共有ボリュームに書き戻す。
これにより、トークンリフレッシュ等の更新が他コンテナ（次回起動時）に伝播する。

### 認証フロー

```
┌─────────┐     ┌───────────────────┐     ┌──────────────┐
│ ユーザー │     │ login 一時コンテナ │     │ auth volume  │
└────┬────┘     └────────┬──────────┘     └──────┬───────┘
     │                   │                        │
     │ claude-dev login  │                        │
     │──────────────────→│                        │
     │                   │ volume → ~/.claude-shared │
     │                   │←───────────────────────│
     │                   │                        │
     │ Claude Code 起動  │ 既存の認証ファイルを     │
     │   URL 表示        │ ~/.claude/ にコピー     │
     │←──────────────────│                        │
     │                   │                        │
     │ ブラウザで認証     │                        │
     │──────────────────→│                        │
     │                   │ ~/.claude/ に書込       │
     │                   │                        │
     │ /exit で終了      │ 認証ファイルを           │
     │──────────────────→│ ~/.claude-shared/ にコピー│
     │                   │───────────────────────→│
```

1. `claude-dev login` が一時コンテナを起動（auth ボリュームを `~/.claude-shared/` にマウント）
2. 既存の認証ファイルがあれば `~/.claude/` にコピー
3. Claude Code が対話的に起動し、ブラウザ認証 URL を表示
4. ユーザーがブラウザで認証を完了
5. `/exit` で終了後、認証ファイル（`.credentials.json`, `.claude.json`）を共有ボリュームにコピー

### プロジェクト起動時

```
claude-dev start
     │
     ├─ ホスト側（claude-dev CLI）
     │   1. ssh-agent が未起動なら起動
     │   2. 鍵が未登録なら ssh-add を実行
     │   3. コンテナを作成・起動
     │
     ▼
┌─ entrypoint-claude.sh ──────────────────────────┐
│ 1. /workspace の UID/GID を検出                  │
│ 2. ユーザーの UID/GID をホストに合わせる            │
│ 3. ~/.ssh ディレクトリの所有権を設定               │
│ 4. 認証ファイルを ~/.claude-shared/ → ~/.claude/ へコピー │
│ 5. ~/.claude.json → ~/.claude/.claude.json へリンク │
│ 6. settings.json がなければ新規作成（コンテナ固有）  │
│ 7. 認証ファイル同期のバックグラウンドプロセス起動     │
│ 8. ファイアウォール設定                           │
│ 9. tmux セッション開始                           │
└──────────────────────────────────────────────────┘
```

## ポートマッピング

### 概要

コンテナ内で起動した Web アプリにクライアント PC のブラウザからアクセスするため、主要な開発用ポートを自動的にホストにマッピングする。

```
┌─ Client PC ──────────────┐
│  Browser → localhost:8102 │
└──────┬───────────────────┘
       │ SSH Tunnel (ssh -O forward)
       │
┌──────▼───────────────────────────────────────┐
│  Server Host                                 │
│                                              │
│  ┌─ claude-frontend (BASE=8100) ───────────┐ │
│  │  Vite :5173   ←─ host:8102              │ │
│  │  Express :3000 ←─ host:8100             │ │
│  └─────────────────────────────────────────┘ │
│                                              │
│  ┌─ claude-backend (BASE=8110) ────────────┐ │
│  │  Go :8080     ←─ host:8115              │ │
│  └─────────────────────────────────────────┘ │
└──────────────────────────────────────────────┘
```

### ポート割り当て

コンテナごとに 10 ポートのブロックを割り当てる。ブロック内のオフセットは固定テーブルで管理する。

| オフセット | コンテナ内ポート | 主な用途 |
|-----------|----------------|---------|
| +0 | 3000 | React, Next.js, Express, Rails |
| +1 | 4200 | Angular |
| +2 | 5173 | Vite |
| +3 | 5000 | Flask |
| +4 | 8000 | Django, FastAPI, Hugo |
| +5 | 8080 | Go, Spring Boot |
| +6 | 8888 | Jupyter |
| +7〜+9 | (予備) | 将来の拡張用 |

**ホスト側ポート範囲:**

| 用途 | 範囲 | 備考 |
|------|------|------|
| noVNC | 6080 | Chrome/VNC 共有コンテナ用（固定） |
| Web アプリ | 8100-8899 | コンテナごとに 10 ポートブロック（最大 80 コンテナ） |

**例: コンテナ 2 つの場合**

| コンテナ | BASE | host:8100+N | コンテナ内ポート |
|---------|------|-------------|----------------|
| claude-frontend | 8100 | 8100 | 3000 |
| claude-frontend | 8100 | 8102 | 5173 |
| claude-backend | 8110 | 8115 | 8080 |

### クライアントからのアクセス方法

SSH の ControlMaster + `-O forward` を使い、既存の SSH 接続にポートフォワードを動的に追加する。

```bash
# 既存の SSH 接続にフォワードを追加（新しいターミナルは不要）
ssh -O forward -L 8102:localhost:8102 myserver

# ブラウザでアクセス
# http://localhost:8102
```

`claude-dev ports` でマッピングを確認、`claude-dev ssh-forward` で SSH コマンドを生成できる。

## Docker リソース

### ネットワーク

| 名前 | 用途 |
|------|------|
| `claude-dev-net` | コンテナ間通信 + 外部通信 |

### ボリューム

| 名前 | 用途 | マウント先 |
|------|------|-----------|
| `claude-dev-auth` | 認証ファイル（`.credentials.json`, `.claude.json`） | `/home/<user>/.claude-shared` (RW) |
| `claude-dev-history` | bash/zsh 履歴の永続化 | `/home/<user>/.command_history` |
| `claude-dev-config` | 共有シェル設定（`.zshrc`） | `/home/<user>/.config-shared` (RW) |

### イメージ

| 名前 | ベース | サイズ目安 |
|------|--------|----------|
| `claude-dev-claude` | ubuntu:24.04 | ~2.5GB |
| `claude-dev-chrome` | ubuntu:24.04 | — |
| `claude-dev-docker-proxy` | golang (multi-stage → scratch or alpine) | ~15MB |

## コンテナのライフサイクル

```
start で起動 → 常駐（restart: unless-stopped）→ stop で破棄
```

- `claude-dev start`: Claude コンテナ起動 + Chrome コンテナ自動起動 + tmux アタッチ
- SSH 切断 / tmux デタッチ (`Ctrl-B D`): コンテナは動き続ける
- `claude-dev start`（再実行）: 既存コンテナに再接続（tmux セッションがなければ再作成）
- `claude-dev stop`: Claude コンテナ削除（全 Claude コンテナ停止時は Chrome コンテナも自動停止）

## ディレクトリマッピング

```
ホスト                         コンテナ内
───────────────────────────    ─────────────────────────
~/repos/my-project        →   /workspace (RW)
claude-dev-auth volume    →   /home/<user>/.claude-shared (RW)  ※認証ファイルのみ
                               /home/<user>/.claude/ はコンテナローカル
                               /home/<user>/.claude.json → symlink
claude-dev-config volume  →   /home/<user>/.config-shared (RW)
                               /home/<user>/.zshrc → symlink → .config-shared/.zshrc
~/claude-dev-env/CLAUDE.md →  /home/<user>/CLAUDE.md (RO)
~/claude-dev-env/scripts/  →  /home/<user>/.tmux.conf (RO)
                               /usr/local/bin/init-firewall.sh
                               /usr/local/bin/entrypoint.sh
~/.gitconfig              →   /home/<user>/.gitconfig (RO)  ※存在時のみ
$SSH_AUTH_SOCK             →   /tmp/ssh-agent.sock (RO)     ※存在時のみ
~/.ssh/known_hosts        →   /home/<user>/.ssh/known_hosts (RO)  ※存在時のみ
~/.ssh/config             →   /home/<user>/.ssh/config (RO)       ※存在時のみ
```

プロジェクトディレクトリ・認証情報・シェル設定は読み書き可能。
CLAUDE.md・tmux.conf・gitconfig・SSH 関連ファイルは読み取り専用。
SSH 秘密鍵ファイル (`id_rsa`, `id_ed25519` 等) はマウントされない。

### シェル設定の共有

PATH やランタイム初期化はシステム側 (`/etc/zsh/zshrc`) に配置され、イメージに焼かれる。ユーザーの `~/.zshrc` は `claude-dev-config` ボリュームに保存され、コンテナ間で共有される（ホストとは共有しない）。

```
/etc/zsh/zshrc              ← PATH, fnm 等（イメージに固定、全コンテナ共通）
~/.zshrc → symlink          ← ユーザーカスタマイズ（ボリュームで共有）
    └→ ~/.config-shared/.zshrc
```

初回起動時にイメージのデフォルト `.zshrc` がボリュームにコピーされる。以降はボリューム側のファイルが使われるため、あるコンテナ内で `~/.zshrc` を編集すると、他のコンテナにも反映される。

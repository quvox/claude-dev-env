---
summary: システム全体の設計（コンテナ構成・Dockerリソース・認証フロー・ポートフォワード・ブラウザ操作）を俯瞰する設計文書。実装の詳細仕様は docs/impl/ を参照。
keywords: [ アーキテクチャ, Docker, VNC, 認証, ポートフォワード, コンテナ, Chrome ]
---

# アーキテクチャ設計

> **この文書の役割**: システム全体の設計（コンテナ構成・Docker リソース・認証フロー・ポートフォワード・ブラウザ操作）を俯瞰する設計文書。実装の詳細仕様は [docs/impl/](impl/INDEX.md) を参照。

## 全体構成

```
Linux サーバ (SSH でアクセス)
│
├── Makefile          セットアップ・ビルド・管理タスク
├── claude-dev CLI    日常の開発操作（/usr/local/bin/claude-dev にシンボリックリンク）
│
├── プロジェクトコンテナ（都度起動）
│   ├── project-a  (claude-dev-claude-vnc)   VNC + Chrome 付き
│   ├── project-b  (claude-dev-claude)       VNC なし（--no-vnc）
│   └── ...
│
├── Docker Socket Proxy コンテナ（共有、自動管理）
│   └── claude-dev-docker-proxy   Docker API を制限付きで中継
│
├── Docker ネットワーク
│   └── claude-dev-net         コンテナ間通信
│
└── Docker ボリューム
    ├── claude-dev-auth        認証ファイル（.credentials.json, .claude.json）
    ├── claude-dev-config      共有シェル設定（.zshrc をコンテナ間共有）
    └── claude-dev-history     コマンド履歴
```

## コンテナ構成

### Claude コンテナ（プロジェクトごと）

プロジェクトディレクトリをマウントして Claude Code を実行する環境。VNC あり/なしの 2 種類のイメージがある。

#### VNC ありコンテナ（デフォルト: `claude-dev start`）

```
┌───────────────────────────────────────────────┐
│ <project-name>  (claude-dev-claude-vnc)       │
│                                               │
│  ─── 開発ツール ───                             │
│  Node.js 24/22 (fnm) + pnpm + Claude Code    │
│  Python3 + venv/pyenv, Go, Rust               │
│  git, zsh, tmux, vim, make, gcc, curl, wget   │
│  iptables ファイアウォール                      │
│                                               │
│  ─── GUI / ブラウザ ───                         │
│  Google Chrome + TigerVNC (Xvnc) + noVNC      │
│  openbox + 日本語入力（IBus-Mozc）              │
│  ポート 6080 で noVNC を公開                    │
│  Claude Code が chrome-devtools MCP で操作             │
│                                               │
│  /workspace      ← ホストのプロジェクト (RW)    │
│  ~/.claude-shared/ ← 認証ボリューム (RW)        │
│  ~/.claude/      ← コンテナローカル（認証はコピー）│
│  ~/.claude.json  ← symlink → ~/.claude/ 内     │
│  ~/.gitconfig    ← ホストから共有 (RO)           │
│  SSH agent       ← ソケット転送（鍵ファイルなし） │
│                                               │
│  ※ Docker ソケットなし（proxy 経由で Docker API）│
│  ※ UID/GID はビルド時にホストと一致させる        │
└───────────────────────────────────────────────┘
```

#### VNC なしコンテナ（`claude-dev start --no-vnc`）

```
┌───────────────────────────────────────────────┐
│ <project-name>  (claude-dev-claude)           │
│                                               │
│  ─── 開発ツール ───                             │
│  Node.js 24/22 (fnm) + pnpm + Claude Code    │
│  Python3 + venv/pyenv, Go, Rust               │
│  git, zsh, tmux, vim, make, gcc, curl, wget   │
│  iptables ファイアウォール                      │
│                                               │
│  （Chrome / VNC なし — 軽量）                    │
│                                               │
│  /workspace      ← ホストのプロジェクト (RW)    │
│  ~/.claude-shared/ ← 認証ボリューム (RW)        │
│  ~/.claude/      ← コンテナローカル（認証はコピー）│
│  SSH agent       ← ソケット転送（鍵ファイルなし） │
└───────────────────────────────────────────────┘
```

#### 共通仕様

- **ベース**: `ubuntu:24.04`
- **言語**: Node.js 24/22 (fnm), Python3 (venv / pyenv), Go, Rust
- **ツール**: git, zsh, tmux, vim, make, gcc, curl, wget, pnpm
- **Docker**: 生ソケットはマウントしない。`DOCKER_HOST=tcp://claude-dev-docker-proxy:2375` 経由で制限付き Docker API を利用
- **ユーザー**: ホストのカレントユーザーと同名 (UID/GID はビルド時にホストと一致。entrypoint でも競合を解消して追従)
- **git 設定**: ホストの `~/.gitconfig` を読み取り専用でマウント（存在する場合）
- **SSH**: SSH agent ソケットを転送。秘密鍵ファイルはマウントしない。`~/.ssh/known_hosts` と `~/.ssh/config` は読み取り専用でマウント
- **ハードウェア仮想化 (KVM/QEMU)**: QEMU 一式（`qemu-system-x86`, `qemu-utils`, `ovmf`, `cpu-checker`, `bridge-utils`）をイメージに同梱。通常は Chrome 操作のみで十分なため、KVM デバイスは**既定では渡さない**。`claude-dev start --kvm` を指定したとき**のみ**、ホストに存在する `/dev/kvm`・`/dev/vhost-net`・`/dev/net/tun` を `--device` でコンテナに渡し、コンテナ内で KVM アクセラレーション付きの VM を起動できる（ホストに `/dev/kvm` が無ければ警告し、QEMU はソフトウェアエミュレーションで動作）。`--kvm` 指定時は entrypoint がデバイスの GID に合わせたグループを作成してユーザーをアクセス可能にする。詳細は [docs/impl/10_cli.md](impl/10_cli.md) / [docs/impl/31_entrypoint.md](impl/31_entrypoint.md)
- **VM モード（オプトイン。実装済み・要イメージ再ビルド反映）**: Docker を多用するシステム開発向けに `claude-dev start --vm` でゲスト VM（QEMU+virtiofs）を起動し、その中で**ネイティブ Docker**（bind mount・compose・privileged 可）を動かす層構成（ホスト → claude コンテナ → ゲスト VM → VM 内 Docker）。コードは virtiofs で `/workspace` を同一パス共有（ライブ反映）、Docker 接続は `DOCKER_HOST`。claude コンテナは privileged 化しない。既定は従来の軽量コンテナ（DooD+proxy）で、VM モードは重い Docker 案件のときだけ使う。設計は [docs/08_vm-mode.md](08_vm-mode.md)、実装仕様は [docs/impl/80_vm-mode.md](impl/80_vm-mode.md)

#### VNC あり固有の仕様

- **イメージ**: `claude-dev-claude-vnc`（`claude-dev-claude` のベースレイヤーを共有）
- **GUI**: Google Chrome, Xvnc, noVNC (websockify), openbox, IBus-Mozc（日本語入力）
- **ブラウザ操作**: chrome-devtools MCP サーバー経由で Chrome を操作（Chrome は `--remote-debugging-port=9222` で起動）
- **ポート**: Xvnc はディスプレイ `:99`（VNC ポート 5999）で起動。noVNC（websockify）が VNC ポート 5999 を WebSocket に変換し、HTTP ポートとしてホストに公開する。VNC 生ポート 5999 はホストに公開しない。noVNC ポートは起動時に 6080〜 の範囲で空きポートを動的に割り当てる
- **ポート確認**: `claude-dev list` で全セッションの noVNC URL を表示、`claude-dev ports [NAME]` でプロジェクト単位のポートを確認
- **日本語入力**: `Super+Space` で切替（IBus-Mozc）。`Ctrl+Shift+Space` / `Ctrl+\` / `F3` も予備として有効だが、ホスト OS やブラウザに横取りされやすいので `Super+Space` を推奨

#### VNC なし固有の仕様

- **イメージ**: `claude-dev-claude`
- **用途**: バックエンド開発、CLI ツール開発、ブラウザ不要のプロジェクト
- **起動**: `claude-dev start --no-vnc`

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
- **セキュリティ**: リクエストボディを検査し、ホストバインドマウント（ただし呼び出し元の `/workspace` 配下は実ホストパスへ書き換えて許可＝既定有効・`CLAUDE_DEV_ALLOW_WORKSPACE_BINDS` で切替）・privileged・`host` ネットワーク/PID モード等を拒否。詳細は [セキュリティ設計](03_security.md) §5 を参照

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

### DooD のポートアクセス（dood-portsync）

DooD ではコンテナは**ホストの Docker デーモン**で起動し、公開ポートは**ホストの `0.0.0.0:PORT`** に出る。一方 Claude コンテナは別 network namespace のため、コンテナ内テスト等が叩く `127.0.0.1:PORT` はホストの公開ポートに届かない（Claude コンテナ自身のループバックを指すため）。

これを解消するため、DooD モードでは Claude コンテナ内に常駐ヘルパー **`dood-portsync`** を起動する（VM モードの `vm-portsync` に相当）。ホスト（共有 daemon）に公開されたポートを検出し、`socat` で **`127.0.0.1:PORT`（コンテナ内ループバック限定）→ デフォルトゲートウェイ（＝ホスト）:PORT** の転送を張る。これにより `127.0.0.1:PORT` がホスト公開ポートへ到達できる。

- 転送のリスナーは各 Claude コンテナ内 `127.0.0.1` のみ（ホストへは何も新規公開しない）。ただし DooD の性質上、**サービスの実ポートはホスト `0.0.0.0:PORT` に既に公開**されている（ホスト側で可視・別プロジェクトと同一ポートは衝突しうる）。ホスト非公開・ポート隔離が必要なら VM モードを使う（[03_security.md](03_security.md) §5 / [08_vm-mode.md](08_vm-mode.md)）。
- 既定有効。`CLAUDE_DEV_DOOD_PORTSYNC=0` で無効化できる。実装は [docs/impl/30_scripts.md](impl/30_scripts.md)（`dood-portsync.sh`）・[docs/impl/31_entrypoint.md](impl/31_entrypoint.md)（自動起動）。

## ブラウザ操作

VNC ありコンテナでは、chrome-devtools MCP サーバー経由でコンテナ内の Google Chrome を操作する。Chrome は `--remote-debugging-port=9222` で起動し、MCP サーバーが DevTools Protocol で Chrome を制御する。

### 構成

```
┌─ ユーザーの PC ─────────────────────────────────┐
│  ブラウザ → http://localhost:<port>/vnc.html   │  ← リアルタイム確認
└────────────────────────────────────────────────┘
        │ HTTP/WebSocket（noVNC ポートのみ公開）
        ▼
┌─ Claude コンテナ (claude-dev-claude-vnc) ─────────────────────┐
│                                                               │
│  Xvnc :99 (port 5999)  ← X11 + VNC 統合（コンテナ内のみ）      │
│  noVNC (websockify)    ← HTTP port <動的割当> → VNC port 5999 │
│  openbox               ← ウィンドウマネージャ                  │
│  IBus-Mozc             ← 日本語入力                           │
│                                                               │
│  Google Chrome         ← --remote-debugging-port=9222         │
│  chrome-devtools MCP   ← DevTools Protocol で Chrome を操作    │
│                                                               │
│  Claude Code           ← MCP 経由で Chrome を操作              │
│  tmux                  ← 開発作業                             │
│                                                               │
│  /workspace            ← プロジェクトディレクトリ               │
└───────────────────────────────────────────────────────────────┘
※ Xvnc :99 → VNC port 5999（コンテナ内のみ、ホスト非公開）
※ noVNC (websockify) が VNC port 5999 → HTTP port に変換
※ noVNC の HTTP ポートは起動時に 6080〜 から空きを動的割り当て
※ Chrome DevTools port 9222 はコンテナ内のみ（ホスト非公開）
```

**旧アーキテクチャとの違い:**

| 項目 | 旧（共有 Chrome コンテナ） | 新（コンテナ内統合） |
|------|--------------------------|---------------------|
| Chrome の場所 | 別コンテナ（`claude-dev-chrome`） | Claude コンテナ内 |
| 操作方法 | MCP Chrome DevTools（socat 二段リレー） | chrome-devtools MCP（コンテナ内 localhost 直結） |
| 複数プロジェクト | 1つの Chrome を共有（競合あり） | プロジェクトごとに独立（競合なし） |
| noVNC ポート | 6080 固定（共有） | コンテナごとに個別割り当て（6080〜） |
| ブラウザ不要時 | Chrome コンテナが常に起動 | `--no-vnc` で軽量コンテナを使用 |

### MCP 設定

entrypoint がコンテナ起動時に以下を自動設定する:

1. **`.mcp.json`**: `/workspace/.mcp.json` に `chrome-devtools` エントリを追加。既存の `.mcp.json` がある場合は `chrome-devtools` が未定義のときのみ追加し、他のエントリは保持する。ファイルがなければ新規作成する。

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["-y", "chrome-devtools-mcp@latest", "--browserUrl", "http://localhost:9222"]
    }
  }
}
```

2. **`.claude.json`**: `/workspace/.claude/.claude.json` の `projects["/workspace"].enabledMcpjsonServers` に `"chrome-devtools"` を追加（未登録の場合のみ）。これにより Claude Code が MCP サーバーを自動的に利用する。

### 動作フロー

1. `claude-dev start` でコンテナ起動。entrypoint が Xvnc → openbox → Chrome（`--remote-debugging-port=9222`）→ noVNC を順に起動
2. Claude Code が chrome-devtools MCP サーバー経由で Chrome を操作（ページ遷移、クリック、入力、スクリーンショット等）
3. ユーザーは noVNC (`http://localhost:<port>/vnc.html`) で操作をリアルタイムに確認
4. `--no-vnc` の場合は VNC/Chrome/MCP 関連のプロセスが起動しない

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
│ 4. 認証ファイルのパーミッション修正（コピーは CLI 側で実施済み）│
│ 5. ~/.claude.json → ~/.claude/.claude.json へリンク │
│ 6. settings.json がなければ新規作成（コンテナ固有）  │
│ 7. 認証ファイル同期のバックグラウンドプロセス起動     │
│ 8. ファイアウォール設定                           │
│ 9. CLAUDE.md にコンテナ環境情報を書き込み          │
│ 10. MCP 設定（VNC あり: .mcp.json + .claude.json） │
│ 11. VNC/Chrome 起動（VNC ありイメージの場合）      │
│ 12. tmux セッション開始                          │
└──────────────────────────────────────────────────┘
```

## ポートフォワーディング

### 概要

コンテナ内で起動した Web アプリにクライアント PC のブラウザからアクセスするため、`claude-dev forward` コマンドでポートを動的にフォワードする。`claude-dev start` 時にはポートマッピングは行われない（noVNC ポートのみ VNC ありコンテナで公開）。

フォワードは軽量な socat プロキシコンテナ（`fwd-<name>-<port>`）を同じ Docker ネットワーク上に作成することで実現する。ホスト側ポートは 8100 番台から自動的に割り当てられる。

```
┌─ Client PC ──────────────┐
│  Browser → localhost:8100 │
└──────┬───────────────────┘
       │ SSH Tunnel (ssh -O forward)
       │
┌──────▼──────────────────────────────────────────────┐
│  Server Host                                        │
│                                                     │
│  ┌─ fwd-frontend-5173 (socat proxy) ──────────────┐ │
│  │  host:8100 → claude-dev-net → frontend:5173    │ │
│  └────────────────────────────────────────────────┘ │
│                                                     │
│  ┌─ fwd-backend-8080 (socat proxy) ───────────────┐ │
│  │  host:8101 → claude-dev-net → backend:8080     │ │
│  └────────────────────────────────────────────────┘ │
│                                                     │
│  ┌─ frontend (claude-dev-claude-vnc) ─────────────┐ │
│  │  Vite :5173                                    │ │
│  └────────────────────────────────────────────────┘ │
│                                                     │
│  ┌─ backend (claude-dev-claude) ──────────────────┐ │
│  │  Go :8080                                      │ │
│  └────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### ポート割り当て

ポートは事前に固定割り当てされず、`claude-dev forward` 実行時に 8100 番台から空きポートを順に割り当てる。

**ホスト側ポート範囲:**

| 用途 | 範囲 | 備考 |
|------|------|------|
| noVNC | 6080〜 | VNC ありコンテナごとに動的割り当て（HTTP/WebSocket のみ公開） |
| Web アプリ | 8100〜 | `claude-dev forward` で動的に割り当て |

Xvnc はディスプレイ `:99`（VNC ポート 5999 = 5900 + 99）で起動し、noVNC（websockify）が VNC ポート 5999 を HTTP/WebSocket に変換してホストに公開する。noVNC ポートは起動時に 6080〜 から空きを探して割り当てる。VNC 生ポート 5999 はコンテナ内でのみ使用し、ホストには公開しない。

**ポート確認方法:**

```bash
claude-dev ports [NAME]      # アクティブなフォワードと noVNC URL を表示
claude-dev list              # 全セッションの noVNC URL + フォワード状況を表示
```

### フォワードの操作

```bash
# ポートをフォワード（ホスト側ポートは自動割り当て）
claude-dev forward 3000                # カレントディレクトリのプロジェクト
claude-dev forward 8080 backend        # プロジェクト名を指定

# フォワード解除
claude-dev unforward 3000
claude-dev unforward 8080 backend

# アクティブなフォワード一覧
claude-dev ports
```

### クライアントからのアクセス方法

SSH の ControlMaster + `-O forward` を使い、既存の SSH 接続にポートフォワードを動的に追加する。

```bash
# サーバ上でフォワードを作成
claude-dev forward 5173           # → ✅ host:8100 → myproject:5173

# クライアント PC で SSH トンネルを追加
ssh -O forward -L 8100:localhost:8100 myserver

# ブラウザでアクセス
# http://localhost:8100
```

`claude-dev ports` でアクティブなフォワードを確認できる。

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
| `claude-dev-chrome-data` | Chrome プロファイル（VNC ありコンテナのみ） | `/home/<user>/.chrome-profile` (RW) |

### イメージ

| 名前 | ベース | 内容 | サイズ目安 |
|------|--------|------|----------|
| `claude-dev-claude` | ubuntu:24.04 | 開発ツール + Claude Code（VNC なし） | ~2.5GB |
| `claude-dev-claude-vnc` | claude-dev-claude | + Chrome + TigerVNC + noVNC | ~3.5GB |
| `claude-dev-docker-proxy` | golang (multi-stage) | Docker API プロキシ | ~15MB |

`claude-dev-claude-vnc` は `claude-dev-claude` をベースレイヤーとして共有するため、Docker の層キャッシュにより追加のディスク使用量は Chrome/VNC 分のみ。

## Docker イメージのビルド構成

マルチステージビルドにより、ベースイメージのレイヤーを VNC あり/なしで共有する。

```
Dockerfile.claude
├── Stage: base （FROM ubuntu:24.04 AS base）
│   └── Ubuntu 24.04 + Node.js + Python + Go + Rust
│       + Claude Code + 開発ツール一式
│       → イメージ claude-dev-claude（VNC なし）
│
└── Stage: vnc （FROM base AS vnc）
    └── + Google Chrome + TigerVNC + noVNC + openbox + IBus-Mozc
        （chrome-devtools-mcp は npx で実行時に取得）
        → イメージ claude-dev-claude-vnc（VNC あり）
```

- 1 つの Dockerfile に 2 つのステージ（`base` / `vnc`）を定義する
- `docker build --target base -t claude-dev-claude` → VNC なしイメージ
- `docker build --target vnc -t claude-dev-claude-vnc` → VNC ありイメージ
- ベースレイヤーは Docker のキャッシュで共有されるため、ディスク効率が良い
- `make build-claude` は `base`（VNC なし）のみ、`make build-claude-vnc` は `base` に続けて `vnc` をビルドする。両方をまとめて作るには `make build`

## コンテナのライフサイクル

```
start で起動 → 常駐（restart: unless-stopped）→ stop で破棄
```

- `claude-dev start`: Claude コンテナ起動（VNC あり）+ tmux アタッチ
- `claude-dev start --no-vnc`: Claude コンテナ起動（VNC なし）+ tmux アタッチ
- SSH 切断 / tmux デタッチ (`Ctrl-_ D`): コンテナは動き続ける
- `claude-dev start`（再実行）: 既存コンテナに再接続（tmux セッションがなければ再作成）
- `claude-dev stop`: Claude コンテナ削除（全 Claude コンテナ停止時は Docker Proxy コンテナも自動停止）

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

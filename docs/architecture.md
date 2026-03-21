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
├── Docker ネットワーク
│   └── claude-dev-net         コンテナ間通信
│
└── Docker ボリューム
    ├── claude-dev-auth        認証情報（~/.claude/ と ~/.claude.json）+ Chrome 認証共有
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
│  Playwright Chromium（ヘッドレステスト用）       │
│  git, zsh, tmux, vim, make, gcc, curl, wget   │
│  iptables ファイアウォール                      │
│                                               │
│  /workspace      ← ホストのプロジェクト (RW)    │
│  ~/.claude/      ← 認証ボリューム (RW)          │
│  ~/.claude.json  ← symlink → ~/.claude/ 内     │
│  ~/.gitconfig    ← ホストから共有 (RO)           │
│  SSH agent       ← ソケット転送（鍵ファイルなし） │
│                                               │
│  ※ Docker ソケットなし                         │
│  ※ UID/GID はビルド時にホストと一致させる        │
└───────────────────────────────────────────────┘
```

- **イメージ**: `claude-dev-claude`
- **ベース**: `ubuntu:24.04`
- **言語**: Node.js 24/22 (fnm), Python3 (venv), Go, Rust
- **ツール**: git, zsh, tmux, vim, make, gcc, curl, wget, pnpm, Playwright Chromium（ヘッドレステスト用）, etc.
- **ユーザー**: ホストのカレントユーザーと同名 (UID/GID はビルド時にホストと一致。entrypoint でも競合を解消して追従)
- **git 設定**: ホストの `~/.gitconfig` を読み取り専用でマウント（存在する場合）
- **SSH**: SSH agent ソケットを転送。秘密鍵ファイルはマウントしない。`~/.ssh/known_hosts` と `~/.ssh/config` は読み取り専用でマウント
- **起動**: ssh-agent 準備 → Chrome コンテナ自動起動 → Claude コンテナ作成 → entrypoint が UID/GID 調整 → 認証 symlink → ファイアウォール → tmux → 待機

### Chrome/VNC コンテナ（共有）

全 Claude コンテナで共有される GUI 環境。`claude-dev start` 時に自動的に起動される。

```
┌───────────────────────────────────────────────┐
│ claude-dev-chrome  (ubuntu:24.04)             │
│                                               │
│  Google Chrome + 日本語入力（fcitx5-mozc）      │
│  Xvfb + x11vnc + noVNC                       │
│  ポート 6080 で noVNC を公開                    │
│                                               │
│  ~/.claude/      ← 認証ボリューム (RW)          │
│                    Chrome 認証情報の共有用       │
│                                               │
│  ※ Ctrl+Space で日本語入力切替                  │
│  ※ 全 Claude コンテナ停止時に自動停止            │
└───────────────────────────────────────────────┘
```

- **イメージ**: `claude-dev-chrome`
- **ベース**: `ubuntu:24.04`
- **ツール**: Google Chrome, Xvfb, x11vnc, noVNC, fcitx5-mozc（日本語入力）
- **ポート**: 6080（noVNC、全コンテナ共有）
- **ボリューム**: `claude-dev-auth` を `~/.claude/` にマウント（Chrome の認証情報共有用）
- **ライフサイクル**: `claude-dev start` で自動起動、全 Claude コンテナ停止時に自動停止

## 認証の仕組み

Claude Code は認証情報を以下の 2 箇所に保存する：

- `~/.claude.json` — アカウント情報、設定、セッションデータ
- `~/.claude/` — 設定ファイル、内部データ

### ボリュームマウント方式

`claude-dev-auth` ボリュームを `~/.claude/` に直接マウントすることで、認証情報を永続化する。`~/.claude.json` は `~/.claude/.claude.json` へのシンボリックリンクとして管理する。

```
Docker ボリューム: claude-dev-auth
    │
    ├── .claude.json     ← ~/.claude.json の実体
    ├── settings.json    ← bypassPermissions 設定
    └── (その他の内部データ)

コンテナ内:
    ~/.claude/           ← ボリュームが直接マウント (RW)
    ~/.claude.json       ← symlink → ~/.claude/.claude.json
```

この方式により：
- login で保存した認証情報が、全プロジェクトコンテナで共有される
- コンテナを削除・再作成しても認証情報は失われない
- コピー処理が不要（ボリュームが直接マウントされるため）

### 認証フロー

```
┌─────────┐     ┌───────────────────┐     ┌──────────────┐
│ ユーザー │     │ login 一時コンテナ │     │ auth volume  │
└────┬────┘     └────────┬──────────┘     └──────┬───────┘
     │                   │                        │
     │ claude-dev login  │                        │
     │──────────────────→│                        │
     │                   │ volume を ~/.claude に   │
     │                   │ 直接マウント             │
     │                   │←───────────────────────│
     │                   │                        │
     │ Claude Code 起動  │                        │
     │   URL 表示        │                        │
     │←──────────────────│                        │
     │                   │                        │
     │ ブラウザで認証     │                        │
     │──────────────────→│                        │
     │                   │ ~/.claude.json 書込     │
     │                   │ ~/.claude/ 書込         │
     │                   │───────────────────────→│
     │                   │                        │
     │ /exit で終了      │ .claude.json を         │
     │──────────────────→│ ボリュームにコピー        │
     │                   │───────────────────────→│
```

1. `claude-dev login` が一時コンテナを起動（`claude-dev-auth` ボリュームを `~/.claude/` にマウント）
2. Claude Code が対話的に起動し、ブラウザ認証 URL を表示
3. ユーザーがブラウザで認証を完了
4. Claude Code が `~/.claude.json` と `~/.claude/` に認証データを書き込み
5. `/exit` で終了すると、`~/.claude.json` がボリューム内（`~/.claude/.claude.json`）にコピーされ永続化

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
┌─ entrypoint-claude.sh ──────────────────────┐
│ 1. /workspace の UID/GID を検出              │
│ 2. ユーザーの UID/GID をホストに合わせる        │
│    （競合する既存ユーザー/グループは退避）       │
│ 3. ~/.ssh ディレクトリの所有権を設定           │
│ 4. ~/.claude/.claude.json への symlink 作成  │
│    → ~/.claude.json                         │
│ 5. settings.json がなければ再作成            │
│ 6. ファイアウォール設定                       │
│ 7. tmux セッション開始                       │
└──────────────────────────────────────────────┘
```

`claude-dev-auth` ボリュームが `~/.claude/` にマウントされるため、login で保存した認証情報がそのまま使える。entrypoint はシンボリックリンクの作成と `settings.json` の確保のみ行う。

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
| `claude-dev-auth` | 認証情報（`~/.claude.json` + `~/.claude/`） | `/home/<user>/.claude` (RW) |
| `claude-dev-history` | bash/zsh 履歴の永続化 | `/home/<user>/.command_history` |
| `claude-dev-config` | 共有シェル設定（`.zshrc`） | `/home/<user>/.config-shared` (RW) |

### イメージ

| 名前 | ベース | サイズ目安 |
|------|--------|----------|
| `claude-dev-claude` | ubuntu:24.04 | ~2.5GB |
| `claude-dev-chrome` | ubuntu:24.04 | — |

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
claude-dev-auth volume    →   /home/<user>/.claude (RW)
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

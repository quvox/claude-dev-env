# アーキテクチャ設計

## 全体構成

```
Linux サーバ (SSH でアクセス)
│
├── Makefile          セットアップ・ビルド・管理タスク
├── claude-dev CLI    日常の開発操作（/usr/local/bin/claude-dev にシンボリックリンク）
│
├── Samba コンテナ（常駐）
│   └── ファイル共有
│
├── プロジェクトコンテナ（都度起動）
│   ├── claude-project-a       ~/repos/project-a をマウント
│   ├── claude-project-b       ~/repos/project-b をマウント
│   └── ...
│
├── Docker ネットワーク
│   └── claude-dev-net         コンテナ間通信
│
└── Docker ボリューム
    ├── claude-dev-auth        認証情報（~/.claude/ と ~/.claude.json）
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
│  Chromium + Playwright 依存パッケージ           │
│  git, zsh, tmux, vim, make, gcc, curl, wget   │
│  iptables ファイアウォール                      │
│                                               │
│  /workspace      ← ホストのプロジェクト (RW)    │
│  ~/.claude/      ← 認証ボリューム (RW)          │
│  ~/.claude.json  ← symlink → ~/.claude/ 内     │
│                                               │
│  ※ Docker ソケットなし                         │
│  ※ UID/GID はホストに自動追従                   │
└───────────────────────────────────────────────┘
```

- **イメージ**: `claude-dev-claude`
- **ベース**: `ubuntu:24.04`
- **言語**: Node.js 24/22 (fnm), Python3 (venv), Go, Rust
- **ツール**: git, zsh, tmux, vim, make, gcc, curl, wget, pnpm, Chromium, etc.
- **ユーザー**: `devuser` (UID はホストに自動追従)
- **起動**: entrypoint が UID/GID 調整 → 認証 symlink → ファイアウォール → tmux → 待機

### Samba コンテナ（常駐）

プロジェクトファイルをネットワーク経由で公開する。

- **イメージ**: `claude-dev-samba`
- **ベース**: `alpine:3.21`
- **共有先**: `.env` の `SAMBA_SHARE_DIR` で指定したディレクトリ
- **macOS 互換**: VFS fruit モジュール有効

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
     ▼
┌─ entrypoint-claude.sh ──────────────────────┐
│ 1. /workspace の UID/GID を検出              │
│ 2. devuser の UID/GID をホストに合わせる      │
│ 3. ~/.claude/.claude.json への symlink 作成  │
│    → ~/.claude.json                         │
│ 4. settings.json がなければ再作成            │
│ 5. ファイアウォール設定                       │
│ 6. tmux セッション開始                       │
└──────────────────────────────────────────────┘
```

`claude-dev-auth` ボリュームが `~/.claude/` にマウントされるため、login で保存した認証情報がそのまま使える。entrypoint はシンボリックリンクの作成と `settings.json` の確保のみ行う。

## Docker リソース

### ネットワーク

| 名前 | 用途 |
|------|------|
| `claude-dev-net` | コンテナ間通信 + 外部通信 |

### ボリューム

| 名前 | 用途 | マウント先 |
|------|------|-----------|
| `claude-dev-auth` | 認証情報（`~/.claude.json` + `~/.claude/`） | `/home/devuser/.claude` (RW) |
| `claude-dev-history` | bash/zsh 履歴の永続化 | `/home/devuser/.command_history` |

### イメージ

| 名前 | ベース | サイズ目安 |
|------|--------|----------|
| `claude-dev-claude` | ubuntu:24.04 | ~2.5GB |
| `claude-dev-samba` | alpine:3.21 | ~15MB |

## コンテナのライフサイクル

### Samba（常駐）

```
make setup で起動 → 常駐（restart: unless-stopped）→ make clean で破棄
```

サーバ再起動後も自動復帰する。

### プロジェクトコンテナ

```
start で起動 → 常駐（restart: unless-stopped）→ stop で破棄
```

- `claude-dev start`: 起動 + tmux アタッチ
- SSH 切断 / tmux デタッチ (`Ctrl-B D`): コンテナは動き続ける
- `claude-dev start`（再実行）: 既存コンテナに再接続（tmux セッションがなければ再作成）
- `claude-dev stop`: コンテナ削除（プロジェクトファイルはホスト上なので安全）

## ディレクトリマッピング

```
ホスト                         コンテナ内
───────────────────────────    ─────────────────────────
~/repos/my-project        →   /workspace (RW)
claude-dev-auth volume    →   /home/devuser/.claude (RW)
                               /home/devuser/.claude.json → symlink
~/claude-dev-env/CLAUDE.md →  /home/devuser/CLAUDE.md (RO)
~/claude-dev-env/scripts/  →  /home/devuser/.tmux.conf (RO)
                               /usr/local/bin/init-firewall.sh
                               /usr/local/bin/entrypoint.sh
```

プロジェクトディレクトリと認証情報は読み書き可能。
CLAUDE.md・tmux.conf は読み取り専用。

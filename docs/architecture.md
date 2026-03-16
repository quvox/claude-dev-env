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
    ├── claude-dev-auth        OAuth 認証情報
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
│  git, zsh, tmux, vim, make, gcc, curl, wget   │
│  iptables ファイアウォール                      │
│                                               │
│  /workspace ← ホストのプロジェクトディレクトリ    │
│  ~/.claude-auth/ ← 認証情報（読み取り専用）      │
│  ~/.claude.json ← 起動時にコピー               │
│                                               │
│  ※ Docker ソケットなし                         │
│  ※ UID/GID はホストに自動追従                   │
└───────────────────────────────────────────────┘
```

- **イメージ**: `claude-dev-claude`
- **ベース**: `ubuntu:24.04`
- **言語**: Node.js 24/22 (fnm), Python3 (venv), Go, Rust
- **ツール**: git, zsh, tmux, vim, make, gcc, curl, wget, pnpm, etc.
- **ユーザー**: `devuser` (UID はホストに自動追従)
- **起動**: entrypoint が UID/GID 調整 → 認証情報コピー → ファイアウォール → tmux → 待機

### Samba コンテナ（常駐）

プロジェクトファイルをネットワーク経由で公開する。

- **イメージ**: `claude-dev-samba`
- **ベース**: `alpine:3.21`
- **共有先**: `.env` の `SAMBA_SHARE_DIR` で指定したディレクトリ
- **macOS 互換**: VFS fruit モジュール有効

## 認証フロー

```
┌─────────┐     ┌───────────────┐     ┌──────────────┐
│ ユーザー │     │ 一時コンテナ   │     │  auth volume  │
└────┬────┘     └───────┬───────┘     └──────┬───────┘
     │                  │                     │
     │ claude-dev login │                     │
     │─────────────────→│                     │
     │                  │                     │
     │    URL 表示      │                     │
     │←─────────────────│                     │
     │                  │                     │
     │ ブラウザで認証    │                     │
     │─────────────────→│                     │
     │                  │ claude.json 保存     │
     │                  │────────────────────→│
     │                  │                     │
```

1. `claude-dev login` が Claude イメージを使った一時コンテナを起動
2. コンテナ内で `claude login` を実行（ブラウザ認証）
3. 認証情報 (`~/.claude.json`) を `claude-dev-auth` ボリュームに `claude.json` として保存
4. 一時コンテナは終了

### プロジェクト起動時の認証

```
claude-dev start
     │
     ▼
┌─ entrypoint-claude.sh ──────────────────────┐
│ 1. /workspace の UID/GID を検出              │
│ 2. devuser の UID/GID をホストに合わせる      │
│ 3. ~/.claude-auth/claude.json (RO) を       │
│    ~/.claude.json にコピー                   │
│ 4. ファイアウォール設定                       │
│ 5. tmux セッション開始                       │
└──────────────────────────────────────────────┘
```

`claude-dev-auth` ボリュームは読み取り専用 (`:ro`) でマウントされる。entrypoint がコンテナ内の `~/.claude.json` にコピーすることで Claude Code が認証情報を読み取れるようになる。

## Docker リソース

### ネットワーク

| 名前 | 用途 |
|------|------|
| `claude-dev-net` | コンテナ間通信 + 外部通信 |

### ボリューム

| 名前 | 用途 | アクセス |
|------|------|---------|
| `claude-dev-auth` | OAuth 認証情報 | login 時に書き込み、start 時に読み取り専用マウント |
| `claude-dev-history` | bash/zsh 履歴の永続化 | 全 Claude コンテナ |

### イメージ

| 名前 | ベース | サイズ目安 |
|------|--------|----------|
| `claude-dev-claude` | ubuntu:24.04 | ~2GB |
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
- SSH 切断 / tmux デタッチ: コンテナは動き続ける
- `claude-dev start`（再実行）: 既存コンテナに再接続
- `claude-dev stop`: コンテナ削除（プロジェクトファイルはホスト上なので安全）

## ディレクトリマッピング

```
ホスト                         コンテナ内
───────────────────────────    ─────────────────────────
~/repos/my-project        →   /workspace (RW)
claude-dev-auth volume    →   /home/devuser/.claude-auth (RO)
~/claude-dev-env/CLAUDE.md →  /home/devuser/CLAUDE.md (RO)
~/claude-dev-env/scripts/  →  /home/devuser/.tmux.conf (RO)
                               /usr/local/bin/init-firewall.sh
                               /usr/local/bin/entrypoint.sh
```

プロジェクトディレクトリは読み書き可能でマウントされる。
認証情報・CLAUDE.md・tmux.conf は読み取り専用。

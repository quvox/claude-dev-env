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
│  Xvfb + x11vnc + noVNC（--chrome 時のみ起動）  │
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
- **ユーザー**: ホストのカレントユーザーと同名 (UID/GID はホストに自動追従)
- **起動**: entrypoint が UID/GID 調整 → 認証 symlink → ファイアウォール → (VNC) → tmux → 待機
- **`--chrome` モード**: `ENABLE_VNC=1` 環境変数で Xvfb + x11vnc + noVNC を起動。ポート 6080 を公開し、ブラウザから Chrome を操作できる

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
│ 2. ユーザーの UID/GID をホストに合わせる        │
│ 3. ~/.claude/.claude.json への symlink 作成  │
│    → ~/.claude.json                         │
│ 4. settings.json がなければ再作成            │
│ 5. ファイアウォール設定                       │
│ 6. tmux セッション開始                       │
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
| noVNC | 6080-6179 | `--chrome` オプション用（既存） |
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

### イメージ

| 名前 | ベース | サイズ目安 |
|------|--------|----------|
| `claude-dev-claude` | ubuntu:24.04 | ~2.5GB |

## コンテナのライフサイクル

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
claude-dev-auth volume    →   /home/<user>/.claude (RW)
                               /home/<user>/.claude.json → symlink
~/claude-dev-env/CLAUDE.md →  /home/<user>/CLAUDE.md (RO)
~/claude-dev-env/scripts/  →  /home/<user>/.tmux.conf (RO)
                               /usr/local/bin/init-firewall.sh
                               /usr/local/bin/entrypoint.sh
```

プロジェクトディレクトリと認証情報は読み書き可能。
CLAUDE.md・tmux.conf は読み取り専用。

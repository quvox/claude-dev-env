---
summary: ファイアウォール・CLAUDE.md・tmux・hooks/envなど、利用者が環境を調整するためのカスタマイズ手順をまとめた利用者向けガイド。
keywords: [ カスタマイズ, ファイアウォール, hooks, Slack通知, tmux, KVM, デスクトップ操作 ]
---

# カスタマイズガイド

> **この文書の役割**: ファイアウォール・CLAUDE.md・tmux・hooks/env など、利用者が環境を調整するためのカスタマイズ手順をまとめた利用者向けガイド。

## ファイアウォールのカスタマイズ

### ブラックリストにドメインを追加する

`scripts/init-firewall-claude.sh` の `BLACKLIST_DOMAINS` 配列を編集する:

```bash
BLACKLIST_DOMAINS=(
    # 既存のリスト...

    # 自社の本番環境
    "production-api.example.com"
    "prod-db.example.com"

    # その他のブロックしたいサービス
    "some-dangerous-site.com"
)
```

変更後、イメージを再ビルドしてコンテナを再起動すると反映される:

```bash
make build-claude
claude-dev stop my-project
cd ~/repos/my-project
claude-dev start
```

### ポートを追加でブロックする

同ファイル内に iptables ルールを追加する:

```bash
# FTP をブロック
iptables -A OUTPUT -p tcp --dport 21 -j REJECT

# MySQL への直接接続をブロック
iptables -A OUTPUT -p tcp --dport 3306 -j REJECT
```

### ホワイトリスト方式に切り替える

セキュリティを最大化する場合。`scripts/init-firewall-claude.sh` を編集:

```bash
# デフォルトポリシーを DROP に変更
iptables -P OUTPUT DROP

# 必要な宛先のみ許可
# ローカル
iptables -A OUTPUT -o lo -j ACCEPT
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# DNS
iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
iptables -A OUTPUT -p tcp --dport 53 -j ACCEPT

# npm registry
iptables -A OUTPUT -d registry.npmjs.org -p tcp --dport 443 -j ACCEPT

# GitHub
iptables -A OUTPUT -d github.com -p tcp --dport 443 -j ACCEPT

# Anthropic API
iptables -A OUTPUT -d api.anthropic.com -p tcp --dport 443 -j ACCEPT

# PyPI
iptables -A OUTPUT -d pypi.org -p tcp --dport 443 -j ACCEPT
```

## Claude Code の更新

Claude Code はネイティブインストーラー (`curl -fsSL https://claude.ai/install.sh | bash`) でインストールされる。更新するにはイメージを再ビルドする:

```bash
make upgrade
```

実行中のコンテナには反映されないので、再起動が必要:

```bash
claude-dev stop my-project
cd ~/repos/my-project
claude-dev start
```

## CLAUDE.md のカスタマイズ

### グローバル設定（全プロジェクト共通）

`<claude-dev-env>/CLAUDE.md` を編集する。このファイルはコンテナ内のホームディレクトリに読み取り専用でマウントされ、Claude Code がどのプロジェクトでも読み取る。

```markdown
# CLAUDE.md - コンテナ内開発環境

## 環境情報
- Docker コンテナ内で実行中
- API 通信は直接 Anthropic API に接続

## 共通ルール
- テストは必ず実行してからコミットすること
- 日本語でコメントを書くこと
```

### プロジェクト固有の設定

プロジェクトのルートディレクトリに `CLAUDE.md` を配置する:

```markdown
# CLAUDE.md - my-project

## 技術スタック
- TypeScript + React
- PostgreSQL

## コーディング規約
- ...
```

プロジェクトの `CLAUDE.md` はグローバル設定より優先される（より具体的なパスが優先）。

## Claude Code hooks / 環境変数の設定

Claude Code の **hooks**（`UserPromptSubmit`, `Notification`, `Stop` 等のイベントで任意コマンドを実行する機構）と **環境変数**（`env` フィールド）は、ホストの `~/.claude/settings.json` に記述する。コンテナ内の `/workspace/.claude/settings.json` ではなく、必ず**ホスト側の `~/.claude/settings.json`** に書くこと。

### 仕組み

`claude-dev start` 時、ホストの `~/.claude/settings.json` から `hooks` と `env` のフィールドだけが抽出され、Claude コンテナの `~/.claude/settings.json` にマージされる（`scripts/entrypoint-claude.sh` 内で `jq * $overlay[0]` を使用）。抽出対象は **`hooks` と `env` のみ**。それ以外（`permissions` 等）はコピーされない。

### 組み込み hook スクリプト

`scripts/save_prompt.sh`（プロンプト先頭30文字を `/tmp/claude_prompt_${session_id}.txt` に保存）と `scripts/sendslackmsg.sh`（Slack に通知を送信）はリポジトリで管理され、Claude イメージのビルド時に **`/usr/local/bin/` に焼き込まれる**（`Dockerfile.claude`）。hook の command でフルパスを指定すれば、すべての Claude コンテナで使える。

スクリプトを編集した場合は **イメージの再ビルドが必要**:

```bash
make build-claude
claude-dev stop my-project
cd ~/repos/my-project
claude-dev start
```

### ユーザー独自の hook スクリプト

組み込みスクリプトとは別に、ホストの `~/.local/bin/` 配下にスクリプトを置けば `claude-dev start` 時にコンテナの `~/.local/bin/` にコピーされる。再ビルド不要で反映できるため、試作や個人用カスタマイズはこちらが向く。

### 例: Slack 通知 hook

ホストの `~/.claude/settings.json` で hook と環境変数を定義:

```json
{
  "env": {
    "SLACK_BOT_TOKEN": "xoxb-...",
    "SLACK_CHANNEL": "Cxxxxxxxx"
  },
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/usr/local/bin/save_prompt.sh"
          }
        ]
      }
    ],
    "Notification": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "/usr/local/bin/sendslackmsg.sh \"🔔 Claude Code が入力待ちです\""
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/usr/local/bin/sendslackmsg.sh \"✅ Claude Code の処理が完了しました\""
          }
        ]
      }
    ]
  }
}
```

`SLACK_BOT_TOKEN` は Slack Bot User OAuth Token、`SLACK_CHANNEL` は通知先のチャンネル ID または DM のユーザー ID。

### 注意事項

- **コンテナ起動中の変更は反映されない**: `hooks` や `env` を変更したら `claude-dev stop` → `claude-dev start` で再起動する。
- **プロジェクトの `<workspace>/.claude/settings.json` に同じ hooks を書かない**: ユーザーレベル（`~/.claude/`）とプロジェクトレベル（`<workspace>/.claude/`）の hooks は両方とも実行されるので、両方に同じ hook を書くと**通知が2回飛ぶ**。
- **シークレットのハードコード禁止**: `scripts/sendslackmsg.sh` のような git 管理下のスクリプトにトークンを書き込まないこと。`env` フィールドに置き、スクリプトは環境変数経由で受け取る。

## tmux 設定のカスタマイズ

`scripts/tmux.conf` を編集する。主な設定項目:

```bash
# プレフィックスキーの変更（デフォルト: Ctrl-_、例: Ctrl-A に変更する場合）
set -g prefix C-a
unbind C-_
bind C-a send-prefix

# 履歴の上限変更
set -g history-limit 100000

# マウス操作の無効化
set -g mouse off
```

変更後、イメージの再ビルドは不要（読み取り専用マウントで直接反映）。ただし実行中のコンテナには再起動が必要:

```bash
claude-dev stop my-project
cd ~/repos/my-project
claude-dev start
```

## zshrc のカスタマイズ

`~/.zshrc` は `claude-dev-config` ボリュームに保存され、全コンテナ間で共有される（ホストとは共有しない）。

任意のコンテナ内で `~/.zshrc` を編集すれば、他のコンテナにも反映される:

```bash
# コンテナ内で
echo 'alias ll="ls -la"' >> ~/.zshrc
source ~/.zshrc
```

PATH やランタイム初期化（fnm, Go, Rust, pyenv 等）はシステム側 (`/etc/zsh/zshrc`) に配置されており、`~/.zshrc` を編集しても壊れない（pyenv は `~/.zshrc.default` にも二重初期化ガード付きで入っている）。

**注意:** `~/.zshrc` のリセットが必要な場合は、`claude-dev-config` ボリュームを削除してコンテナを再起動する:

```bash
claude-dev stop my-project
docker volume rm claude-dev-config
cd ~/repos/my-project
claude-dev start   # ボリュームが再作成され、デフォルトの .zshrc がコピーされる
```

## DooD モードのポートアクセス（127.0.0.1:PORT）

既定（DooD）モードでは、`docker`/`docker compose` で起動したコンテナは**ホストの Docker デーモン**で動き、公開ポートは**ホスト側**に出る。Claude コンテナは別ネットワークのため、コンテナ内のテスト等が叩く `127.0.0.1:PORT` はそのままでは届かない。

これを解消するため、DooD モードでは Claude コンテナ内で `dood-portsync` が自動起動し、ホストに公開されたポートを `127.0.0.1:PORT`（コンテナ内ループバック）へ自動転送する。`docker compose up` で公開したポートは数秒以内に `127.0.0.1:PORT` で叩けるようになる（追加設定不要）。

- **無効化**: `claude-dev start` 時に環境変数 `CLAUDE_DEV_DOOD_PORTSYNC=0` を渡す（または `-e` で設定）。
- **転送しないポート**: コンテナ内部サービス（noVNC `6080` / VNC `5999` / Chrome `9222`）は既定で転送対象外（`CLAUDE_DEV_DOOD_PORTSYNC_EXCLUDE` で変更可）。これらを転送すると noVNC 等の起動と競合するため。
- **注意**: DooD ではサービスの実ポートはホストに公開される（ホストから見え、同じポートを使う別プロジェクトとはホスト上で衝突しうる）。ホスト非公開・ポート隔離が必要な場合は **VM モード（`claude-dev start --vm`）** を使う（[04_cli-reference.md](04_cli-reference.md) / [08_vm-mode.md](08_vm-mode.md)）。

## Linux デスクトップの操作

Web アプリの確認は `chrome-devtools` MCP（Chrome 操作）が標準だが、それ以外の **Linux デスクトップ（GUI）全般**を Claude に操作させたい場合は、用途に応じて次の 2 方式を使う。いずれも VNC ありコンテナ（`claude-dev start`、デフォルト）が前提で、ユーザーは noVNC 画面で操作をリアルタイムに確認できる。

### A. コンテナ内デスクトップを直接操作する（追加導入不要）

VNC ありコンテナには X ディスプレイ `:99` 上で openbox が動いており、`xdotool`（入力）と `scrot`（画面取得）が同梱されている。Claude はシェルからこれらを実行するだけで、`:99` 上の**任意の X アプリ**を操作できる。

```bash
# 画面取得（Claude は出力ファイルを Read で確認する）
DISPLAY=:99 scrot /tmp/shot.png

# マウス移動＋クリック
DISPLAY=:99 xdotool mousemove 400 300 click 1

# キーボード入力・キーコンビネーション
DISPLAY=:99 xdotool type "hello"
DISPLAY=:99 xdotool key ctrl+s

# ウィンドウ操作（例: アクティブウィンドウを最大化）
DISPLAY=:99 xdotool getactivewindow windowsize 100% 100%
```

「アプリ起動 → 操作 → `scrot` で確認」のループをそのまま回せる。追加の MCP やパッケージは不要。コンテナ内の openbox 上で動く GUI アプリ（エディタ・端末・各種ツール）が対象。

### C. KVM VM のデスクトップを computer-use MCP で操作する

別 OS・フルデスクトップ環境・より強い隔離が必要な場合は、KVM/QEMU でデスクトップ付き VM を起動し、その画面を `:99` に表示して computer-use MCP で操作する（KVM の前提・セキュリティ上の含意は [docs/03_security.md](03_security.md) を参照）。

**1) デスクトップ VM を `:99` に表示して起動する**

QEMU の表示先をコンテナの X ディスプレイ `:99` にすると、ゲストの画面が openbox 上のウィンドウに出る（ユーザーは noVNC で確認できる）。

```bash
# 例: デスクトップ付き Linux のディスクイメージを GTK 表示で起動
DISPLAY=:99 qemu-system-x86_64 \
  -enable-kvm -m 4096 -smp 2 \
  -drive file=guest.qcow2,if=virtio \
  -display gtk &
```

`-enable-kvm` を効かせるには、コンテナを **`claude-dev start --kvm`** で起動して `/dev/kvm` を渡しておく必要がある（既定では渡らない）。ホストに `/dev/kvm` が無い／`--kvm` を付けていない場合は `-enable-kvm` を外す（＝低速なソフトウェアエミュレーション）。`--kvm` で `/dev/net/tun` も渡るため tap ネットワークも利用可能。

**2) computer-use MCP を有効化する**

VNC イメージには入力操作用の MCP サーバー **`rmcp-xdotool`** が焼き込まれており、entrypoint が `/workspace/.mcp.json` に `computer-use` エントリを**定義**する（DISPLAY=`:99`）。ただし**既定では有効化されない**（デスクトップ全体を操作できる強い権限のため、必要なときだけ有効化する）。利用するには次のいずれか:

- Claude Code の `/mcp` で `computer-use` を有効化する
- `/workspace/.claude/.claude.json` の `projects["/workspace"].enabledMcpjsonServers` に `"computer-use"` を追加する

**3) 操作する**

有効化後、computer-use の MCP ツール（`move_mouse` / `click` / `click_at` / `type_text` / `key_press` / `scroll` / `double_click` 等）で `:99` を操作する。QEMU ウィンドウにフォーカスがある状態で入力すればゲストに渡る。**画面の視認は `scrot`（A と同じ）で取得する**（`rmcp-xdotool` は入力専用のため）。

> 画面取得まで MCP に統合したい場合は、スクリーンショット機能を持つ代替サーバー（例: PyPI の `computer-control-mcp` 等）を `.mcp.json` に追加してもよい。その場合は対象サーバーの依存（PyAutoGUI 等）をコンテナに導入する。

**注意点**
- `rmcp-xdotool` は `:99` 全体を操作するため、A と同じく X セッション全体が対象。VM 操作時は QEMU ウィンドウを最大化・フォーカスしておく。
- VNC イメージの再ビルド（`make build-claude-vnc`）で `rmcp-xdotool` が焼き込まれる。ビルドに失敗した場合は computer-use は登録されない（A の `xdotool`/`scrot` は引き続き利用可能）。

### 使い分け

| やりたいこと | 方式 |
|-------------|------|
| Web アプリの確認 | `chrome-devtools` MCP（標準） |
| コンテナ内の任意 GUI アプリ操作 | **A**: `xdotool` + `scrot`（追加導入不要） |
| 別 OS / フルデスクトップ / 強い隔離 | **C**: KVM VM + computer-use MCP（`rmcp-xdotool`）+ `scrot` |

## Claude コンテナに追加パッケージをインストールする

### 一時的（コンテナ再起動で消える）

コンテナ内で直接インストール:

```bash
# tmux セッション内で
sudo apt-get update && sudo apt-get install -y <package>
```

### 恒久的（Dockerfile を編集）

`.devcontainer/Dockerfile.claude` の `base` ステージの apt-get 行に追加（VNC あり/なし両方に反映される）:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 既存のパッケージ...
    # 追加パッケージ
    your-package \
    && rm -rf /var/lib/apt/lists/*
```

再ビルド:

```bash
make build-claude     # Claude ベースイメージのみ
make build-claude-vnc # Claude VNC イメージ（ベースに続けてビルド）
make build            # 全イメージ
```

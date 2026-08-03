---
id: cli-container
version: 1.0.0
updated: 2026-08-03
source:
  - docs/02-design/contracts/cli-container.md
kind: other
impl: claude-dev::main#start
summary: ホスト CLI がコンテナへ渡す環境変数・マウント・起動オプションの取り決め(実装側)
keywords: [契約, CTR, 実装]
verified:
  at: 2026-08-03
  version: 1.0.0
  against:
    - doc: docs/02-design/contracts/cli-container.md
      version: 1.0.0
---

# CTR-cli-container ホスト CLI → コンテナ/entrypoint(実装)

- 実装: `claude-dev::main#start` / `claude-dev-mac::main#start`(発行側)、
  `scripts/entrypoint-claude.sh::main`(受け側)
- 当事者: MOD-cli-start → MOD-entrypoint
- 対応する設計: `docs/02-design/contracts/cli-container.md`

## 実装上の事実

| 項目 | 実際の値 | 定義箇所 |
|---|---|---|
| 起動コマンド | `docker run -d --cap-add NET_ADMIN --cap-add NET_RAW --restart unless-stopped` | `claude-dev:901`〜`907` |
| `--security-opt` | **付けていない**(Docker 既定の seccomp と `docker-default` AppArmor が有効なまま) | `claude-dev:901`〜(不在であることが実装) |
| `DOCKER_HOST` | `tcp://claude-dev-docker-proxy:2375`。ホストに Docker ソケットが検出できたときだけ付与する | `claude-dev` の `DOCKER_OPTS` 組み立て |
| `COMPOSE_PROJECT_NAME` | コンテナ名を compose 互換へ正規化した値を `-e` で付与 | `claude-dev:821` |
| `CLAUDE_DEV_VNC` | `1` のときブラウザ確認資産を起動する | `scripts/entrypoint-claude.sh:556`, `613`, `678` |
| `CLAUDE_DEV_VM` | `1` のときゲスト VM を起動し `DOCKER_HOST` を上書きする | `scripts/entrypoint-claude.sh:476` |
| `CLAUDE_DEV_DOOD_PORTSYNC` | `0` 以外(既定 `1`)かつ VM モードでないときポート同期を起動する | `scripts/entrypoint-claude.sh:509`〜`510` |
| `CLAUDE_DEV_SSH_BRIDGE_PORT` | macOS のみ。socat の TCP ブリッジのポート | `claude-dev-mac::main#start` |
| `NODE_OPTIONS` | `--max-old-space-size=4096` | `claude-dev` の `docker run` 引数 |
| `container` | `docker`。**起動時ではなくイメージの `ENV` で付与** | `.devcontainer/Dockerfile.claude`(base ステージ) |
| マウント | カレントディレクトリ → `/workspace`(読み書き)、共有ボリューム3本、`~/.gitconfig` と `~/.config/gh` は読み取り専用、tmux 設定と `CLAUDE.md` は読み取り専用 | `claude-dev` の `docker run` 引数 |
| SSH | Linux は専用 agent のソケットを `/tmp/ssh-agent.sock` へ読み取り専用で転送。macOS は socat の TCP ブリッジ。`~/.ssh/config` は `IdentityFile` / `IdentitiesOnly` / `IdentityAgent` を除去した一時コピーを読み取り専用でマウント | `claude-dev` の `SSH_OPTS` 組み立て |
| 認証の受け渡し | 一時コンテナで共有ボリューム(読み取り専用)から `${PROJECT_DIR}/.claude/` と `${PROJECT_DIR}/.codex/auth.json` へコピーし、ホストの UID/GID へ `chown` する | `claude-dev::main#start` 手順8 |
| 認証の書き戻し | コンテナ内で 30 秒間隔のバックグラウンドループ | `scripts/entrypoint-claude.sh:449` |
| ファイアウォールの起動 | `/usr/local/bin/init-firewall.sh 2>/dev/null \|\| true` | `scripts/entrypoint-claude.sh:471` |

## 設計との差異

差異なし。

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 空きポートの選定から `docker run` までが原子的でない | 同時起動でポート競合が起きうる(最大20回の再試行で吸収する) | なし |
| `.claude/host-hooks.json` の名前が実態(hooks と env)と乖離している | 読み手が誤解しうる。歴史的経緯で据え置き | なし |
| コンテナ名がディレクトリ名だけで決まる | 別パスの同名ディレクトリが同一セッション扱いになる | なし |

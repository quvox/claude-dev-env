# 実装仕様: scripts/ ディレクトリ概要 と 小スクリプト

> **この文書の役割**: `scripts/` ディレクトリ全体の役割を示す概要であり、かつ小規模スクリプト（Claude Code hook 2 種と tmux 設定）の実装仕様を記述する。大規模なスクリプトは別文書に分離する。

## scripts/ の構成と対応文書

```
scripts/
├── entrypoint-claude.sh     コンテナ起動時の初期化（→ 31_entrypoint.md）
├── init-firewall-claude.sh  ブラックリスト方式 FW（→ 32_firewall.md）
├── save_prompt.sh           Claude Code hook: 直近プロンプト保存（本書）
├── sendslackmsg.sh          Claude Code hook: Slack 通知（本書）
└── tmux.conf                claude-dev start が RO マウントする tmux 設定（本書）
```

`save_prompt.sh` / `sendslackmsg.sh` はイメージビルド時に `/usr/local/bin/` へ焼き込まれる（→ [40_devcontainer.md](40_devcontainer.md)）。`entrypoint-claude.sh` / `init-firewall-claude.sh` も同様に焼き込まれ、それぞれ `/usr/local/bin/entrypoint.sh` / `/usr/local/bin/init-firewall.sh` として配置される。

---

## save_prompt.sh

### 要件
Slack 通知（`sendslackmsg.sh`）が「直前にユーザーが入力したプロンプト」を本文に含められるよう、Claude Code の hook 入力からプロンプト先頭を一時ファイルに保存する。

### 仕様
- 標準入力から hook の JSON を受け取る。
- `python3` で `session_id` と `prompt`（先頭 30 文字）を抽出。失敗時は `session_id=unknown` / 空文字へフォールバック。
- 抽出したプロンプトを `/tmp/claude_prompt_<session_id>.txt` に上書き保存する。

---

## sendslackmsg.sh

### 要件
Claude Code の特定イベント（hook）発生時に、セッションのプロンプト文脈つきで Slack へ通知したい。

### 仕様
- 環境変数 `SLACK_BOT_TOKEN`（必須）と `SLACK_CHANNEL`（任意、既定 `U5SJG0XEK`）を参照。`SLACK_BOT_TOKEN` 未設定なら何もせず `exit 0`。
- 第 1 引数 `$1` を通知メッセージ本文の接頭辞 `MSG` とする。
- 標準入力の JSON から `jq` で `session_id` を抽出し、`save_prompt.sh` が保存した `/tmp/claude_prompt_<session_id>.txt` を読む（無ければ `(no prompt)`）。
- `jq -n` で `{channel, text: "<MSG> 「<PROMPT>...」"}` を組み立て、`https://slack.com/api/chat.postMessage` へ `Authorization: Bearer <TOKEN>` で POST。失敗は握りつぶす（`|| true`）。

### 連携
`SLACK_BOT_TOKEN` / `SLACK_CHANNEL` はホストの `~/.claude/settings.json` の `env` に置けば、`claude-dev start` → `host-hooks.json` 抽出 → entrypoint のマージ（[31_entrypoint.md](31_entrypoint.md)）でコンテナの `settings.json` に反映される。hook 自体の登録（どのイベントで何を実行するか）も同経路の `hooks` 設定で行う。

---

## scripts/tmux.conf

### 要件
コンテナ内の開発作業を tmux でセッション永続化しつつ、通常ターミナルとの操作差を最小化する。

### 仕様（主要設定）
- **プレフィックスキー**: `C-_`（`Ctrl-_`）。`C-b` は解除。
- シェル: `/bin/zsh`。`history-limit 50000`。`default-terminal screen-256color` + truecolor override。
- `mouse on`、`escape-time 0`。
- ウィンドウ: `base-index 1` / `pane-base-index 1` / `renumber-windows on`。
- 最小限のステータスバー（セッション名・時刻）。
- `detach-on-destroy off`（セッション破棄時にデタッチし、クライアントを落とさない）。

### 配置
`claude-dev start` がこのファイルを `~/.tmux.conf` として読み取り専用マウントする（[10_cli.md](10_cli.md)）。ビルド時にイメージへ焼き込まれる `.devcontainer/tmux.conf`（→ `/etc/tmux.conf`、[40_devcontainer.md](40_devcontainer.md)）とは別物で、用途も異なる（こちらが実際の tmux セッション設定）。

---
summary: scripts/ ディレクトリの構成概要と、Claude Code hookスクリプト（save_prompt.sh / sendslackmsg.sh）および tmux.conf の実装仕様を記述する。
keywords: [ scripts, hook, Slack通知, tmux, save_prompt, sendslackmsg, 設定 ]
---

# 実装仕様: scripts/ ディレクトリ概要 と 小スクリプト

> **この文書の役割**: `scripts/` ディレクトリ全体の役割を示す概要であり、かつ小規模スクリプト（Claude Code hook 2 種と tmux 設定）の実装仕様を記述する。大規模なスクリプトは別文書に分離する。

## scripts/ の構成と対応文書

```
scripts/
├── entrypoint-claude.sh     コンテナ起動時の初期化（→ 31_entrypoint.md）
├── init-firewall-claude.sh  ブラックリスト方式 FW（→ 32_firewall.md）
├── save_prompt.sh           Claude Code hook: 直近プロンプト保存（本書）
├── sendslackmsg.sh          Claude Code hook: Slack 通知（本書）
├── tmux.conf                claude-dev start が RO マウントする tmux 設定（本書。status-right の @vm_health は 80）
├── vm-up.sh / vm / vm-portsync.sh / vm-healthd.sh / VM_DEV.md.tmpl   VM モード（→ 80_vm-mode.md）
├── dood-portsync.sh         DooD モードのホスト公開ポート→127.0.0.1 転送（本書）
└── ...
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
- 最小限のステータスバー（セッション名・時刻）。**status-right には VM 資源逼迫警告 `@vm_health` を先頭に条件表示**（`#{?#{@vm_health},#[fg=red#,bold]#{@vm_health} ,}` 相当。`#[fg=…#,bold]` の `#,` は `#{?…}` 内でカンマを分岐区切りと誤解させないためのエスケープ）。この tmux ユーザ変数は VM モードの `vm-healthd`（[80_vm-mode.md](80_vm-mode.md) §7.2）が WARN 時に set・OK 復帰時に unset する。非 VM モードでは常に未設定＝非表示。
- `detach-on-destroy off`（セッション破棄時にデタッチし、クライアントを落とさない）。

### 配置
`claude-dev start` がこのファイルを `~/.tmux.conf` として読み取り専用マウントする（[10_cli.md](10_cli.md)）。ビルド時にイメージへ焼き込まれる `.devcontainer/tmux.conf`（→ `/etc/tmux.conf`、[40_devcontainer.md](40_devcontainer.md)）とは別物で、用途も異なる（こちらが実際の tmux セッション設定）。

## scripts/dood-portsync.sh

### 要件
DooD モードではコンテナはホストの Docker デーモンで起動し、公開ポートはホストの `0.0.0.0:PORT` に出る。claude コンテナは別 network namespace のため、コンテナ内テスト等が叩く `127.0.0.1:PORT` はホスト公開ポートに届かない。これを解消し、`127.0.0.1:PORT` をホスト公開ポートへ到達させる（VM モードの `vm-portsync` に相当。設計 [02_architecture.md](../02_architecture.md#dood-のポートアクセスdood-portsync)）。

### 仕様（成果物）
- **検出**: `docker ps`（`DOCKER_HOST`＝socket proxy 経由）の `Ports` から `0.0.0.0:PORT` の PORT を抽出。
- **転送**: 各 PORT について `socat TCP-LISTEN:PORT,fork,reuseaddr,bind=127.0.0.1 → TCP:<デフォルトGW>:PORT` を `setsid` で常駐起動。デフォルトGW（`ip route` の default）＝docker bridge のゲートウェイ＝ホストで、ホスト公開ポートに到達できる。**リスナーは `127.0.0.1` 限定**（コンテナ内ループバックのみ・ホストへは新規公開しない）。
- **重複回避／自己除外**: 転送済みポートを `/tmp/dood-portsync/forwarded` に記録。既に `127.0.0.1:PORT` がローカル待受中（noVNC 等・自分の転送含む。`/dev/tcp` で判定）ならスキップ。
- **起動形態**: `--loop` で常駐（既定 5 秒間隔・`CLAUDE_DEV_DOOD_PORTSYNC_INTERVAL`）。引数なしは一度だけ同期。多重起動は entrypoint 側で `pgrep` により防止。
- **自動起動**: entrypoint が **非 VM かつ `DOCKER_HOST` が socket proxy を指す**場合に `--loop` を常駐起動（[31_entrypoint.md](31_entrypoint.md)）。`CLAUDE_DEV_DOOD_PORTSYNC=0` で無効化。
- **前提**: `socat`（イメージに導入済み）、デフォルトGW が引けること。いずれか欠けると FATAL で終了。
- **DooD の性質上の注意**: サービスの実ポートはホスト `0.0.0.0:PORT` に既に公開されている（ホスト可視・別プロジェクトと同一ポートは衝突しうる）。ホスト非公開・ポート隔離が必要なら VM モードを使う。

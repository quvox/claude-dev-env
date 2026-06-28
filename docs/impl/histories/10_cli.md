# 変更履歴: 10_cli.md

> 対応文書: `docs/impl/10_cli.md`

## 2026-06-08
- 新規作成。`claude-dev` CLI の初期化・定数・ヘルパー関数・全サブコマンド（setup/login/logout/start/code/attach/stop/forward/unforward/ports/list/upgrade/firewall/reset/help）の実装仕様を記述。
- `start` に `--kvm` フラグを追加。KVM/QEMU デバイス（`/dev/kvm` 等）の受け渡しを「既定で常に（デバイスがあれば）」から「`--kvm` 指定時のみ」に変更した仕様を反映。通常は Chrome 操作のみで十分なため既定では渡さず、VM を動かす時だけオプトインする。

## 2026-06-28
- AI オーケストレーター実装に伴い `orchestrate [<ゴール>] [--workers-window]` サブコマンドを追記。`code` と同系統で、稼働中コンテナの新規 tmux ウィンドウ（`-c /workspace`）に `claude-orchestrator` を起動し attach する。引数処理（`--workers-window` フラグ除去後の位置引数をゴールとして扱う）を含む。詳細仕様の正本は 60_orchestrator.md。

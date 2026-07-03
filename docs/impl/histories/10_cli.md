# 変更履歴: 10_cli.md

> 対応文書: `docs/impl/10_cli.md`

## 2026-06-29
- `orchestrate` サブコマンドから `--workers-window`（Config B）を削除。worker のライブ出力はダッシュボードの `[d]` に一本化したため（旧フラグは未実装のままだった）。

## 2026-06-28
- `orchestrate` サブコマンドに `--fresh` フラグを追加。`--workers-window` と同様にフラグとして除外して `<ゴール>` を判定し、`claude-orchestrator` へそのまま受け渡す（前回の実行状態を破棄して壁打ちから新規開始する）。

## 2026-06-08
- 新規作成。`claude-dev` CLI の初期化・定数・ヘルパー関数・全サブコマンド（setup/login/logout/start/code/attach/stop/forward/unforward/ports/list/upgrade/firewall/reset/help）の実装仕様を記述。
- `start` に `--kvm` フラグを追加。KVM/QEMU デバイス（`/dev/kvm` 等）の受け渡しを「既定で常に（デバイスがあれば）」から「`--kvm` 指定時のみ」に変更した仕様を反映。通常は Chrome 操作のみで十分なため既定では渡さず、VM を動かす時だけオプトインする。

## 2026-06-28
- AI オーケストレーター実装に伴い `orchestrate [<ゴール>] [--workers-window]` サブコマンドを追記。`code` と同系統で、稼働中コンテナの新規 tmux ウィンドウ（`-c /workspace`）に `claude-orchestrator` を起動し attach する。引数処理（`--workers-window` フラグ除去後の位置引数をゴールとして扱う）を含む。詳細仕様の正本は 60_orchestrator.md。

## 2026-06-29
- `orchestrate` の説明に、オーケストレーター本体バイナリが自己検証用に受け付けるフラグ（`--instructions`・`--start-executing`）への注記を追加。`claude-dev orchestrate` 自体はこれらを公開しない旨を明記。

## 2026-07-04（proxy へ CLAUDE_DEV_ALLOW_WORKSPACE_BINDS を付与）
- ensure_docker_proxy_container の docker run に `-e CLAUDE_DEV_ALLOW_WORKSPACE_BINDS=${CLAUDE_DEV_ALLOW_WORKSPACE_BINDS:-1}` を追加（/workspace 配下 bind 許可。既定有効。正本 50/03）。共有・常駐のため設定変更は proxy 作り直しが必要な旨を明記。

## 2026-07-04（整合性確認による調整）
- 実装仕様内の徹底整合確認を受け、`--vm` 説明の `vm` ヘルパー列挙に欠落していた `portsync` を追加（status に health 表示含む旨も明記）。80_vm-mode.md の列挙と一致させた。

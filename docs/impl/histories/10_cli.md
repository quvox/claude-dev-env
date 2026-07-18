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

## 2026-07-06（login の settings.json 生成のクォート不具合修正）
- `login` の一時コンテナ内 `settings.json` 生成を `su -c "..."` 内から root 部（`su` 前）へ移動し、`\"` エスケープの二重引用符で生成して `chown` する仕様に変更。
- 旧実装（su 内の `echo '{\"...\"}'`）は、`docker run ... -c '...'` のホスト側シングルクォートを echo のシングルクォートが閉じてしまい、露出した JSON がホストシェルのエスケープ消費とブレース展開を受けて引数が 2 つに分裂、生成ファイルが `permissions:{defaultMode:bypassPermissions}`（不正 JSON）になる不具合があった（macOS 実機の login コンテナで確認。Linux 版も同一コード）。
- login 節に「クォート制約」（-c スクリプト内でシングルクォート使用禁止）の注記を追加。claude-dev / claude-dev-mac の両方に同一修正。

## 2026-07-18（Chrome プロファイルをコンテナごとに分離）
- 複数の VNC コンテナが固定名の共有ボリューム `claude-dev-chrome-data` を同一 `~/.chrome-profile` にマウントしていたため、同時起動時に同一プロファイルへ多重書き込みし、SingletonLock 奪取・プロファイル破損・Chrome 異常終了（「正しく終了しませんでした」）が発生していた。noVNC のポート開放・websockify・Xvnc 自体は正常で、体感上の「接続できない/画面が壊れる」の原因はこのプロファイル競合だった。
- 定数 `VOL_CHROME=claude-dev-chrome-data` を廃止し、`VOL_CHROME_PREFIX=claude-dev-chrome` を導入。`start` の `NOVNC_PORT_OPT` で **コンテナごとの `claude-dev-chrome-<name>`**（VM ボリューム `claude-dev-vm-<name>` と同方式）を `~/.chrome-profile` にマウントするよう変更。
- コンテナごとボリュームは `docker run` が自動作成するため、`ensure_infrastructure`・`setup` からの Chrome ボリューム事前作成を削除（共有は auth/history/config の 3 ボリュームに）。
- `reset` は共有 3 ボリューム削除に加え、`claude-dev-chrome-*`（全コンテナのプロファイル。旧 `-data` 含む）をワイルドカードで削除するよう変更。
- claude-dev / claude-dev-mac の両方に同一修正。既存の稼働中コンテナへ反映するには `claude-dev stop`（または該当コンテナ削除）後に再 `start` が必要。

## 2026-07-18（noVNC ポート選択レースの吸収：docker run リトライ）
- `find_available_novnc_port` の選定〜`docker run -p` バインドが非アトミックなため、複数の `start` をほぼ同時に実行すると双方が同じ空きポートを選び、片方の `docker run` が「port is already allocated」で失敗する競合があった（他プロセスのポート横取りでも同様）。
- `start` の `docker run -d` を while ループで包み、`2>&1 >/dev/null` で stderr を捕捉。失敗時は作成途中コンテナを `docker rm -f "$NAME"` で掃除し、エラーがポート競合（`port is already allocated` / `address already in use` / `bind for .* failed`）でかつ VNC 有効なら `find_available_novnc_port` で別ポートを取り直して再試行（最大 20 回、取り直しポートを表示）。ポート以外の失敗・上限到達時は stderr を表示して `exit 1`。
- claude-dev / claude-dev-mac の両方に同一修正（mac 版は KVM/VM オプションを持たない点のみ差分）。

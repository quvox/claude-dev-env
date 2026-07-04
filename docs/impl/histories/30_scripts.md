# 変更履歴: 30_scripts.md

> 対応文書: `docs/impl/30_scripts.md`

## 2026-06-08
- 新規作成。`scripts/` ディレクトリ概要と、小スクリプト（`save_prompt.sh` / `sendslackmsg.sh` / `tmux.conf`）の実装仕様を記述。

## 2026-07-04（tmux status-right に @vm_health）
- `tmux.conf` の status-right 先頭に `@vm_health` の条件表示を追加（`#{?#{@vm_health},#[fg=red#,bold]#{@vm_health} ,}`）。VM モードの vm-healthd（80 §7.2）が資源逼迫時に set・復帰時に unset する。非 VM モードでは未設定＝非表示。scripts/ ツリーに VM スクリプト群（vm-healthd.sh 含む）のポインタ行を追加。

## 2026-07-04（整合性確認による調整）
- 徹底整合確認を受け、status-right の tmux フォーマット例のカンマエスケープを実ファイル(scripts/tmux.conf)に合わせ `#[fg=…#,bold]` へ訂正し、`#,` エスケープの意図を注記。

## 2026-07-04（DooD ポート転送 dood-portsync 追加）
- scripts/dood-portsync.sh（新規）の実装仕様を追加。docker ps(proxy 経由)の 0.0.0.0:PORT を検出し socat TCP-LISTEN:PORT,bind=127.0.0.1→GW:PORT を常駐（--loop・既定5s）。ローカル待受中(noVNC 等)はスキップ、/tmp/dood-portsync/forwarded で重複回避。scripts/ ツリーにも追加。

## 2026-07-04（dood-portsync: 内部サービスポート除外の修正）
- 不具合修正: dood-portsync がホスト公開ポートを無差別に 127.0.0.1 へ転送していたため、別コンテナが 0.0.0.0:6080 を公開していると 127.0.0.1:6080 へ socat 転送し、しかも entrypoint で VNC 起動より前に走るため hisol-work 自身の noVNC(websockify, 6080) が bind できず起動失敗＝noVNC 不通になっていた（実機で確認）。
- EXCLUDE（既定 "6080 5999 9222"・CLAUDE_DEV_DOOD_PORTSYNC_EXCLUDE で上書き）を追加し、内部サービスポートを転送対象から除外。05_customization にも追記。実機 hisol-work をライブ修復（stale socat 除去→websockify 再起動→修正版ループ再起動）し localhost:6081→HTTP200・6080 が転送対象外になったことを確認。

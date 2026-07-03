# 変更履歴: 30_scripts.md

> 対応文書: `docs/impl/30_scripts.md`

## 2026-06-08
- 新規作成。`scripts/` ディレクトリ概要と、小スクリプト（`save_prompt.sh` / `sendslackmsg.sh` / `tmux.conf`）の実装仕様を記述。

## 2026-07-04（tmux status-right に @vm_health）
- `tmux.conf` の status-right 先頭に `@vm_health` の条件表示を追加（`#{?#{@vm_health},#[fg=red#,bold]#{@vm_health} ,}`）。VM モードの vm-healthd（80 §7.2）が資源逼迫時に set・復帰時に unset する。非 VM モードでは未設定＝非表示。scripts/ ツリーに VM スクリプト群（vm-healthd.sh 含む）のポインタ行を追加。

## 2026-07-04（整合性確認による調整）
- 徹底整合確認を受け、status-right の tmux フォーマット例のカンマエスケープを実ファイル(scripts/tmux.conf)に合わせ `#[fg=…#,bold]` へ訂正し、`#,` エスケープの意図を注記。

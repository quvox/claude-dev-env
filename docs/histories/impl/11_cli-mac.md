# 変更履歴: impl/11_cli-mac.md

> 対応文書: `docs/impl/11_cli-mac.md`（対応コード: `claude-dev-mac`）

## 2026-07-06
- SSH 鍵を**ディレクトリ（プロジェクト）単位で切り替え**られるようにした（Linux 版 `claude-dev` と同方針。macOS は転送手段が socat TCP ブリッジである点のみ差分）。
  - 定数を per-project 化: `DEV_AGENT_DIR`（`~/.claude-dev/agents`）と `PROJECT_CONFIG_NAME`（`.claude-dev.yaml`）を追加。旧・単一 agent/ブリッジのパスは `LEGACY_*` として reset 掃除用に残置。パス導出は `dev_agent_path <name> <kind>`。
  - 鍵解決を追加: `_parse_ssh_keys_yaml <file>`（共通パーサ）／`resolve_ssh_keys_for_start <project_dir>`（プロジェクト `.claude-dev.yaml` 優先 → グローバル選択、未選択なら対話選択）。`load_config_ssh_keys` は `_parse_ssh_keys_yaml` を使う形に整理。
  - `ensure_dedicated_agent <name>` / `ensure_ssh_bridge <name>` を**プロジェクト専用**（`<name>.sock`／`<name>.bridge.{pid,port}`）に変更。agent は指紋照合で既登録鍵をスキップ（パスフレーズ再入力回避）、`chmod 700` で置き場を保護。ブリッジはプロジェクトごとに別ポート。
  - `start` の SSH 部を `resolve_ssh_keys_for_start "$PROJECT_DIR"` → `ensure_dedicated_agent "$NAME"` → `ensure_ssh_bridge "$NAME"` に更新。
  - `stop` はそのプロジェクトのブリッジのみ停止する `stop_ssh_bridge <name>` に変更（旧 `stop_ssh_bridge_if_idle` は削除）。専用 agent は鍵保持のため残す。
  - `ssh-keys reset` を、グローバル選択の消去＋`~/.claude-dev/agents/` 配下の全プロジェクト agent/ブリッジ停止・削除＋旧 `LEGACY_*` 掃除に拡張。プロジェクト直下の `.claude-dev.yaml` は削除しない。

## 2026-07-06（追補: ローカル設定のみ・フォールバック廃止）
- SSH 鍵の解決を**プロジェクト直下 `.claude-dev.yaml` の `ssh_keys` のみ**に簡素化（Linux 版と同方針）。グローバル `~/.config/claude-dev.yaml` へのフォールバック・`start` 時の対話選択・自動生成を廃止し、定数 `USER_CONFIG`・関数 `config_has_ssh_selection`・`load_config_ssh_keys` を削除。
  - `resolve_ssh_keys_for_start <project_dir>` は当該プロジェクトの `.claude-dev.yaml` だけを読む。
  - `write_config_ssh_keys`（グローバルへ書き込み）を `write_project_ssh_keys <file> <keys...>` に置換。`select_ssh_keys_interactive` は**カレントプロジェクトの `.claude-dev.yaml`** に保存するよう変更。
  - `ssh-keys reset` を**カレントプロジェクト単位**に変更（そのプロジェクトの `.claude-dev.yaml` の `ssh_keys` 除去＝ssh_keys だけなら削除／他記述は残す、および `container_name` の専用 agent/ブリッジ停止・削除。旧 `LEGACY_*` 掃除は継続）。

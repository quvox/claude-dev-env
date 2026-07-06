# 変更履歴: impl/10_cli.md

> 対応文書: `docs/impl/10_cli.md`（対応コード: `claude-dev`）

## 2026-07-06
- SSH 鍵を**ディレクトリ（プロジェクト）単位で切り替え**られるようにした。
  - 定数 `DEV_DIR` / `DEV_AGENT_DIR`（`~/.claude-dev` / `~/.claude-dev/agents`）と `PROJECT_CONFIG_NAME`（`.claude-dev.yaml`）を追加。
  - `load_ssh_keys_from_config <project_dir>` を鍵リストの**解決関数**に変更。優先順位は (1) `<project_dir>/.claude-dev.yaml`（`ssh_keys:` を含む場合）→ (2) グローバル `~/.config/claude-dev.yaml`（無ければ `~/.ssh/id_*` から自動生成）。採用元を `SSH_CONFIG_SOURCE` に記録。YAML パースは共通ヘルパー `_parse_ssh_keys_yaml` に切り出し。
  - `ensure_ssh_agent <project_dir> <name>` を、ホストの環境 agent を使う方式から、**プロジェクト専用 ssh-agent（`~/.claude-dev/agents/<name>.sock`）を起動/再利用して解決した鍵だけを登録する方式**に変更（ディレクトリごとの鍵の見え方を隔離）。登録前に `ssh-add -l` の指紋と各鍵の指紋（`ssh-keygen -lf`、パスフレーズ不要）を突き合わせ、**既登録の鍵はスキップ**してパスフレーズ再入力を回避。鍵 0 件時は `SSH_AUTH_SOCK` を空にして SSH 転送しない。
  - `start` の呼び出しを `ensure_ssh_agent "$PROJECT_DIR" "$NAME"` に更新。`SSH_OPTS` は専用 agent のソケットを `/tmp/ssh-agent.sock` へ転送する（従来どおり秘密鍵ファイルはマウントしない）。

## 2026-07-06（追補: ローカル設定のみ・フォールバック廃止）
- SSH 鍵の解決を**プロジェクト直下 `<project_dir>/.claude-dev.yaml` の `ssh_keys` のみ**に簡素化。グローバル `~/.config/claude-dev.yaml` へのフォールバックと雛形自動生成を廃止し、定数 `USER_CONFIG` を削除。
  - `load_ssh_keys_from_config <project_dir>` は当該プロジェクトの `.claude-dev.yaml` だけを `_parse_ssh_keys_yaml` で読む（`SSH_CONFIG_SOURCE` は常にそのパス）。
  - `ensure_ssh_agent` の鍵0件メッセージを、`.claude-dev.yaml` に `ssh_keys:` を記述するよう促す案内に変更。

## 2026-07-06（追補: gh 認証の共有）
- `start` に `GH_CONFIG_OPT` を追加。ホストに `~/.config/gh` があれば `${CHOME}/.config/gh` へ RO マウントし、コンテナ内でも GitHub CLI `gh` が認証済み（`hosts.yml` の oauth トークン）で使えるようにした（`gh` 本体はイメージに同梱＝[40_devcontainer.md](../../impl/40_devcontainer.md)）。

## 2026-07-06（追補: ssh-keys サブコマンドを Linux 版にも追加）
- macOS 版と同じ `ssh-keys` サブコマンドを Linux `claude-dev` に追加（両 OS 共通仕様に）。
  - ヘルパー `discover_ssh_keys` / `write_project_ssh_keys` / `select_ssh_keys_interactive` を移植（対話選択はカレントプロジェクトの `.claude-dev.yaml` に保存）。
  - `ssh-keys`（引数なし/`select`）＝対話選択、`ssh-keys reset`＝カレントプロジェクトの `.claude-dev.yaml` の ssh_keys 除去（ssh_keys だけなら削除／他記述は残す）＋そのプロジェクトの専用 agent（`${DEV_AGENT_DIR}/<name>.{sock,pid}`）を停止・削除。
  - `help` 出力に ssh-keys の項を追加。macOS 版との差分は reset がブリッジ socat も止める点のみ（Linux にブリッジは無い）。

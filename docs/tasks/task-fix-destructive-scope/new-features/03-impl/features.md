---
target: docs/03-impl/features.md
change: replace
sections:
  - "## 機能一覧"
  - "## 統合した機能"
  - "## 昇格させた共通基盤機能"
deletes: []
reason: D0-env-08 項6 の排他を6コマンドで共有するため、共有基盤に MODULE-cli-common-lock を1機能追加する(PLAN-cli-common-lock / FR-env-01 受入基準 16・17)
reflected: 2026-08-04
---

## 機能一覧

<!-- 変更指示は差分の表で書く(.claude/directions/change-set.md 例外1)。
     ここに挙げた行だけが追加・変更の対象で、既存の他の行は変更しない。 -->

| 機能ID | 種別 | 入口 | 所属 | 概要 |
|---|---|---|---|---|
| MODULE-cli-common-lock | function-call | claude-dev::acquire_lock, claude-dev::release_lock, claude-dev-mac::acquire_lock, claude-dev-mac::release_lock | MOD-cli-common | 共有資源を触る6コマンドを直列化するロックを取得・解放し、残骸を引き継ぐ |

## 統合した機能

<!-- 複数の入口を1行にまとめた場合だけ、その理由をここに残す。 -->

| 機能ID | まとめた入口 | まとめた理由 |
|---|---|---|
| `MODULE-cli-*`(20件すべて) | `claude-dev::main#<subcmd>` と `claude-dev-mac::main#<subcmd>` | 同一のコマンド面を Linux/macOS で別実装しているだけで、外から見える振る舞いは同じ。OS 別に割ると同一仕様のモジュールが18本増えて依存表が読めなくなる(決定シート 委任(e))。**旧 `cli-mac` モジュールはこれにより解体される** |
| `MODULE-cli-common-*`(12件すべて) | `claude-dev::<fn>` と `claude-dev-mac::<fn>` | 同上。同名対の共通基盤関数を1機能として扱い、OS 差分は本文の「異常系・差分」に書く |
| `MODULE-portsync-dood` / `MODULE-vm-mode-portsync` / `MODULE-vm-mode-healthd` | `main#--loop` と `main` | 同じスクリプトの一発実行と常駐実行。抽出器は `--loop` だけをエントリポイントとするが、一発実行も公開インターフェースなので同一機能に含める |
| `MODULE-orchestrator-*`(main を除く) | 各ファイルの公開 API 群 | orchestrator は入口が `main` 1つしかない単一バイナリで、そのままでは219シンボルが1機能になる。責務(ファイル境界)ごとに公開 API を昇格させて機能に割る |
| MODULE-sample-project-mathkit | mathkit の5関数 | 自己検証の実装対象となるライブラリ。関数単位に割っても仕様として意味を持たない |

## 昇格させた共通基盤機能

<!-- ファンイン(到達できる機能の数)が2以上の関数は境界の実体である。 -->

| 機能ID / シンボル | ファンイン | 昇格したか | 判断の理由 |
|---|---|---|---|
| `claude-dev::container_name` / `claude-dev-mac::container_name` | 10 | 昇格 | コンテナ命名規則の実体。全サブコマンドがこの規則に依存する |
| `claude-dev::project_name` / `claude-dev-mac::project_name` | 10 | 畳み込む | 呼び出し元は `container_name` だけ。命名規則の内側の一段で、単独では意味を持たない |
| `claude-dev::is_running` / `claude-dev-mac::is_running` | 9 | 昇格 | 「セッションが動いているか」の判定はこのシステムの状態モデルそのもの |
| `claude-dev::image_exists` / `claude-dev-mac::image_exists` | 7 | 昇格 | `require_setup` を昇格させても `ensure_docker_proxy_container` から到達するのでファンイン2が残る |
| `claude-dev::require_setup` / `claude-dev-mac::require_setup` | 7 | 昇格 | セットアップ未実施時の停止条件。7機能に共通の事前条件ゲート |
| `claude-dev::acquire_lock` / `release_lock`(および macOS 版の同名対) | 6 | 昇格 | 共有資源(共有ボリューム・docker-proxy)を触る6機能を直列化する排他の実体。`start` / `stop` / `logout` / `reset` / `login` / `login-codex` が同じキー体系(`CTR-cli-container` の「排他(ロックキー)」)に依存する |
| `claude-dev::container_exists` / `claude-dev-mac::container_exists` | 5 | 昇格 | 停止中コンテナを含む存在判定。`is_running` と別概念で、stop/logout の分岐条件 |
| `claude-dev::resolve_container_user` / `claude-dev-mac::resolve_container_user` | 4 | 昇格 | docker exec の実行ユーザ決定。権限に関わる判断を含む |
| `claude-dev::ensure_infrastructure` / `claude-dev-mac::ensure_infrastructure` | 3 | 昇格 | docker network とボリュームを作る副作用を持つ |
| `claude-dev::get_novnc_url` / `claude-dev-mac::get_novnc_url` | 3 | 昇格 | 利用者に提示する接続 URL の組み立て規則。3機能が同じ URL を出す |
| `claude-dev-mac::dev_agent_path` | 3 | 昇格 | macOS 専用の ssh-agent ソケット配置規則。start/stop/ssh-keys reset が同じ場所を前提にする |
| `claude-dev::select_ssh_keys_interactive` / `claude-dev-mac::select_ssh_keys_interactive` | 2 | 昇格 | 対話 UI を持ち、`start` と `ssh-keys select` の双方から呼ばれる |
| `claude-dev::write_project_ssh_keys` / `claude-dev-mac::write_project_ssh_keys` | 2 | 昇格 | `.claude-dev.yaml` への書き込み(副作用)。`ensure_project_config` と選択 UI の双方から呼ばれる |
| `claude-dev::discover_ssh_keys` / `claude-dev-mac::discover_ssh_keys` | 2 | 畳み込む | `select_ssh_keys_interactive` を昇格させれば呼び出し元は1つになる |
| `orchestrator/state.go::Store.path` ほか state.go の公開 API 全件 | 7〜2 | 昇格 | 状態永続化層の表面。`MODULE-orchestrator-state` / `-state-intervention` / `-state-io` の3機能へ割り当てた |
| `orchestrator/session.go::SessionManager.*` / `tmuxRun` / `splitTarget` | 3〜2 | 昇格 | tmux セッション操作の表面。`MODULE-orchestrator-session` へ含めた |
| `orchestrator/mode.go::Mode.instructionPath` ほか mode.go の内部 API | 2 | 昇格 | 指示テンプレートの解決規則。`MODULE-orchestrator-mode` へ含めた |
| `orchestrator/worker.go::extractFromClaudeEnvelope` / `resultFromStream` | 3 | 昇格 | Claude の応答封筒の解釈規則。review と controller が同じ規則に依存する |
| `orchestrator/worker.go::ExecGit.*` | (interface 経由) | 昇格 | `Git` インターフェース経由の動的束縛で抽出器から辺が見えない。git 操作の表面として `MODULE-orchestrator-worktree` に明示する |
| `orchestrator/dashboard.go::oneline` | 3 | 畳み込む | 文字列を1行に潰すだけの整形ユーティリティ。単独で仕様として意味を持たない(§4 の「薄いユーティリティ」) |

---
id: features
updated: 2026-08-02
summary: claude-dev 開発環境の機能一覧と入口。CLI サブコマンド・Makefile ターゲット・常駐スクリプト・Go バイナリの入口を列挙する
keywords: [機能表, 境界, claude-dev, Makefile, orchestrator, docker-proxy]
# version / verified は持たない(relations 層の代表として docs/03-impl/index.md が持つ)
---

# 機能表

<!-- ★ 境界の定義。仕様の正は .claude/directions/features.md
     ・1入口 = 1機能が既定。複数入口を1行にまとめてよいのは、人間が統合を決めたときだけ
     ・機能ID は relations/<機能ID>.md のファイル名と同一(1:1 は写像ではなく同一ID)
     ・入口は callgraphs/ の表記と1文字も違わないこと
     ・並びは 所属 → 機能ID の辞書順に固定する
     ・版・合格証は持たない(relations 層の代表として docs/03-impl/index.md が持つ) -->

## 機能一覧

| 機能ID | 種別 | 入口 | 所属 | 概要 |
|---|---|---|---|---|
| MODULE-cli-attach | tool | dispatch attach @ claude-dev::main, dispatch attach @ claude-dev-mac::main | MOD-cli-attach | 実行中コンテナの tmux セッションに接続する |
| MODULE-cli-code | tool | dispatch code @ claude-dev::main, dispatch code @ claude-dev-mac::main | MOD-cli-code | 新しい tmux ウィンドウで Claude Code を起動する |
| MODULE-cli-common-container-exists | function-call | claude-dev::container_exists, claude-dev-mac::container_exists | MOD-cli-common | 指定名のコンテナが存在するか(停止中を含む)を判定する |
| MODULE-cli-common-container-name | function-call | claude-dev::container_name, claude-dev-mac::container_name | MOD-cli-common | プロジェクト名からコンテナ名を導出する(命名規則の実体) |
| MODULE-cli-common-dev-agent-path | function-call | claude-dev-mac::dev_agent_path | MOD-cli-common | macOS の専用 ssh-agent ソケットのパスを決める |
| MODULE-cli-common-ensure-infrastructure | function-call | claude-dev::ensure_infrastructure, claude-dev-mac::ensure_infrastructure | MOD-cli-common | docker network と共有ボリュームを必要なら作成する |
| MODULE-cli-common-get-novnc-url | function-call | claude-dev::get_novnc_url, claude-dev-mac::get_novnc_url | MOD-cli-common | 公開中の noVNC ポートから接続 URL を組み立てる |
| MODULE-cli-common-image-exists | function-call | claude-dev::image_exists, claude-dev-mac::image_exists | MOD-cli-common | 指定イメージがローカルに存在するかを判定する |
| MODULE-cli-common-is-running | function-call | claude-dev::is_running, claude-dev-mac::is_running | MOD-cli-common | 指定コンテナが running 状態かを判定する |
| MODULE-cli-common-lock | function-call | claude-dev::acquire_lock, claude-dev::release_lock, claude-dev-mac::acquire_lock, claude-dev-mac::release_lock | MOD-cli-common | 共有資源を触る6コマンドを直列化するロックを取得・解放し、残骸を引き継ぐ |
| MODULE-cli-common-require-setup | function-call | claude-dev::require_setup, claude-dev-mac::require_setup | MOD-cli-common | セットアップ未実施なら理由を表示して終了する事前条件ゲート |
| MODULE-cli-common-resolve-container-user | function-call | claude-dev::resolve_container_user, claude-dev-mac::resolve_container_user | MOD-cli-common | docker exec に渡す実行ユーザを決定する |
| MODULE-cli-common-select-ssh-keys | function-call | claude-dev::select_ssh_keys_interactive, claude-dev-mac::select_ssh_keys_interactive | MOD-cli-common | 利用可能な SSH 鍵を列挙し対話選択させる |
| MODULE-cli-common-write-project-ssh-keys | function-call | claude-dev::write_project_ssh_keys, claude-dev-mac::write_project_ssh_keys | MOD-cli-common | 選択した鍵を .claude-dev.yaml へ書き出す |
| MODULE-cli-firewall | tool | dispatch firewall @ claude-dev::main, dispatch firewall @ claude-dev-mac::main | MOD-cli-firewall | コンテナ内のファイアウォールルールを表示する |
| MODULE-cli-forward | tool | dispatch forward @ claude-dev::main, dispatch forward @ claude-dev-mac::main | MOD-cli-forward | 指定コンテナポートのホスト側フォワードを動的に追加する |
| MODULE-cli-list | tool | dispatch list @ claude-dev::main, dispatch list @ claude-dev-mac::main | MOD-cli-list | 実行中セッションの一覧と noVNC URL を表示する |
| MODULE-cli-login | tool | dispatch login @ claude-dev::main, dispatch login @ claude-dev-mac::main | MOD-cli-login | Claude の OAuth ログインをコンテナ内で実行する |
| MODULE-cli-login-codex | tool | dispatch login-codex @ claude-dev::main, dispatch login-codex @ claude-dev-mac::main | MOD-cli-login-codex | Codex のデバイス認証ログインを実行し認証情報を共有ボリュームへ置く |
| MODULE-cli-logout | tool | dispatch logout @ claude-dev::main, dispatch logout @ claude-dev-mac::main | MOD-cli-logout | Claude と Codex の認証情報を削除する |
| MODULE-cli-orchestrate | tool | dispatch orchestrate @ claude-dev::main, dispatch orchestrate @ claude-dev-mac::main | MOD-cli-orchestrate | コンテナ内で orchestrator を起動する(ゴール指定・--fresh 対応) |
| MODULE-cli-ports | tool | dispatch ports @ claude-dev::main, dispatch ports @ claude-dev-mac::main | MOD-cli-ports | コンテナのポートフォワード一覧を表示する |
| MODULE-cli-pull | tool | dispatch pull @ claude-dev::main, dispatch pull @ claude-dev-mac::main | MOD-cli-pull | GHCR からビルド済みイメージを取得する(既定タグ latest) |
| MODULE-cli-reset | tool | dispatch reset @ claude-dev::main, dispatch reset @ claude-dev-mac::main | MOD-cli-reset | コンテナ・ボリューム・イメージを全削除する |
| MODULE-cli-setup | tool | dispatch setup @ claude-dev::main, dispatch setup @ claude-dev-mac::main | MOD-cli-setup | イメージをビルドし docker network とボリュームを作る |
| MODULE-cli-ssh-keys | tool | dispatch ssh-keys @ claude-dev::main, dispatch ssh-keys @ claude-dev-mac::main | MOD-cli-ssh-keys | ssh-keys の引数を reset / select へ振り分けるディスパッチャ |
| MODULE-cli-ssh-keys-reset | tool | dispatch ssh-keys.reset @ claude-dev::main, dispatch ssh-keys.reset @ claude-dev-mac::main | MOD-cli-ssh-keys | このプロジェクトの SSH 鍵選択を初期化する |
| MODULE-cli-ssh-keys-select | tool | dispatch ssh-keys.select @ claude-dev::main, dispatch ssh-keys.select @ claude-dev-mac::main | MOD-cli-ssh-keys | 使う SSH 鍵を対話選択して .claude-dev.yaml に保存する |
| MODULE-cli-start | tool | dispatch start @ claude-dev::main, dispatch start @ claude-dev-mac::main | MOD-cli-start | カレントディレクトリで開発コンテナを起動する(VNC+Chrome が既定) |
| MODULE-cli-stop | tool | dispatch stop @ claude-dev::main, dispatch stop @ claude-dev-mac::main | MOD-cli-stop | セッションを停止し、遊休なら docker-proxy と ssh ブリッジも止める |
| MODULE-cli-unforward | tool | dispatch unforward @ claude-dev::main, dispatch unforward @ claude-dev-mac::main | MOD-cli-unforward | 指定ポートのフォワードを解除する |
| MODULE-cli-upgrade | tool | dispatch upgrade @ claude-dev::main, dispatch upgrade @ claude-dev-mac::main | MOD-cli-upgrade | 全イメージを --no-cache で再ビルドして更新する |
| MODULE-container-tools-wait-limit-reset | tool | dispatch wait-limit-reset.sh @ scripts/wait-limit-reset.sh::main | MOD-container-tools | Claude のレート制限解除時刻まで待機する |
| MODULE-docker-proxy-serve | tool | dispatch main @ docker-proxy/main.go::main | MOD-docker-proxy | Docker API を検査・書き換えして透過中継する常駐プロキシ |
| MODULE-entrypoint-claude | tool | dispatch entrypoint-claude.sh @ scripts/entrypoint-claude.sh::main | MOD-entrypoint | コンテナ起動時に UID/GID・認証共有・VNC・firewall・portsync を整える |
| MODULE-firewall-init | tool | dispatch init-firewall-claude.sh @ scripts/init-firewall-claude.sh::main | MOD-firewall | iptables/ipset でブラックリスト型のファイアウォールを構成する |
| MODULE-hooks-save-prompt | tool | dispatch save_prompt.sh @ scripts/save_prompt.sh::main | MOD-hooks | Claude Code フックから渡されたプロンプトを保存する |
| MODULE-hooks-send-slack-message | tool | dispatch sendslackmsg.sh @ scripts/sendslackmsg.sh::main | MOD-hooks | Claude Code フックの通知を Slack へ送る |
| MODULE-makefile-build | tool | dispatch build @ Makefile::build | MOD-makefile | claude / claude-vnc / docker-proxy の全イメージをビルドする |
| MODULE-makefile-build-claude | tool | dispatch build-claude @ Makefile::build-claude | MOD-makefile | Claude ベースイメージをビルドする |
| MODULE-makefile-build-claude-vnc | tool | dispatch build-claude-vnc @ Makefile::build-claude-vnc | MOD-makefile | ベースイメージの上に VNC/Chrome 層を重ねてビルドする |
| MODULE-makefile-build-docker-proxy | tool | dispatch build-docker-proxy @ Makefile::build-docker-proxy | MOD-makefile | Docker Socket Proxy のイメージをビルドする |
| MODULE-makefile-build-orchestrator | tool | dispatch build-orchestrator @ Makefile::build-orchestrator | MOD-makefile | orchestrator をローカルでビルドしテストする |
| MODULE-makefile-clean | tool | dispatch clean @ Makefile::clean | MOD-makefile | コンテナ・ボリューム・イメージを削除して初期化する |
| MODULE-makefile-env | tool | dispatch env @ Makefile::env | MOD-makefile | .env を雛形から作成する |
| MODULE-makefile-help | tool | dispatch help @ Makefile::help | MOD-makefile | 利用可能なターゲットの一覧を表示する |
| MODULE-makefile-install | tool | dispatch install @ Makefile::install | MOD-makefile | claude-dev CLI のシンボリックリンクを PATH へ登録する |
| MODULE-makefile-login | tool | dispatch login @ Makefile::login | MOD-makefile | Claude の OAuth ログインを実行する |
| MODULE-makefile-network | tool | dispatch network @ Makefile::network | MOD-makefile | 専用 docker network を作成する |
| MODULE-makefile-orch-sample | tool | dispatch orch-sample @ Makefile::orch-sample | MOD-makefile | orchestrator 自己検証用のサンプルプロジェクトを配置する |
| MODULE-makefile-orch-sample-clean | tool | dispatch orch-sample-clean @ Makefile::orch-sample-clean | MOD-makefile | サンプルプロジェクトの生成物を削除する |
| MODULE-makefile-setup | tool | dispatch setup @ Makefile::setup | MOD-makefile | env→network→volumes→build→install を順に実行する初回セットアップ |
| MODULE-makefile-status | tool | dispatch status @ Makefile::status | MOD-makefile | イメージ・コンテナ・ボリュームの状態を表示する |
| MODULE-makefile-uninstall | tool | dispatch uninstall @ Makefile::uninstall | MOD-makefile | CLI のシンボリックリンクを削除する |
| MODULE-makefile-update-claude | tool | dispatch update-claude @ Makefile::update-claude | MOD-makefile | Claude Code だけをキャッシュ利用で高速更新する |
| MODULE-makefile-upgrade | tool | dispatch upgrade @ Makefile::upgrade | MOD-makefile | 全イメージを --no-cache で完全再ビルドする |
| MODULE-makefile-volumes | tool | dispatch volumes @ Makefile::volumes | MOD-makefile | 認証情報などの共有ボリュームを作成する |
| MODULE-orchestrator-claude-exec | function-call | orchestrator/worker.go::ExecClaude.RunPrompt, orchestrator/claudebin.go::claudeChildEnv, orchestrator/claudebin.go::claudePath, orchestrator/claudebin.go::localBinDir | MOD-orchestrator | Claude CLI を子プロセスとして起動し環境と PATH を整える |
| MODULE-orchestrator-config | function-call | orchestrator/config.go::LoadConfig, orchestrator/config.go::DefaultConfig | MOD-orchestrator | 実行設定を読み込み既定値で補完する |
| MODULE-orchestrator-controller | function-call | orchestrator/controller.go::Controller.Run, orchestrator/controller.go::newRunID | MOD-orchestrator | ブレインストーミング→実行→統合の状態機械を統括する |
| MODULE-orchestrator-dashboard | function-call | orchestrator/dashtui.go::newDashProgram, orchestrator/dashtui.go::dashModel.Init, orchestrator/dashtui.go::dashModel.Update, orchestrator/dashtui.go::dashModel.View, orchestrator/dashboard.go::DashboardState.Set | MOD-orchestrator | 進捗ダッシュボード(bubbletea TUI)を表示し操作を受ける |
| MODULE-orchestrator-handoff | function-call | orchestrator/handoff.go::Handoff.Consume, orchestrator/handoff.go::Handoff.WaitConsume, orchestrator/handoff.go::Handoff.DiscardStale | MOD-orchestrator | TUI と制御ループの間で介入指示を受け渡す |
| MODULE-orchestrator-main | tool | dispatch main @ orchestrator/main.go::main | MOD-orchestrator | フラグを解釈し実行環境を組み立てて制御ループを起動する |
| MODULE-orchestrator-mode | function-call | orchestrator/mode.go::Mode.RunInteractive, orchestrator/mode.go::Mode.BrainstormingArgs, orchestrator/mode.go::Mode.ResolveArgs, orchestrator/mode.go::Mode.ResolveArgsOne, orchestrator/mode.go::Mode.IntervenePrompt, orchestrator/mode.go::Mode.WriteLaunchScript, orchestrator/mode.go::Mode.brainstormingInstr, orchestrator/mode.go::Mode.interveneInstr, orchestrator/mode.go::Mode.instructionPath, orchestrator/mode.go::readFileOr, orchestrator/mode.go::shellSingleQuote | MOD-orchestrator | 対話モードの起動引数・指示テンプレート・起動スクリプトを決める |
| MODULE-orchestrator-plan | function-call | orchestrator/controller.go::ReadyTasks, orchestrator/controller.go::AllDone, orchestrator/controller.go::AllSettled, orchestrator/controller.go::MarkBlockedByFailedDeps, orchestrator/controller.go::NormalizeForResume | MOD-orchestrator | 計画の依存関係から着手可能タスクと完了判定を導く |
| MODULE-orchestrator-review | function-call | orchestrator/review.go::Reviewer.RunGate, orchestrator/review.go::ParseReviewResult | MOD-orchestrator | worker の成果をレビューし重大指摘があれば差し戻す品質ゲート |
| MODULE-orchestrator-session | function-call | orchestrator/session.go::NewSessionManager, orchestrator/session.go::SessionManager.Ensure, orchestrator/session.go::SessionManager.EnsureAll, orchestrator/session.go::SessionManager.SetupMainSession, orchestrator/session.go::SessionManager.LaunchInteractive, orchestrator/session.go::SessionManager.SwitchTo, orchestrator/session.go::SessionManager.Kill, orchestrator/session.go::SessionManager.Run, orchestrator/session.go::SessionManager.MainSession, orchestrator/session.go::SessionManager.Has, orchestrator/session.go::SessionManager.BrainstormingWindow, orchestrator/session.go::SessionManager.WorkerWindow, orchestrator/session.go::SessionManager.DashboardWindow, orchestrator/session.go::SessionManager.DetectSession, orchestrator/session.go::SessionManager.ExpectedWindows, orchestrator/session.go::SessionManager.PaneDead, orchestrator/session.go::splitTarget, orchestrator/session.go::tmuxRun | MOD-orchestrator | tmux セッションとウィンドウを作成・切替・破棄する |
| MODULE-orchestrator-slack | function-call | orchestrator/slack.go::NewSlackNotifier, orchestrator/slack.go::SlackNotifier.Notify, orchestrator/slack.go::NopNotifier.Notify | MOD-orchestrator | 節目の出来事を Slack へ通知する(未設定時は無通知) |
| MODULE-orchestrator-state | function-call | orchestrator/state.go::NewStore, orchestrator/state.go::Store.path, orchestrator/state.go::Store.SaveState, orchestrator/state.go::Store.LoadState, orchestrator/state.go::Store.SavePlan, orchestrator/state.go::Store.LoadPlan, orchestrator/state.go::Store.ArchiveRun, orchestrator/state.go::Store.WriteSummary, orchestrator/state.go::Store.WorkerLogPath, orchestrator/state.go::Store.WorktreeAbs, orchestrator/state.go::Store.WorktreeRel, orchestrator/state.go::LoadProjectPolicy, orchestrator/state.go::VMModePreamble | MOD-orchestrator | 実行状態・計画・作業ツリーの配置を .orchestrator/ に永続化する |
| MODULE-orchestrator-state-intervention | function-call | orchestrator/state.go::Store.AddOpenIntervention, orchestrator/state.go::Store.RemoveOpenIntervention, orchestrator/state.go::Store.LoadOpenInterventions, orchestrator/state.go::Store.SaveOpenInterventions, orchestrator/state.go::Store.AppendIntervention, orchestrator/state.go::Store.AppendAssumption, orchestrator/state.go::Store.AppendAudit, orchestrator/state.go::Store.ReadAnswer, orchestrator/state.go::Store.WriteQuestion, orchestrator/mode.go::Store.ReadQuestion, orchestrator/state.go::Store.LoadControl, orchestrator/state.go::Store.DeleteControl, orchestrator/state.go::Store.ReadAtomicSidecar, orchestrator/state.go::Store.WriteAtomicSidecar | MOD-orchestrator | 介入・質問・監査ログの永続化と、制御ファイルの読取と破棄を担う |
| MODULE-orchestrator-state-io | function-call | orchestrator/state.go::readJSON, orchestrator/state.go::writeAtomic, orchestrator/state.go::writeJSONAtomic, orchestrator/state.go::appendJSONL | MOD-orchestrator | JSON の読み書きを一時ファイル経由の原子的置換で行う |
| MODULE-orchestrator-streamlog | function-call | orchestrator/streamlog.go::newStreamPrettyWriter, orchestrator/streamlog.go::streamPrettyWriter.Write | MOD-orchestrator | Claude の stream-json 出力を人が読める形へ整形する |
| MODULE-orchestrator-term | function-call | orchestrator/term.go::ttyRestoreSane, orchestrator/term.go::selectMenu, orchestrator/term.go::printModeBanner, orchestrator/term.go::rawKeyMode, orchestrator/term.go::sttyRun, orchestrator/mode.go::isTTY | MOD-orchestrator | 端末の raw モード制御・TTY 判定・メニュー選択を提供する |
| MODULE-orchestrator-trigger | function-call | orchestrator/trigger.go::Evaluate | MOD-orchestrator | 停滞・介入要求などの発火条件を判定する |
| MODULE-orchestrator-worker | function-call | orchestrator/worker.go::Worker.Dispatch, orchestrator/worker.go::Worker.BuildPrompt, orchestrator/worker.go::ParseWorkerResult, orchestrator/worker.go::extractFromClaudeEnvelope, orchestrator/worker.go::resultFromStream | MOD-orchestrator | タスクを worker へ割り当てて並列実行し結果を解釈する |
| MODULE-orchestrator-worktree | function-call | orchestrator/worker.go::Worker.PrepareWorktree, orchestrator/worker.go::CleanOrchWorktrees, orchestrator/worker.go::ExecGit.run, orchestrator/worker.go::ExecGit.WorktreeAdd, orchestrator/worker.go::ExecGit.WorktreeAddExisting, orchestrator/worker.go::ExecGit.WorktreeRemove, orchestrator/worker.go::ExecGit.BranchExists, orchestrator/worker.go::ExecGit.CurrentBranch, orchestrator/worker.go::ExecGit.HasCommits, orchestrator/worker.go::ExecGit.Merge | MOD-orchestrator | worker ごとの git worktree を作成・撤去し、統合の git 操作を実行する |
| MODULE-portsync-dood | tool | dispatch --loop @ scripts/dood-portsync.sh::main, scripts/dood-portsync.sh::main | MOD-portsync | DooD 環境で公開ポートを検出し socat で 127.0.0.1 へ転送する |
| MODULE-sample-project-mathkit | function-call | examples/orch-sample/src/mathkit/geometry.py::circle_area, examples/orch-sample/src/mathkit/geometry.py::rect_area, examples/orch-sample/src/mathkit/stats.py::mean, examples/orch-sample/src/mathkit/stats.py::median, examples/orch-sample/src/mathkit/strings.py::slugify | MOD-sample-project | 自己検証で orchestrator が実装対象とする mathkit の関数群 |
| MODULE-sample-project-scaffold | tool | dispatch orch-sample.sh @ scripts/orch-sample.sh::main | MOD-sample-project | サンプルプロジェクトと seed plan を作業領域へ配置する |
| MODULE-vm-mode-cli | tool | dispatch vm @ scripts/vm::main | MOD-vm-mode | VM の起動状態・health・ポート同期を操作するヘルパー |
| MODULE-vm-mode-healthd | tool | dispatch --loop @ scripts/vm-healthd.sh::main, scripts/vm-healthd.sh::main | MOD-vm-mode | QEMU の CPU 使用率から資源逼迫を検知し tmux と health へ書く |
| MODULE-vm-mode-portsync | tool | dispatch --loop @ scripts/vm-portsync.sh::main, scripts/vm-portsync.sh::main | MOD-vm-mode | ゲストの公開ポートを QMP hostfwd_add で 127.0.0.1 へ転送する |
| MODULE-vm-mode-up | tool | dispatch vm-up.sh @ scripts/vm-up.sh::main | MOD-vm-mode | QEMU/KVM で VM を起動し provision して常駐ヘルパーを立ち上げる |

<!-- 種別: user-action | event | function-call | rest-api | tool | other -->

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

## 到達しない関数についての判断

<!-- feature-graph.md の「どの入口からも到達しない関数」16件に対する仕分け。生成物ではなく人間の判断。 -->

| シンボル | 判断 |
|---|---|
| `claude-dev::main` / `claude-dev-mac::main` | ディスパッチャ本体。サブコマンドのハンドラを入口にしているので本体には辺が立たない(抽出の構造上そうなる) |
| `docker-proxy/main.go::cachedResolveProjectDir` / `lookupProjectDir` | `var resolveProjectDir = cachedResolveProjectDir`(`docker-proxy/main.go:47`)の関数値経由。Tier 2 の静的解決の限界 |
| `orchestrator/main.go::terminalConfirm` | `Confirm: terminalConfirm`(`orchestrator/main.go:166`)の関数値経由。同上 |
| `orchestrator/term.go::resolveMenu` | `selectMenu` の鍵操作を単体テスト可能にした純粋関数(`orchestrator/term.go:184` のコメント)。テスト専用であることが明示されている |
| `orchestrator/state.go::Store.SaveControl` / `Store.RemoveSidecar` | 「used in tests / by tooling」と明示(`orchestrator/state.go:472`)。外部ツール向けの公開 API |
| `orchestrator/controller.go::Controller.resolveInterventions` / `resolveOne` / `openInterventionCount`、`orchestrator/dashboard.go::DashboardState.SelectableWorker` / `SelectableWorkerStatus`(と私有ヘルパ2件) | **製品コードからの呼び出しが見つからない**(テストからのみ参照)。到達不能コードの疑い → `docs/issues/001-modify-orchestrator-test-only-symbols.md` で報告し、本タスクでは直さない |

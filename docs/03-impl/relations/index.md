# 機能間連携仕様書 一覧

<!-- このファイルは build-index.py が生成する。手書きしない。 -->

<!-- BEGIN GENERATED: build-index.py -->

| ID | モジュール | 種別 | 同期 | 呼び出し元 | 呼び出す先 | 概要 |
|---|---|---|---|---|---|---|
| [MODULE-cli-attach](MODULE-cli-attach.md) | MOD-cli-attach | tool | sync | なし | MODULE-cli-common-container-name, MODULE-cli-common-is-running, MODULE-cli-common-require-setup, MODULE-cli-common-resolve-container-user | 実行中コンテナの tmux セッションに接続する |
| [MODULE-cli-code](MODULE-cli-code.md) | MOD-cli-code | tool | sync | なし | MODULE-cli-common-container-name, MODULE-cli-common-is-running, MODULE-cli-common-require-setup, MODULE-cli-common-resolve-container-user | 新しい tmux ウィンドウで Claude Code を起動する |
| [MODULE-cli-common-container-exists](MODULE-cli-common-container-exists.md) | MOD-cli-common | function-call | sync | MODULE-cli-forward, MODULE-cli-logout, MODULE-cli-start, MODULE-cli-stop, MODULE-cli-unforward | なし | 指定名のコンテナが存在するか(停止中を含む)を判定する |
| [MODULE-cli-common-container-name](MODULE-cli-common-container-name.md) | MOD-cli-common | function-call | sync | MODULE-cli-attach, MODULE-cli-code, MODULE-cli-firewall, MODULE-cli-forward, MODULE-cli-orchestrate, MODULE-cli-ports, MODULE-cli-ssh-keys, MODULE-cli-ssh-keys-reset, MODULE-cli-start, MODULE-cli-stop, MODULE-cli-unforward | なし | プロジェクト名からコンテナ名を導出する(命名規則の実体) |
| [MODULE-cli-common-dev-agent-path](MODULE-cli-common-dev-agent-path.md) | MOD-cli-common | function-call | sync | MODULE-cli-ssh-keys-reset, MODULE-cli-start, MODULE-cli-stop | なし | macOS の専用 ssh-agent とブリッジのファイル配置を決める |
| [MODULE-cli-common-ensure-infrastructure](MODULE-cli-common-ensure-infrastructure.md) | MOD-cli-common | function-call | sync | MODULE-cli-login, MODULE-cli-login-codex, MODULE-cli-start | なし | docker network と共有 3 ボリュームを冪等に作成する |
| [MODULE-cli-common-get-novnc-url](MODULE-cli-common-get-novnc-url.md) | MOD-cli-common | function-call | sync | MODULE-cli-list, MODULE-cli-ports, MODULE-cli-start | なし | 公開中の noVNC ポートから接続 URL を組み立てる |
| [MODULE-cli-common-image-exists](MODULE-cli-common-image-exists.md) | MOD-cli-common | function-call | sync | MODULE-cli-common-require-setup, MODULE-cli-start | なし | 指定イメージがローカルに存在するかを判定する |
| [MODULE-cli-common-is-running](MODULE-cli-common-is-running.md) | MOD-cli-common | function-call | sync | MODULE-cli-attach, MODULE-cli-code, MODULE-cli-firewall, MODULE-cli-forward, MODULE-cli-list, MODULE-cli-orchestrate, MODULE-cli-ports, MODULE-cli-start, MODULE-cli-stop | なし | 指定コンテナが running 状態かを判定する |
| [MODULE-cli-common-require-setup](MODULE-cli-common-require-setup.md) | MOD-cli-common | function-call | sync | MODULE-cli-attach, MODULE-cli-code, MODULE-cli-login, MODULE-cli-login-codex, MODULE-cli-logout, MODULE-cli-orchestrate, MODULE-cli-start | MODULE-cli-common-image-exists | セットアップ未実施なら必要なイメージを自動ビルドする事前条件ゲート |
| [MODULE-cli-common-resolve-container-user](MODULE-cli-common-resolve-container-user.md) | MOD-cli-common | function-call | sync | MODULE-cli-attach, MODULE-cli-code, MODULE-cli-orchestrate, MODULE-cli-start | なし | docker exec に渡す実行ユーザを稼働中コンテナ自身の env から決定する |
| [MODULE-cli-common-select-ssh-keys](MODULE-cli-common-select-ssh-keys.md) | MOD-cli-common | function-call | sync | MODULE-cli-ssh-keys-select, MODULE-cli-start | MODULE-cli-common-write-project-ssh-keys | 利用可能な SSH 鍵を列挙し対話選択させて保存する |
| [MODULE-cli-common-write-project-ssh-keys](MODULE-cli-common-write-project-ssh-keys.md) | MOD-cli-common | function-call | sync | MODULE-cli-common-select-ssh-keys, MODULE-cli-start | なし | 選択した鍵を .claude-dev.yaml へ書き出す |
| [MODULE-cli-firewall](MODULE-cli-firewall.md) | MOD-cli-firewall | tool | sync | なし | MODULE-cli-common-container-name, MODULE-cli-common-is-running | コンテナ内のファイアウォールルールを表示する |
| [MODULE-cli-forward](MODULE-cli-forward.md) | MOD-cli-forward | tool | sync | なし | MODULE-cli-common-container-exists, MODULE-cli-common-container-name, MODULE-cli-common-is-running | 指定コンテナポートのホスト側フォワードを動的に追加する |
| [MODULE-cli-list](MODULE-cli-list.md) | MOD-cli-list | tool | sync | なし | MODULE-cli-common-get-novnc-url, MODULE-cli-common-is-running | 実行中セッションの一覧と noVNC URL を表示する |
| [MODULE-cli-login](MODULE-cli-login.md) | MOD-cli-login | tool | sync | なし | MODULE-cli-common-ensure-infrastructure, MODULE-cli-common-require-setup | Claude の OAuth ログインをコンテナ内で実行し共有ボリュームへ保存する |
| [MODULE-cli-login-codex](MODULE-cli-login-codex.md) | MOD-cli-login-codex | tool | sync | なし | MODULE-cli-common-ensure-infrastructure, MODULE-cli-common-require-setup | Codex のデバイス認証を実行し認証情報を共有ボリュームの codex/ へ置く |
| [MODULE-cli-logout](MODULE-cli-logout.md) | MOD-cli-logout | tool | sync | なし | MODULE-cli-common-container-exists, MODULE-cli-common-require-setup | Claude と Codex の認証情報を共有ボリュームごと削除する |
| [MODULE-cli-orchestrate](MODULE-cli-orchestrate.md) | MOD-cli-orchestrate | tool | sync | なし | MODULE-cli-common-container-name, MODULE-cli-common-is-running, MODULE-cli-common-require-setup, MODULE-cli-common-resolve-container-user, MODULE-cli-start | コンテナ内で orchestrator を起動する(ゴール指定・--fresh 対応) |
| [MODULE-cli-ports](MODULE-cli-ports.md) | MOD-cli-ports | tool | sync | なし | MODULE-cli-common-container-name, MODULE-cli-common-get-novnc-url, MODULE-cli-common-is-running | コンテナのポートフォワード一覧と noVNC URL を表示する |
| [MODULE-cli-pull](MODULE-cli-pull.md) | MOD-cli-pull | tool | sync | なし | なし | GHCR からビルド済みイメージを取得して latest へ retag する |
| [MODULE-cli-reset](MODULE-cli-reset.md) | MOD-cli-reset | tool | sync | なし | なし | コンテナ・ボリューム・イメージを全削除して初期状態へ戻す |
| [MODULE-cli-setup](MODULE-cli-setup.md) | MOD-cli-setup | tool | sync | なし | なし | イメージをビルドし docker network と共有ボリュームを作る初回セットアップ |
| [MODULE-cli-ssh-keys](MODULE-cli-ssh-keys.md) | MOD-cli-ssh-keys | tool | sync | なし | MODULE-cli-common-container-name | ssh-keys の引数を reset / select へ振り分けるディスパッチャ |
| [MODULE-cli-ssh-keys-reset](MODULE-cli-ssh-keys-reset.md) | MOD-cli-ssh-keys | tool | sync | なし | MODULE-cli-common-container-name, MODULE-cli-common-dev-agent-path | このプロジェクトの SSH 鍵選択を初期化する |
| [MODULE-cli-ssh-keys-select](MODULE-cli-ssh-keys-select.md) | MOD-cli-ssh-keys | tool | sync | なし | MODULE-cli-common-select-ssh-keys | 使う SSH 鍵を対話選択して .claude-dev.yaml に保存する |
| [MODULE-cli-start](MODULE-cli-start.md) | MOD-cli-start | tool | sync | MODULE-cli-orchestrate | MODULE-entrypoint-claude, MODULE-cli-common-container-exists, MODULE-cli-common-container-name, MODULE-cli-common-dev-agent-path, MODULE-cli-common-ensure-infrastructure, MODULE-cli-common-get-novnc-url, MODULE-cli-common-image-exists, MODULE-cli-common-is-running, MODULE-cli-common-require-setup, MODULE-cli-common-resolve-container-user, MODULE-cli-common-select-ssh-keys, MODULE-cli-common-write-project-ssh-keys | カレントディレクトリで開発コンテナを起動する(VNC+Chrome が既定) |
| [MODULE-cli-stop](MODULE-cli-stop.md) | MOD-cli-stop | tool | sync | なし | MODULE-cli-common-container-exists, MODULE-cli-common-container-name, MODULE-cli-common-dev-agent-path, MODULE-cli-common-is-running | セッションを停止し、遊休なら docker-proxy と ssh ブリッジも止める |
| [MODULE-cli-unforward](MODULE-cli-unforward.md) | MOD-cli-unforward | tool | sync | なし | MODULE-cli-common-container-exists, MODULE-cli-common-container-name | 指定ポートのフォワードを解除する |
| [MODULE-cli-upgrade](MODULE-cli-upgrade.md) | MOD-cli-upgrade | tool | sync | なし | なし | 全イメージを --no-cache で再ビルドして更新する |
| [MODULE-container-tools-wait-limit-reset](MODULE-container-tools-wait-limit-reset.md) | MOD-container-tools | tool | sync | なし | なし | Claude のレート制限解除時刻まで待機し tmux 経由で作業を再開させる |
| [MODULE-docker-proxy-serve](MODULE-docker-proxy-serve.md) | MOD-docker-proxy | tool | sync | なし | なし | Docker API を検査・書き換えして透過中継する常駐プロキシ |
| [MODULE-entrypoint-claude](MODULE-entrypoint-claude.md) | MOD-entrypoint | tool | sync | MODULE-cli-start | MODULE-firewall-init, MODULE-portsync-dood, MODULE-vm-mode-up | コンテナ起動時に UID/GID・認証共有・VNC・firewall・portsync を整える |
| [MODULE-firewall-init](MODULE-firewall-init.md) | MOD-firewall | tool | sync | MODULE-entrypoint-claude | なし | iptables/ipset でブラックリスト型のファイアウォールを構成する |
| [MODULE-hooks-save-prompt](MODULE-hooks-save-prompt.md) | MOD-hooks | tool | sync | なし | なし | Claude Code フックから渡されたプロンプトを一時ファイルへ保存する |
| [MODULE-hooks-send-slack-message](MODULE-hooks-send-slack-message.md) | MOD-hooks | tool | sync | なし | なし | Claude Code フックの通知をプロンプト文脈つきで Slack へ送る |
| [MODULE-makefile-build](MODULE-makefile-build.md) | MOD-makefile | tool | sync | MODULE-makefile-setup | MODULE-makefile-build-claude, MODULE-makefile-build-claude-vnc, MODULE-makefile-build-docker-proxy | claude / claude-vnc / docker-proxy の全イメージをビルドする |
| [MODULE-makefile-build-claude](MODULE-makefile-build-claude.md) | MOD-makefile | tool | sync | MODULE-makefile-build, MODULE-makefile-build-claude-vnc | なし | Claude ベースイメージをビルドする |
| [MODULE-makefile-build-claude-vnc](MODULE-makefile-build-claude-vnc.md) | MOD-makefile | tool | sync | MODULE-makefile-build | MODULE-makefile-build-claude | ベースイメージの上に VNC/Chrome 層を重ねてビルドする |
| [MODULE-makefile-build-docker-proxy](MODULE-makefile-build-docker-proxy.md) | MOD-makefile | tool | sync | MODULE-makefile-build | なし | Docker Socket Proxy のイメージをビルドする |
| [MODULE-makefile-build-orchestrator](MODULE-makefile-build-orchestrator.md) | MOD-makefile | tool | sync | なし | なし | orchestrator をローカルでビルドしテストする |
| [MODULE-makefile-clean](MODULE-makefile-clean.md) | MOD-makefile | tool | sync | なし | なし | コンテナ・ボリューム・イメージを削除して初期化する |
| [MODULE-makefile-env](MODULE-makefile-env.md) | MOD-makefile | tool | sync | MODULE-makefile-setup | なし | .env を雛形から作成する |
| [MODULE-makefile-help](MODULE-makefile-help.md) | MOD-makefile | tool | sync | なし | なし | 利用可能なターゲットの一覧を表示する |
| [MODULE-makefile-install](MODULE-makefile-install.md) | MOD-makefile | tool | sync | MODULE-makefile-setup | なし | claude-dev CLI のシンボリックリンクを PATH へ登録する |
| [MODULE-makefile-login](MODULE-makefile-login.md) | MOD-makefile | tool | sync | なし | なし | Claude の OAuth ログインを実行する |
| [MODULE-makefile-network](MODULE-makefile-network.md) | MOD-makefile | tool | sync | MODULE-makefile-setup | なし | 専用 docker network を作成する |
| [MODULE-makefile-orch-sample](MODULE-makefile-orch-sample.md) | MOD-makefile | tool | sync | なし | なし | orchestrator 自己検証用のサンプルプロジェクトを配置する |
| [MODULE-makefile-orch-sample-clean](MODULE-makefile-orch-sample-clean.md) | MOD-makefile | tool | sync | なし | なし | サンプルプロジェクトの生成物を削除する |
| [MODULE-makefile-setup](MODULE-makefile-setup.md) | MOD-makefile | tool | sync | なし | MODULE-makefile-build, MODULE-makefile-env, MODULE-makefile-install, MODULE-makefile-network, MODULE-makefile-volumes | env→network→volumes→build→install を順に実行する初回セットアップ |
| [MODULE-makefile-status](MODULE-makefile-status.md) | MOD-makefile | tool | sync | なし | なし | イメージ・コンテナ・ボリュームの状態を表示する |
| [MODULE-makefile-uninstall](MODULE-makefile-uninstall.md) | MOD-makefile | tool | sync | なし | なし | CLI のシンボリックリンクを削除する |
| [MODULE-makefile-update-claude](MODULE-makefile-update-claude.md) | MOD-makefile | tool | sync | なし | なし | Claude Code だけをキャッシュ利用で高速更新する |
| [MODULE-makefile-upgrade](MODULE-makefile-upgrade.md) | MOD-makefile | tool | sync | なし | なし | 全イメージを --no-cache で完全再ビルドする |
| [MODULE-makefile-volumes](MODULE-makefile-volumes.md) | MOD-makefile | tool | sync | MODULE-makefile-setup | なし | 認証情報などの共有ボリュームを作成する |
| [MODULE-orchestrator-claude-exec](MODULE-orchestrator-claude-exec.md) | MOD-orchestrator | function-call | sync | MODULE-orchestrator-controller, MODULE-orchestrator-mode | MODULE-orchestrator-streamlog | Claude CLI を子プロセスとして起動し環境と PATH を整える |
| [MODULE-orchestrator-config](MODULE-orchestrator-config.md) | MOD-orchestrator | function-call | sync | MODULE-orchestrator-main | なし | 実行設定を4段マージ(組込既定→ユーザー設定→workspace 設定→環境変数)で読み込み既定値で補完する |
| [MODULE-orchestrator-controller](MODULE-orchestrator-controller.md) | MOD-orchestrator | function-call | sync | MODULE-orchestrator-main | MODULE-orchestrator-claude-exec, MODULE-orchestrator-dashboard, MODULE-orchestrator-handoff, MODULE-orchestrator-mode, MODULE-orchestrator-plan, MODULE-orchestrator-review, MODULE-orchestrator-session, MODULE-orchestrator-state, MODULE-orchestrator-state-intervention, MODULE-orchestrator-term, MODULE-orchestrator-trigger, MODULE-orchestrator-worker, MODULE-orchestrator-worktree | ブレインストーミング→実行→統合の状態機械を統括する |
| [MODULE-orchestrator-dashboard](MODULE-orchestrator-dashboard.md) | MOD-orchestrator | function-call | sync | MODULE-orchestrator-controller | MODULE-orchestrator-session, MODULE-orchestrator-state | 進捗ダッシュボード(bubbletea TUI)を表示し操作を受ける |
| [MODULE-orchestrator-handoff](MODULE-orchestrator-handoff.md) | MOD-orchestrator | function-call | sync | MODULE-orchestrator-controller | MODULE-orchestrator-state-intervention | TUI と制御ループの間で介入指示を受け渡す |
| [MODULE-orchestrator-main](MODULE-orchestrator-main.md) | MOD-orchestrator | tool | sync | なし | MODULE-orchestrator-config, MODULE-orchestrator-controller, MODULE-orchestrator-plan, MODULE-orchestrator-session, MODULE-orchestrator-slack, MODULE-orchestrator-state, MODULE-orchestrator-term, MODULE-orchestrator-worktree | フラグを解釈し実行環境を組み立てて制御ループを起動する |
| [MODULE-orchestrator-mode](MODULE-orchestrator-mode.md) | MOD-orchestrator | function-call | sync | MODULE-orchestrator-controller, MODULE-orchestrator-session | MODULE-orchestrator-claude-exec, MODULE-orchestrator-state, MODULE-orchestrator-state-intervention, MODULE-orchestrator-state-io, MODULE-orchestrator-term | 対話モードの起動引数・指示テンプレート・起動スクリプトを決める |
| [MODULE-orchestrator-plan](MODULE-orchestrator-plan.md) | MOD-orchestrator | function-call | sync | MODULE-orchestrator-controller, MODULE-orchestrator-main | なし | 計画の依存関係から着手可能タスクと完了判定を導く |
| [MODULE-orchestrator-review](MODULE-orchestrator-review.md) | MOD-orchestrator | function-call | sync | MODULE-orchestrator-controller | MODULE-orchestrator-state, MODULE-orchestrator-state-intervention, MODULE-orchestrator-worker | worker の成果をレビューし重大指摘があれば差し戻す品質ゲート |
| [MODULE-orchestrator-session](MODULE-orchestrator-session.md) | MOD-orchestrator | function-call | sync | MODULE-orchestrator-controller, MODULE-orchestrator-dashboard, MODULE-orchestrator-main | MODULE-orchestrator-mode | tmux セッションとウィンドウを作成・切替・破棄する |
| [MODULE-orchestrator-slack](MODULE-orchestrator-slack.md) | MOD-orchestrator | function-call | sync | MODULE-orchestrator-main | なし | 節目の出来事を Slack へ通知する(未設定時は無通知) |
| [MODULE-orchestrator-state](MODULE-orchestrator-state.md) | MOD-orchestrator | function-call | sync | MODULE-orchestrator-controller, MODULE-orchestrator-dashboard, MODULE-orchestrator-main, MODULE-orchestrator-mode, MODULE-orchestrator-review, MODULE-orchestrator-state-intervention, MODULE-orchestrator-worker, MODULE-orchestrator-worktree | MODULE-orchestrator-state-io | 実行状態・計画・作業ツリーの配置を .orchestrator/ に永続化する |
| [MODULE-orchestrator-state-intervention](MODULE-orchestrator-state-intervention.md) | MOD-orchestrator | function-call | sync | MODULE-orchestrator-controller, MODULE-orchestrator-handoff, MODULE-orchestrator-mode, MODULE-orchestrator-review, MODULE-orchestrator-worker | MODULE-orchestrator-state, MODULE-orchestrator-state-io | 介入・質問・監査ログの永続化と、制御ファイルの読取と破棄を担う |
| [MODULE-orchestrator-state-io](MODULE-orchestrator-state-io.md) | MOD-orchestrator | function-call | sync | MODULE-orchestrator-mode, MODULE-orchestrator-state, MODULE-orchestrator-state-intervention | なし | JSON の読み書きを一時ファイル経由の原子的置換で行う |
| [MODULE-orchestrator-streamlog](MODULE-orchestrator-streamlog.md) | MOD-orchestrator | function-call | sync | MODULE-orchestrator-claude-exec | なし | Claude の stream-json 出力を人が読める形へ整形する |
| [MODULE-orchestrator-term](MODULE-orchestrator-term.md) | MOD-orchestrator | function-call | sync | MODULE-orchestrator-controller, MODULE-orchestrator-main, MODULE-orchestrator-mode | なし | 端末の raw モード制御・TTY 判定・メニュー選択を提供する |
| [MODULE-orchestrator-trigger](MODULE-orchestrator-trigger.md) | MOD-orchestrator | function-call | sync | MODULE-orchestrator-controller | なし | 停滞・介入要求などの発火条件を判定する |
| [MODULE-orchestrator-worker](MODULE-orchestrator-worker.md) | MOD-orchestrator | function-call | sync | MODULE-orchestrator-controller, MODULE-orchestrator-review | MODULE-orchestrator-state, MODULE-orchestrator-state-intervention, MODULE-orchestrator-worktree | タスクを worker へ割り当てて並列実行し結果を解釈する |
| [MODULE-orchestrator-worktree](MODULE-orchestrator-worktree.md) | MOD-orchestrator | function-call | sync | MODULE-orchestrator-controller, MODULE-orchestrator-main, MODULE-orchestrator-worker | MODULE-orchestrator-state | worker ごとの git worktree を作成・撤去し、統合の git 操作を実行する |
| [MODULE-portsync-dood](MODULE-portsync-dood.md) | MOD-portsync | tool | sync | MODULE-entrypoint-claude | なし | DooD 環境で公開ポートを検出し socat で 127.0.0.1 へ転送する |
| [MODULE-sample-project-mathkit](MODULE-sample-project-mathkit.md) | MOD-sample-project | function-call | sync | EXTERNAL-pytest | なし | 自己検証で orchestrator が実装対象とする mathkit の関数群 |
| [MODULE-sample-project-scaffold](MODULE-sample-project-scaffold.md) | MOD-sample-project | tool | sync | なし | なし | サンプルプロジェクトと seed plan を作業領域へ配置する |
| [MODULE-vm-mode-cli](MODULE-vm-mode-cli.md) | MOD-vm-mode | tool | sync | なし | なし | VM の起動状態・health・ポート同期を操作するヘルパー |
| [MODULE-vm-mode-healthd](MODULE-vm-mode-healthd.md) | MOD-vm-mode | tool | sync | なし | なし | QEMU の CPU 使用率から資源逼迫を検知し tmux と health へ書く |
| [MODULE-vm-mode-portsync](MODULE-vm-mode-portsync.md) | MOD-vm-mode | tool | sync | なし | なし | ゲストの公開ポートを QMP hostfwd_add で 127.0.0.1 へ転送する |
| [MODULE-vm-mode-up](MODULE-vm-mode-up.md) | MOD-vm-mode | tool | sync | MODULE-entrypoint-claude | なし | QEMU/KVM で VM を起動し provision して常駐ヘルパーを立ち上げる |

件数: 82

<!-- END GENERATED -->

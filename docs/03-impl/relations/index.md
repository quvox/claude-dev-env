# 機能間連携仕様書 一覧

<!-- このファイルは build-index.py が生成する。手書きしない。 -->

<!-- BEGIN GENERATED: build-index.py -->

| ID | モジュール | 種別 | 同期 | 呼び出し元 | 呼び出す先 | 概要 |
|---|---|---|---|---|---|---|
| [MODULE-cli-attach](MODULE-cli-attach.md) | MOD-cli-attach | tool | sync | なし | MODULE-cli-common-container-name, MODULE-cli-common-is-running, MODULE-cli-common-require-setup, MODULE-cli-common-resolve-container-user | 実行中コンテナの tmux セッションに接続する |
| [MODULE-cli-code](MODULE-cli-code.md) | MOD-cli-code | tool | sync | なし | MODULE-cli-common-container-name, MODULE-cli-common-is-running, MODULE-cli-common-require-setup, MODULE-cli-common-resolve-container-user | 新しい tmux ウィンドウで Claude Code を起動する |
| [MODULE-cli-common-compose-project-name](MODULE-cli-common-compose-project-name.md) | MOD-cli-common | function-call | sync | MODULE-cli-start, MODULE-cli-stop | なし | compose プロジェクト名の一意化名と旧い名前を、両 OS で同じ値になる1機能で導出する |
| [MODULE-cli-common-container-exists](MODULE-cli-common-container-exists.md) | MOD-cli-common | function-call | sync | MODULE-cli-forward, MODULE-cli-logout, MODULE-cli-reset, MODULE-cli-start, MODULE-cli-stop, MODULE-cli-unforward | なし | 指定名のコンテナが存在するか(停止中を含む)を判定する |
| [MODULE-cli-common-container-name](MODULE-cli-common-container-name.md) | MOD-cli-common | function-call | sync | MODULE-cli-attach, MODULE-cli-code, MODULE-cli-firewall, MODULE-cli-forward, MODULE-cli-ports, MODULE-cli-ssh-keys, MODULE-cli-ssh-keys-reset, MODULE-cli-start, MODULE-cli-stop, MODULE-cli-unforward | なし | プロジェクト名からコンテナ名を導出する(命名規則の実体) |
| [MODULE-cli-common-container-project-dir](MODULE-cli-common-container-project-dir.md) | MOD-cli-common | function-call | sync | MODULE-cli-start, MODULE-cli-stop | なし | コンテナの管理ラベル claude-dev.project-dir(起動時の絶対パス)を読む |
| [MODULE-cli-common-destructive](MODULE-cli-common-destructive.md) | MOD-cli-common | function-call | sync | MODULE-cli-logout, MODULE-cli-reset | なし | 削除の計画・実行・結果の記録と、中断要求の遅延を扱う共通手順 |
| [MODULE-cli-common-dev-agent-path](MODULE-cli-common-dev-agent-path.md) | MOD-cli-common | function-call | sync | MODULE-cli-ssh-keys-reset, MODULE-cli-start, MODULE-cli-stop | なし | macOS の専用 ssh-agent とブリッジのファイル配置を決める |
| [MODULE-cli-common-ensure-infrastructure](MODULE-cli-common-ensure-infrastructure.md) | MOD-cli-common | function-call | sync | MODULE-cli-login, MODULE-cli-login-codex, MODULE-cli-start | なし | docker network と共有 3 ボリュームを冪等に作成する |
| [MODULE-cli-common-get-novnc-url](MODULE-cli-common-get-novnc-url.md) | MOD-cli-common | function-call | sync | MODULE-cli-list, MODULE-cli-ports, MODULE-cli-start | なし | 公開中の noVNC ポートから接続 URL を組み立てる |
| [MODULE-cli-common-image-exists](MODULE-cli-common-image-exists.md) | MOD-cli-common | function-call | sync | MODULE-cli-common-require-setup, MODULE-cli-reset, MODULE-cli-start | なし | 指定イメージがローカルに存在するかを判定する |
| [MODULE-cli-common-is-running](MODULE-cli-common-is-running.md) | MOD-cli-common | function-call | sync | MODULE-cli-attach, MODULE-cli-code, MODULE-cli-firewall, MODULE-cli-forward, MODULE-cli-list, MODULE-cli-ports, MODULE-cli-start, MODULE-cli-stop | なし | 指定コンテナが running 状態かを判定する |
| [MODULE-cli-common-lock](MODULE-cli-common-lock.md) | MOD-cli-common | function-call | sync | MODULE-cli-login, MODULE-cli-login-codex, MODULE-cli-logout, MODULE-cli-reset, MODULE-cli-start, MODULE-cli-stop | なし | 共有資源を触る6コマンドを直列化するロックを取得・解放し、残骸を引き継ぐ |
| [MODULE-cli-common-net-other-running-containers](MODULE-cli-common-net-other-running-containers.md) | MOD-cli-common | function-call | sync | MODULE-cli-logout, MODULE-cli-reset, MODULE-cli-stop | なし | 遊休判定に使う「claude-dev-net に接続している稼働中の他コンテナ」を列挙する |
| [MODULE-cli-common-require-setup](MODULE-cli-common-require-setup.md) | MOD-cli-common | function-call | sync | MODULE-cli-attach, MODULE-cli-code, MODULE-cli-login, MODULE-cli-login-codex, MODULE-cli-logout, MODULE-cli-start | MODULE-cli-common-image-exists | セットアップ未実施なら必要なイメージを自動ビルドする事前条件ゲート |
| [MODULE-cli-common-resolve-container-user](MODULE-cli-common-resolve-container-user.md) | MOD-cli-common | function-call | sync | MODULE-cli-attach, MODULE-cli-code, MODULE-cli-start | なし | docker exec に渡す実行ユーザを稼働中コンテナ自身の env から決定する |
| [MODULE-cli-common-select-ssh-keys](MODULE-cli-common-select-ssh-keys.md) | MOD-cli-common | function-call | sync | MODULE-cli-ssh-keys-select, MODULE-cli-start | MODULE-cli-common-write-project-ssh-keys | 利用可能な SSH 鍵を列挙し対話選択させて保存する |
| [MODULE-cli-common-spawned-resources](MODULE-cli-common-spawned-resources.md) | MOD-cli-common | function-call | sync | MODULE-cli-logout, MODULE-cli-reset, MODULE-cli-stop | なし | セッション由来の資源を種別とラベルフィルタ式から名前で列挙する |
| [MODULE-cli-common-write-project-ssh-keys](MODULE-cli-common-write-project-ssh-keys.md) | MOD-cli-common | function-call | sync | MODULE-cli-common-select-ssh-keys, MODULE-cli-start | なし | 選択した鍵を .claude-dev.yaml の ssh_keys 節へ書き、他のキーは保存する |
| [MODULE-cli-firewall](MODULE-cli-firewall.md) | MOD-cli-firewall | tool | sync | なし | MODULE-cli-common-container-name, MODULE-cli-common-is-running | コンテナ内のファイアウォールルールを表示する |
| [MODULE-cli-forward](MODULE-cli-forward.md) | MOD-cli-forward | tool | sync | なし | MODULE-cli-common-container-exists, MODULE-cli-common-container-name, MODULE-cli-common-is-running | 指定コンテナポートのホスト側フォワードを動的に追加する |
| [MODULE-cli-list](MODULE-cli-list.md) | MOD-cli-list | tool | sync | なし | MODULE-cli-common-get-novnc-url, MODULE-cli-common-is-running | 実行中セッションの一覧と noVNC URL を表示する |
| [MODULE-cli-login](MODULE-cli-login.md) | MOD-cli-login | tool | sync | なし | MODULE-cli-common-ensure-infrastructure, MODULE-cli-common-lock, MODULE-cli-common-require-setup | Claude の OAuth ログインをコンテナ内で実行し共有ボリュームへ保存する |
| [MODULE-cli-login-codex](MODULE-cli-login-codex.md) | MOD-cli-login-codex | tool | sync | なし | MODULE-cli-common-ensure-infrastructure, MODULE-cli-common-lock, MODULE-cli-common-require-setup | Codex のデバイス認証を実行し認証情報を共有ボリュームの codex/ へ置く |
| [MODULE-cli-logout](MODULE-cli-logout.md) | MOD-cli-logout | tool | sync | なし | MODULE-cli-common-container-exists, MODULE-cli-common-destructive, MODULE-cli-common-lock, MODULE-cli-common-net-other-running-containers, MODULE-cli-common-require-setup, MODULE-cli-common-spawned-resources | Claude と Codex の認証情報を共有ボリュームごと削除する |
| [MODULE-cli-ports](MODULE-cli-ports.md) | MOD-cli-ports | tool | sync | なし | MODULE-cli-common-container-name, MODULE-cli-common-get-novnc-url, MODULE-cli-common-is-running | コンテナのポートフォワード一覧と noVNC URL を表示する |
| [MODULE-cli-pull](MODULE-cli-pull.md) | MOD-cli-pull | tool | sync | なし | なし | GHCR からビルド済みイメージを取得して latest へ retag する |
| [MODULE-cli-reset](MODULE-cli-reset.md) | MOD-cli-reset | tool | sync | なし | MODULE-cli-common-container-exists, MODULE-cli-common-destructive, MODULE-cli-common-image-exists, MODULE-cli-common-lock, MODULE-cli-common-net-other-running-containers, MODULE-cli-common-spawned-resources | 管理ラベルを持つコンテナ・セッション由来の資源・固定名の共有資源を削除して初期状態へ戻す |
| [MODULE-cli-setup](MODULE-cli-setup.md) | MOD-cli-setup | tool | sync | なし | なし | イメージをビルドし docker network と共有ボリュームを作る初回セットアップ |
| [MODULE-cli-ssh-keys](MODULE-cli-ssh-keys.md) | MOD-cli-ssh-keys | tool | sync | なし | MODULE-cli-common-container-name | ssh-keys の引数を reset / select へ振り分けるディスパッチャ |
| [MODULE-cli-ssh-keys-reset](MODULE-cli-ssh-keys-reset.md) | MOD-cli-ssh-keys | tool | sync | なし | MODULE-cli-common-container-name, MODULE-cli-common-dev-agent-path | このプロジェクトの SSH 鍵選択を初期化する(他のキーは保存する) |
| [MODULE-cli-ssh-keys-select](MODULE-cli-ssh-keys-select.md) | MOD-cli-ssh-keys | tool | sync | なし | MODULE-cli-common-select-ssh-keys | 使う SSH 鍵を対話選択して .claude-dev.yaml に保存する |
| [MODULE-cli-start](MODULE-cli-start.md) | MOD-cli-start | tool | sync | なし | MODULE-entrypoint-claude, MODULE-cli-common-compose-project-name, MODULE-cli-common-container-exists, MODULE-cli-common-container-name, MODULE-cli-common-container-project-dir, MODULE-cli-common-dev-agent-path, MODULE-cli-common-ensure-infrastructure, MODULE-cli-common-get-novnc-url, MODULE-cli-common-image-exists, MODULE-cli-common-is-running, MODULE-cli-common-lock, MODULE-cli-common-require-setup, MODULE-cli-common-resolve-container-user, MODULE-cli-common-select-ssh-keys, MODULE-cli-common-write-project-ssh-keys | カレントディレクトリで開発コンテナを起動する(VNC+Chrome が既定) |
| [MODULE-cli-stop](MODULE-cli-stop.md) | MOD-cli-stop | tool | sync | なし | MODULE-cli-common-compose-project-name, MODULE-cli-common-container-exists, MODULE-cli-common-container-name, MODULE-cli-common-container-project-dir, MODULE-cli-common-dev-agent-path, MODULE-cli-common-is-running, MODULE-cli-common-lock, MODULE-cli-common-net-other-running-containers, MODULE-cli-common-spawned-resources | セッションと、そのセッションが作った資源を停止・削除し、遊休なら docker-proxy も削除する |
| [MODULE-cli-unforward](MODULE-cli-unforward.md) | MOD-cli-unforward | tool | sync | なし | MODULE-cli-common-container-exists, MODULE-cli-common-container-name | 指定ポートのフォワードを解除する |
| [MODULE-cli-upgrade](MODULE-cli-upgrade.md) | MOD-cli-upgrade | tool | sync | なし | なし | 全イメージを --no-cache で再ビルドして更新する |
| [MODULE-container-tools-wait-limit-reset](MODULE-container-tools-wait-limit-reset.md) | MOD-container-tools | tool | sync | なし | なし | Claude のレート制限解除時刻まで待機し tmux 経由で作業を再開させる |
| [MODULE-docker-proxy-serve](MODULE-docker-proxy-serve.md) | MOD-docker-proxy | tool | sync | なし | なし | Docker API を検査・書き換えして中継し、作られた資源に所有者ラベルを付ける常駐プロキシ |
| [MODULE-entrypoint-claude](MODULE-entrypoint-claude.md) | MOD-entrypoint | tool | sync | MODULE-cli-start | MODULE-firewall-init, MODULE-portsync-dood, MODULE-vm-mode-up | コンテナ起動時に UID/GID・認証共有・VNC・firewall・portsync を整える |
| [MODULE-firewall-init](MODULE-firewall-init.md) | MOD-firewall | tool | sync | MODULE-entrypoint-claude | なし | iptables/ipset でブラックリスト型のファイアウォールを構成する |
| [MODULE-makefile-build](MODULE-makefile-build.md) | MOD-makefile | tool | sync | MODULE-makefile-setup | MODULE-makefile-build-claude, MODULE-makefile-build-claude-vnc, MODULE-makefile-build-docker-proxy | claude / claude-vnc / docker-proxy の全イメージをビルドする |
| [MODULE-makefile-build-claude](MODULE-makefile-build-claude.md) | MOD-makefile | tool | sync | MODULE-makefile-build, MODULE-makefile-build-claude-vnc | なし | Claude ベースイメージをビルドする |
| [MODULE-makefile-build-claude-vnc](MODULE-makefile-build-claude-vnc.md) | MOD-makefile | tool | sync | MODULE-makefile-build | MODULE-makefile-build-claude | ベースイメージの上に VNC/Chrome 層を重ねてビルドする |
| [MODULE-makefile-build-docker-proxy](MODULE-makefile-build-docker-proxy.md) | MOD-makefile | tool | sync | MODULE-makefile-build | なし | Docker Socket Proxy のイメージをビルドする |
| [MODULE-makefile-clean](MODULE-makefile-clean.md) | MOD-makefile | tool | sync | なし | なし | コンテナ・ボリューム・イメージを削除して初期化する |
| [MODULE-makefile-env](MODULE-makefile-env.md) | MOD-makefile | tool | sync | MODULE-makefile-setup | なし | .env を雛形から作成する |
| [MODULE-makefile-help](MODULE-makefile-help.md) | MOD-makefile | tool | sync | なし | なし | 利用可能なターゲットの一覧を表示する |
| [MODULE-makefile-install](MODULE-makefile-install.md) | MOD-makefile | tool | sync | MODULE-makefile-setup | なし | claude-dev CLI のシンボリックリンクを PATH へ登録する |
| [MODULE-makefile-login](MODULE-makefile-login.md) | MOD-makefile | tool | sync | なし | なし | Claude の OAuth ログインを実行する |
| [MODULE-makefile-network](MODULE-makefile-network.md) | MOD-makefile | tool | sync | MODULE-makefile-setup | なし | 専用 docker network を作成する |
| [MODULE-makefile-setup](MODULE-makefile-setup.md) | MOD-makefile | tool | sync | なし | MODULE-makefile-build, MODULE-makefile-env, MODULE-makefile-install, MODULE-makefile-network, MODULE-makefile-volumes | env→network→volumes→build→install を順に実行する初回セットアップ |
| [MODULE-makefile-status](MODULE-makefile-status.md) | MOD-makefile | tool | sync | なし | なし | イメージ・コンテナ・ボリュームの状態を表示する |
| [MODULE-makefile-uninstall](MODULE-makefile-uninstall.md) | MOD-makefile | tool | sync | なし | なし | CLI のシンボリックリンクを削除する |
| [MODULE-makefile-update-claude](MODULE-makefile-update-claude.md) | MOD-makefile | tool | sync | なし | なし | コンテナイメージを作り直さずに Claude Code だけを更新する(ビルドキャッシュを使う) |
| [MODULE-makefile-upgrade](MODULE-makefile-upgrade.md) | MOD-makefile | tool | sync | なし | なし | 全イメージを --no-cache で完全再ビルドする |
| [MODULE-makefile-volumes](MODULE-makefile-volumes.md) | MOD-makefile | tool | sync | MODULE-makefile-setup | なし | 認証情報などの共有ボリュームを作成する |
| [MODULE-portsync-dood](MODULE-portsync-dood.md) | MOD-portsync | tool | sync | MODULE-entrypoint-claude | なし | DooD 環境で公開ポートを検出し socat で 127.0.0.1 へ転送する |
| [MODULE-vm-mode-cli](MODULE-vm-mode-cli.md) | MOD-vm-mode | tool | sync | なし | なし | VM の起動状態・health・ポート同期を操作するヘルパー |
| [MODULE-vm-mode-healthd](MODULE-vm-mode-healthd.md) | MOD-vm-mode | tool | sync | なし | なし | QEMU の CPU 使用率から資源逼迫を検知し tmux と health へ書く |
| [MODULE-vm-mode-portsync](MODULE-vm-mode-portsync.md) | MOD-vm-mode | tool | sync | なし | なし | ゲストの公開ポートを QMP hostfwd_add で 127.0.0.1 へ転送する |
| [MODULE-vm-mode-up](MODULE-vm-mode-up.md) | MOD-vm-mode | tool | sync | MODULE-entrypoint-claude | なし | QEMU/KVM で VM を起動し provision して常駐ヘルパーを立ち上げる |

件数: 61

<!-- END GENERATED: build-index.py -->

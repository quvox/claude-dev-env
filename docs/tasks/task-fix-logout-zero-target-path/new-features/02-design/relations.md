---
target: docs/02-design/relations.md
change: replace
version_bump: minor
sections:
  - "## 一覧"
deletes: []
reason: '`PLAN-cli-logout` の「呼び出す先」へ `PLAN-cli-common-spawned-resources` を足す。`logout` が「管理ラベルを持たないコンテナ」の表示集合から `claude-dev.role=spawned` を除くために、`reset` と同じ引き方でこの共有基盤を呼ぶようになるため(`CTR-cli-container`「残したものをどう列挙するか」が4つの除外を `logout` と `reset` の双方に課している / `docs/issues/089`)。あわせて `PLAN-cli-common-spawned-resources` の「呼び出し元」へ `PLAN-cli-logout` を足す(この表は両方向を持つため片側だけでは CS9 と check E が落ちる)。**`logout` は規則 D を使わない**(セッション由来の資源を削除対象にしない — `D0-env-05` 項2)という設計は変えない: この一覧は**表示から除くため**にだけ引く。他の `PLAN-*` 行は変更しない'
---

## 一覧

<!-- 網羅の範囲(この設計での取り決め):
     ・要件に係る**入口となる機能**(kind: tool)を全件書く。
     ・**モジュール境界をまたぐ呼び出し**の相手方(MOD-cli-common の共有基盤)を全件書く。
     ・同一モジュール内部で完結する private helper は書かない。呼び出す先の欄に
       「同一モジュール内部で完結」と書いてあるものは、03 側では内部の機能を呼んでいる。
     ・**入口機能の呼び出し元は「なし」と書く**。利用者の操作が契機であることは kind: tool と
       下の「連携の詳細」の契機で表す(03 側の実装仕様と語彙を揃えるため。USER-* は使わない)。 -->

| PLAN-ID | モジュール | kind | sync | 呼び出し元 | 呼び出す先 | 契約 | 対応要件 | 概要 |
|---|---|---|---|---|---|---|---|---|
| PLAN-cli-attach | MOD-cli-attach | tool | sync | なし | PLAN-cli-common-container-name, PLAN-cli-common-is-running, PLAN-cli-common-require-setup, PLAN-cli-common-resolve-container-user | なし | FR-env-01 | 実行中コンテナの tmux セッションに接続する |
| PLAN-cli-code | MOD-cli-code | tool | sync | なし | PLAN-cli-common-container-name, PLAN-cli-common-is-running, PLAN-cli-common-require-setup, PLAN-cli-common-resolve-container-user | なし | FR-env-01, FR-env-08, FR-env-12 | 新しい tmux ウィンドウで Claude Code を起動する |
| PLAN-cli-common-compose-project-name | MOD-cli-common | function-call | sync | PLAN-cli-start, PLAN-cli-stop | なし | CTR-cli-container | FR-env-01, FR-env-07 | compose プロジェクト名の一意化名と旧い名前を、両 OS で同じ値になる1機能で導出する |
| PLAN-cli-common-container-exists | MOD-cli-common | function-call | sync | PLAN-cli-forward, PLAN-cli-logout, PLAN-cli-reset, PLAN-cli-start, PLAN-cli-stop, PLAN-cli-unforward | なし | なし | FR-env-01 | 指定名のコンテナが存在するか(停止中を含む)を判定する |
| PLAN-cli-common-container-name | MOD-cli-common | function-call | sync | PLAN-cli-attach, PLAN-cli-code, PLAN-cli-firewall, PLAN-cli-forward, PLAN-cli-ports, PLAN-cli-ssh-keys, PLAN-cli-ssh-keys-reset, PLAN-cli-start, PLAN-cli-stop, PLAN-cli-unforward | なし | なし | FR-env-01 | プロジェクト名からコンテナ名を導出する(命名規則の実体) |
| PLAN-cli-common-container-project-dir | MOD-cli-common | function-call | sync | PLAN-cli-start, PLAN-cli-stop | なし | CTR-cli-container | FR-env-01 | コンテナの管理ラベル claude-dev.project-dir(起動時の絶対パス)を読む |
| PLAN-cli-common-destructive | MOD-cli-common | function-call | sync | PLAN-cli-logout, PLAN-cli-reset | なし | CTR-cli-container | FR-env-01, FR-env-03 | 削除の計画・実行・結果の記録と、中断要求の遅延を扱う共通手順 |
| PLAN-cli-common-dev-agent-path | MOD-cli-common | function-call | sync | PLAN-cli-ssh-keys-reset, PLAN-cli-start, PLAN-cli-stop | なし | なし | FR-env-04, FR-env-10 | macOS の専用 ssh-agent とブリッジのファイル配置を決める |
| PLAN-cli-common-ensure-infrastructure | MOD-cli-common | function-call | sync | PLAN-cli-login, PLAN-cli-login-codex, PLAN-cli-start | なし | CTR-cli-container | FR-env-01, FR-env-03 | docker network と共有 3 ボリュームを冪等に作成する |
| PLAN-cli-common-get-novnc-url | MOD-cli-common | function-call | sync | PLAN-cli-list, PLAN-cli-ports, PLAN-cli-start | なし | なし | FR-env-11 | 公開中の noVNC ポートから接続 URL を組み立てる |
| PLAN-cli-common-image-exists | MOD-cli-common | function-call | sync | PLAN-cli-common-require-setup, PLAN-cli-reset, PLAN-cli-start | なし | なし | FR-env-01, FR-env-09 | 指定イメージがローカルに存在するかを判定する |
| PLAN-cli-common-is-running | MOD-cli-common | function-call | sync | PLAN-cli-attach, PLAN-cli-code, PLAN-cli-firewall, PLAN-cli-forward, PLAN-cli-list, PLAN-cli-ports, PLAN-cli-start, PLAN-cli-stop | なし | なし | FR-env-01 | 指定コンテナが running 状態かを判定する |
| PLAN-cli-common-lock | MOD-cli-common | function-call | sync | PLAN-cli-login, PLAN-cli-login-codex, PLAN-cli-logout, PLAN-cli-reset, PLAN-cli-start, PLAN-cli-stop | なし | CTR-cli-container | FR-env-01, FR-env-03 | 共有資源を触る6コマンドを直列化するロックを取得・解放し、残骸を引き継ぐ |
| PLAN-cli-common-net-other-running-containers | MOD-cli-common | function-call | sync | PLAN-cli-logout, PLAN-cli-reset, PLAN-cli-stop | なし | CTR-cli-container | FR-env-01, FR-env-03 | 遊休判定に使う「claude-dev-net に接続している稼働中の他コンテナ」を列挙する |
| PLAN-cli-common-require-setup | MOD-cli-common | function-call | sync | PLAN-cli-attach, PLAN-cli-code, PLAN-cli-login, PLAN-cli-login-codex, PLAN-cli-logout, PLAN-cli-start | PLAN-cli-common-image-exists | なし | FR-env-01, FR-env-09 | セットアップ未実施なら必要なイメージを自動ビルドする事前条件ゲート |
| PLAN-cli-common-resolve-container-user | MOD-cli-common | function-call | sync | PLAN-cli-attach, PLAN-cli-code, PLAN-cli-start | なし | なし | FR-env-01, FR-env-02, FR-env-09 | docker exec に渡す実行ユーザを稼働中コンテナ自身の env から決定する |
| PLAN-cli-common-select-ssh-keys | MOD-cli-common | function-call | sync | PLAN-cli-ssh-keys-select, PLAN-cli-start | PLAN-cli-common-write-project-ssh-keys | なし | FR-env-04 | 利用可能な SSH 鍵を列挙し対話選択させて保存する |
| PLAN-cli-common-spawned-resources | MOD-cli-common | function-call | sync | PLAN-cli-logout, PLAN-cli-reset, PLAN-cli-stop | なし | CTR-cli-container | FR-env-01, FR-env-03 | セッション由来の資源を種別とラベルフィルタ式から名前で列挙する |
| PLAN-cli-common-write-project-ssh-keys | MOD-cli-common | function-call | sync | PLAN-cli-common-select-ssh-keys, PLAN-cli-start | なし | なし | FR-env-04 | 選択した鍵を .claude-dev.yaml へ書き出す |
| PLAN-cli-firewall | MOD-cli-firewall | tool | sync | なし | PLAN-cli-common-container-name, PLAN-cli-common-is-running | なし | FR-env-05 | コンテナ内のファイアウォールルールを表示する |
| PLAN-cli-forward | MOD-cli-forward | tool | sync | なし | PLAN-cli-common-container-exists, PLAN-cli-common-container-name, PLAN-cli-common-is-running | なし | FR-env-06 | 指定コンテナポートのホスト側フォワードを動的に追加する |
| PLAN-cli-list | MOD-cli-list | tool | sync | なし | PLAN-cli-common-get-novnc-url, PLAN-cli-common-is-running | なし | FR-env-01, FR-env-11 | 実行中セッションの一覧と noVNC URL を表示する |
| PLAN-cli-login | MOD-cli-login | tool | sync | なし | PLAN-cli-common-ensure-infrastructure, PLAN-cli-common-lock, PLAN-cli-common-require-setup | CTR-cli-container | FR-env-03 | Claude の OAuth ログインをコンテナ内で実行し共有ボリュームへ保存する |
| PLAN-cli-login-codex | MOD-cli-login-codex | tool | sync | なし | PLAN-cli-common-ensure-infrastructure, PLAN-cli-common-lock, PLAN-cli-common-require-setup | CTR-cli-container | FR-env-03, FR-env-12 | Codex のデバイス認証を実行し認証情報を共有ボリュームの codex/ へ置く |
| PLAN-cli-logout | MOD-cli-logout | tool | sync | なし | PLAN-cli-common-container-exists, PLAN-cli-common-destructive, PLAN-cli-common-lock, PLAN-cli-common-net-other-running-containers, PLAN-cli-common-require-setup, PLAN-cli-common-spawned-resources | CTR-cli-container | FR-env-03 | Claude と Codex の認証情報を共有ボリュームごと削除する |
| PLAN-cli-ports | MOD-cli-ports | tool | sync | なし | PLAN-cli-common-container-name, PLAN-cli-common-get-novnc-url, PLAN-cli-common-is-running | なし | FR-env-06, FR-env-11 | コンテナのポートフォワード一覧と noVNC URL を表示する |
| PLAN-cli-pull | MOD-cli-pull | tool | sync | なし | なし | なし | FR-env-09 | GHCR からビルド済みイメージを取得して latest へ retag する |
| PLAN-cli-reset | MOD-cli-reset | tool | sync | なし | PLAN-cli-common-container-exists, PLAN-cli-common-destructive, PLAN-cli-common-image-exists, PLAN-cli-common-lock, PLAN-cli-common-net-other-running-containers, PLAN-cli-common-spawned-resources | CTR-cli-container | FR-env-01, FR-env-03 | 管理ラベルを持つ Claude コンテナ・**所有者を問わないセッション由来の資源**・固定名の共有資源(ボリューム・イメージ・docker-proxy・ネットワーク)を削除して初期状態へ戻す(共有 docker-proxy とネットワークは遊休のときだけ) |
| PLAN-cli-setup | MOD-cli-setup | tool | sync | なし | なし | なし | FR-env-01, FR-env-09 | イメージをビルドし docker network と共有ボリュームを作る初回セットアップ |
| PLAN-cli-ssh-keys | MOD-cli-ssh-keys | tool | sync | なし | PLAN-cli-common-container-name | なし | FR-env-04 | ssh-keys の引数を reset / select へ振り分けるディスパッチャ |
| PLAN-cli-ssh-keys-reset | MOD-cli-ssh-keys | tool | sync | なし | PLAN-cli-common-container-name, PLAN-cli-common-dev-agent-path | なし | FR-env-04 | このプロジェクトの SSH 鍵選択を初期化する |
| PLAN-cli-ssh-keys-select | MOD-cli-ssh-keys | tool | sync | なし | PLAN-cli-common-select-ssh-keys | なし | FR-env-04 | 使う SSH 鍵を対話選択して .claude-dev.yaml に保存する |
| PLAN-cli-start | MOD-cli-start | tool | sync | なし | PLAN-entrypoint-claude, PLAN-cli-common-compose-project-name, PLAN-cli-common-container-exists, PLAN-cli-common-container-name, PLAN-cli-common-container-project-dir, PLAN-cli-common-dev-agent-path, PLAN-cli-common-ensure-infrastructure, PLAN-cli-common-get-novnc-url, PLAN-cli-common-image-exists, PLAN-cli-common-is-running, PLAN-cli-common-lock, PLAN-cli-common-require-setup, PLAN-cli-common-resolve-container-user, PLAN-cli-common-select-ssh-keys, PLAN-cli-common-write-project-ssh-keys | CTR-cli-container | FR-env-01, FR-env-02, FR-env-03, FR-env-04, FR-env-05, FR-env-06, FR-env-07, FR-env-08, FR-env-11, FR-env-12 | カレントディレクトリで開発コンテナを起動する(VNC+Chrome が既定) |
| PLAN-cli-stop | MOD-cli-stop | tool | sync | なし | PLAN-cli-common-compose-project-name, PLAN-cli-common-container-exists, PLAN-cli-common-container-name, PLAN-cli-common-container-project-dir, PLAN-cli-common-dev-agent-path, PLAN-cli-common-is-running, PLAN-cli-common-lock, PLAN-cli-common-net-other-running-containers, PLAN-cli-common-spawned-resources | CTR-cli-container | FR-env-01, FR-env-07 | セッションと、**そのセッションが作った資源(コンテナ・ネットワーク)**を停止・削除し、遊休なら docker-proxy と ssh ブリッジも止める |
| PLAN-cli-unforward | MOD-cli-unforward | tool | sync | なし | PLAN-cli-common-container-exists, PLAN-cli-common-container-name | なし | FR-env-06 | 指定ポートのフォワードを解除する |
| PLAN-cli-upgrade | MOD-cli-upgrade | tool | sync | なし | なし | なし | FR-env-01, FR-env-09 | 全イメージを --no-cache で再ビルドして更新する |
| PLAN-container-tools-wait-limit-reset | MOD-container-tools | tool | sync | なし | なし | なし | FR-env-01 | Claude のレート制限解除時刻まで待機し tmux 経由で作業を再開させる |
| PLAN-docker-proxy-serve | MOD-docker-proxy | tool | sync | なし | なし | CTR-docker-api | FR-env-07, NFR-sec-01 | Docker API を検査・書き換えして透過中継し、**作られたコンテナとネットワークに所有者ラベルを付ける**常駐プロキシ |
| PLAN-entrypoint-claude | MOD-entrypoint | tool | sync | PLAN-cli-start | PLAN-firewall-init, PLAN-portsync-dood, PLAN-vm-mode-up | CTR-cli-container, CTR-entrypoint-firewall | FR-env-02, FR-env-03, FR-env-05, FR-env-06, FR-env-07, FR-env-08, FR-env-11, FR-env-12 | コンテナ起動時に UID/GID・認証共有・VNC・firewall・portsync を整える |
| PLAN-firewall-init | MOD-firewall | tool | sync | PLAN-entrypoint-claude | なし | CTR-entrypoint-firewall | FR-env-05, NFR-sec-01 | iptables/ipset でブラックリスト型のファイアウォールを構成する |
| PLAN-makefile-build | MOD-makefile | tool | sync | PLAN-makefile-setup | PLAN-makefile-build-claude, PLAN-makefile-build-claude-vnc, PLAN-makefile-build-docker-proxy | なし | FR-env-01, FR-env-09, FR-env-12 | claude / claude-vnc / docker-proxy の全イメージをビルドする |
| PLAN-makefile-build-claude | MOD-makefile | tool | sync | PLAN-makefile-build, PLAN-makefile-build-claude-vnc | なし | なし | FR-env-01, FR-env-09, FR-env-12 | Claude ベースイメージをビルドする |
| PLAN-makefile-build-claude-vnc | MOD-makefile | tool | sync | PLAN-makefile-build | PLAN-makefile-build-claude | なし | FR-env-01, FR-env-09, FR-env-11 | ベースイメージの上に VNC/Chrome 層を重ねてビルドする |
| PLAN-makefile-build-docker-proxy | MOD-makefile | tool | sync | PLAN-makefile-build | なし | なし | FR-env-07, FR-env-09 | Docker Socket Proxy のイメージをビルドする |
| PLAN-makefile-clean | MOD-makefile | tool | sync | なし | なし | なし | FR-env-01, FR-env-03 | コンテナ・ボリューム・イメージを削除して初期化する |
| PLAN-makefile-env | MOD-makefile | tool | sync | PLAN-makefile-setup | なし | なし | FR-env-01 | .env を雛形から作成する |
| PLAN-makefile-help | MOD-makefile | tool | sync | なし | なし | なし | FR-env-01 | 利用可能なターゲットの一覧を表示する |
| PLAN-makefile-install | MOD-makefile | tool | sync | PLAN-makefile-setup | なし | なし | FR-env-01, FR-env-10 | claude-dev CLI のシンボリックリンクを PATH へ登録する |
| PLAN-makefile-login | MOD-makefile | tool | sync | なし | なし | なし | FR-env-03 | Claude の OAuth ログインを実行する |
| PLAN-makefile-network | MOD-makefile | tool | sync | PLAN-makefile-setup | なし | なし | FR-env-01 | 専用 docker network を作成する |
| PLAN-makefile-setup | MOD-makefile | tool | sync | なし | PLAN-makefile-build, PLAN-makefile-env, PLAN-makefile-install, PLAN-makefile-network, PLAN-makefile-volumes | なし | FR-env-01, FR-env-09 | env→network→volumes→build→install を順に実行する初回セットアップ |
| PLAN-makefile-status | MOD-makefile | tool | sync | なし | なし | なし | FR-env-01 | イメージ・コンテナ・ボリュームの状態を表示する |
| PLAN-makefile-uninstall | MOD-makefile | tool | sync | なし | なし | なし | FR-env-01, FR-env-10 | CLI のシンボリックリンクを削除する |
| PLAN-makefile-update-claude | MOD-makefile | tool | sync | なし | なし | なし | FR-env-09, FR-env-12 | コンテナイメージを作り直さずに Claude Code だけを更新する(ビルドキャッシュを使う) |
| PLAN-makefile-upgrade | MOD-makefile | tool | sync | なし | なし | なし | FR-env-01, FR-env-09 | 全イメージを --no-cache で完全再ビルドする |
| PLAN-makefile-volumes | MOD-makefile | tool | sync | PLAN-makefile-setup | なし | なし | FR-env-01, FR-env-03 | 認証情報などの共有ボリュームを作成する |
| PLAN-portsync-dood | MOD-portsync | tool | sync | PLAN-entrypoint-claude | なし | なし | FR-env-06, FR-env-07 | DooD 環境で公開ポートを検出し socat で 127.0.0.1 へ転送する |
| PLAN-vm-mode-cli | MOD-vm-mode | tool | sync | なし | なし | なし | FR-env-08 | VM の起動状態・health・ポート同期を操作するヘルパー |
| PLAN-vm-mode-healthd | MOD-vm-mode | tool | sync | なし | なし | なし | FR-env-08 | QEMU の CPU 使用率から資源逼迫を検知し tmux と health へ書く |
| PLAN-vm-mode-portsync | MOD-vm-mode | tool | sync | なし | なし | なし | FR-env-06, FR-env-08 | ゲストの公開ポートを QMP hostfwd_add で 127.0.0.1 へ転送する |
| PLAN-vm-mode-up | MOD-vm-mode | tool | sync | PLAN-entrypoint-claude | なし | なし | FR-env-08 | QEMU/KVM で VM を起動し provision して常駐ヘルパーを立ち上げる |


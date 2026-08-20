---
id: features
updated: 2026-08-11
summary: claude-dev 開発環境の機能一覧と入口。CLI サブコマンド・Makefile ターゲット・常駐スクリプト・Go バイナリの入口を列挙する
keywords: [機能表, 境界, claude-dev, Makefile, docker-proxy]
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
| MODULE-cli-common-compose-project-name | function-call | claude-dev::compose_project_name, claude-dev::compose_project_name_legacy, claude-dev::sha256_hex, claude-dev-mac::compose_project_name, claude-dev-mac::compose_project_name_legacy, claude-dev-mac::sha256_hex | MOD-cli-common | compose プロジェクト名の一意化名と旧い名前を両 OS で同じ値になる1機能で導出する |
| MODULE-cli-common-container-exists | function-call | claude-dev::container_exists, claude-dev-mac::container_exists | MOD-cli-common | 指定名のコンテナが存在するか(停止中を含む)を判定する |
| MODULE-cli-common-container-name | function-call | claude-dev::container_name, claude-dev-mac::container_name | MOD-cli-common | プロジェクト名からコンテナ名を導出する(命名規則の実体) |
| MODULE-cli-common-container-project-dir | function-call | claude-dev::container_project_dir, claude-dev-mac::container_project_dir | MOD-cli-common | コンテナの管理ラベル claude-dev.project-dir(起動時の絶対パス)を読む |
| MODULE-cli-common-destructive | function-call | claude-dev::destructive_plan, claude-dev::destructive_rm, claude-dev::destructive_deleted, claude-dev::destructive_failed, claude-dev::destructive_skipped, claude-dev::destructive_report, claude-dev::destructive_arm_interrupt, claude-dev::destructive_abort_if_interrupted, claude-dev-mac::destructive_plan, claude-dev-mac::destructive_rm, claude-dev-mac::destructive_deleted, claude-dev-mac::destructive_failed, claude-dev-mac::destructive_skipped, claude-dev-mac::destructive_report, claude-dev-mac::destructive_arm_interrupt, claude-dev-mac::destructive_abort_if_interrupted | MOD-cli-common | 削除の計画・実行・結果の記録と、中断要求の遅延を扱う共通手順 |
| MODULE-cli-common-dev-agent-path | function-call | claude-dev-mac::dev_agent_path | MOD-cli-common | macOS の専用 ssh-agent ソケットのパスを決める |
| MODULE-cli-common-ensure-infrastructure | function-call | claude-dev::ensure_infrastructure, claude-dev-mac::ensure_infrastructure | MOD-cli-common | docker network と共有ボリュームを必要なら作成する |
| MODULE-cli-common-get-novnc-url | function-call | claude-dev::get_novnc_url, claude-dev-mac::get_novnc_url | MOD-cli-common | 公開中の noVNC ポートから接続 URL を組み立てる |
| MODULE-cli-common-image-exists | function-call | claude-dev::image_exists, claude-dev-mac::image_exists | MOD-cli-common | 指定イメージがローカルに存在するかを判定する |
| MODULE-cli-common-is-running | function-call | claude-dev::is_running, claude-dev-mac::is_running | MOD-cli-common | 指定コンテナが running 状態かを判定する |
| MODULE-cli-common-lock | function-call | claude-dev::acquire_lock, claude-dev::release_lock, claude-dev-mac::acquire_lock, claude-dev-mac::release_lock | MOD-cli-common | 共有資源を触る6コマンドを直列化するロックを取得・解放し、残骸を引き継ぐ |
| MODULE-cli-common-net-other-running-containers | function-call | claude-dev::net_other_running_containers, claude-dev-mac::net_other_running_containers | MOD-cli-common | 遊休判定に使う claude-dev-net 接続中の他コンテナを列挙する |
| MODULE-cli-common-require-setup | function-call | claude-dev::require_setup, claude-dev-mac::require_setup | MOD-cli-common | セットアップ未実施なら理由を表示して終了する事前条件ゲート |
| MODULE-cli-common-resolve-container-user | function-call | claude-dev::resolve_container_user, claude-dev-mac::resolve_container_user | MOD-cli-common | docker exec に渡す実行ユーザを決定する |
| MODULE-cli-common-select-ssh-keys | function-call | claude-dev::select_ssh_keys_interactive, claude-dev-mac::select_ssh_keys_interactive | MOD-cli-common | 利用可能な SSH 鍵を列挙し対話選択させる |
| MODULE-cli-common-spawned-resources | function-call | claude-dev::spawned_resources, claude-dev-mac::spawned_resources | MOD-cli-common | セッション由来の資源を種別とラベルフィルタ式から名前で列挙する |
| MODULE-cli-common-write-project-ssh-keys | function-call | claude-dev::write_project_ssh_keys, claude-dev-mac::write_project_ssh_keys | MOD-cli-common | 選択した鍵を .claude-dev.yaml へ書き出す |
| MODULE-cli-firewall | tool | dispatch firewall @ claude-dev::main, dispatch firewall @ claude-dev-mac::main | MOD-cli-firewall | コンテナ内のファイアウォールルールを表示する |
| MODULE-cli-forward | tool | dispatch forward @ claude-dev::main, dispatch forward @ claude-dev-mac::main | MOD-cli-forward | 指定コンテナポートのホスト側フォワードを動的に追加する |
| MODULE-cli-list | tool | dispatch list @ claude-dev::main, dispatch list @ claude-dev-mac::main | MOD-cli-list | 実行中セッションの一覧と noVNC URL を表示する |
| MODULE-cli-login | tool | dispatch login @ claude-dev::main, dispatch login @ claude-dev-mac::main | MOD-cli-login | Claude の OAuth ログインをコンテナ内で実行する |
| MODULE-cli-login-codex | tool | dispatch login-codex @ claude-dev::main, dispatch login-codex @ claude-dev-mac::main | MOD-cli-login-codex | Codex のデバイス認証ログインを実行し認証情報を共有ボリュームへ置く |
| MODULE-cli-logout | tool | dispatch logout @ claude-dev::main, dispatch logout @ claude-dev-mac::main | MOD-cli-logout | Claude と Codex の認証情報を削除する |
| MODULE-cli-ports | tool | dispatch ports @ claude-dev::main, dispatch ports @ claude-dev-mac::main | MOD-cli-ports | コンテナのポートフォワード一覧を表示する |
| MODULE-cli-pull | tool | dispatch pull @ claude-dev::main, dispatch pull @ claude-dev-mac::main | MOD-cli-pull | GHCR からビルド済みイメージを取得する(既定タグ latest) |
| MODULE-cli-reset | tool | dispatch reset @ claude-dev::main, dispatch reset @ claude-dev-mac::main | MOD-cli-reset | 管理ラベルを持つ Claude コンテナと固定名の共有資源を削除して初期状態へ戻す |
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
| MODULE-makefile-build | tool | dispatch build @ Makefile::build | MOD-makefile | claude / claude-vnc / docker-proxy の全イメージをビルドする |
| MODULE-makefile-build-claude | tool | dispatch build-claude @ Makefile::build-claude | MOD-makefile | Claude ベースイメージをビルドする |
| MODULE-makefile-build-claude-vnc | tool | dispatch build-claude-vnc @ Makefile::build-claude-vnc | MOD-makefile | ベースイメージの上に VNC/Chrome 層を重ねてビルドする |
| MODULE-makefile-build-docker-proxy | tool | dispatch build-docker-proxy @ Makefile::build-docker-proxy | MOD-makefile | Docker Socket Proxy のイメージをビルドする |
| MODULE-makefile-clean | tool | dispatch clean @ Makefile::clean | MOD-makefile | コンテナ・ボリューム・イメージを削除して初期化する |
| MODULE-makefile-env | tool | dispatch env @ Makefile::env | MOD-makefile | .env を雛形から作成する |
| MODULE-makefile-help | tool | dispatch help @ Makefile::help | MOD-makefile | 利用可能なターゲットの一覧を表示する |
| MODULE-makefile-install | tool | dispatch install @ Makefile::install | MOD-makefile | claude-dev CLI のシンボリックリンクを PATH へ登録する |
| MODULE-makefile-login | tool | dispatch login @ Makefile::login | MOD-makefile | Claude の OAuth ログインを実行する |
| MODULE-makefile-network | tool | dispatch network @ Makefile::network | MOD-makefile | 専用 docker network を作成する |
| MODULE-makefile-setup | tool | dispatch setup @ Makefile::setup | MOD-makefile | env→network→volumes→build→install を順に実行する初回セットアップ |
| MODULE-makefile-status | tool | dispatch status @ Makefile::status | MOD-makefile | イメージ・コンテナ・ボリュームの状態を表示する |
| MODULE-makefile-uninstall | tool | dispatch uninstall @ Makefile::uninstall | MOD-makefile | CLI のシンボリックリンクを削除する |
| MODULE-makefile-update-claude | tool | dispatch update-claude @ Makefile::update-claude | MOD-makefile | コンテナイメージを作り直さずに Claude Code だけを更新する(ビルドキャッシュを使う) |
| MODULE-makefile-upgrade | tool | dispatch upgrade @ Makefile::upgrade | MOD-makefile | 全イメージを --no-cache で完全再ビルドする |
| MODULE-makefile-volumes | tool | dispatch volumes @ Makefile::volumes | MOD-makefile | 認証情報などの共有ボリュームを作成する |
| MODULE-portsync-dood | tool | dispatch --loop @ scripts/dood-portsync.sh::main, scripts/dood-portsync.sh::main | MOD-portsync | DooD 環境で公開ポートを検出し socat で 127.0.0.1 へ転送する |
| MODULE-vm-mode-cli | tool | dispatch vm @ scripts/vm::main | MOD-vm-mode | VM の起動状態・health・ポート同期を操作するヘルパー |
| MODULE-vm-mode-healthd | tool | dispatch --loop @ scripts/vm-healthd.sh::main, scripts/vm-healthd.sh::main | MOD-vm-mode | QEMU の CPU 使用率から資源逼迫を検知し tmux と health へ書く |
| MODULE-vm-mode-portsync | tool | dispatch --loop @ scripts/vm-portsync.sh::main, scripts/vm-portsync.sh::main | MOD-vm-mode | ゲストの公開ポートを QMP hostfwd_add で 127.0.0.1 へ転送する |
| MODULE-vm-mode-up | tool | dispatch vm-up.sh @ scripts/vm-up.sh::main | MOD-vm-mode | QEMU/KVM で VM を起動し provision して常駐ヘルパーを立ち上げる |

<!-- 種別: user-action | event | function-call | rest-api | tool | other -->

## 統合した機能

<!-- 複数の入口を1行にまとめた場合だけ、その理由をここに残す。 -->

| 機能ID | まとめた入口 | まとめた理由 |
|---|---|---|
| `MODULE-cli-*`(19件すべて) | `claude-dev::main#<subcmd>` と `claude-dev-mac::main#<subcmd>` | 同一のコマンド面を Linux/macOS で別実装しているだけで、外から見える振る舞いは同じ。OS 別に割ると同一仕様のモジュールが17本増えて依存表が読めなくなる(決定シート 委任(e))。**旧 `cli-mac` モジュールはこれにより解体される** |
| `MODULE-cli-common-*`(17件のうち**16件**) | `claude-dev::<fn>` と `claude-dev-mac::<fn>` | 同上。同名対の共通基盤関数を1機能として扱い、OS 差分は本文の「異常系・差分」に書く。**`MODULE-cli-common-dev-agent-path` は例外で、入口が `claude-dev-mac::dev_agent_path` だけである**(macOS 専用の ssh-agent ソケット配置規則であり、Linux 側に同名関数が無い) |
| `MODULE-cli-common-destructive` | `destructive_plan` / `destructive_rm` / `destructive_deleted` / `destructive_failed` / `destructive_skipped` / `destructive_report` / `destructive_arm_interrupt` / `destructive_abort_if_interrupted`(OS 別実装を含めて16シンボル) | 4つのモジュール水準変数(`_DESTRUCTIVE_PENDING` / `_DESTRUCTIVE_DELETED` / `_DESTRUCTIVE_FAILED` / `_DESTRUCTIVE_INTERRUPTED`)を共有する**1つの手順**であり、呼び出し順にも意味がある(`plan` で対象を出そろえてから `arm_interrupt` → `rm` → `abort_if_interrupted` → `report`)。個別に昇格させると状態の持ち主が8つに分散し、順序をどこにも書けない。`_destructive_done` はこのグループ内部のヘルパなので入口にしない |
| `MODULE-cli-common-compose-project-name` | `compose_project_name` / `compose_project_name_legacy` / `sha256_hex`(OS 別実装を含めて6シンボル) | 3つで compose 一意化名という1つの命名規則を成す(`DSN-env-03`)。**`compose_project_name` だけを昇格させると `compose_project_name_legacy` が `stop` の本体から直接呼ばれる分(`claude-dev:1615` / `:1692`)でファンイン2のまま残り、次回の `propose-features.py` に同じ候補が再提示される** |
| `MODULE-portsync-dood` / `MODULE-vm-mode-portsync` / `MODULE-vm-mode-healthd` | `main#--loop` と `main` | 同じスクリプトの一発実行と常駐実行。抽出器は `--loop` だけをエントリポイントとするが、一発実行も公開インターフェースなので同一機能に含める |

## 昇格させた共通基盤機能

<!-- ファンイン(到達できる機能の数)が2以上の関数は境界の実体である。 -->

| 機能ID / シンボル | ファンイン | 昇格したか | 判断の理由 |
|---|---|---|---|
| `claude-dev::container_name` / `claude-dev-mac::container_name` | 9 | 昇格 | コンテナ命名規則の実体。全サブコマンドがこの規則に依存する |
| `claude-dev::project_name` / `claude-dev-mac::project_name` | 9 | 畳み込む | 呼び出し元は `container_name` だけ。命名規則の内側の一段で、単独では意味を持たない |
| `claude-dev::is_running` / `claude-dev-mac::is_running` | 8 | 昇格 | 「セッションが動いているか」の判定はこのシステムの状態モデルそのもの |
| `claude-dev::image_exists` / `claude-dev-mac::image_exists` | 7 | 昇格 | `require_setup` を昇格させても `ensure_docker_proxy_container` から到達するのでファンイン2が残る |
| `claude-dev::require_setup` / `claude-dev-mac::require_setup` | 6 | 昇格 | セットアップ未実施時の停止条件。6機能に共通の事前条件ゲート |
| `claude-dev::acquire_lock` / `release_lock`(および macOS 版の同名対) | 6 | 昇格 | 共有資源(共有ボリューム・docker-proxy)を触る6機能を直列化する排他の実体。`start` / `stop` / `logout` / `reset` / `login` / `login-codex` が同じキー体系(`CTR-cli-container` の「排他(ロックキー)」)に依存する |
| `claude-dev::container_exists` / `claude-dev-mac::container_exists` | 5 | 昇格 | 停止中コンテナを含む存在判定。`is_running` と別概念で、stop/logout の分岐条件 |
| `claude-dev::net_other_running_containers` / `claude-dev-mac::net_other_running_containers` | 3 | 昇格 | 共有 docker-proxy と共有ネットワークを止めてよいかの判定(`FR-env-01` 受入基準9)の実体。`stop` / `logout` / `reset` が同じ集合に依存し、**数え落とすと稼働中の他プロジェクトから Docker が使えなくなる**。判定を管理ラベルにもイメージにも依存させない理由(`D0-env-10`)を1箇所に置く |
| `claude-dev::resolve_container_user` / `claude-dev-mac::resolve_container_user` | 3 | 昇格 | docker exec の実行ユーザ決定。権限に関わる判断を含む |
| `claude-dev::ensure_infrastructure` / `claude-dev-mac::ensure_infrastructure` | 3 | 昇格 | docker network とボリュームを作る副作用を持つ |
| `claude-dev::get_novnc_url` / `claude-dev-mac::get_novnc_url` | 3 | 昇格 | 利用者に提示する接続 URL の組み立て規則。3機能が同じ URL を出す |
| `claude-dev-mac::dev_agent_path` | 3 | 昇格 | macOS 専用の ssh-agent ソケット配置規則。start/stop/ssh-keys reset が同じ場所を前提にする |
| `claude-dev::compose_project_name` / `claude-dev-mac::compose_project_name` | 2 | 昇格 | `start` が渡す値と `stop` が再計算する値が1バイトでも違うと `stop` が何も消せない。**2機能が共有する形式の規則**である(`DSN-env-03` / `CTR-cli-container`「compose 資源の識別」) |
| `claude-dev::compose_project_name_legacy` / `claude-dev-mac::compose_project_name_legacy` | 2 | 昇格(`MODULE-cli-common-compose-project-name` へ統合) | `compose_project_name` から呼ばれるほか、**`stop` の本体からも直接呼ばれる**(`claude-dev:1615` / `:1692`。旧い名前の compose 資源の案内)。`compose_project_name` だけを昇格させてもファンイン2が残るので、同じ命名規則として1機能に統合する |
| `claude-dev::sha256_hex` / `claude-dev-mac::sha256_hex` | 2 | 昇格(`MODULE-cli-common-compose-project-name` へ統合) | 呼び出し元は `compose_project_name` だけなので、`compose_project_name` の昇格でファンインは1へ落ちる。**単独では畳み込みが正しい**が、`sha256sum` と `shasum -a 256` の OS 別分岐が compose 命名の一部であるため、統合の対象に含めて同じ文書で説明する |
| `claude-dev::container_project_dir` / `claude-dev-mac::container_project_dir` | 2 | 昇格 | 管理ラベル `claude-dev.project-dir` は compose 一意化名のハッシュ源(`FR-env-01` 受入基準19)と所有者ラベルの照合値(同22)の**唯一の出どころ**で、本体コンテナを削除すると失われる。読み取りの順序制約が `start` と `stop` の双方に掛かる |
| `claude-dev::spawned_resources` / `claude-dev-mac::spawned_resources` | 2 | 昇格 | セッション由来の資源の列挙(`DSN-env-04` の規則 D)。`stop` は所有者の値で、`reset` は `claude-dev.role=spawned` で引くが、**違うのはフィルタ式だけ**で種別ごとの引き方は共通である。0件と問い合わせ失敗を同一視しない規則(`CTR-cli-container`「エラーケース」)を1箇所に置く |
| `claude-dev::destructive_plan` / `destructive_rm` / `destructive_deleted` / `destructive_failed` / `destructive_skipped` / `destructive_report` / `destructive_arm_interrupt` / `destructive_abort_if_interrupted`(および macOS 版の同名対。8シンボル) | 2 | 昇格(`MODULE-cli-common-destructive` へ統合) | `logout` と `reset` が共有する削除の記録・報告・中断の手順。**畳み込んだままだと同一実装(`claude-dev:634`-`:700`)の説明が2つの連携仕様書に分かれ、実測で4項目が重複していた**(1件ごとの終了コードの記録 / `INT`・`TERM` を進行中の1件を終えてから受けること / 削除できなかった資源の1件ずつの列挙 / 戻り値1の条件)。片方だけを直すと2つの仕様が食い違う |
| `claude-dev::select_ssh_keys_interactive` / `claude-dev-mac::select_ssh_keys_interactive` | 2 | 昇格 | 対話 UI を持ち、`start` と `ssh-keys select` の双方から呼ばれる |
| `claude-dev::write_project_ssh_keys` / `claude-dev-mac::write_project_ssh_keys` | 2 | 昇格 | `.claude-dev.yaml` への書き込み(副作用)。`ensure_project_config` と選択 UI の双方から呼ばれる |
| `claude-dev::discover_ssh_keys` / `claude-dev-mac::discover_ssh_keys` | 2 | 畳み込む | `select_ssh_keys_interactive` を昇格させれば呼び出し元は1つになる |

## 到達しない関数についての判断

<!-- feature-graph.md の「どの入口からも到達しない関数」に対する仕分け。生成物ではなく人間の判断。 -->

| シンボル | 判断 |
|---|---|
| `claude-dev::main` / `claude-dev-mac::main` | ディスパッチャ本体。サブコマンドのハンドラを入口にしているので本体には辺が立たない(抽出の構造上そうなる) |
| `docker-proxy/main.go::cachedResolveProjectDir` / `lookupProjectDir` | `var resolveProjectDir = cachedResolveProjectDir`(`docker-proxy/main.go:76`)の関数値経由。Tier 2 の静的解決の限界 |
| `claude-dev::_destructive_done` / `claude-dev-mac::_destructive_done` | 到達する。呼び出し元 `destructive_deleted` / `destructive_failed` / `destructive_skipped`(`claude-dev:805`-`:808`)が**1行形式の関数定義**で、Tier 3(正規表現)抽出器がその本体を走査しないため辺が立たない。`destructive_skipped` 自体は `logout` の本体(`claude-dev:1293`)から呼ばれる。削除しない |
| `claude-dev::_release_all_locks` / `claude-dev-mac::_release_all_locks` | 到達する。呼び出しは `trap '_release_all_locks' EXIT` / `trap '_release_all_locks; exit 130' INT TERM`(`claude-dev:601`-`:602`)の**シグナルハンドラ文字列**経由で、静的抽出では見えない。削除しない |

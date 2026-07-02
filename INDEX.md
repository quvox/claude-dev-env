# ドキュメント索引

> このファイルは自動生成されます。直接編集しないでください。
> 再生成: airules docs index

まずこの索引を見て、必要なファイルだけを開いてください。
キーワードで絞り込めない場合は `rg "検索語" docs/` を使ってください。

| ファイル | 内容 | キーワード |
|---|---|---|
| [docs/00_idea-2.md](docs/00_idea-2.md) | 1 コンテナ内に AI オーケストレーター（リードエージェント）を立て、Claude Code・Codex 等のコーディングエージェントを連携させて複数プロジェクトを並列に進める仕組みの要件定義。介入トリガー・品質ゲート・配布/セキュリティ要件を定める。オーケストレーション設計（docs/06_orchestration.md）の出発点。 | 要件定義, AIオーケストレーター, マルチエージェント, Docker Agent, 介入トリガー, 品質ゲート, 並列開発 |
| [docs/01_getting-started.md](docs/01_getting-started.md) | 本環境を初めて導入する利用者向けに、前提条件・インストール手順・基本的な使い方・Webアクセス・トラブルシューティングを説明する導入ガイド。 | クイックスタート, インストール, OAuth認証, tmux, ポートフォワード, セッション管理, SSH |
| [docs/02_architecture.md](docs/02_architecture.md) | システム全体の設計（コンテナ構成・Dockerリソース・認証フロー・ポートフォワード・ブラウザ操作）を俯瞰する設計文書。実装の詳細仕様は docs/impl/ を参照。 | アーキテクチャ, Docker, VNC, 認証, ポートフォワード, コンテナ, Chrome |
| [docs/03_security.md](docs/03_security.md) | 脅威モデルと多層防御（コンテナ隔離・Docker Socket Proxy・ファイアウォール・SSH agent転送）の設計意図を説明するセキュリティ設計文書。 | セキュリティ, 脅威モデル, ファイアウォール, Docker Socket Proxy, コンテナ隔離, KVM, ブラックリスト |
| [docs/04_cli-reference.md](docs/04_cli-reference.md) | claude-dev CLI と Makefile の全コマンド・オプションの利用者向けリファレンス。CLIの内部実装仕様は docs/impl/10_cli.md を参照。 | CLI, コマンドリファレンス, claude-dev, orchestrate, ポートフォワード, セッション管理, VNC |
| [docs/05_customization.md](docs/05_customization.md) | ファイアウォール・CLAUDE.md・tmux・hooks/envなど、利用者が環境を調整するためのカスタマイズ手順をまとめた利用者向けガイド。 | カスタマイズ, ファイアウォール, hooks, Slack通知, tmux, KVM, デスクトップ操作 |
| [docs/06_orchestration.md](docs/06_orchestration.md) | プロジェクトごとに AI オーケストレーターを 1 体立て、人間は壁打ちと例外対応だけに関与して実行を自律・並列化する仕組みの設計文書。方式選択（自作の外部制御ループ）・2 モード構成・画面/プロセス像・介入設計を定める。 | オーケストレーター, 壁打ち, 自律実行, 外部制御ループ, 介入トリガー, マルチエージェント, tmux |
| [docs/07_self-verification.md](docs/07_self-verification.md) | 本オーケストレーター自身を、リポジトリ同梱の小さなサンプルサブプロジェクトに対して実際に動かし、ユースケースに沿って検証・改善するための設計文書。実プロジェクトを犠牲にせず高速・再現可能にオーケストレーターの不具合を発見/修正する開発ループを定める。 | 自己検証, ドッグフーディング, サンプルプロジェクト, 再現性, 介入, 中断再開, 動作確認 |
| [docs/08_vm-mode.md](docs/08_vm-mode.md) | Docker を多用する開発のために、claude コンテナ内で QEMU/KVM のゲスト VM を起動し、その中でネイティブ Docker を動かす「VM モード」の設計文書。virtiofs で /workspace を同一パス共有してライブ編集を保ち、ゲストの dockerd を DOCKER_HOST で claude 側エージェントから使う。bind mount・privileged 等を VM 境界に隔離して安全に許す。 | VMモード, QEMU, KVM, virtiofs, Docker, 隔離, DOCKER_HOST |
| [docs/MODIFICATION.md](docs/MODIFICATION.md) | オーケストレーター方針 追記提案（MODIFICATION） |  |
| [docs/impl/00_overview.md](docs/impl/00_overview.md) | リポジトリの実装全体を俯瞰し、コンポーネントの責務・制御フロー・Dockerリソース命名・ルート設定ファイルの役割・設計上の不変条件を示す。 | 実装仕様, コンポーネント構成, 制御フロー, Dockerリソース, 不変条件, 設計概要, CLI |
| [docs/impl/10_cli.md](docs/impl/10_cli.md) | ホスト側の claude-dev シェルスクリプトの実装仕様。ヘルパー関数・サブコマンド・コンテナ起動引数などの成果物仕様を記述する。 | CLI, claude-dev, bash, ヘルパー関数, コンテナ起動, ポートフォワード, orchestrate |
| [docs/impl/20_makefile.md](docs/impl/20_makefile.md) | セットアップ・ビルド・メンテナンスを担う Makefile のターゲット仕様（claude/VNC/docker-proxy イメージ・orchestrator のローカルビルド）とマルチステージビルド構成を記述する。 | Makefile, ビルド, セットアップ, マルチステージ, Docker, インストール, orchestrator |
| [docs/impl/30_scripts.md](docs/impl/30_scripts.md) | scripts/ ディレクトリの構成概要と、Claude Code hookスクリプト（save_prompt.sh / sendslackmsg.sh）および tmux.conf の実装仕様を記述する。 | scripts, hook, Slack通知, tmux, save_prompt, sendslackmsg, 設定 |
| [docs/impl/31_entrypoint.md](docs/impl/31_entrypoint.md) | Claude コンテナのENTRYPOINTとして起動し、UID/GID追従・認証共有・MCP設定・VNC/Chrome起動・tmuxセッション開始までを行う初期化スクリプトの実装仕様。 | entrypoint, UID/GID, 認証, MCP, VNC, Chrome, tmux |
| [docs/impl/32_firewall.md](docs/impl/32_firewall.md) | Claude コンテナ内で適用されるブラックリスト方式ファイアウォールの iptables 構成・適用ルール・カスタマイズ点の実装仕様。 | ファイアウォール, iptables, ipset, ブラックリスト, SMTP, SSH, セキュリティ |
| [docs/impl/40_devcontainer.md](docs/impl/40_devcontainer.md) | Dockerfile.claude（orch-builder/base/vnc ステージ。orchestrator バイナリと instructions を base へ同梱）・Dockerfile.docker-proxy・tmux.conf・.zshrc のビルド仕様を記述する。 | Dockerfile, Docker, VNC, マルチステージ, Go, orchestrator, ビルド |
| [docs/impl/50_docker-proxy.md](docs/impl/50_docker-proxy.md) | Docker APIを安全に中継するGo製リバースプロキシの検査ロジック・接続ハイジャック処理・テスト仕様を記述する。 | Docker Socket Proxy, Go, リバースプロキシ, API検査, セキュリティ, hijack, コンテナ |
| [docs/impl/60_orchestrator.md](docs/impl/60_orchestrator.md) | AI オーケストレーター（Go 製コントローラ）の実装仕様。外部制御ループ・状態ストア・モード切替・worker 並行ディスパッチ・品質ゲート・介入・判断基準・Slack 通知・ビルド配置を定める。設計の意図は docs/06_orchestration.md を参照。 | オーケストレーター, Go, 制御ループ, 状態ストア, worker, 介入, 並行実行 |
| [docs/impl/70_sample-project.md](docs/impl/70_sample-project.md) | オーケストレーター自己検証用のサンプルサブプロジェクト（テンプレート examples/orch-sample/）と、それを使い捨て作業コピーへ展開する scaffold（Makefile/スクリプト）、決定論的に介入・並行・中断再開を踏ませる seed plan、検証用 CLI affordance の実装仕様。 | サンプルプロジェクト, scaffold, seed plan, 自己検証, Makefile, orchestrate, テンプレート |
| [docs/impl/80_vm-mode.md](docs/impl/80_vm-mode.md) | VM モード（QEMU+KVM でゲスト VM を起動し virtiofs で /workspace を同一パス共有、ゲスト内 dockerd を DOCKER_HOST で使う）の実装仕様。Dockerfile への virtiofsd/cloud-image-utils 追加、Ubuntu cloud image の provision、起動スクリプト、claude-dev の --vm/vm、VM_DEV.md 生成の成果物仕様を定める。 | VMモード, QEMU, virtiofs, cloud-init, DOCKER_HOST, hostfwd, VM_DEV |
| [docs/reviews/2026-06-28_orchestrator-tty-fix.md](docs/reviews/2026-06-28_orchestrator-tty-fix.md) | レビュー: オーケストレーター 端末モード不具合の修正 |  |
| [docs/reviews/2026-07-01_orchestrator-e2e.md](docs/reviews/2026-07-01_orchestrator-e2e.md) | オーケストレーター 実機 E2E 動作確認（自己検証サンプル） |  |

_計 23 件_

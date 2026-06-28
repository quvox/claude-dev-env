# ドキュメント索引

> このファイルは自動生成されます。直接編集しないでください。
> 再生成: airules docs index

まずこの索引を見て、必要なファイルだけを開いてください。
キーワードで絞り込めない場合は `rg "検索語" docs/` を使ってください。

| ファイル | 内容 | キーワード |
|---|---|---|
| [docs/01_getting-started.md](docs/01_getting-started.md) | 本環境を初めて導入する利用者向けに、前提条件・インストール手順・基本的な使い方・Webアクセス・トラブルシューティングを説明する導入ガイド。 | クイックスタート, インストール, OAuth認証, tmux, ポートフォワード, セッション管理, SSH |
| [docs/02_architecture.md](docs/02_architecture.md) | システム全体の設計（コンテナ構成・Dockerリソース・認証フロー・ポートフォワード・ブラウザ操作）を俯瞰する設計文書。実装の詳細仕様は docs/impl/ を参照。 | アーキテクチャ, Docker, VNC, 認証, ポートフォワード, コンテナ, Chrome |
| [docs/03_security.md](docs/03_security.md) | 脅威モデルと多層防御（コンテナ隔離・Docker Socket Proxy・ファイアウォール・SSH agent転送）の設計意図を説明するセキュリティ設計文書。 | セキュリティ, 脅威モデル, ファイアウォール, Docker Socket Proxy, コンテナ隔離, KVM, ブラックリスト |
| [docs/04_cli-reference.md](docs/04_cli-reference.md) | claude-dev CLI と Makefile の全コマンド・オプションの利用者向けリファレンス。CLIの内部実装仕様は docs/impl/10_cli.md を参照。 | CLI, コマンドリファレンス, Makefile, claude-dev, ポートフォワード, セッション管理, VNC |
| [docs/05_customization.md](docs/05_customization.md) | ファイアウォール・CLAUDE.md・tmux・hooks/envなど、利用者が環境を調整するためのカスタマイズ手順をまとめた利用者向けガイド。 | カスタマイズ, ファイアウォール, hooks, Slack通知, tmux, KVM, デスクトップ操作 |
| [docs/impl/00_overview.md](docs/impl/00_overview.md) | リポジトリの実装全体を俯瞰し、コンポーネントの責務・制御フロー・Dockerリソース命名・ルート設定ファイルの役割・設計上の不変条件を示す。 | 実装仕様, コンポーネント構成, 制御フロー, Dockerリソース, 不変条件, 設計概要, CLI |
| [docs/impl/10_cli.md](docs/impl/10_cli.md) | ホスト側の claude-dev シェルスクリプトの実装仕様。ヘルパー関数・サブコマンド・コンテナ起動引数などの成果物仕様を記述する。 | CLI, claude-dev, bash, ヘルパー関数, コンテナ起動, ポートフォワード, VNC |
| [docs/impl/20_makefile.md](docs/impl/20_makefile.md) | セットアップ・ビルド・メンテナンスを担う Makefile のターゲット仕様とマルチステージビルド構成を記述する。 | Makefile, ビルド, セットアップ, マルチステージ, Docker, イメージ, インストール |
| [docs/impl/30_scripts.md](docs/impl/30_scripts.md) | scripts/ ディレクトリの構成概要と、Claude Code hookスクリプト（save_prompt.sh / sendslackmsg.sh）および tmux.conf の実装仕様を記述する。 | scripts, hook, Slack通知, tmux, save_prompt, sendslackmsg, 設定 |
| [docs/impl/31_entrypoint.md](docs/impl/31_entrypoint.md) | Claude コンテナのENTRYPOINTとして起動し、UID/GID追従・認証共有・MCP設定・VNC/Chrome起動・tmuxセッション開始までを行う初期化スクリプトの実装仕様。 | entrypoint, UID/GID, 認証, MCP, VNC, Chrome, tmux |
| [docs/impl/32_firewall.md](docs/impl/32_firewall.md) | Claude コンテナ内で適用されるブラックリスト方式ファイアウォールの iptables 構成・適用ルール・カスタマイズ点の実装仕様。 | ファイアウォール, iptables, ipset, ブラックリスト, SMTP, SSH, セキュリティ |
| [docs/impl/40_devcontainer.md](docs/impl/40_devcontainer.md) | Dockerfile.claude（base/vnc 2ステージ）・Dockerfile.docker-proxy・tmux.conf・.zshrc のビルド仕様を記述する。 | Dockerfile, Docker, VNC, Chrome, マルチステージ, Go, ビルド |
| [docs/impl/50_docker-proxy.md](docs/impl/50_docker-proxy.md) | Docker APIを安全に中継するGo製リバースプロキシの検査ロジック・接続ハイジャック処理・テスト仕様を記述する。 | Docker Socket Proxy, Go, リバースプロキシ, API検査, セキュリティ, hijack, コンテナ |

_計 13 件_

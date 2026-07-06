# 実装仕様一覧 (INDEX)

> 実装仕様ドキュメント群の全体構成を示す索引。各文書はソースコードと 1 対 1（または特定ディレクトリ）に対応する Single Source of Truth。まずこの一覧で必要な文書を絞り、該当ファイルのみを開くこと。

| ファイル | 対応するコード | 内容 |
|---|---|---|
| [00_overview.md](00_overview.md) | リポジトリ全体 | 実装全体の俯瞰。コンポーネントの責務・制御フロー・Docker リソース命名・ルート設定ファイル・設計上の不変条件。 |
| [10_cli.md](10_cli.md) | `claude-dev` | ホスト側 CLI（Linux 版）の実装仕様。ヘルパー関数・サブコマンド・コンテナ起動引数。 |
| [11_cli-mac.md](11_cli-mac.md) | `claude-dev-mac` | ホスト側 CLI（macOS 版）の実装仕様。Linux 版との差分（SSH agent の転送が socat TCP ブリッジ・Docker ソケット検出・VM/KVM 拒否・ポート直結・ネイティブアーキ）。鍵解決やローカル `.claude-dev.yaml`・`ssh-keys` サブコマンドは両 OS 共通（10_cli.md 正本）。設計は [../09_macos-support.md](../09_macos-support.md)。 |
| [20_makefile.md](20_makefile.md) | `Makefile` | セットアップ・ビルド・メンテナンスのターゲット仕様とマルチステージビルド構成（OS 判定での CLI 選択を含む）。 |
| [30_scripts.md](30_scripts.md) | `scripts/`（hook・tmux.conf 等） | `scripts/` の構成概要と hook スクリプト（save_prompt.sh / sendslackmsg.sh）・tmux.conf・dood-portsync 等の実装仕様。 |
| [31_entrypoint.md](31_entrypoint.md) | `scripts/entrypoint-claude.sh` | Claude コンテナの ENTRYPOINT。UID/GID 追従・認証共有・MCP 設定・VNC/Chrome 起動・tmux セッション開始。 |
| [32_firewall.md](32_firewall.md) | `scripts/init-firewall-claude.sh` | ブラックリスト方式ファイアウォールの iptables 構成・適用ルール・カスタマイズ点。 |
| [40_devcontainer.md](40_devcontainer.md) | `.devcontainer/Dockerfile.claude` ほか | Dockerfile.claude（orch-builder/base/vnc）・Dockerfile.docker-proxy・tmux.conf・.zshrc のビルド仕様（arm64 アーキ別分岐を含む）。 |
| [50_docker-proxy.md](50_docker-proxy.md) | `docker-proxy/`（Go） | Docker API を安全に中継するリバースプロキシの検査ロジック・hijack 処理・テスト仕様。 |
| [60_orchestrator.md](60_orchestrator.md) | `orchestrator/`（Go） | AI オーケストレーターの実装仕様。制御ループ・状態ストア・worker 並行ディスパッチ・品質ゲート・介入・Slack 通知・ビルド配置。 |
| [70_sample-project.md](70_sample-project.md) | `examples/orch-sample/` ほか | オーケストレーター自己検証用サンプルの scaffold・seed plan・検証用 CLI affordance。 |
| [80_vm-mode.md](80_vm-mode.md) | VM モード関連（`scripts/vm*` 等） | VM モード（QEMU+KVM＋virtiofs、ゲスト内 dockerd を DOCKER_HOST で利用）の実装仕様。**Linux 専用**（macOS では非対応）。 |
| [90_ghcr-workflow.md](90_ghcr-workflow.md) | `.github/workflows/ghcr-images.yml` | GHCR へ 3 イメージを毎日・マルチアーキ(amd64/arm64)で push する GitHub Actions ワークフロー（prepare→build[matrix, push-by-digest]→merge[imagetools]、YYYYMMDDHHmm+latest タグ）。設計は [../10_ghcr-images.md](../10_ghcr-images.md)。 |

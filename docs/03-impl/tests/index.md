# テスト実装仕様 一覧

<!-- このファイルは build-index.py が生成する。手書きしない。 -->

<!-- BEGIN GENERATED: build-index.py -->

| ファイル | 対象 | 実装済み/未検証/テスト対象外 | version | 更新 | 概要 |
|---|---|---|---|---|---|
| [cli-attach](cli-attach.md) | MOD-cli-attach | 0 / **1** / 0 | 1.1.0 | 2026-08-07 | MOD-cli-attach(実行中コンテナへの接続)の受入基準⇄テスト対応 |
| [cli-code](cli-code.md) | MOD-cli-code | 0 / **1** / 0 | 1.1.0 | 2026-08-07 | MOD-cli-code(tmux ウィンドウでの Claude Code 起動)の受入基準⇄テスト対応 |
| [cli-common](cli-common.md) | MOD-cli-common | 0 / **25** / 0 | 1.4.1 | 2026-08-11 | MOD-cli-common(CLI 共有基盤の17機能)の受入基準⇄テスト対応 |
| [cli-firewall](cli-firewall.md) | MOD-cli-firewall | 0 / **1** / 0 | 1.1.0 | 2026-08-07 | MOD-cli-firewall(ファイアウォール状態の表示)の受入基準⇄テスト対応 |
| [cli-forward](cli-forward.md) | MOD-cli-forward | 0 / **10** / 0 | 1.2.0 | 2026-08-07 | MOD-cli-forward(ポートフォワードの追加)の受入基準⇄テスト対応 |
| [cli-list](cli-list.md) | MOD-cli-list | 0 / **2** / 0 | 1.1.0 | 2026-08-07 | MOD-cli-list(セッション一覧の表示)の受入基準⇄テスト対応 |
| [cli-login](cli-login.md) | MOD-cli-login | 0 / **3** / 0 | 1.1.0 | 2026-08-07 | MOD-cli-login(Claude の認証)の受入基準⇄テスト対応 |
| [cli-login-codex](cli-login-codex.md) | MOD-cli-login-codex | 0 / **4** / 0 | 1.2.0 | 2026-08-07 | MOD-cli-login-codex(Codex CLI のデバイス認証)の受入基準⇄テスト対応 |
| [cli-logout](cli-logout.md) | MOD-cli-logout | 0 / **16** / 0 | 1.6.0 | 2026-08-11 | MOD-cli-logout(認証情報の破棄)の受入基準⇄テスト対応 |
| [cli-ports](cli-ports.md) | MOD-cli-ports | 0 / **2** / 0 | 1.1.0 | 2026-08-07 | MOD-cli-ports(公開ポートの一覧)の受入基準⇄テスト対応 |
| [cli-pull](cli-pull.md) | MOD-cli-pull | 0 / **5** / 0 | 1.2.0 | 2026-08-07 | MOD-cli-pull(GHCR からのイメージ取得)の受入基準⇄テスト対応 |
| [cli-reset](cli-reset.md) | MOD-cli-reset | 0 / **3** / 0 | 1.4.0 | 2026-08-07 | MOD-cli-reset(環境の初期化)の受入基準⇄テスト対応 |
| [cli-setup](cli-setup.md) | MOD-cli-setup | 0 / **1** / 0 | 1.1.0 | 2026-08-07 | MOD-cli-setup(初回セットアップ)の受入基準⇄テスト対応 |
| [cli-ssh-keys](cli-ssh-keys.md) | MOD-cli-ssh-keys | 0 / **5** / 0 | 1.1.0 | 2026-08-07 | MOD-cli-ssh-keys(転送する SSH 鍵の選択と解除)の受入基準⇄テスト対応 |
| [cli-start](cli-start.md) | MOD-cli-start | 2 / **35** / 0 | 1.3.0 | 2026-08-07 | MOD-cli-start(開発コンテナの起動)の受入基準⇄テスト対応 |
| [cli-stop](cli-stop.md) | MOD-cli-stop | 0 / **16** / 0 | 1.6.1 | 2026-08-11 | MOD-cli-stop(コンテナの停止)の受入基準⇄テスト対応 |
| [cli-unforward](cli-unforward.md) | MOD-cli-unforward | 0 / **3** / 0 | 1.2.0 | 2026-08-07 | MOD-cli-unforward(ポートフォワードの解除)の受入基準⇄テスト対応 |
| [cli-upgrade](cli-upgrade.md) | MOD-cli-upgrade | 0 / **1** / 0 | 1.1.0 | 2026-08-07 | MOD-cli-upgrade(CLI とイメージの更新)の受入基準⇄テスト対応 |
| [container-tools](container-tools.md) | MOD-container-tools | 0 / **1** / 0 | 1.1.0 | 2026-08-07 | MOD-container-tools(コンテナ内補助ツール)の受入基準⇄テスト対応 |
| [docker-proxy](docker-proxy.md) | MOD-docker-proxy | 10 / **2** / 0 | 1.3.0 | 2026-08-07 | MOD-docker-proxy(Docker API の検査と中継)の受入基準⇄テスト対応 |
| [e2e](e2e.md) | E2E | 0 / **4** / 0 | 1.7.0 | 2026-08-11 | E2Eシナリオ E2E-01〜E2E-03 と E2E-06 ⇄ テスト対応 |
| [entrypoint](entrypoint.md) | MOD-entrypoint | 0 / **23** / 0 | 1.2.0 | 2026-08-07 | MOD-entrypoint(コンテナ起動シーケンス)の受入基準⇄テスト対応 |
| [firewall](firewall.md) | MOD-firewall | 0 / **5** / 0 | 1.2.0 | 2026-08-07 | MOD-firewall(外向き通信のブラックリスト適用)の受入基準⇄テスト対応 |
| [images](images.md) | (モジュール外)イメージのビルドと GHCR 配布 | 0 / **15** / 0 | 1.3.0 | 2026-08-10 | どのモジュールにも属さないイメージのビルドと GHCR 配布の受入基準⇄テスト対応 |
| [makefile](makefile.md) | MOD-makefile | 0 / **18** / 0 | 1.2.0 | 2026-08-10 | MOD-makefile(ビルド・導入・運用ターゲット)の受入基準⇄テスト対応 |
| [portsync](portsync.md) | MOD-portsync | 0 / **1** / 0 | 1.1.0 | 2026-08-07 | MOD-portsync(DooD 経路のポート同期)の受入基準⇄テスト対応 |
| [strategy](strategy.md) | 全体 | - | 1.5.0 | 2026-08-10 | テストのレベル別実行方法・状態列の語彙・受入基準の配分規約 |
| [vm-mode](vm-mode.md) | MOD-vm-mode | 0 / **8** / 0 | 1.1.0 | 2026-08-07 | MOD-vm-mode(ゲスト VM 内ネイティブ Docker)の受入基準⇄テスト対応 |

件数: 28

<!-- END GENERATED: build-index.py -->

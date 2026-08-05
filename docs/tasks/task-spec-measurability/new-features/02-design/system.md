---
target: docs/02-design/system.md
change: replace
sections:
  - "## モジュール分割定義"
  - "## 要件カバレッジ確認"
deletes: []
reason: >
  決定シート概念#2・#6 の裁定で NFR-sec-02 と NFR-ops-01 を 01 から削除するため、
  モジュール分割定義の「対応要件」列と要件カバレッジ確認の該当2行から両 ID を外す
  (実在しない要件 ID を 02 が指したままにしない)。責務・分割・割り当ては変えない。
---

<!-- 変更したのは次の6箇所だけである(責務欄・依存欄・詳細設計欄・接頭辞欄は無変更)。
     - モジュール分割定義: `MOD-firewall` から `NFR-sec-02` を外す /
       `MOD-vm-mode`・`MOD-hooks`・`MOD-container-tools` から `NFR-ops-01` を外す
     - 要件カバレッジ確認: `NFR-sec-02` の行と `NFR-ops-01` の行を削除する

     **`MOD-container-tools` は `NFR-ops-01` を外しても `FR-env-01` と `SR-20` が残る**ので、
     要件の裏付けを失うモジュールは1つも無い(`relations-query.py --requirement NFR-ops-01` の
     5機能すべてが他の FR も根拠に持つことを 2026-08-05 に実測した)。
     `MOD-vm-mode` の責務欄にある「資源逼迫」は用語集が閾値付きで定義した語なので測定不能語では
     なくなっており、書き替えない。 -->

## モジュール分割定義

<!-- 29モジュール。CLI はサブコマンド単位で1モジュール(決定シート 論点3)。
     機能(relations)は83本で、その境界は docs/03-impl/features.md が持つ。 -->

| モジュールID | 責務 | 対応要件 | 依存 | 詳細設計 | relations の接頭辞 |
|---|---|---|---|---|---|
| MOD-cli-common | ホスト CLI の共有基盤。コンテナ名の導出、稼働・存在・イメージの判定、インフラ(ネットワーク・共有ボリューム)の用意、SSH 鍵の選択と保存、noVNC URL の組み立て、実行ユーザの解決、**共有資源を触る6コマンドの排他ロックの取得・解放・残骸の引き継ぎ**(`D0-env-08` 項6 / `DSN-env-02`) | FR-env-01, FR-env-02, FR-env-03, FR-env-04, FR-env-09, FR-env-10, FR-env-11, NFR-ops-02, NFR-ops-03, NFR-scale-01, SR-01, SR-10, SR-11, SR-12, SR-20 | — | なし | `MODULE-cli-common-*` |
| MOD-cli-setup | イメージをビルドし、ネットワークと共有ボリュームを作る初回セットアップ | FR-env-01, FR-env-09, SR-01 | MOD-cli-common | なし | `MODULE-cli-setup` |
| MOD-cli-start | 開発コンテナの起動(既定はブラウザ確認あり)。再接続・VM モード・認証受け渡し・鍵転送・ポート割当を含む | FR-env-01〜08, FR-env-11, FR-env-12, NFR-avail-02, NFR-scale-01, NFR-sec-01, NFR-ops-02, SR-04, SR-14, SR-20 | MOD-cli-common | なし | `MODULE-cli-start` |
| MOD-cli-stop | セッションの停止と compose 生成物の片付け。遊休なら docker-proxy と SSH ブリッジも停止する | FR-env-01, FR-env-07, NFR-ops-02, SR-20 | MOD-cli-common | なし | `MODULE-cli-stop` |
| MOD-cli-attach | 実行中コンテナの tmux セッションへ接続する | FR-env-01, NFR-ops-02, SR-20 | MOD-cli-common | なし | `MODULE-cli-attach` |
| MOD-cli-code | 新しい tmux ウィンドウで Claude Code を起動する | FR-env-01, FR-env-08, FR-env-12, NFR-ops-02, SR-20 | MOD-cli-common | なし | `MODULE-cli-code` |
| MOD-cli-list | 実行中セッションの一覧と noVNC URL を表示する | FR-env-01, FR-env-11, NFR-ops-02, SR-20 | MOD-cli-common | なし | `MODULE-cli-list` |
| MOD-cli-login | Claude の OAuth ログインをコンテナ内で実行し共有ボリュームへ保存する | FR-env-03, NFR-ops-02, SR-03, SR-15, SR-20 | MOD-cli-common | なし | `MODULE-cli-login` |
| MOD-cli-login-codex | Codex のデバイス認証を実行し共有ボリュームの `codex/` へ保存する | FR-env-03, FR-env-12, NFR-scale-02, NFR-ops-02, SR-03, SR-15, SR-20 | MOD-cli-common | なし | `MODULE-cli-login-codex` |
| MOD-cli-logout | Claude と Codex の認証情報を共有ボリュームごと削除する | FR-env-03, NFR-scale-02, NFR-ops-02, SR-20 | MOD-cli-common | なし | `MODULE-cli-logout` |
| MOD-cli-forward | 指定ポートのホスト側フォワードを動的に追加する | FR-env-06, NFR-scale-01, NFR-ops-02, SR-20 | MOD-cli-common | なし | `MODULE-cli-forward` |
| MOD-cli-unforward | 指定ポートのフォワードを解除する | FR-env-06, NFR-ops-02, SR-20 | MOD-cli-common | なし | `MODULE-cli-unforward` |
| MOD-cli-ports | フォワード一覧と noVNC URL を表示する | FR-env-06, FR-env-11, NFR-ops-02, SR-20 | MOD-cli-common | なし | `MODULE-cli-ports` |
| MOD-cli-ssh-keys | 使う SSH 鍵の対話選択・保存・初期化(`select` / `reset` のディスパッチを含む) | FR-env-04, NFR-ops-02, SR-20 | MOD-cli-common | なし | `MODULE-cli-ssh-keys*` |
| MOD-cli-firewall | コンテナ内のファイアウォールルールを表示する | FR-env-05, NFR-ops-02, SR-20 | MOD-cli-common | なし | `MODULE-cli-firewall` |
| MOD-cli-orchestrate | コンテナ内で orchestrator を起動する(ゴール指定・`--fresh` 対応、未起動時の自動起動) | FR-orch-01, FR-orch-02, NFR-avail-01, NFR-ops-02, SR-20 | MOD-cli-common | なし | `MODULE-cli-orchestrate` |
| MOD-cli-pull | GHCR からビルド済みイメージを取得して以降の判定名へ付け替える | FR-env-09, NFR-ops-02, SR-20 | — | なし | `MODULE-cli-pull` |
| MOD-cli-upgrade | 全イメージをキャッシュ無しで再ビルドして更新する | FR-env-01, FR-env-09, NFR-ops-02, SR-20 | — | なし | `MODULE-cli-upgrade` |
| MOD-cli-reset | **管理ラベルを持つ Claude コンテナ**と、**本システムの固定名・固定接頭辞を持つ資源**(`fwd-*` 中継コンテナ / 共有ボリューム / イメージ / docker-proxy / `claude-dev-net`)を削除して初期状態へ戻す。**どちらで識別するかは資源の種類ごとに `CTR-cli-container` の規則A が定める**(管理ラベルを付けるのは Claude コンテナだけである)。**削除対象の列挙は、コンテナ・`fwd-*`・ボリューム・イメージについては実在するものだけを挙げ、共有 docker-proxy と `claude-dev-net` は遊休判定の結果に依存するため候補として常に挙げる**。**共有資源(docker-proxy / `claude-dev-net`)は遊休のときだけ削除し、他が稼働中なら残して「完全な初期化になっていない」ことを表示する**(`D0-env-08` 項2 / `FR-env-01` 受入基準9) | FR-env-01, FR-env-03, NFR-ops-02, SR-20 | MOD-cli-common | なし | `MODULE-cli-reset` |
| MOD-makefile | ビルド・セットアップ・CLI の導入/除去・ログイン・更新・自己検証題材の配置といった入口 | FR-env-01, FR-env-03, FR-env-07, FR-env-09, FR-env-10, FR-env-11, FR-env-12, FR-orch-01, FR-orch-09, NFR-ops-03, SR-10, SR-20, SR-30 | — | なし | `MODULE-makefile-*` |
| MOD-entrypoint | コンテナ起動時の初期化(UID/GID 追従・認証コピー・既定設定の生成/補完・ファイアウォール起動・MCP/VNC/Chrome・tmux・同期ループ・ポート同期の起動) | FR-env-02, FR-env-03, FR-env-05〜08, FR-env-11, FR-env-12, NFR-avail-02, NFR-avail-03, NFR-ops-02, NFR-scale-02, SR-02, SR-20 | MOD-firewall, MOD-portsync, MOD-vm-mode | なし | `MODULE-entrypoint-claude` |
| MOD-firewall | コンテナ内のブラックリスト型ファイアウォールの構成 | FR-env-05, NFR-sec-01, NFR-avail-03, SR-02, SR-20 | — | なし | `MODULE-firewall-init` |
| MOD-docker-proxy | Docker API を検査・書き換えして透過中継する常駐プロキシ | FR-env-07, NFR-sec-01, SR-02, SR-04, SR-21, SR-31 | — | なし | `MODULE-docker-proxy-serve` |
| MOD-portsync | DooD 環境で公開ポートを検出し転送する | FR-env-06, FR-env-07, SR-20 | — | なし | `MODULE-portsync-dood` |
| MOD-vm-mode | ゲスト VM の起動・provision・ポート同期・資源逼迫の監視と操作ヘルパー | FR-env-06, FR-env-08, NFR-avail-03, SR-14, SR-20 | — | なし | `MODULE-vm-mode-*` |
| MOD-orchestrator | 2モードの制御ループ、worker の並列実行と分離、タスク単位の介入、相互レビュー、TUI、通知、状態保全 | FR-orch-01〜FR-orch-08, NFR-perf-03, NFR-avail-01, NFR-avail-03, NFR-sec-03, NFR-ops-04, SR-21, SR-22, SR-31 | — | なし | `MODULE-orchestrator-*` |
| MOD-hooks | エージェントのフックからプロンプトを保存し、通知を送る | FR-orch-07, NFR-sec-03, NFR-avail-03 | — | なし | `MODULE-hooks-*` |
| MOD-container-tools | コンテナ内で利用者が使う補助資産(レート制限の解除待ちなど) | FR-env-01, SR-20 | — | なし | `MODULE-container-tools-*` |
| MOD-sample-project | 自己検証題材の配置と、題材そのもの | FR-orch-09, SR-23 | — | なし | `MODULE-sample-project-*` |

**分割定義に含めないもの**: コンテナイメージの定義(`Dockerfile.*`)と GHCR 配布ワークフローは
モジュールではなく、**イメージの作り方は `03-impl/environments/images.md`、GHCR への公開構成は
`03-impl/infra/local/ghcr.md`** が持つ(理由は `DSN-mod-05`)。

**どのモジュールにも属さない要件(8件)とその担い手**。上の表の「対応要件」に現れないのはこの8件
だけであり、いずれも「振る舞いを実装するモジュール」が原理的に存在しない種類の要件である
(割り当て漏れではない)。下の「要件カバレッジ確認」にも同じ担い手を書く。

| 要件 | 担い手 | なぜモジュールでないか |
|---|---|---|
| NFR-perf-01, NFR-perf-02 | `03-impl/environments/images.md`, `03-impl/infra/local/ghcr.md` | イメージのレイヤー構成とビルド設定が決める性能であり、実行される入口を持たない(`DSN-mod-05`) |
| SR-13(マルチアーキ), SR-24(マルチステージ), SR-33(CI 日次実行) | 同上 | 同上。ビルド・配布の構成そのもの |
| SR-05(信頼できる社内開発用途に限る) | `00-requests/request.md`「やらないこと」2 | 利用の前提条件であり、実装物を持たない |
| SR-32(Bash に自動テストを設けない) | 本書「テスト戦略」`DSN-test-01` | 「作らない」ことの宣言であり、実装物を持たない |
| SR-34(Codex を confinement を緩めずに実行) | `02-design/environments.md`「Codex実行設定」 | 外部エージェントの実行設定であり、製品コードのモジュールではない |

## 要件カバレッジ確認

| 要件 ID | 割り当てモジュール | 備考 |
|---|---|---|
| FR-env-01 | MOD-cli-start, MOD-cli-stop, MOD-cli-attach, MOD-cli-list, MOD-cli-code, MOD-cli-setup, MOD-cli-upgrade, MOD-cli-reset, MOD-cli-common, MOD-makefile, MOD-container-tools | 起動・再接続・停止・一覧 |
| FR-env-02 | MOD-entrypoint, MOD-cli-start, MOD-cli-common | UID/GID 追従は entrypoint が実施 |
| FR-env-03 | MOD-cli-login, MOD-cli-login-codex, MOD-cli-logout, MOD-cli-start, MOD-cli-reset, MOD-cli-common, MOD-entrypoint, MOD-makefile | 保存は CLI、コピーと同期は entrypoint |
| FR-env-04 | MOD-cli-ssh-keys, MOD-cli-start, MOD-cli-common | macOS の TCP ブリッジも同モジュール群 |
| FR-env-05 | MOD-firewall, MOD-entrypoint, MOD-cli-start, MOD-cli-firewall | 適用は firewall、起動は entrypoint、表示は CLI |
| FR-env-06 | MOD-cli-forward, MOD-cli-unforward, MOD-cli-ports, MOD-portsync, MOD-vm-mode, MOD-entrypoint | VM 経路のポート同期は vm-mode |
| FR-env-07 | MOD-docker-proxy, MOD-cli-start, MOD-cli-stop, MOD-portsync, MOD-makefile | compose 名の一意化は start |
| FR-env-08 | MOD-vm-mode, MOD-cli-start, MOD-cli-code, MOD-entrypoint | 起動判定は start、常駐は vm-mode |
| FR-env-09 | MOD-cli-pull, MOD-cli-setup, MOD-cli-upgrade, MOD-cli-common, MOD-makefile | 配布側の構成は `03-impl/infra/local/ghcr.md` |
| FR-env-10 | MOD-makefile(install/uninstall), MOD-cli-common, 各 MOD-cli-*(macOS 実装の相乗り) | `DSN-mod-02` |
| FR-env-11 | MOD-entrypoint, MOD-cli-start, MOD-cli-list, MOD-cli-ports, MOD-cli-common, MOD-makefile | イメージ側の同梱は `03-impl/environments/images.md` |
| FR-env-12 | MOD-entrypoint, MOD-cli-start, MOD-cli-code, MOD-cli-login-codex, MOD-makefile | 同梱そのものは `03-impl/environments/images.md` |
| FR-orch-01 | MOD-orchestrator, MOD-cli-orchestrate, MOD-makefile | |
| FR-orch-02 | MOD-orchestrator, MOD-cli-orchestrate | |
| FR-orch-03 | MOD-orchestrator | worker・worktree・統合 |
| FR-orch-04 | MOD-orchestrator | 介入キューとハンドオフ |
| FR-orch-05 | MOD-orchestrator | 状態の永続化と再開 |
| FR-orch-06 | MOD-orchestrator | レビューと改訂ループ |
| FR-orch-07 | MOD-orchestrator, MOD-hooks | 通知の発信源はコントローラに一本化 |
| FR-orch-08 | MOD-orchestrator | ダッシュボード・端末制御・整形 |
| FR-orch-09 | MOD-sample-project, MOD-makefile, MOD-orchestrator | |
| NFR-perf-01, NFR-perf-02 | (モジュール外)`03-impl/environments/images.md`, `03-impl/infra/local/ghcr.md` | レイヤー構成とビルド設定が担う |
| NFR-perf-03 | MOD-orchestrator | worker の割り当て粒度と文脈の絞り込み |
| NFR-avail-01 | MOD-orchestrator, MOD-cli-orchestrate | |
| NFR-avail-02 | MOD-cli-start, MOD-entrypoint | |
| NFR-avail-03 | MOD-entrypoint, MOD-firewall, MOD-orchestrator, MOD-hooks, MOD-vm-mode | 補助機能の失敗を主機能へ波及させない |
| NFR-sec-01 | MOD-docker-proxy, MOD-firewall, MOD-cli-start, MOD-cli-common | |
| NFR-sec-03 | MOD-orchestrator, MOD-hooks | |
| NFR-ops-02 | MOD-cli-common, 各 MOD-cli-*, MOD-entrypoint | OS 依存をホスト CLI に閉じる |
| NFR-ops-03 | MOD-makefile, MOD-cli-common | `make help` と CLI のヘルプ |
| NFR-ops-04 | MOD-orchestrator | |
| NFR-scale-01 | MOD-cli-start, MOD-cli-common, MOD-cli-forward | 命名・ポート割当・プロファイル分離 |
| NFR-scale-02 | MOD-cli-login-codex, MOD-cli-logout, MOD-entrypoint | |

**システム要件(`SR-nn`)の割り当て**。SR は「システムが満たす振る舞い」ではなく**技術前提と制約**
であるため、モジュールが実装するとは限らない。担い手がモジュールでないものは、その制約を保持する
02 のドキュメントを担い手として書く(空欄を作らないための規約)。

| 要件 ID | 割り当てモジュール / 担い手 | 備考 |
|---|---|---|
| SR-01 | MOD-cli-common, MOD-cli-setup | 前提コマンドの検査とインフラ作成が Docker の存在に依存する |
| SR-02 | MOD-entrypoint, MOD-firewall, MOD-docker-proxy, (モジュール外)`03-impl/environments/images.md` | OS 依存はホスト CLI 側に閉じる(`DSN-mod-02`) |
| SR-03 | MOD-cli-login, MOD-cli-login-codex, MOD-cli-common, (モジュール外)`03-impl/environments/images.md` | 認証は共有ボリューム経由のみ。イメージへ焼き込まない |
| SR-04 | MOD-cli-start, MOD-docker-proxy, (担い手)`02-design/environments.md`「Codex実行設定」 | `--security-opt` を付けない=既定の confinement を維持する |
| SR-05 | (担い手)`00-requests/request.md`「やらないこと」2 | 利用前提。設計上の実装物を持たない |
| SR-10 | MOD-cli-common, MOD-makefile | 前提コマンド検査と `make setup` の対象環境 |
| SR-11 | MOD-cli-common | Docker API の版に依存する判定を持つ |
| SR-12 | MOD-cli-common | 不足コマンドを列挙して導入方法を案内する |
| SR-13 | (モジュール外)`03-impl/infra/local/ghcr.md` | マルチアーキ配布は CI が担う(`DSN-mod-05`) |
| SR-14 | MOD-vm-mode, MOD-cli-start | `/dev/kvm` の有無で分岐する。macOS では提供しない |
| SR-15 | MOD-cli-login, MOD-cli-login-codex | 認証方式の選択そのもの |
| SR-20 | MOD-cli-common, 各 MOD-cli-*, MOD-makefile, MOD-portsync, MOD-vm-mode, MOD-entrypoint, MOD-firewall, MOD-container-tools | Bash 実装のモジュール群 |
| SR-21 | MOD-docker-proxy, MOD-orchestrator | Go 実装の2モジュール |
| SR-22 | MOD-orchestrator | TUI のみ外部依存を許容し vendor へ同梱する |
| SR-23 | MOD-sample-project | Python + pytest の自己検証題材 |
| SR-24 | (モジュール外)`03-impl/environments/images.md` | マルチステージと終端レイヤー(`DSN-dist-01` / `DSN-mod-05`) |
| SR-30 | MOD-makefile | 単一の入口 |
| SR-31 | MOD-docker-proxy, MOD-orchestrator | 実コマンドは `environments.md` が正 |
| SR-32 | (担い手)本書「テスト戦略」`DSN-test-01` | 自動テストを設けないという明示的な割り切り |
| SR-33 | (モジュール外)`03-impl/infra/local/ghcr.md` | GitHub Actions の日次実行 |
| SR-34 | (担い手)`02-design/environments.md`「Codex実行設定」 | legacy landlock で confinement を緩めずに実行する |

**要件を持たないモジュールは無い**(全 29 モジュールが上表のいずれかに現れる)。
**割り当て先の無い要件も無い**(FR 21 件・NFR 13 件・SR 21 件がすべて上の3表に現れる)。

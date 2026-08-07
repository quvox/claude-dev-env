---
target: docs/02-design/system.md
change: replace
sections:
  - "## モジュール分割定義"
  - "## 分割の根拠"
  - "## 要件カバレッジ確認"
  - "### 結合テスト対象"
  - "### E2Eシナリオ一覧"
deletes: []
reason: '`FR-env-01` に条項6件、`FR-env-07` に条項2件を追加したことを 02 側へ降ろす。(1) 要件カバレッジ表に8行を追加する — `FR-env-01-22`/`23`/`26`/`27` は `MOD-cli-stop`、`FR-env-01-25` は `MOD-cli-reset`、`FR-env-01-24` は `MOD-cli-stop`、`FR-env-07-11`/`12` は `MOD-docker-proxy` を主担当とし、いずれも 充足=`完全`、根拠は `DSN-env-04`(`FR-env-01-24` と `FR-env-01-27` と `FR-env-07-12` は設計判断を要さない/`DSN-dp-01`)。**1条項1主担当の規則を守り、既存行は1つも動かさない**。あわせて表下の注記の条項数を 201 → 209 に更新する。(2) 結合テスト対象の `CTR-cli-container`(破壊的操作の対象の識別)の行に、**発行側として `MOD-docker-proxy` が加わった**ことを書く(所有者ラベルはホスト CLI ではなく docker-proxy が付けるため、発行側が2つになる)。`CTR-docker-api` の行に、ラベル注入は `go test` で機械検証できることを書く。(3) E2E-01 のシナリオに「セッション内から `docker run` で作ったコンテナと `docker network create` で作ったネットワークが `stop` で消え、削除した名前が表示されること」を、E2E-03 に「作成要求へ所有者ラベルが付与されること」を足す(`FR-env-01-22`〜`27` / `FR-env-07-11`・`12` の実機確認の担い手)。(4) **`/doc-check`(2026-08-07)の独立レビュー3本の指摘により「## モジュール分割定義」を影響範囲に加えた** — 3行が合成ビューで古くなる: `MOD-cli-stop` の責務が「compose 生成物の片付け」に限られている(セッション由来の資源へ広がった)/ `MOD-docker-proxy` の責務に所有者ラベルの注入が無い/ `MOD-cli-reset` の責務がセッション由来の資源を挙げず、括弧書き「管理ラベルを付けるのは Claude コンテナだけである」が**事実として偽になり**、同じ 02 層の `DSN-env-01`(改訂後)と正面から食い違う。この表は `D0-scope-01` のガードレールが「モジュールの一覧はここが正本」と定めるものなので、正本側が古いまま反映されると 02 の中に2つの答えが残る。**行の追加・削除は無く、責務欄だけを直した**(モジュール数 29 と依存欄は不変なので `CS4` に触れない)。(5) 同じ指摘により、`FR-env-01-26` / `FR-env-01-27` の根拠欄に **`reset` 側の担い手が `MOD-cli-reset` であること**を書いた(両条項は `stop` と `reset` の双方に掛かるが主担当は1つなので、根拠欄で辿れるようにする。1条項1主担当の規則は変えない)。(6) **規範の更新(`.claude/directions/delegation.md` §3.1・検査 CS19)により「## 分割の根拠」を影響範囲に加えた** — モジュール分割定義を触る変更は、その根拠を全件読み直すことが要求される。6件(`DSN-mod-01`〜`06`)を読み直した結果、**6件とも継続**で文面を1文字も変えない: 本タスクはモジュールを増やさず(29 本のまま)、境界も動かさず、`MOD-docker-proxy` の責務が1つ増えただけだからである。とくに `DSN-mod-04`(共有するものとプロジェクト単位のものを分ける)は「docker-proxy は全 Claude コンテナで共有する」と述べており、**所有者ラベルの注入は共有された1つの docker-proxy が行い、ラベルの値でプロジェクトを見分ける**ので、この判断の前提を崩さない(崩れるのは、プロジェクトごとに docker-proxy を立てる必要が出たときである)'
reflected: 2026-08-07
---

## モジュール分割定義

<!-- 29モジュール。CLI はサブコマンド単位で1モジュール(決定シート 論点3)。
     機能(relations)は83本で、その境界は docs/03-impl/features.md が持つ。 -->

| モジュールID | 責務 | 対応要件 | 依存 | 詳細設計 | relations の接頭辞 |
|---|---|---|---|---|---|
| MOD-cli-common | ホスト CLI の共有基盤。コンテナ名の導出、稼働・存在・イメージの判定、インフラ(ネットワーク・共有ボリューム)の用意、SSH 鍵の選択と保存、noVNC URL の組み立て、実行ユーザの解決、**共有資源を触る6コマンドの排他ロックの取得・解放・残骸の引き継ぎ**(`D0-env-08` 項6 / `DSN-env-02`) | FR-env-01, FR-env-02, FR-env-03, FR-env-04, FR-env-09, FR-env-10, FR-env-11, NFR-ops-02, NFR-ops-03, NFR-scale-01, SR-01, SR-10, SR-11, SR-12, SR-20 | — | なし | `MODULE-cli-common-*` |
| MOD-cli-setup | イメージをビルドし、ネットワークと共有ボリュームを作る初回セットアップ | FR-env-01, FR-env-09, SR-01 | MOD-cli-common | なし | `MODULE-cli-setup` |
| MOD-cli-start | 開発コンテナの起動(既定はブラウザ確認あり)。再接続・VM モード・認証受け渡し・鍵転送・ポート割当を含む | FR-env-01〜08, FR-env-11, FR-env-12, NFR-avail-02, NFR-scale-01, NFR-sec-01, NFR-ops-02, SR-04, SR-14, SR-20 | MOD-cli-common, MOD-entrypoint | なし | `MODULE-cli-start` |
| MOD-cli-stop | セッションの停止と、**そのセッションが作った資源(セッション由来のコンテナとネットワーク。経路が `docker run` か `docker compose` かを問わない)**の片付け。遊休なら docker-proxy と SSH ブリッジも停止する。**セッション由来の資源は所有者ラベル(`DSN-env-04` の規則 D)で、compose 資源は加えて一意化した compose プロジェクト名(`DSN-env-03`)で引く** | FR-env-01, FR-env-07, NFR-ops-02, SR-20 | MOD-cli-common | なし | `MODULE-cli-stop` |
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
| MOD-cli-orchestrate | コンテナ内で orchestrator を起動する(ゴール指定・`--fresh` 対応、未起動時の自動起動) | FR-orch-01, FR-orch-02, NFR-avail-01, NFR-ops-02, SR-20 | MOD-cli-common, MOD-cli-start | なし | `MODULE-cli-orchestrate` |
| MOD-cli-pull | GHCR からビルド済みイメージを取得して以降の判定名へ付け替える | FR-env-09, NFR-ops-02, SR-20 | — | なし | `MODULE-cli-pull` |
| MOD-cli-upgrade | 全イメージをキャッシュ無しで再ビルドして更新する | FR-env-01, FR-env-09, NFR-ops-02, SR-20 | — | なし | `MODULE-cli-upgrade` |
| MOD-cli-reset | **管理ラベルを持つ Claude コンテナ**と、**所有者ラベル `claude-dev.role=spawned` を持つセッション由来のコンテナ・ネットワーク(所有者を問わない)**と、**本システムの固定名・固定接頭辞を持つ資源**(`fwd-*` 中継コンテナ / 共有ボリューム / イメージ / docker-proxy / `claude-dev-net`)を削除して初期状態へ戻す。**どれで識別するかは資源の種類ごとに `CTR-cli-container` の規則 A(管理ラベル)/ 規則 D(所有者ラベル)/ 名前が定める**(**管理ラベルを付けるのは、名前から所有権が読み取れない Claude コンテナとセッション由来の資源の2つだけである。前者はホスト CLI が、後者は docker-proxy が付ける** — `DSN-env-01` / `DSN-env-04`)。**削除対象として何を列挙するかは `logging.md`「破壊的操作の削除対象の確認」が正である**。**共有資源(docker-proxy / `claude-dev-net`)は遊休のときだけ削除し、他が稼働中なら残して「完全な初期化になっていない」ことを表示する**(`D0-env-08` 項2 / `FR-env-01` 受入基準9) | FR-env-01, FR-env-03, NFR-ops-02, SR-20 | MOD-cli-common | なし | `MODULE-cli-reset` |
| MOD-makefile | ビルド・セットアップ・CLI の導入/除去・ログイン・更新・自己検証題材の配置といった入口 | FR-env-01, FR-env-03, FR-env-07, FR-env-09, FR-env-10, FR-env-11, FR-env-12, FR-orch-01, FR-orch-09, NFR-ops-03, SR-10, SR-20, SR-30 | — | なし | `MODULE-makefile-*` |
| MOD-entrypoint | コンテナ起動時の初期化(UID/GID 追従・認証コピー・既定設定の生成/補完・ファイアウォール起動・MCP/VNC/Chrome・tmux・同期ループ・ポート同期の起動) | FR-env-02, FR-env-03, FR-env-05〜08, FR-env-11, FR-env-12, NFR-avail-02, NFR-avail-03, NFR-ops-02, NFR-scale-02, SR-02, SR-20 | MOD-firewall, MOD-portsync, MOD-vm-mode | なし | `MODULE-entrypoint-claude` |
| MOD-firewall | コンテナ内のブラックリスト型ファイアウォールの構成 | FR-env-05, NFR-sec-01, NFR-avail-03, SR-02, SR-20 | — | なし | `MODULE-firewall-init` |
| MOD-docker-proxy | Docker API を検査・書き換えして透過中継する常駐プロキシ。**あわせてコンテナ作成要求とネットワーク作成要求へ所有者ラベルを注入し、セッション由来の資源に「誰が後で片付けてよいか」の印を付ける**(`DSN-env-04`。印を読んで削除するのは `MOD-cli-stop` / `MOD-cli-reset`) | FR-env-07, NFR-sec-01, SR-02, SR-04, SR-21, SR-31 | — | なし | `MODULE-docker-proxy-serve` |
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

<!-- 受入基準の**条項ごと**に行を作る(要件ごとではない)。充足の語彙・主担当の規則の正は
     .claude/directions/02-design.md。03 のテスト対応表の「状態」列とは別の列・別の意味。 -->

**`充足` はこの設計がその条項を覆っているか**を言う(4値: `完全` / `部分(P-nn)` / `対象外(理由)` / `-`)。
**実装の達成度・検証状態はここでは言わない** — それは `03-impl/tests/` の各対応表の「状態」列が持つ。
1条項につき主担当モジュールはちょうど1つで、`充足` はその行にだけ書く(非機能要件は条項に分けず
1要件1行。`SR-*` は技術前提であり充足は適用外 = `-`)。

| 受入基準 ID | 割り当てモジュール | 充足 | 根拠 |
|---|---|---|---|
| FR-env-01-1 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-01-2 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-01-3 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-01-4 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-01-5 | MOD-cli-list | 完全 | -(設計判断を要さない) |
| FR-env-01-6 | MOD-cli-stop | 完全 | DSN-env-03 |
| FR-env-01-7 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-01-8 | MOD-cli-stop | 完全 | -(設計判断を要さない) |
| FR-env-01-9 | MOD-cli-stop | 完全 | DSN-env-01 |
| FR-env-01-10 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-01-11 | MOD-cli-stop | 完全 | -(設計判断を要さない) |
| FR-env-01-12 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-01-13 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-01-14 | MOD-cli-start | 完全 | DSN-env-01 |
| FR-env-01-15 | MOD-cli-stop | 完全 | DSN-env-01 |
| FR-env-01-16 | MOD-cli-common | 完全 | DSN-env-02 |
| FR-env-01-17 | MOD-cli-common | 完全 | DSN-env-02 |
| FR-env-01-18 | MOD-cli-stop | 完全 | DSN-env-02 |
| FR-env-01-19 | MOD-cli-stop | 部分(P-005) | compose 名の一意化(`DSN-env-03`)で実現するが、ハッシュ先頭6桁の衝突は検出しない設計であり、衝突した2ディレクトリでは一方の `stop` が他方の compose 資源を削除しうる |
| FR-env-01-20 | MOD-cli-stop | 完全 | DSN-env-03 |
| FR-env-01-21 | MOD-cli-stop | 完全 | DSN-env-03 |
| FR-env-01-22 | MOD-cli-stop | 完全 | DSN-env-04 |
| FR-env-01-23 | MOD-cli-stop | 完全 | DSN-env-04 |
| FR-env-01-24 | MOD-cli-stop | 完全 | -(設計判断を要さない) |
| FR-env-01-25 | MOD-cli-reset | 完全 | DSN-env-04 |
| FR-env-01-26 | MOD-cli-stop | 完全 | DSN-env-04。**本条項は `stop` と `reset` の双方に掛かるが、主担当は1つなので `reset` 側の担い手は `MOD-cli-reset`(`FR-env-01-25` の行が持つ)である** |
| FR-env-01-27 | MOD-cli-stop | 完全 | -(設計判断を要さない)。**`reset` 側の担い手は `FR-env-01-26` の根拠欄と同じ** |
| FR-env-02-1 | MOD-entrypoint | 完全 | -(設計判断を要さない) |
| FR-env-02-2 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-02-3 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-02-4 | MOD-entrypoint | 完全 | -(設計判断を要さない) |
| FR-env-02-5 | MOD-entrypoint | 完全 | -(設計判断を要さない) |
| FR-env-02-6 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-03-1 | MOD-cli-login | 完全 | -(設計判断を要さない) |
| FR-env-03-2 | MOD-cli-start | 完全 | DSN-auth-01 |
| FR-env-03-3 | MOD-entrypoint | 完全 | DSN-auth-01 |
| FR-env-03-4 | MOD-entrypoint | 完全 | -(設計判断を要さない) |
| FR-env-03-5 | MOD-cli-logout | 完全 | DSN-env-01 |
| FR-env-03-6 | MOD-cli-login-codex | 完全 | -(設計判断を要さない) |
| FR-env-03-7 | MOD-cli-start | 完全 | DSN-auth-01 |
| FR-env-03-8 | MOD-entrypoint | 完全 | DSN-auth-01 |
| FR-env-03-9 | MOD-entrypoint | 完全 | -(設計判断を要さない) |
| FR-env-03-10 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-03-11 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-03-12 | MOD-cli-login | 完全 | -(設計判断を要さない) |
| FR-env-03-13 | MOD-cli-login-codex | 完全 | -(設計判断を要さない) |
| FR-env-03-14 | MOD-cli-logout | 完全 | -(設計判断を要さない) |
| FR-env-03-15 | MOD-cli-logout | 完全 | -(設計判断を要さない) |
| FR-env-03-16 | MOD-cli-logout | 完全 | -(設計判断を要さない) |
| FR-env-03-17 | MOD-cli-logout | 完全 | DSN-env-01 |
| FR-env-03-18 | MOD-cli-logout | 完全 | -(設計判断を要さない) |
| FR-env-03-19 | MOD-cli-logout | 完全 | -(設計判断を要さない) |
| FR-env-03-20 | MOD-cli-logout | 完全 | -(設計判断を要さない) |
| FR-env-03-21 | MOD-cli-logout | 完全 | -(設計判断を要さない) |
| FR-env-03-22 | MOD-cli-logout | 完全 | -(設計判断を要さない) |
| FR-env-03-23 | MOD-cli-logout | 完全 | -(設計判断を要さない) |
| FR-env-04-1 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-04-2 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-04-3 | MOD-cli-ssh-keys | 完全 | -(設計判断を要さない) |
| FR-env-04-4 | MOD-cli-ssh-keys | 完全 | -(設計判断を要さない) |
| FR-env-04-5 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-04-6 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-04-7 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-05-1 | MOD-entrypoint | 完全 | -(設計判断を要さない) |
| FR-env-05-2 | MOD-cli-common | 完全 | -(設計判断を要さない) |
| FR-env-05-3 | MOD-firewall | 完全 | -(設計判断を要さない) |
| FR-env-05-4 | MOD-firewall | 完全 | -(設計判断を要さない) |
| FR-env-05-5 | MOD-entrypoint | 完全 | DSN-fw-01 |
| FR-env-05-6 | MOD-firewall | 完全 | -(設計判断を要さない) |
| FR-env-05-7 | MOD-firewall | 完全 | -(設計判断を要さない) |
| FR-env-06-1 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-06-2 | MOD-cli-forward | 完全 | -(設計判断を要さない) |
| FR-env-06-3 | MOD-cli-unforward | 完全 | -(設計判断を要さない) |
| FR-env-06-4 | MOD-cli-ports | 完全 | -(設計判断を要さない) |
| FR-env-06-5 | MOD-cli-forward | 完全 | -(設計判断を要さない) |
| FR-env-06-6 | MOD-cli-forward | 完全 | -(設計判断を要さない) |
| FR-env-06-7 | MOD-cli-forward | 完全 | -(設計判断を要さない) |
| FR-env-06-8 | MOD-cli-forward | 完全 | -(設計判断を要さない) |
| FR-env-06-9 | MOD-cli-forward | 完全 | -(設計判断を要さない) |
| FR-env-06-10 | MOD-cli-forward | 完全 | -(設計判断を要さない) |
| FR-env-06-11 | MOD-cli-forward | 完全 | -(設計判断を要さない) |
| FR-env-06-12 | MOD-cli-unforward | 完全 | -(設計判断を要さない) |
| FR-env-06-13 | MOD-cli-forward | 完全 | -(設計判断を要さない) |
| FR-env-07-1 | MOD-cli-start | 完全 | DSN-arch-01 |
| FR-env-07-2 | MOD-docker-proxy | 完全 | -(設計判断を要さない) |
| FR-env-07-3 | MOD-docker-proxy | 完全 | -(設計判断を要さない) |
| FR-env-07-4 | MOD-cli-common | 完全 | -(設計判断を要さない) |
| FR-env-07-5 | MOD-cli-start | 部分(P-005) | 一意化(`DSN-env-03` = `FR-env-01-19` と同じ機構)で実現するが、ハッシュ先頭6桁の衝突時は名前が一意にならない(衝突検出を設計しない) |
| FR-env-07-6 | MOD-docker-proxy | 完全 | DSN-dp-02 |
| FR-env-07-7 | MOD-docker-proxy | 完全 | DSN-dp-01 |
| FR-env-07-8 | MOD-docker-proxy | 完全 | DSN-dp-01 |
| FR-env-07-9 | MOD-docker-proxy | 完全 | -(設計判断を要さない) |
| FR-env-07-10 | MOD-docker-proxy | 完全 | -(設計判断を要さない) |
| FR-env-07-11 | MOD-docker-proxy | 完全 | DSN-env-04 |
| FR-env-07-12 | MOD-docker-proxy | 完全 | DSN-dp-01(判定できない入力は通す。`DSN-env-04` がこの倒し方を採る) |
| FR-env-08-1 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-08-2 | MOD-entrypoint | 完全 | -(設計判断を要さない) |
| FR-env-08-3 | MOD-entrypoint | 完全 | -(設計判断を要さない) |
| FR-env-08-4 | MOD-vm-mode | 完全 | -(設計判断を要さない) |
| FR-env-08-5 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-08-6 | MOD-vm-mode | 完全 | -(設計判断を要さない) |
| FR-env-08-7 | MOD-vm-mode | 完全 | -(設計判断を要さない) |
| FR-env-08-8 | MOD-vm-mode | 完全 | -(設計判断を要さない) |
| FR-env-09-1 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 完全 | -(設計判断を要さない) |
| FR-env-09-2 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 完全 | -(設計判断を要さない) |
| FR-env-09-3 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 完全 | -(設計判断を要さない) |
| FR-env-09-4 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 完全 | -(設計判断を要さない) |
| FR-env-09-5 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 完全 | -(設計判断を要さない) |
| FR-env-09-6 | MOD-cli-pull | 完全 | -(設計判断を要さない) |
| FR-env-09-7 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 完全 | -(設計判断を要さない) |
| FR-env-09-8 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 完全 | DSN-dist-01 |
| FR-env-09-9 | MOD-cli-pull | 完全 | -(設計判断を要さない) |
| FR-env-09-10 | MOD-cli-pull | 完全 | -(設計判断を要さない) |
| FR-env-09-11 | MOD-cli-pull | 完全 | -(設計判断を要さない) |
| FR-env-10-1 | MOD-makefile | 完全 | -(設計判断を要さない) |
| FR-env-10-2 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-10-3 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 完全 | -(設計判断を要さない) |
| FR-env-10-4 | MOD-cli-common | 完全 | -(設計判断を要さない) |
| FR-env-10-5 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-10-6 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-11-1 | MOD-entrypoint | 完全 | -(設計判断を要さない) |
| FR-env-11-2 | MOD-entrypoint | 完全 | -(設計判断を要さない) |
| FR-env-11-3 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 完全 | -(設計判断を要さない) |
| FR-env-11-4 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-11-5 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-11-6 | MOD-cli-start | 完全 | DSN-mod-04 |
| FR-env-11-7 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-11-8 | MOD-cli-common | 完全 | -(設計判断を要さない) |
| FR-env-12-1 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 完全 | DSN-dist-01 |
| FR-env-12-2 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 完全 | -(設計判断を要さない) |
| FR-env-12-3 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 完全 | DSN-dist-01 |
| FR-env-12-4 | MOD-entrypoint | 完全 | DSN-dist-02 |
| FR-env-12-5 | MOD-entrypoint | 完全 | DSN-dist-02 |
| FR-env-12-6 | MOD-entrypoint | 完全 | DSN-dist-02 |
| FR-env-12-7 | MOD-cli-start | 完全 | DSN-dist-02 |
| FR-env-12-8 | MOD-entrypoint | 完全 | DSN-dist-02 |
| FR-env-12-9 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 完全 | DSN-dist-02 |
| FR-env-12-10 | MOD-entrypoint | 完全 | DSN-dist-02 |
| FR-env-12-11 | MOD-entrypoint | 完全 | DSN-dist-02 |
| FR-env-12-12 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 対象外(オーケストレーターが codex を worker/レビューアーとして常用するかは未決で、01 自身が本要件の対象外と定める) | D0-orch-17 |
| FR-orch-01-1 | MOD-cli-orchestrate | 完全 | -(設計判断を要さない) |
| FR-orch-01-2 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-01-3 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-01-4 | MOD-orchestrator | 完全 | DSN-arch-02 |
| FR-orch-01-5 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-01-6 | MOD-orchestrator | 完全 | DSN-ui-01 |
| FR-orch-01-7 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-02-1 | MOD-orchestrator | 完全 | DSN-orch-01 |
| FR-orch-02-2 | MOD-orchestrator | 完全 | DSN-orch-02 |
| FR-orch-02-3 | MOD-orchestrator | 完全 | DSN-prompt-03 |
| FR-orch-02-4 | MOD-cli-orchestrate | 完全 | DSN-orch-02 |
| FR-orch-02-5 | MOD-cli-orchestrate | 完全 | -(設計判断を要さない) |
| FR-orch-03-1 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-03-2 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-03-3 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-03-4 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-03-5 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-03-6 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-03-7 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-03-8 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-03-9 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-03-10 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-03-11 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-04-1 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-04-2 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-04-3 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-04-4 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-04-5 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-04-6 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-04-7 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-04-8 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-04-9 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-05-1 | MOD-orchestrator | 完全 | DSN-log-02 |
| FR-orch-05-2 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-05-3 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-05-4 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-05-5 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-05-6 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-05-7 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-05-8 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-05-9 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-05-10 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-06-1 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-06-2 | MOD-orchestrator | 完全 | DSN-prompt-02 |
| FR-orch-06-3 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-06-4 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-06-5 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-06-6 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-06-7 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-07-1 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-07-2 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-07-3 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-07-4 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-07-5 | MOD-hooks | 完全 | -(設計判断を要さない) |
| FR-orch-07-6 | MOD-hooks | 完全 | -(設計判断を要さない) |
| FR-orch-08-1 | MOD-orchestrator | 完全 | DSN-ui-02 |
| FR-orch-08-2 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-08-3 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-08-4 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-08-5 | MOD-orchestrator | 完全 | DSN-prompt-01 |
| FR-orch-08-6 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-08-7 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-08-8 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-09-1 | MOD-sample-project | 完全 | -(設計判断を要さない) |
| FR-orch-09-2 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| FR-orch-09-3 | MOD-sample-project | 完全 | -(設計判断を要さない) |
| FR-orch-09-4 | MOD-sample-project | 完全 | -(設計判断を要さない) |
| FR-orch-09-5 | MOD-sample-project | 完全 | -(設計判断を要さない) |
| FR-orch-09-6 | MOD-sample-project | 完全 | -(設計判断を要さない) |
| NFR-perf-01 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 完全 | DSN-dist-01 |
| NFR-perf-02 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 完全 | DSN-dist-01 |
| NFR-perf-03 | MOD-orchestrator | 完全 | DSN-prompt-03 |
| NFR-avail-01 | MOD-orchestrator, MOD-cli-orchestrate | 完全 | DSN-orch-02 |
| NFR-avail-02 | MOD-cli-start, MOD-entrypoint | 完全 | -(設計判断を要さない) |
| NFR-avail-03 | MOD-entrypoint, MOD-firewall, MOD-orchestrator, MOD-hooks, MOD-vm-mode | 完全 | DSN-fw-01(ファイアウォール分。他の補助機能の失敗許容は各契約のエラーケースが定める) |
| NFR-sec-01 | MOD-docker-proxy, MOD-firewall, MOD-cli-start, MOD-cli-common | 完全 | DSN-arch-01 |
| NFR-sec-03 | MOD-orchestrator, MOD-hooks | 完全 | -(設計判断を要さない) |
| NFR-ops-02 | MOD-cli-common, 各 MOD-cli-*, MOD-entrypoint | 完全 | DSN-arch-01 |
| NFR-ops-03 | MOD-makefile, MOD-cli-common | 完全 | -(設計判断を要さない) |
| NFR-ops-04 | MOD-orchestrator | 完全 | -(設計判断を要さない) |
| NFR-scale-01 | MOD-cli-start, MOD-cli-common, MOD-cli-forward | 完全 | DSN-env-03 |
| NFR-scale-02 | MOD-cli-login-codex, MOD-cli-logout, MOD-entrypoint | 完全 | DSN-auth-01 |
| SR-01 | MOD-cli-common, MOD-cli-setup | - | SR-01(技術前提。充足は適用外)。前提コマンドの検査とインフラ作成が Docker の存在に依存する |
| SR-02 | MOD-entrypoint, MOD-firewall, MOD-docker-proxy, (モジュール外)`03-impl/environments/images.md` | - | SR-02(技術前提。充足は適用外)。OS 依存はホスト CLI 側に閉じる(`DSN-mod-02`) |
| SR-03 | MOD-cli-login, MOD-cli-login-codex, MOD-cli-common, (モジュール外)`03-impl/environments/images.md` | - | SR-03(技術前提。充足は適用外)。認証は共有ボリューム経由のみ。イメージへ焼き込まない |
| SR-04 | MOD-cli-start, MOD-docker-proxy, (担い手)`02-design/environments.md`「Codex実行設定」 | - | SR-04(技術前提。充足は適用外)。`--security-opt` を付けない=既定の confinement を維持する |
| SR-05 | (担い手)`00-requests/request.md`「やらないこと」2 | - | SR-05(技術前提。充足は適用外)。利用前提。設計上の実装物を持たない |
| SR-10 | MOD-cli-common, MOD-makefile | - | SR-10(技術前提。充足は適用外)。前提コマンド検査と `make setup` の対象環境 |
| SR-11 | MOD-cli-common | - | SR-11(技術前提。充足は適用外)。Docker API の版に依存する判定を持つ |
| SR-12 | MOD-cli-common | - | SR-12(技術前提。充足は適用外)。不足コマンドを列挙して導入方法を案内する |
| SR-13 | (モジュール外)`03-impl/infra/local/ghcr.md` | - | SR-13(技術前提。充足は適用外)。マルチアーキ配布は CI が担う(`DSN-mod-05`) |
| SR-14 | MOD-vm-mode, MOD-cli-start | - | SR-14(技術前提。充足は適用外)。`/dev/kvm` の有無で分岐する。macOS では提供しない |
| SR-15 | MOD-cli-login, MOD-cli-login-codex | - | SR-15(技術前提。充足は適用外)。認証方式の選択そのもの |
| SR-20 | MOD-cli-common, 各 MOD-cli-*, MOD-makefile, MOD-portsync, MOD-vm-mode, MOD-entrypoint, MOD-firewall, MOD-container-tools | - | SR-20(技術前提。充足は適用外)。Bash 実装のモジュール群 |
| SR-21 | MOD-docker-proxy, MOD-orchestrator | - | SR-21(技術前提。充足は適用外)。Go 実装の2モジュール |
| SR-22 | MOD-orchestrator | - | SR-22(技術前提。充足は適用外)。TUI のみ外部依存を許容し vendor へ同梱する |
| SR-23 | MOD-sample-project | - | SR-23(技術前提。充足は適用外)。Python + pytest の自己検証題材 |
| SR-24 | (モジュール外)`03-impl/environments/images.md` | - | SR-24(技術前提。充足は適用外)。マルチステージと終端レイヤー(`DSN-dist-01` / `DSN-mod-05`) |
| SR-30 | MOD-makefile | - | SR-30(技術前提。充足は適用外)。単一の入口 |
| SR-31 | MOD-docker-proxy, MOD-orchestrator | - | SR-31(技術前提。充足は適用外)。実コマンドは `environments.md` が正 |
| SR-32 | (担い手)本書「テスト戦略」`DSN-test-01` | - | SR-32(技術前提。充足は適用外)。自動テストを設けないという明示的な割り切り |
| SR-33 | (モジュール外)`03-impl/infra/local/ghcr.md` | - | SR-33(技術前提。充足は適用外)。GitHub Actions の日次実行 |
| SR-34 | (担い手)`02-design/environments.md`「Codex実行設定」 | - | SR-34(技術前提。充足は適用外)。legacy landlock で confinement を緩めずに実行する |

**システム要件(`SR-nn`)の行**について: SR は「システムが満たす振る舞い」ではなく**技術前提と制約**
であるため充足を持たない(`充足` = `-`。`.claude/directions/01-requirements.md` が定める)。
担い手がモジュールでないものは、その制約を保持する 02 のドキュメントを担い手として書く
(空欄を作らないための規約)。

**要件を持たないモジュールは無い**(全 29 モジュールが「モジュール分割定義」の対応要件と上表の
いずれかに現れる)。**割り当て先の無い条項も無い**(機能要件の全 209 条項・NFR 13 件・SR 21 件が
すべて上表に現れる)。

### 結合テスト対象

| 契約 ID | 契約の当事者 | テストを持つ責任モジュール |
|---|---|---|
| CTR-cli-container(**起動側**) | MOD-cli-start → MOD-entrypoint | MOD-entrypoint(呼び出し元はシェルで自動テストを持てないため観測側が担当。手段は実機確認) |
| CTR-cli-container(**破壊的操作の対象の識別**) | **発行側は2つある**: MOD-cli-start(Claude コンテナの管理ラベル)と **MOD-docker-proxy(セッション由来の資源の所有者ラベル。`DSN-env-04`)**。→ 読み手は MOD-cli-stop / MOD-cli-logout / MOD-cli-reset | **MOD-cli-stop / MOD-cli-logout / MOD-cli-reset**(読み手が観測側。`D0-env-08`。**発行側がラベルを付けるのをやめると読み手の削除対象が空になる**ため、契約の遵守は読み手の側でしか観測できない)。全モジュールがシェル実装で自動テストを持てないため、手段は**実機確認 = E2E-01**(`FR-env-01` 受入基準 9・14〜27 / `FR-env-03` 受入基準 14〜23)。**発行側が docker-proxy である分だけは Go の単体テストで機械検証できる**が、それは下の `CTR-docker-api` の行が持つ(この行が観測するのは「読み手が正しい集合を消すか」である) |
| CTR-entrypoint-firewall | MOD-entrypoint → MOD-firewall | MOD-entrypoint(手段は実機確認) |
| CTR-docker-api | Claude コンテナ → MOD-docker-proxy | MOD-docker-proxy(観測側。`go test` で機械検証。**所有者ラベルの付与(`FR-env-07` 受入基準11・12)も、要求ボディの変換なので同じ `go test` で検証できる**) |
| CTR-cli-orchestrator | MOD-cli-orchestrate → MOD-orchestrator | MOD-orchestrator(観測側。実 tmux と実エージェントを要するため手段は実機確認=E2E-04 / E2E-05) |
| CTR-orchestrator-prompt | MOD-orchestrator → worker / 対話 Claude | MOD-orchestrator(生成と検知は `go test`。実プロセスとの結合は実機確認=E2E-04) |

**`CTR-cli-container` を2行に分けた理由**: この契約は当事者の異なる2つの取り決めを持つ。
起動時に渡す環境変数・オプション(`MOD-cli-start` → `MOD-entrypoint`)と、
**破壊的操作が削除対象を決めるための管理ラベル・所有者ラベル・遊休判定・ロックキー**
(`MOD-cli-start` と `MOD-docker-proxy` が付け、`MOD-cli-stop` / `-logout` / `-reset` が読む)である。
後者は `MOD-entrypoint` を一切通らないため、1行目の責任モジュールでは観測できない。

### E2Eシナリオ一覧

| E2E ID | 対応 UC | シナリオ | 対象/対象外(理由) |
|---|---|---|---|
| E2E-01 | UC-01 | `claude-dev start`(ブラウザ確認あり / `--no-vnc`)→ `/workspace` マウント・認証・ファイアウォール・tmux → `claude` 起動 → 再実行での再接続。**続けて破壊的操作が「自分が作った資源」にだけ効くことを確認する**: 管理ラベルの付与 / 遊休判定がイメージに依存しないこと / 排他ロックと残骸の引き継ぎ / ラベルを持たない既存コンテナを巻き込まないこと / compose 資源が別プロジェクトを巻き込まないこと / `stop` が受理しない名前 / `logout` がプロジェクト配下の認証コピーを消すこと / 確認と非対話時の中止 / 削除失敗の列挙(`FR-env-01` 受入基準 9・14〜21 / `FR-env-03` 受入基準 14〜23)。**さらにセッション由来の資源の片付けを確認する**(`FR-env-01` 受入基準 22〜27。確認する項目と手順は `03-impl/tests/e2e.md` が持つ) | 対象(Must) |
| E2E-02 | UC-02 | `claude-dev forward` → 8100 番台の割当と SSH トンネル → クライアントのブラウザで表示 → `claude-dev ports` で確認 | 対象(Must) |
| E2E-03 | UC-03 | コンテナ内で危険な `docker run` → 拒否 / `/workspace` bind の許可 / 通常操作の透過。**あわせて、作成されたコンテナとネットワークに所有者ラベルが付いていることを確認する**(`FR-env-07` 受入基準11) | 対象(Must) |
| E2E-04 | UC-04 | `orchestrate` → ブレインストーミング → plan 確定 → worker 並列 → 要判断1件のみ待機・他は継続 → 回答で復帰 → 完了(`make orch-sample` で題材を配置して実走) | 対象(Must) |
| E2E-05 | UC-05 | 実行中に端末を全終了 → `orchestrate` 再実行 → 合流/再開・完了済みの非再実行・plan と履歴の保持 | 対象(Should) |
| E2E-06 | UC-06 | `claude-dev login-codex` → デバイス認証 → 別プロジェクトで `start` → 再ログイン不要で `codex` が起動し、**シェルコマンドが成功して `/workspace` を読み書きできる**。landlock の疎通確認が通り、読み取り専用の明示指定で読み取りが成功する。トークン更新が次のコンテナへ引き継がれる | 対象(Must) |

**全 UC がカバーされている**(UC-01〜UC-06 → E2E-01〜E2E-06)。上流の UC を持たない E2E シナリオは
作らない。

## 分割の根拠

### DSN-mod-01 モジュールは「利用者から見た入口」と1対1にする

- 判断: ホスト CLI をサブコマンド単位で1モジュールに割り、Makefile・スクリプト・Go プログラムも
  それぞれ入口の単位で割る。全 29 モジュール。
- 理由: 変更が起きる単位が入口(サブコマンド・ターゲット・常駐プロセス)であり、影響範囲を
  「どのコマンドが変わるか」で説明できる。旧構成では `cli` が1モジュールで 18 サブコマンドを
  抱えており、`start` の変更と `ports` の変更が同じ影響範囲に見えていた。
- 却下した案: ファイル単位で割る(旧構成) — 1ファイルに 18 の入口が同居し、影響範囲が引けない。
  機能グループ(認証系・ポート系など)で割る — 境界が主観的になり、コードとの1対1が崩れる。

### DSN-mod-02 macOS 実装は同名サブコマンドのモジュールへ相乗りさせる

- 判断: macOS 版(`claude-dev-mac`)を独立モジュール群にせず、同名サブコマンドのモジュールに
  `impl` パスとして相乗りさせる。旧 `cli-mac` モジュールは解体する。
- 理由: `claude-dev-mac` は同じコマンド面の別 OS 実装であり、サブコマンド単位で割ると同一ロジックの
  モジュールが 18 本増えて依存表が読めなくなる。OS 差分は「同じ入口の別実装」として1箇所で
  対比できる方がよい。
- 却下した案: `MOD-cli-mac-*` を 18 本立てる — モジュール数が倍になり、対応要件も重複する。
  旧構成のまま `cli-mac` を1モジュールで残す — `DSN-mod-01` の1対1と矛盾する。

### DSN-mod-03 共有基盤は1モジュールに集約する

- 判断: ホスト CLI の先頭にある定数・ヘルパー関数群を `MOD-cli-common` として独立させる。
- 理由: 全サブコマンドがここへファンインする(実測で 25 関数、最大ファンイン 10)。集約しないと
  18 モジュールが同じ実装パスを重複して持ち、実装とドキュメントの 1 対 1 が崩れる。
- 却下した案: 各サブコマンドのモジュールに複製して書く — 重複により整合検査が落ちる。
  共有基盤を作らず呼び出し関係だけで表す — 境界の無いコードが機能表から漏れる。

### DSN-mod-04 共有するものとプロジェクト単位のものを分ける

- 判断: `docker-proxy` は全 Claude コンテナで共有し、それ以外はプロジェクト単位(またはイメージ単位)
  とする。共有ボリュームは認証・シェル設定・履歴の3本に限る。
- 理由: 共有すると常駐が1つで済む一方、プロジェクト間の干渉が起きうる。干渉が問題になるもの
  (セッション・Chrome プロファイル・運用状態)はプロジェクト単位に置く。
- 却下した案: すべてをプロジェクト単位にする — docker-proxy がプロジェクト数だけ常駐する。
  すべてを共有する — セッションと運用状態が混ざる。

### DSN-mod-05 コールグラフに入口を持たない資産はモジュールにしない

- 判断: コンテナイメージの定義(`Dockerfile.*`)と GHCR 配布ワークフロー(GitHub Actions)は
  モジュール分割定義から外し、`03-impl/environments/`(仕組み)と `03-impl/infra/local/`(構成値)
  に置く。
- 理由: この2つは実行される関数の入口を持たないため、コールグラフに現れない。モジュールとして
  機能表に載せると、機械検査 FT1(入口がコールグラフに存在するか)が重大度「高」で落ち、FT1 は
  落ちると以降の検査を打ち切るゲートであるため、CG1〜CG7 まで含めた機械検査が丸ごと無効になる。
  記述内容は `environments/` と `infra/` が保持するため失われない(`.claude/directions/03-impl.md`
  の「仕組みは environments/、具体的な構成値は infra/」に合致する)。
- 却下した案: モジュールとして残す — 上記のとおり機械検査が無効になる。Dockerfile と GitHub
  Actions のコールグラフ抽出器を作る — このキットの範囲外(`/kit-improve` 案件)。

### DSN-mod-06 モジュールあたりの機能数の上限を超えている2モジュールを許容する

- 判断: `MOD-orchestrator`(19機能)と `MOD-makefile`(19機能)は、1モジュールあたり 15 本という
  分割見直しの目安を超えるが、分割しない。
- 理由: `MOD-orchestrator` は入口が1つ(単一バイナリ)で 219 シンボルを持ち、ファイル境界=責務境界で
  機能へ昇格させた結果が 19 本である。これを1機能に畳むと「1機能=1バイナリ」になり境界が消える。
  逆にモジュールを分けると、単一バイナリが複数モジュールにまたがることになり `DSN-mod-01` の
  1対1が崩れる。`MOD-makefile` も同様に、入口(ターゲット)が 19 個ある単一ファイルである。
- 却下した案: Makefile のターゲットを用途別に束ねる — 束ねた内部に境界が埋没し、記述量は減らない。
  orchestrator を複数モジュールへ割る — 物理配置との1対1が崩れる。

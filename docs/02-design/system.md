---
id: 02-system
version: 2.15.0
updated: 2026-08-19
source:
  - docs/01-requirements/functional.md
  - docs/01-requirements/non-functional.md
  - docs/01-requirements/usecases.md
  - docs/02-design/architecture.md
summary: >
  25モジュールの分割定義とその根拠(DSN-mod-*)、要件カバレッジ確認、テスト戦略(単体/結合/E2E)と
  E2Eシナリオ一覧、UI設計を定める。アーキテクチャと契約と設計判断は architecture.md / contracts/ が持つ。
keywords: [モジュール分割, DSN-mod, テスト戦略, E2E, UI設計, 要件カバレッジ]
verified:
  at: 2026-08-19
  version: 2.15.0
  against:
    - {doc: docs/01-requirements/functional.md, version: 1.19.0}
    - {doc: docs/01-requirements/non-functional.md, version: 1.8.0}
    - {doc: docs/01-requirements/usecases.md, version: 1.7.0}
    - {doc: docs/02-design/architecture.md, version: 1.7.0}
---

# モジュール分割・テスト戦略・UI設計

## モジュール分割定義

<!-- 25モジュール。CLI はサブコマンド単位で1モジュール(決定シート 論点3)。
     機能(relations)は61本で、その境界は docs/03-impl/features.md が持つ。 -->

| モジュールID | 責務 | 対応要件 | 依存 | 詳細設計 | relations の接頭辞 |
|---|---|---|---|---|---|
| MOD-cli-common | ホスト CLI の共有基盤。コンテナ名の導出、稼働・存在・イメージの判定、インフラ(ネットワーク・共有ボリューム)の用意、SSH 鍵の選択と保存、noVNC URL の組み立て、実行ユーザの解決、**共有資源を触る6コマンドの排他ロックの取得・解放・残骸の引き継ぎ**(`D0-env-08` 項6 / `DSN-env-02`)、**compose 一意化名の導出**(`DSN-env-03`)、**管理ラベル `claude-dev.project-dir` の読み取り**、**セッション由来の資源の列挙**(`DSN-env-04`)、**共有資源の遊休判定に使う集合の算出**、**`logout` / `reset` が共有する削除結果の記録と中断の遅延**(`D0-env-08` 項5) | FR-env-01, FR-env-02, FR-env-03, FR-env-04, FR-env-07, FR-env-09, FR-env-10, FR-env-11, NFR-ops-02, NFR-ops-03, NFR-ops-05, NFR-scale-01, SR-01, SR-10, SR-11, SR-12, SR-20 | — | なし | `MODULE-cli-common-*` |
| MOD-cli-setup | イメージをビルドし、ネットワークと共有ボリュームを作る初回セットアップ | FR-env-01, FR-env-09, SR-01, NFR-ops-05 | MOD-cli-common | なし | `MODULE-cli-setup` |
| MOD-cli-start | 開発コンテナの起動(既定はブラウザ確認あり)。再接続・VM モード・認証受け渡し・鍵転送・ポート割当・**プロジェクト環境ファイルの読み取りと環境変数の受け渡し**(`DSN-env-05`)を含む | FR-env-01〜08, FR-env-11, FR-env-12, FR-env-14, NFR-avail-02, NFR-scale-01, NFR-sec-01, NFR-ops-02, SR-04, SR-14, SR-20, NFR-ops-05 | MOD-cli-common, MOD-entrypoint | なし | `MODULE-cli-start` |
| MOD-cli-stop | セッションの停止と、**そのセッションが作った資源(セッション由来のコンテナ・ネットワーク・名前付きボリュームと、それらのコンテナが抱えていた名前無しのボリューム。経路が `docker run` か `docker compose` かを問わない。ボリュームは削除の明示があるときにだけ消し、無ければ残っている名前付きボリュームの名前と削除する方法を表示する)**の片付け。遊休なら docker-proxy と SSH ブリッジも停止する。**セッション由来の資源は所有者ラベル(`DSN-env-04` の規則 D)で、compose 資源は加えて一意化した compose プロジェクト名(`DSN-env-03`)で引く** | FR-env-01, FR-env-07, NFR-ops-02, SR-20, NFR-ops-05 | MOD-cli-common | なし | `MODULE-cli-stop` |
| MOD-cli-attach | 実行中コンテナの tmux セッションへ接続する | FR-env-01, NFR-ops-02, SR-20, NFR-ops-05 | MOD-cli-common | なし | `MODULE-cli-attach` |
| MOD-cli-code | 新しい tmux ウィンドウで Claude Code を起動する | FR-env-01, FR-env-08, FR-env-12, NFR-ops-02, SR-20, NFR-ops-05 | MOD-cli-common | なし | `MODULE-cli-code` |
| MOD-cli-list | 実行中セッションの一覧と noVNC URL を表示する | FR-env-01, FR-env-11, NFR-ops-02, SR-20, NFR-ops-05 | MOD-cli-common | なし | `MODULE-cli-list` |
| MOD-cli-login | Claude の OAuth ログインをコンテナ内で実行し共有ボリュームへ保存する | FR-env-03, NFR-ops-02, SR-03, SR-15, SR-20, NFR-ops-05 | MOD-cli-common | なし | `MODULE-cli-login` |
| MOD-cli-login-codex | Codex のデバイス認証を実行し共有ボリュームの `codex/` へ保存する | FR-env-03, FR-env-12, NFR-scale-02, NFR-ops-02, SR-03, SR-15, SR-20, NFR-ops-05 | MOD-cli-common | なし | `MODULE-cli-login-codex` |
| MOD-cli-logout | Claude と Codex の認証情報を共有ボリュームごと削除する | FR-env-03, NFR-scale-02, NFR-ops-02, SR-20, NFR-ops-05 | MOD-cli-common | なし | `MODULE-cli-logout` |
| MOD-cli-forward | 指定ポートのホスト側フォワードを動的に追加する | FR-env-06, NFR-scale-01, NFR-ops-02, SR-20, NFR-ops-05 | MOD-cli-common | なし | `MODULE-cli-forward` |
| MOD-cli-unforward | 指定ポートのフォワードを解除する | FR-env-06, NFR-ops-02, SR-20, NFR-ops-05 | MOD-cli-common | なし | `MODULE-cli-unforward` |
| MOD-cli-ports | フォワード一覧と noVNC URL を表示する | FR-env-06, FR-env-11, NFR-ops-02, SR-20, NFR-ops-05 | MOD-cli-common | なし | `MODULE-cli-ports` |
| MOD-cli-ssh-keys | 使う SSH 鍵の対話選択・保存・初期化(`select` / `reset` のディスパッチを含む) | FR-env-04, NFR-ops-02, SR-20, NFR-ops-05 | MOD-cli-common | なし | `MODULE-cli-ssh-keys*` |
| MOD-cli-firewall | コンテナ内のファイアウォールルールを表示する | FR-env-05, NFR-ops-02, SR-20, NFR-ops-05 | MOD-cli-common | なし | `MODULE-cli-firewall` |
| MOD-cli-pull | GHCR からビルド済みイメージを取得して以降の判定名へ付け替える | FR-env-09, NFR-ops-02, SR-20, NFR-ops-05 | — | なし | `MODULE-cli-pull` |
| MOD-cli-upgrade | 全イメージをキャッシュ無しで再ビルドして更新する | FR-env-01, FR-env-09, NFR-ops-02, SR-20, NFR-ops-05 | — | なし | `MODULE-cli-upgrade` |
| MOD-cli-reset | **管理ラベルを持つ Claude コンテナ**と、**所有者ラベル `claude-dev.role=spawned` を持つセッション由来のコンテナ・ネットワーク・名前付きボリュームと、それらのコンテナが抱えていた名前無しのボリューム(所有者を問わない。ボリュームは削除の明示があるときだけ)**と、**本システムの固定名・固定接頭辞を持つ資源**(`fwd-*` 中継コンテナ / 共有ボリューム / イメージ / docker-proxy / `claude-dev-net`)を削除して初期状態へ戻す。**どれで識別するかは資源の種類ごとに `CTR-cli-container` の規則 A(管理ラベル)/ 規則 D(所有者ラベル)/ 名前が定める**(**管理ラベルを付けるのは、名前から所有権が読み取れない Claude コンテナとセッション由来の資源の2つだけである。前者はホスト CLI が、後者は docker-proxy が付ける** — `DSN-env-01` / `DSN-env-04`)。**削除対象として何を列挙するかは `logging.md`「破壊的操作の削除対象の確認」が正である**。**共有資源(docker-proxy / `claude-dev-net`)は遊休のときだけ削除し、他が稼働中なら残して「完全な初期化になっていない」ことを表示する**(`D0-env-08` 項2 / `FR-env-01` 受入基準9) | FR-env-01, FR-env-03, NFR-ops-02, SR-20, NFR-ops-05 | MOD-cli-common | なし | `MODULE-cli-reset` |
| MOD-makefile | ビルド・セットアップ・CLI の導入/除去・ログイン・更新といった入口 | FR-env-01, FR-env-03, FR-env-07, FR-env-09, FR-env-10, FR-env-11, FR-env-12, NFR-ops-03, SR-10, SR-20, SR-30 | — | なし | `MODULE-makefile-*` |
| MOD-entrypoint | コンテナ起動時の初期化(UID/GID 追従・認証コピー・既定設定の生成/補完・ファイアウォール起動・MCP/VNC/Chrome・tmux・同期ループ・ポート同期の起動) | FR-env-02, FR-env-03, FR-env-05〜08, FR-env-11, FR-env-12, NFR-avail-02, NFR-avail-03, NFR-ops-02, NFR-ops-05, NFR-scale-02, SR-02, SR-20 | MOD-firewall, MOD-portsync, MOD-vm-mode | なし | `MODULE-entrypoint-claude` |
| MOD-firewall | コンテナ内のブラックリスト型ファイアウォールの構成 | FR-env-05, NFR-sec-01, NFR-avail-03, SR-02, SR-20 | — | なし | `MODULE-firewall-init` |
| MOD-docker-proxy | Docker API を検査・書き換えして透過中継する常駐プロキシ。**あわせてコンテナ作成要求・ネットワーク作成要求・ボリューム作成要求へ所有者ラベルを注入し、セッション由来の資源に「誰が後で片付けてよいか」の印を付ける**(`DSN-env-04`。印を読んで削除するのは `MOD-cli-stop` / `MOD-cli-reset`) | FR-env-07, NFR-sec-01, SR-02, SR-04, SR-21, SR-31 | — | なし | `MODULE-docker-proxy-serve` |
| MOD-portsync | DooD 環境で公開ポートを検出し転送する | FR-env-06, FR-env-07, SR-20 | — | なし | `MODULE-portsync-dood` |
| MOD-vm-mode | ゲスト VM の起動・provision・ポート同期・資源逼迫の監視と操作ヘルパー | FR-env-06, FR-env-08, NFR-avail-03, SR-14, SR-20 | — | なし | `MODULE-vm-mode-*` |
| MOD-container-tools | コンテナ内で利用者が使う補助資産(レート制限の解除待ちなど) | FR-env-01, SR-20 | — | なし | `MODULE-container-tools-*` |

**分割定義に含めないもの**: コンテナイメージの定義(`Dockerfile.*`)と GHCR 配布ワークフローは
モジュールではなく、**イメージの作り方は `03-impl/environments/images.md`、GHCR への公開構成は
`03-impl/infra/local/ghcr.md`** が持つ(理由は `DSN-mod-05`)。

**どのモジュールにも属さない要件(9件)とその担い手**。上の表の「対応要件」に現れないのはこの9件
だけであり、いずれも「振る舞いを実装するモジュール」が原理的に存在しない種類の要件である
(割り当て漏れではない)。下の「要件カバレッジ確認」にも同じ担い手を書く。

| 要件 | 担い手 | なぜモジュールでないか |
|---|---|---|
| NFR-perf-01, NFR-perf-02 | `03-impl/environments/images.md`, `03-impl/infra/local/ghcr.md` | イメージのレイヤー構成とビルド設定が決める性能であり、実行される入口を持たない(`DSN-mod-05`) |
| SR-13(マルチアーキ), SR-24(マルチステージ), SR-33(CI 日次実行) | 同上 | 同上。ビルド・配布の構成そのもの |
| FR-env-13(同梱外部バイナリ) | `03-impl/environments/images.md` | イメージのビルドが同梱物を設置する処理であり、実行される入口を持たない(`DSN-mod-05`)。保守者がビルド前に置いたものをビルドが設置するだけで、利用者が呼ぶコマンドもターゲットも持たない |
| SR-05(信頼できる社内開発用途に限る) | `00-requests/request.md`「やらないこと」2 | 利用の前提条件であり、実装物を持たない |
| SR-32(Bash に自動テストを設けない) | 本書「テスト戦略」`DSN-test-01` | 「作らない」ことの宣言であり、実装物を持たない |
| SR-34(Codex を confinement を緩めずに実行) | `02-design/environments.md`「Codex実行設定」 | 外部エージェントの実行設定であり、製品コードのモジュールではない |

## 分割の根拠

下の `DSN-mod-01`〜`DSN-mod-07` は、**この製品をどのモジュールへ割るか**の判断である。
**2026-08-18 に `FR-env-13`(同梱外部バイナリ)の新設にあたって7件すべてを読み直し、
いずれも継続と判断した**: 同梱外部バイナリの設置はコンテナイメージの定義(`Dockerfile.*`)の
中で完結し、実行される関数の入口を持たない。これは `DSN-mod-05` が
「コールグラフに入口を持たない資産はモジュールにしない」と決めた範囲の内側であり、
**新しいモジュールを立てない**(立てると機械検査 FT1 が重大度「高」で落ちる)。
`DSN-mod-06` / `DSN-mod-07` が扱うモジュールあたりの機能数の目安にも影響しない
(どのモジュールにも機能を足さないため)。

### DSN-mod-01 モジュールは「利用者から見た入口」と1対1にする

- 判断: ホスト CLI をサブコマンド単位で1モジュールに割り、Makefile・スクリプト・Go プログラムも
  それぞれ入口の単位で割る。全 25 モジュール。
- 理由: 変更が起きる単位が入口(サブコマンド・ターゲット・常駐プロセス)であり、影響範囲を
  「どのコマンドが変わるか」で説明できる。旧構成では `cli` が1モジュールで 17 サブコマンドを
  抱えており、`start` の変更と `ports` の変更が同じ影響範囲に見えていた。
- 却下した案: ファイル単位で割る(旧構成) — 1ファイルに 17 の入口が同居し、影響範囲が引けない。
  機能グループ(認証系・ポート系など)で割る — 境界が主観的になり、コードとの1対1が崩れる。

### DSN-mod-02 macOS 実装は同名サブコマンドのモジュールへ相乗りさせる

- 判断: macOS 版(`claude-dev-mac`)を独立モジュール群にせず、同名サブコマンドのモジュールに
  `impl` パスとして相乗りさせる。旧 `cli-mac` モジュールは解体する。
- 理由: `claude-dev-mac` は同じコマンド面の別 OS 実装であり、サブコマンド単位で割ると同一ロジックの
  モジュールが 17 本増えて依存表が読めなくなる。OS 差分は「同じ入口の別実装」として1箇所で
  対比できる方がよい。
- 却下した案: `MOD-cli-mac-*` を 17 本立てる — モジュール数が倍になり、対応要件も重複する。
  旧構成のまま `cli-mac` を1モジュールで残す — `DSN-mod-01` の1対1と矛盾する。

### DSN-mod-03 共有基盤は1モジュールに集約する

- 判断: ホスト CLI の先頭にある定数・ヘルパー関数群を `MOD-cli-common` として独立させる。
- 理由: 全サブコマンドがここへファンインする(実測で 25 関数、最大ファンイン 9)。集約しないと
  17 モジュールが同じ実装パスを重複して持ち、実装とドキュメントの 1 対 1 が崩れる。
- 却下した案: 各サブコマンドのモジュールに複製して書く — 重複により整合検査が落ちる。
  共有基盤を作らず呼び出し関係だけで表す — 境界の無いコードが機能表から漏れる。

### DSN-mod-04 共有するものとプロジェクト単位のものを分ける

- 判断: `docker-proxy` は全 Claude コンテナで共有し、それ以外はプロジェクト単位(またはイメージ単位)
  とする。共有ボリュームは認証・シェル設定・履歴の3本に限る。
- 理由: 共有すると常駐が1つで済む一方、プロジェクト間の干渉が起きうる。干渉が問題になるもの
  (セッション・Chrome プロファイル)はプロジェクト単位に置く。
- 却下した案: すべてをプロジェクト単位にする — docker-proxy がプロジェクト数だけ常駐する。
  すべてを共有する — セッションが混ざる。

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

### DSN-mod-06 モジュールあたりの機能数の上限を超えている `MOD-makefile` を許容する

- 判断: `MOD-makefile`(16機能)は、1モジュールあたり 15 本という分割見直しの目安を超えるが、
  分割しない。
- 理由: 入口(ターゲット)が 16 個ある単一ファイルであり、`DSN-mod-01` の「モジュールは利用者から
  見た入口と1対1」をターゲット単位で満たしている。用途別に束ねると束ねた内部に境界が埋没し、
  記述量も減らない。
- 却下した案: Makefile のターゲットを用途別に束ねる — 束ねた内部に境界が埋没し、記述量は減らない。
  ターゲットごとにモジュールを立てる — 1ファイルが 16 モジュールにまたがり、物理配置との
  1対1が崩れる。

### DSN-mod-07 共有基盤の機能数が目安を超えることを許容する

- 判断: `MOD-cli-common`(17機能)は、1モジュールあたり 15 本という分割見直しの目安を超えるが、
  分割しない。`docs/histories/2026-08-11-promote-shared-helpers.md` の昇格(ファンイン2以上の共有関数5件を機能へ上げる)で
  12 → 17 になったものである。
- 理由: `DSN-mod-03` が「共有基盤は1モジュールに集約する」と定めており、分割すると
  `DSN-mod-03` そのものを書き換えることになる。また昇格した5機能はいずれも
  **利用者から見た入口を持たない**ので、`DSN-mod-01` の「モジュールは利用者から見た入口と
  1対1」を満たすモジュールには切り出せない。目安の 15 本は
  `relations-query.py --health` が分割の見直しを**提案する**閾値であって禁止ではなく、
  同じ状況を `DSN-mod-06` が `MOD-makefile`(16機能)について既に許容している。
- 却下した案: 破壊的操作の記録系と compose 命名系を `MOD-cli-destructive` /
  `MOD-cli-naming` へ切り出す — 入口を持たないモジュールが2つ増え、`DSN-mod-01` と
  `DSN-mod-03` の両方に反する。共有基盤を昇格させずに畳み込んだままにする —
  `MODULE-cli-logout` と `MODULE-cli-reset` が同一実装について別々の記述を持ち続け、
  片方だけを直したときに2つの仕様が食い違う(`docs/histories/2026-08-11-promote-shared-helpers.md` が実測した4項目)。
- 見直す条件: `MOD-cli-common` が **20 機能を超えたとき**、または**共有基盤どうしが呼び合う辺が
  5本を超えて、共有基盤の内側に階層ができたとき**(現在は2本 —
  `PLAN-cli-common-require-setup` → `PLAN-cli-common-image-exists` と
  `PLAN-cli-common-select-ssh-keys` → `PLAN-cli-common-write-project-ssh-keys`)。
  そのときは `DSN-mod-03` の集約方針から見直す。
  **「互いに呼び合わない塊が在ること」は見直す条件にしない** — 共有基盤は互いに呼び合わないのが
  既定の姿(`02-design/relations.md`「共有基盤どうしは一方向で循環しない」)であり、
  それを条件にすると新設した時点で常に成立してしまう。

## 要件カバレッジ確認

<!-- 受入基準の**条項ごと**に行を作る(要件ごとではない)。充足の語彙・主担当の規則の正は
     .claude/directions/02-design.md。03 のテスト対応表の「状態」列とは別の列・別の意味。 -->

**`充足` はこの設計がその条項を覆っているか**を言う(4値: `完全` / `部分(P-nn)` / `適用外(理由)` / `-`)。
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
| FR-env-01-6 | MOD-cli-stop | 完全 | DSN-env-03, DSN-env-04 |
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
| FR-env-01-28 | MOD-cli-stop | 完全 | DSN-env-04(所有者ラベルで引く。ボリュームを一意化名で引かない理由も同判断が持つ) |
| FR-env-01-29 | MOD-cli-stop | 完全 | -(設計判断を要さない) |
| FR-env-01-30 | MOD-cli-stop | 完全 | -(設計判断を要さない) |
| FR-env-01-31 | MOD-cli-stop | 完全 | DSN-env-04 |
| FR-env-01-32 | MOD-cli-reset | 完全 | DSN-env-04 |
| FR-env-01-33 | MOD-cli-reset | 完全 | -(設計判断を要さない) |
| FR-env-01-34 | MOD-cli-stop | 完全 | -(設計判断を要さない)。**`reset` 側の担い手は `FR-env-01-26` の根拠欄と同じ** |
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
| FR-env-03-22 | MOD-cli-reset | 完全 | -(設計判断を要さない) |
| FR-env-03-23 | MOD-cli-logout | 完全 | -(設計判断を要さない) |
| FR-env-03-24 | MOD-cli-logout | 完全 | DSN-env-04(所有者ラベルの照合値は所有者の Claude コンテナにしか無いため、`logout` がそれを削除すると `stop` では引けなくなる。規則 D と `CTR-cli-container`「削除対象の決め方」が持つ) |
| FR-env-04-1 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-04-2 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-04-3 | MOD-cli-ssh-keys | 完全 | -(設計判断を要さない) |
| FR-env-04-4 | MOD-cli-ssh-keys | 完全 | -(設計判断を要さない) |
| FR-env-04-5 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-04-6 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-04-7 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-04-8 | MOD-cli-start | 完全 | -(設計判断を要さない)。受理できない値を採用せずに SSH 転送なしで続行する倒し方は `FR-env-04-5` と同型で、`CTR-cli-container`「渡す環境変数」の「値の検証で起動を止めることはしない」に従う |
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
| FR-env-13-1 | (モジュール外)`03-impl/environments/images.md` | 完全 | DSN-dist-01(同梱物の導入を配布ステージの終端レイヤーに置く一般原則。同梱外部バイナリの設置もこの原則の適用である) |
| FR-env-13-2 | (モジュール外)`03-impl/environments/images.md` | 完全 | -(設計判断を要さない) |
| FR-env-13-3 | (モジュール外)`03-impl/environments/images.md` | 完全 | DSN-dist-01(アーキテクチャ別の置き分けは設置層の中で解決し、ステージ構成を増やさない) |
| FR-env-13-4 | (モジュール外)`03-impl/environments/images.md` | 完全 | -(設計判断を要さない) |
| FR-env-13-5 | (モジュール外)`03-impl/environments/images.md` | 完全 | -(設計判断を要さない) |
| FR-env-13-6 | (モジュール外)`03-impl/environments/images.md` | 完全 | -(設計判断を要さない) |
| FR-env-14-1 | MOD-cli-start | 完全 | DSN-env-05 |
| FR-env-14-2 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-14-3 | MOD-cli-start | 完全 | -(設計判断を要さない)。値を出さない規則の正は `logging.md`「出してはならない情報」 |
| FR-env-14-4 | MOD-cli-start | 完全 | DSN-env-05 |
| FR-env-14-5 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-14-6 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-14-7 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| FR-env-14-8 | MOD-cli-start | 完全 | DSN-env-05(予約する環境変数名の集合は `CTR-cli-container` が持つ) |
| FR-env-14-9 | MOD-cli-start | 完全 | DSN-env-05 |
| FR-env-14-10 | MOD-cli-start | 完全 | -(設計判断を要さない) |
| NFR-perf-01 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 完全 | DSN-dist-01 |
| NFR-perf-02 | (モジュール外)`03-impl/environments/images.md` / `03-impl/infra/local/ghcr.md` | 完全 | DSN-dist-01 |
| NFR-avail-02 | MOD-cli-start, MOD-entrypoint | 完全 | -(設計判断を要さない) |
| NFR-avail-03 | MOD-entrypoint, MOD-firewall, MOD-vm-mode | 完全 | DSN-fw-01(ファイアウォール分。他の補助機能の失敗許容は各契約のエラーケースが定める) |
| NFR-sec-01 | MOD-docker-proxy, MOD-firewall, MOD-cli-start, MOD-cli-common | 完全 | DSN-arch-01 |
| NFR-ops-02 | MOD-cli-common, 各 MOD-cli-*, MOD-entrypoint | 完全 | DSN-arch-01 |
| NFR-ops-03 | MOD-makefile, MOD-cli-common | 完全 | -(設計判断を要さない) |
| NFR-ops-05 | MOD-cli-common, 各 MOD-cli-*, MOD-entrypoint | 完全 | -(設計判断を要さない)。担い手が単一モジュールに収まらないため非機能要件として1行で持つ |
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
| SR-21 | MOD-docker-proxy | - | SR-21(技術前提。充足は適用外)。Go 実装は docker-proxy の1モジュールである |
| SR-24 | (モジュール外)`03-impl/environments/images.md` | - | SR-24(技術前提。充足は適用外)。マルチステージと終端レイヤー(`DSN-dist-01` / `DSN-mod-05`) |
| SR-30 | MOD-makefile | - | SR-30(技術前提。充足は適用外)。単一の入口 |
| SR-31 | MOD-docker-proxy | - | SR-31(技術前提。充足は適用外)。実コマンドは `environments.md` が正 |
| SR-32 | (担い手)本書「テスト戦略」`DSN-test-01` | - | SR-32(技術前提。充足は適用外)。自動テストを設けないという明示的な割り切り |
| SR-33 | (モジュール外)`03-impl/infra/local/ghcr.md` | - | SR-33(技術前提。充足は適用外)。GitHub Actions の日次実行 |
| SR-34 | (担い手)`02-design/environments.md`「Codex実行設定」 | - | SR-34(技術前提。充足は適用外)。legacy landlock で confinement を緩めずに実行する |

**システム要件(`SR-nn`)の行**について: SR は「システムが満たす振る舞い」ではなく**技術前提と制約**
であるため充足を持たない(`充足` = `-`。`.claude/directions/01-requirements.md` が定める)。
担い手がモジュールでないものは、その制約を保持する 02 のドキュメントを担い手として書く
(空欄を作らないための規約)。

**要件を持たないモジュールは無い**(全 25 モジュールが「モジュール分割定義」の対応要件と上表の
いずれかに現れる)。**割り当て先の無い条項も無い**(機能要件の全 164 条項・NFR 10 件・SR 19 件が
すべて上表に現れる)。

## テスト戦略

### レベル別方針

#### DSN-test-01 自動テストは docker-proxy に集中させ、シェル系は実機確認で担保する

- 判断: 単体テストは Go の `docker-proxy` に置く。Bash と Makefile には自動テストランナーを
  設けず、実機確認と E2E で担保する。結合テストは契約ごとに**観測可能な側**へ責任を割り当てる。
- 理由: Bash 実装に自動テストランナーを導入すると、実行環境(Docker・tmux・実 SSH)を用意する
  仕掛けが本体より大きくなる。一方、Docker API の検査ロジックという間違えやすい部分は
  docker-proxy に集中しており、そこは機械検証できる。「本物のバイナリで通す E2E は、モックでは
  見つからない欠陥を捕まえる」という実測経験も、この配分の根拠である。
- 却下した案: bats 等で Bash の単体テストを整備する — 実行環境の用意が本体より重い。
  すべてを E2E に寄せる — 失敗時の切り分けができない。

| レベル | 方針 | ツール | 実行環境 | データ | 実行タイミング |
|---|---|---|---|---|---|
| 単体 | Docker API の検査ロジックを機械検証する | `go test`(docker-proxy) | ホストまたはコンテナ内。外部サービスに接続しない | テスト内で組み立てる。一時ディレクトリを使い後始末する | 変更時と PR |
| 結合 | モジュール間の全3契約を、観測可能な側から検証する | `go test`(docker-proxy の API ボディ検査)+ 実機確認 | Go は単体と同じ。実機分はコンテナ起動を伴う | 契約ごとに下表の担当モジュールが用意する | 変更時。実機分はリリース前 |
| E2E | ユースケースを実操作で通す | 実機(`claude-dev` の実操作) | 実際のホストとコンテナ。実 tmux | 利用者のプロジェクトディレクトリ(使い捨ての一時ディレクトリ) | リリース前と、関係する変更のたび |

### 結合テスト対象

| 契約 ID | 契約の当事者 | テストを持つ責任モジュール |
|---|---|---|
| CTR-cli-container(**起動側**) | MOD-cli-start → MOD-entrypoint | MOD-entrypoint(呼び出し元はシェルで自動テストを持てないため観測側が担当。手段は実機確認) |
| CTR-cli-container(**破壊的操作の対象の識別**) | **発行側は2つある**: MOD-cli-start(Claude コンテナの管理ラベル)と **MOD-docker-proxy(セッション由来のコンテナ・ネットワーク・名前付きボリュームの所有者ラベル。`DSN-env-04`)**。→ 読み手は MOD-cli-stop / MOD-cli-logout / MOD-cli-reset | **MOD-cli-stop / MOD-cli-logout / MOD-cli-reset**(読み手が観測側。`D0-env-08`。**発行側がラベルを付けるのをやめると読み手の削除対象が空になる**ため、契約の遵守は読み手の側でしか観測できない)。全モジュールがシェル実装で自動テストを持てないため、手段は**実機確認 = E2E-01**(`FR-env-01` 受入基準 9・14〜27 / `FR-env-03` 受入基準 14〜23)。**発行側が docker-proxy である分だけは Go の単体テストで機械検証できる**が、それは下の `CTR-docker-api` の行が持つ(この行が観測するのは「読み手が `CTR-cli-container`「削除対象の決め方(4つの規則)」の規則 A〜D が定める集合だけを消すか」である) |
| CTR-entrypoint-firewall | MOD-entrypoint → MOD-firewall | MOD-entrypoint(手段は実機確認) |
| CTR-docker-api | Claude コンテナ → MOD-docker-proxy | MOD-docker-proxy(観測側。`go test` で機械検証。**所有者ラベルの付与(`FR-env-07` 受入基準11・12)も、要求ボディの変換なので同じ `go test` で検証できる**) |

**`CTR-cli-container` を2行に分けた理由**: この契約は当事者の異なる2つの取り決めを持つ。
起動時に渡す環境変数・オプション(`MOD-cli-start` → `MOD-entrypoint`)と、
**破壊的操作が削除対象を決めるための管理ラベル・所有者ラベル・遊休判定・ロックキー**
(`MOD-cli-start` と `MOD-docker-proxy` が付け、`MOD-cli-stop` / `-logout` / `-reset` が読む)である。
後者は `MOD-entrypoint` を一切通らないため、1行目の責任モジュールでは観測できない。

### E2Eシナリオ一覧

| E2E ID | 対応 UC | シナリオ | 対象/対象外(理由) |
|---|---|---|---|
| E2E-01 | UC-01 | `claude-dev start`(ブラウザ確認あり / `--no-vnc`)→ `/workspace` マウント・認証・ファイアウォール・tmux → `claude` 起動 → 再実行での再接続。**続けて破壊的操作が「自分が作った資源」にだけ効くことを確認する**: 管理ラベルの付与 / 遊休判定がイメージに依存しないこと / 排他ロックと残骸の引き継ぎ / ラベルを持たない既存コンテナを巻き込まないこと / compose 資源が別プロジェクトを巻き込まないこと / `stop` が受理しない名前 / `logout` がプロジェクト配下の認証コピーを消すこと / 確認と非対話時の中止 / 削除失敗の列挙(`FR-env-01` 受入基準 9・14〜21 / `FR-env-03` 受入基準 14〜24)。**さらにセッション由来の資源の片付けと、`logout` の後にそれが `stop` で回収できないことを確認する**(`FR-env-01` 受入基準 22〜27 / `FR-env-03` 受入基準24)。**あわせて名前付きボリュームの扱い(削除の明示が無いときは残して名前と削除する方法を表示し、明示したときだけ消す)と、存在しなかった資源を「削除できなかった」と表示しないことを確認する**(同 28〜34)。**プロジェクト環境ファイルの受け渡し(渡る・値を出さない・追跡から外れる・予約名を採用しない・無くても起動する)もこのシナリオで確認する**(`FR-env-14`)(確認する項目と手順は `03-impl/tests/e2e.md` が持つ) | 対象(Must) |
| E2E-02 | UC-02 | `claude-dev forward` → 8100 番台の割当と SSH トンネル → クライアントのブラウザで表示 → `claude-dev ports` で確認 | 対象(Must) |
| E2E-03 | UC-03 | コンテナ内で危険な `docker run` → 拒否 / `/workspace` bind の許可 / **`CTR-docker-api` が拒否条件と定めない要求の透過**。**あわせて、作成されたコンテナ・ネットワーク・名前付きボリュームに所有者ラベルが付いていることを確認する**(`FR-env-07` 受入基準11) | 対象(Must) |
| E2E-06 | UC-06 | `claude-dev login-codex` → デバイス認証 → 別プロジェクトで `start` → 再ログイン不要で `codex` が起動し、**シェルコマンドが成功して `/workspace` を読み書きできる**。landlock の疎通確認が通り、読み取り専用の明示指定で読み取りが成功する。トークン更新が次のコンテナへ引き継がれる | 対象(Must) |

**全 UC がカバーされている**(UC-01〜UC-03 / UC-06 → E2E-01〜E2E-03 / E2E-06)。上流の UC を
持たない E2E シナリオは作らない。**`E2E-04` / `E2E-05` は 2026-08-08 に廃止した**
(オーケストレーターの削除にともない `UC-04` / `UC-05` が消えたため)。**番号は再利用しない。**

## UI設計

本システムの UI はターミナル主体である(Web GUI は無い。ブラウザ確認は noVNC で提供するが、
これは本システムのアプリ UI ではなく、利用者が開発中の Web アプリを見るための窓である)。
接点は「ホスト CLI のコマンド体系」だけである。

### 画面一覧

#### DSN-ui-01 UI はホスト CLI に限り、Web GUI を持たない

- 判断: 利用者との接点をホスト CLI の1つに限る。下表の1画面で全操作を賄う。
- 理由: 利用者は開発者であり、作業の場が端末と SSH の中にある。Web GUI を足すと、ホストへ新たな
  待ち受けを開くことになり(`NFR-sec-01`)、認証も別途必要になる。
- 却下した案: Web ダッシュボードを提供する — ポート公開と認証の追加が必要で、隔離方針と衝突する。

| 画面ID | 画面名 | 目的 | 関連 UC |
|---|---|---|---|
| SCR-01 | cli-commands | コンテナ・認証・ポート・鍵の操作 | UC-01, UC-02, UC-03, UC-06 |

**`SCR-02`〜`SCR-06`(オーケストレーターの TUI)は 2026-08-08 に廃止した。番号は再利用しない。**

<!-- 改名する子見出しは、親を `sections` に載せたまま親本文へ入れ子にすると
     `compose-changeset.py` の merge_existing が「親本文経由の新規子見出し」として拒否するため、
     ここへ出してある。反映位置は frontmatter の anchors が決める。
     `.claude/directions/change-set.md` §2「Renaming is an explicit old-child deletes: plus
     that independently anchored new child」。 -->

### 画面ごとの項目と状態

#### SCR-01 cli-commands

| 項目 | 型・制約 | 必須 | 備考 |
|---|---|---|---|
| サブコマンド | 17 種の列挙 | 必須 | 未知の語とヘルプ要求は使い方を表示する |
| 対象セッション名 | 文字列(省略時はカレントディレクトリから導出)。**`stop <name>` に限り `[A-Za-z0-9._-]` のみ受理する** | 任意 | `stop` / `ports` / `forward` など。**受理文字集合の制約は `stop` だけに掛かる**: `stop` は名前をそのまま排他ロックのキー=パス要素として使うため(`CTR-cli-container`「ロックキーとして使える文字」)。**受理できない値を与えられたときに何が起きるかは `FR-env-01` 受入基準18 が定める。** `ports` / `forward` などにはこの制約が掛からない(ロックを取らないため) |
| フラグ | `--no-vnc` / `--kvm` / `--vm` / `--vm-fresh` / **`--yes`** / **`--volumes`** | 任意 | 非対応の組み合わせは実行前に拒否する。**`--yes` は破壊的操作(`logout` / `reset`)の確認プロンプトを飛ばす**(`D0-env-08` 項3)。端末を持たない環境で破壊的操作を実行する唯一の手段である。**`--volumes` は `stop` / `reset` にだけ掛かり、セッション由来の名前付きボリュームを削除対象に加える**(`FR-env-01-28` / `-32`。既定では削除しない。受理の位置と匿名ボリュームの扱いは `CTR-cli-container` の規則 D が定める) |

状態: **初期**=使い方の表示 / **実行中**=進捗行 / **エラー**=原因と次の操作の案内 /
**空**=対象セッションが無い / **完了**=接続 URL とアタッチ。

**破壊的操作の状態**(`logout` / `reset`): **確認** / **中止** / **一部失敗** / **残した資源** の4つ。
**`stop` / `reset` が持つ片付けの状態**: **片付け結果** / **片付け未実施**(`stop` だけが持つ)。
**排他待ちで中止の状態**: `start` / `stop` / `logout` / `reset` / `login` / `login-codex` の
**6コマンド共通**である(**破壊的操作だけの状態ではない**: 共有ボリュームまたは docker-proxy を触る
6コマンドすべてがこの状態を持つ)。

**それぞれの状態で利用者に何を示すかは 01 の受入基準が正である**(`FR-env-01` 受入基準
16・18・26・27 / `FR-env-03` 受入基準 15・17・18・**19**・24)。**この節は状態の存在と名前だけを
定める** — 表示の内容は外から観測できる約束であり、要件の側が持つ(`.claude/directions/02-design.md`
の UI 設計節)。**「残した資源」の状態は削除対象が0件の経路でも現れる**(受入基準19。削除する
集合が空であることと、残したものが無いことは別である)。
**ただし 01 が表示を課しておらず `logging.md` だけが持つものが4つある**: 破壊的操作の
削除対象の列挙の全体(`FR-env-03` 受入基準14 自身が `logging.md` を正と定めている)/ ラベルを
持たないため残したコンテナの表示の限界(停止中のものは列挙していない旨)/ `stop` が片付けを
行わなかったことの案内(`FR-env-01` 受入基準23 は削除の禁止だけを課し、表示を課さない)/
**共有ボリュームが空かを確かめられなかったことの表示**(受入基準19 は「その経路に入らない」ことを
課すだけで、確かめられなかった旨を出すことは課さない)。
ログとしての出力仕様(水準・出力先・文言に課す制約)も `logging.md` が持つ。

### デザイン方針

- 前提不足(未セットアップ・未認証・設定ファイルが無い)は、止めずに次の操作を案内する。
  止めざるを得ない場合は、原因と復旧手段を日本語1行で示してから終了する。
- 端末が対話的でない場合は、選択を求めずに既定値で進む。

## 未解決事項

- なし

---
target: docs/02-design/system.md
change: replace
version_bump: minor
sections:
  - "## 要件カバレッジ確認"
  - "## 分割の根拠"
deletes: []
reason: 'issue 023 の 01 層(`FR-env-04-8` の新設)に対応する要件カバレッジ表の行を足す。`CS13` は 01 の変更指示が触る条項に 02 のカバレッジ行と 03 のテスト行を要求するので、条項を1つ増やすとこの表にも主担当モジュールが1行要る。主担当は `MOD-cli-start`(agent 転送の中継は起動経路が用意する。`FR-env-04` の他の条項のうち起動時に効くもの — 1・2・5・6・7 — と同じ担当である)。**他の行は1文字も変えない**(節末の「割り当て先の無い条項も無い」の件数だけは 140 → 141 へ揃える — 条項を増やして件数を据え置くと、この節が偽を述べることになる)。「分割の根拠」は `CS19` が変更指示の `sections` に載せることを要求する節なので(変更のたびに前の判断を読み直させるため)同時に載せる — 読み直した結果は **`DSN-mod-01`〜`DSN-mod-07` のいずれも継続**であり、本タスクはモジュール分割を1つも動かさない'
reflected: 2026-08-12
---

## 分割の根拠

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
いずれかに現れる)。**割り当て先の無い条項も無い**(機能要件の全 141 条項・NFR 10 件・SR 19 件が
すべて上表に現れる)。

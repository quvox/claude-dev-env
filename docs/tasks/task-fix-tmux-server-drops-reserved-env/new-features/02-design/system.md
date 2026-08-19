---
target: docs/02-design/system.md
change: replace
version_bump: minor
sections:
  - "## 分割の根拠"
  - "## 要件カバレッジ確認"
deletes: []
reason: '`FR-env-07-13` の新設に追随して、要件カバレッジ確認の表に1行を足す。**主担当は `MOD-entrypoint`** — 変数を渡すのはホスト CLI(`MOD-cli-start`)だが、コンテナ内でプロセスの木(tmux サーバ)を起こすのは entrypoint であり、到達を保証できるのはそちらだからである。充足は `完全`(この設計で条項を覆える。到達の義務そのものは `CTR-cli-container` が持つ)。**表の他の行は1行も変えていない。** あわせて「分割の根拠」を `CS19` の要求どおり読み直し、**7件すべて継続**と判断した結果を1段落として記録した(新しい入口もモジュールも増えないため)。**あわせて `FR-env-14-11` の行も足した**(主担当 `MOD-entrypoint`・充足 `完全`。`AC-08` を満たすための到達の義務であり、組を渡すのは CLI だがコンテナ内でプロセスの木を起こすのは entrypoint である)'
---

## 分割の根拠

下の `DSN-mod-01`〜`DSN-mod-07` は、**この製品をどのモジュールへ割るか**の判断である。
**2026-08-18 に `FR-env-13`(同梱外部バイナリ)の新設にあたって7件すべてを読み直し、
いずれも継続と判断した**: 同梱外部バイナリの設置はコンテナイメージの定義(`Dockerfile.*`)の
中で完結し、実行される関数の入口を持たない。これは `DSN-mod-05` が
「コールグラフに入口を持たない資産はモジュールにしない」と決めた範囲の内側であり、
**新しいモジュールを立てない**(立てると機械検査 FT1 が重大度「高」で落ちる)。
`DSN-mod-06` / `DSN-mod-07` が扱うモジュールあたりの機能数の目安にも影響しない
(どのモジュールにも機能を足さないため)。
**2026-08-19 に `FR-env-07-13`(本システムが使う環境変数は、コンテナ内で起動したどのプロセスからも
参照できること)の新設にあたって7件すべてを読み直し、いずれも継続と判断した**: この条項の担い手は
既存の `MOD-entrypoint`(コンテナ起動時の初期化)であり、新しい入口も新しいモジュールも増えない。
`DSN-mod-06` / `DSN-mod-07` が扱うモジュールあたりの機能数の目安にも影響しない。

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
| FR-env-07-13 | MOD-entrypoint | 完全 | -(設計判断を要さない。到達の義務は `CTR-cli-container` の「渡す環境変数」が定める。**主担当が `MOD-cli-start` ではなく `MOD-entrypoint` なのは、変数を渡すのはホスト CLI だが、コンテナ内でプロセスの木を起こすのは entrypoint だからである**) |
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
| FR-env-14-11 | MOD-entrypoint | 完全 | -(設計判断を要さない。到達の義務は `CTR-cli-container` の「渡す環境変数」が定める。**主担当が `MOD-cli-start` ではなく `MOD-entrypoint` なのは、組を渡すのはホスト CLI だが、コンテナ内でプロセスの木を起こすのは entrypoint だからである**) |
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
いずれかに現れる)。**割り当て先の無い条項も無い**(機能要件の全 166 条項・NFR 10 件・SR 19 件が
すべて上表に現れる)。

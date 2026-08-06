---
target: docs/02-design/system.md
change: replace
sections:
  - "## 要件カバレッジ確認"
deletes: []
reason: '要件カバレッジ確認の表を要件単位(FR/NFR 33行 + SR 21行、3列)から**条項単位のキー + 充足列**(FR 201条項 + NFR 13行 + SR 21行、4列)へ作り替える(docs/issues/060。.claude/directions/02-design.md「★ Requirement coverage — by clause」が規範)。変える点: (1) キーを 01 の条項 ID(FR-<domain>-nn-#)にする。(2) 充足列(完全/部分(P-nn)/対象外(理由)/-)と根拠列を追加。充足の意味は「設計がその条項を覆っているか」(決定シート概念4=a)で、表の直前に定義を明記し「実装の達成度は 03-impl/tests/ が持つ」と書き添える。(3) 主担当は1条項につき1モジュールで、03-impl/tests/ の対応表で当該条項の行を持つファイルのモジュールと一致させる(tests/strategy.md「受入基準の行は主担当モジュール1つにだけ置く」)。FR-env-01-9 だけは対応表に3行の重複(cli-stop 1行・cli-logout 2行)があり、02 では MOD-cli-stop を主担当とした(重複の解消は決定シート 論点4)。(4) 部分(P-005) は FR-env-01-19 / FR-env-07-5 の2条項(compose 一意化のハッシュ衝突を検出しない設計 — pendings P-005)。対象外は FR-env-12-12 の1条項(根拠 D0-orch-17)。残る 198 条項と NFR 13件は 完全 で、根拠は該当する DSN-ID または「-(設計判断を要さない)」。(5) SR 21行は要件単位のまま 充足=-、根拠に SR-nn と旧備考を移す(概念3=SR は対象に含めない)。「モジュール分割定義」の対応要件列(要件単位のモジュール集合)は変えていない。条項単位の主担当は今回新設した情報であり、その値は 03-impl/tests/ の対応表の配置(全201条項で一致確認済み)から採った(旧 02 表の要件単位のモジュール集合はその上位集合であり矛盾しない)。モジュール分割定義・テスト戦略・UI設計の節は変更しない。'
---

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
いずれかに現れる)。**割り当て先の無い条項も無い**(機能要件の全 201 条項・NFR 13 件・SR 21 件が
すべて上表に現れる)。

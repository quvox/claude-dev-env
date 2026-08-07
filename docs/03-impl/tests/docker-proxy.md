---
id: docker-proxy
scope: MOD-docker-proxy
version: 1.1.0
updated: 2026-08-07
source:
  - docs/01-requirements/functional.md
  - docs/02-design/system.md
summary: MOD-docker-proxy(Docker API の検査と中継)の受入基準⇄テスト対応
keywords: [テスト]
verified:
  at: 2026-08-07
  version: 1.1.0
  against:
    - doc: docs/01-requirements/functional.md
      version: 1.9.0
    - doc: docs/02-design/system.md
      version: 2.5.0
---

# MOD-docker-proxy のテスト対応

## 受入基準 ⇄ テスト対応表


| 受入基準 ID | 種別 | レベル | テスト識別子 | 状態 |
|---|---|---|---|---|
| FR-env-07-2 | 正常系 | 単体 | `docker-proxy/main_test.go::TestValidateContainerCreate_BlocksHostBind`, `::TestValidateContainerCreate_BlocksPrivileged`, `::TestValidateContainerCreate_BlocksPidHost`, `::TestValidateContainerCreate_BlocksNetworkHost`, `::TestValidateContainerCreate_BlocksUsernsHost` | 実装済み |
| FR-env-07-3 | 正常系 | 単体 | `docker-proxy/main_test.go::TestValidateContainerCreate_RewritesWorkspaceBind`, `docker-proxy/binds_test.go::TestRewriteBinds_RewritesUnderWorkspace`, `::TestRewriteBinds_MountsBind` | 実装済み |
| FR-env-07-6 | 境界値 | 単体 | `docker-proxy/binds_test.go::TestContainWorkspacePath`, `::TestContainWorkspacePath_LexicalOnly`, `::TestRewriteBinds_RejectsOutsideWorkspace` | 実装済み |
| FR-env-07-7 | 境界値 | 単体 | `docker-proxy/binds_test.go::TestRewriteBinds_EmptyProjectRejectsAbsolute`, `docker-proxy/main_test.go::TestValidateContainerCreate_AllowsNamedVolume` | 実装済み |
| FR-env-07-8 | 異常系 | 単体 | `docker-proxy/main_test.go::TestValidateContainerCreate_AllowsEmptyBody`, `::TestValidateContainerCreate_AllowsNoHostConfig`, `::TestValidateContainerCreate_AllowsCleanRequest` | 実装済み |
| FR-env-07-9 | 異常系 | E2E | E2E-03(実機確認手順) | 未検証(テスト未実装) |
| FR-env-07-10 | 異常系 | E2E | E2E-03(実機確認手順) | 未検証(テスト未実装) |
| NFR-sec-01 | 非機能 | 単体 | `docker-proxy/main_test.go::TestValidateContainerCreate_BlocksDangerousCaps`, `::TestValidateContainerCreate_BlocksDevices`, `::TestValidateExecCreate_BlocksPrivileged`, `::TestValidateContainerCreate_AllowsSafeCaps` | 実装済み |

## 契約の結合テスト

| 契約 ID | 相手 | テスト識別子 | 状態 |
|---|---|---|---|
| CTR-docker-api | Claude コンテナ | `cd docker-proxy && go test ./...`(検査ロジック一式) | 実装済み |

## 機能間連携仕様書 ⇄ テスト

| MODULE-ID | テスト識別子 | 状態 |
|---|---|---|
| MODULE-docker-proxy-serve | `docker-proxy/main_test.go::TestValidateContainerCreate_BlocksPrivileged`, `docker-proxy/main_test.go::TestValidateContainerCreate_BlocksPidHost`, `docker-proxy/main_test.go::TestValidateContainerCreate_BlocksNetworkHost`, `docker-proxy/main_test.go::TestValidateContainerCreate_BlocksUsernsHost`, `docker-proxy/main_test.go::TestValidateContainerCreate_BlocksDangerousCaps`, `docker-proxy/main_test.go::TestValidateContainerCreate_BlocksDevices`, `docker-proxy/main_test.go::TestValidateExecCreate_BlocksPrivileged`, `docker-proxy/main_test.go::TestContainerCreateRe`, `docker-proxy/main_test.go::TestHijackEndpointRe`, `docker-proxy/binds_test.go::TestContainWorkspacePath`, `docker-proxy/binds_test.go::TestContainWorkspacePath_LexicalOnly`, `docker-proxy/binds_test.go::TestRewriteBinds_RewritesUnderWorkspace`, `docker-proxy/binds_test.go::TestRewriteBinds_RejectsOutsideWorkspace`, `docker-proxy/binds_test.go::TestRewriteBinds_MountsBindOutsideRejected`, `docker-proxy/binds_test.go::TestValidateContainerCreate_RewritesWorkspaceBind` | 実装済み |

## 未検証(テスト未実装)の全件

| # | 対象 | なぜ未実装か | 解消の条件 |
|---|---|---|---|
| 1 | FR-env-07 — 受入基準 9(異常系) | Go の自動テストは書ける領域だが未実装。中継の失敗と起動時の中断は実プロセスと実ソケットを要するため、現状は E2E-03 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 2 | FR-env-07 — 受入基準 10(異常系) | Go の自動テストは書ける領域だが未実装。中継の失敗と起動時の中断は実プロセスと実ソケットを要するため、現状は E2E-03 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |

---
target: docs/03-impl/tests/docker-proxy.md
change: replace
sections:
  - "## 受入基準 ⇄ テスト対応表"
  - "## 未検証(テスト未実装)の全件"
deletes: []
reason: '`FR-env-07` に追加した条項2件(`FR-env-07-11`(所有者ラベルの付与)/ `FR-env-07-12`(付与できないときは付与せずに中継する))に行を作る。**このモジュールは Go 実装で自動テストを持てる領域なので、レベルは `単体` とし、テスト識別子には実装時に追加する予定のテスト名を書かない**(実装前に具体的なシンボル名を発明しない。`.claude/directions/03-impl.md`)。したがって現時点の状態は両方とも `未検証(テスト未実装)` で、テスト識別子は `-` とする。未検証の全件に2件を追加し、**解消の条件を「このタスクの実装で単体テストを追加した時点」と書く**(自動化の予定が無い他の行と違い、ここは同じタスクの中で解消できる)。既存の8行と2件は変えない。(2) **`/implement`(2026-08-07)で単体テスト14本を追加したので、`FR-env-07-11` / `FR-env-07-12` の状態を `実装済み` にし、テスト識別子を実シンボル名で埋めた**(`docker-proxy/labels_test.go` を新設。11 は付与される・HostConfig 無しでも付く・他フィールドが変わらない・利用者の同名ラベルを上書きする・拒否された要求には付けない・bind の書き換えと再構成が1回に収まる・bind スイッチに依存しない・ネットワークにも付く・経路の正規表現、12 は呼び出し元不明・ラベル値が空・ボディ不正・ネットワークで付かない場合・所有者が空なら no-op)。**あわせて「未検証(テスト未実装)の全件」から 3・4 の行を削除した**(解消の条件「所有者ラベルの注入の実装と同時に単体テストを追加した時点」が満たされたため)。**表の行数は変わらない**ので `03-impl/tests/strategy.md` の集計(209 条項 / 224 行 / 222 件)は動かない'
---

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
| FR-env-07-11 | 正常系 | 単体 | `docker-proxy/labels_test.go::TestValidateContainerCreate_InjectsOwnerLabels`, `::TestValidateContainerCreate_InjectsOwnerLabelsWithoutHostConfig`, `::TestValidateContainerCreate_InjectionLeavesOtherFieldsIntact`, `::TestValidateContainerCreate_OverwritesUserSuppliedOwnerLabel`, `::TestValidateContainerCreate_RejectedRequestIsNotLabelled`, `::TestValidateContainerCreate_BindRewriteAndLabelShareOneReconstruction`, `::TestValidateContainerCreate_LabelsIndependentOfBindSwitch`, `::TestLabelNetworkCreate_InjectsOwnerLabels`, `::TestNetworkCreateRe` | 実装済み |
| FR-env-07-12 | 境界値 | 単体 | `docker-proxy/labels_test.go::TestValidateContainerCreate_NoOwnerLabelWhenCallerUnknown`, `::TestValidateContainerCreate_NoOwnerLabelWhenProjectDirEmpty`, `::TestValidateContainerCreate_UnparseableBodyRelayedUnchanged`, `::TestLabelNetworkCreate_NoOwnerLeavesBodyUntouched`, `::TestInjectOwnerLabels_EmptyOwnerIsNoop` | 実装済み |
| NFR-sec-01 | 非機能 | 単体 | `docker-proxy/main_test.go::TestValidateContainerCreate_BlocksDangerousCaps`, `::TestValidateContainerCreate_BlocksDevices`, `::TestValidateExecCreate_BlocksPrivileged`, `::TestValidateContainerCreate_AllowsSafeCaps` | 実装済み |

## 未検証(テスト未実装)の全件

| # | 対象 | なぜ未実装か | 解消の条件 |
|---|---|---|---|
| 1 | FR-env-07 — 受入基準 9(異常系) | Go の自動テストは書ける領域だが未実装。中継の失敗と起動時の中断は実プロセスと実ソケットを要するため、現状は E2E-03 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 2 | FR-env-07 — 受入基準 10(異常系) | Go の自動テストは書ける領域だが未実装。中継の失敗と起動時の中断は実プロセスと実ソケットを要するため、現状は E2E-03 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |

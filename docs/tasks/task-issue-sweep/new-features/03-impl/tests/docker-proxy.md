---
target: docs/03-impl/tests/docker-proxy.md
change: replace
version_bump: patch
sections:
  - "## 受入基準 ⇄ テスト対応表"
  - "## 機能間連携仕様書 ⇄ テスト"
  - "## 未検証(テスト未実装)の全件"
  - "## テスト設計の判断"
deletes: []
reason: 'issue 087 の修正で単体テストを2本足したので、対応表と機能間連携仕様書 ⇄ テストの識別子を実物へ揃える(`FR-env-07-12` は「付与せずに中継する」条項で、**理由をログへ出すこと**もこの条項が課している)。/ issue 077(条項ID への移行が「受入基準 ⇄ テスト対応表」だけに適用され、「未検証(テスト未実装)の全件」節の「対象」列が旧表記のまま残っている)。`FR-<domain>-nn — 受入基準 N` を条項ID `FR-<domain>-nn-N` へ機械的に置き換える。**種別の注記・理由・解消の条件は1文字も変えない**(表記だけを揃える)(このファイルは 2 箇所)'
reflected: 2026-08-12
---

## 未検証(テスト未実装)の全件

| # | 対象 | なぜ未実装か | 解消の条件 |
|---|---|---|---|
| 1 | FR-env-07-9(異常系) | Go の自動テストは書ける領域だが未実装。中継の失敗と起動時の中断は実プロセスと実ソケットを要するため、現状は E2E-03 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 2 | FR-env-07-10(異常系) | Go の自動テストは書ける領域だが未実装。中継の失敗と起動時の中断は実プロセスと実ソケットを要するため、現状は E2E-03 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |

## テスト設計の判断

- [DS-01] 単体テストは呼び出し元の解決を**スタブへ差し替えて**「特定できた / できない」の分岐を作り、実 Docker を起動しない(差し替えられる形にするという実装側の決定は `MODULE-docker-proxy-serve` の実装上の判断が持つ) — 理由: 所有者ラベルの付与は呼び出し元の解決の結果だけで決まるので、ここ1点を固定すれば `FR-env-07-11` と `-12` の両方を単体で覆える。DS-01 のガードレール「外部ネットワークに出ない」を満たす唯一の接合点でもある / 見直す条件: 呼び出し元の解決が複数の関数に分かれ、1点の差し替えでは固定できなくなったとき
- [DS-01] 新規14本を既存の `docker-proxy/main_test.go` に足さず **`docker-proxy/labels_test.go` を新設**する — 理由: 既存25本は拒否判定と bind の書き換えの試験であり、所有者ラベルの注入は関心が違う。ファイル名で「印付けの試験」を引けるようにする / 見直す条件: 注入が独立した関数でなくなり、拒否判定と同じ関数の分岐でしか試験できなくなったとき
- [DS-01] 検証は**書き戻された要求ボディを JSON として読み直す**形にする(注入関数の戻り値やモックの呼び出し記録を見ない) — 理由: `CTR-docker-api` が保証するのは中継されるボディそのもので、`Content-Length` の整合や他フィールドの不変も同じ見方で確かめられる / 見直す条件: 中継がボディの書き戻しではなくストリーム変換になったとき
- [DS-01] 14本を条項ごとに1関数へ分け、テーブル駆動にしない(`strategy.md`「命名と配置の規約」の既定に対する例外) — 理由: 失敗時にどの条項が壊れたかがテスト名だけで分かる(`FR-env-07-11` は付与される側9本、`-12` は付与しない側5本)。表の1行を増やす手軽さより、対応表の識別子欄に**関数名をそのまま並べられる**ことを採った / 見直す条件: 同じ形の試験が20本を超え、関数名の列挙が対応表で読めなくなったとき

- [DS-01] **既存の単体テストは全件を回帰として流し、覆う条件を減らさない**(所有者ラベルの注入は bind の書き換えと同じボディ再構成の経路に手を入れるため、拒否判定 — 特権・ホスト名前空間の共有・bind・ケーパビリティ・デバイス — の退行がありうる) — 理由: 分解の仕方は変えてよいが、**注入が動くことだけを確かめると既存の拒否判定の退行を見逃す** / 見直す条件: 注入の経路が拒否判定と完全に分離され、同じボディ再構成を共有しなくなったとき。**回帰の範囲は本数ではなく `cd docker-proxy && go test ./...` の全件成功で確かめる**(`MODULE-docker-proxy-serve` の `tests:` の 39 件とコード上のテスト関数 39 本は 2026-08-07 に一致させた。この一致を追跡していた issue は 2026-08-07 に解消して削除した)

## 受入基準 ⇄ テスト対応表


| 受入基準 ID | 種別 | レベル | テスト識別子 | 状態 |
|---|---|---|---|---|
| FR-env-07-2 | 正常系 | 単体 | `docker-proxy/main_test.go::TestValidateContainerCreate_BlocksHostBind`, `::TestValidateContainerCreate_BlocksPrivileged`, `::TestValidateContainerCreate_BlocksPidHost`, `::TestValidateContainerCreate_BlocksNetworkHost`, `::TestValidateContainerCreate_BlocksUsernsHost` | 実装済み |
| FR-env-07-3 | 正常系 | 単体 | `docker-proxy/binds_test.go::TestValidateContainerCreate_RewritesWorkspaceBind`, `docker-proxy/binds_test.go::TestRewriteBinds_RewritesUnderWorkspace`, `::TestRewriteBinds_MountsBind` | 実装済み |
| FR-env-07-6 | 境界値 | 単体 | `docker-proxy/binds_test.go::TestContainWorkspacePath`, `::TestContainWorkspacePath_LexicalOnly`, `::TestRewriteBinds_RejectsOutsideWorkspace` | 実装済み |
| FR-env-07-7 | 境界値 | 単体 | `docker-proxy/binds_test.go::TestRewriteBinds_EmptyProjectRejectsAbsolute`, `docker-proxy/main_test.go::TestValidateContainerCreate_AllowsNamedVolume` | 実装済み |
| FR-env-07-8 | 異常系 | 単体 | `docker-proxy/main_test.go::TestValidateContainerCreate_AllowsEmptyBody`, `::TestValidateContainerCreate_AllowsNoHostConfig`, `::TestValidateContainerCreate_AllowsCleanRequest` | 実装済み |
| FR-env-07-9 | 異常系 | E2E | E2E-03(実機確認手順) | 未検証(テスト未実装) |
| FR-env-07-10 | 異常系 | E2E | E2E-03(実機確認手順) | 未検証(テスト未実装) |
| FR-env-07-11 | 正常系 | 単体 | `docker-proxy/labels_test.go::TestValidateContainerCreate_InjectsOwnerLabels`, `::TestValidateContainerCreate_InjectsOwnerLabelsWithoutHostConfig`, `::TestValidateContainerCreate_InjectionLeavesOtherFieldsIntact`, `::TestValidateContainerCreate_OverwritesUserSuppliedOwnerLabel`, `::TestValidateContainerCreate_RejectedRequestIsNotLabelled`, `::TestValidateContainerCreate_BindRewriteAndLabelShareOneReconstruction`, `::TestValidateContainerCreate_LabelsIndependentOfBindSwitch`, `::TestLabelNetworkCreate_InjectsOwnerLabels`, `::TestNetworkCreateRe` | 実装済み |
| FR-env-07-12 | 境界値 | 単体 | `docker-proxy/labels_test.go::TestValidateContainerCreate_NoOwnerLabelWhenCallerUnknown`, `::TestValidateContainerCreate_NoOwnerLabelWhenProjectDirEmpty`, `::TestValidateContainerCreate_UnparseableBodyRelayedUnchanged`, `::TestLabelNetworkCreate_NoOwnerLeavesBodyUntouched`, `::TestInjectOwnerLabels_EmptyOwnerIsNoop`, `::TestValidateContainerCreate_LogsReasonWhenNotLabelled`, `::TestValidateContainerCreate_NoReasonLogWhenLabelled` | 実装済み |
| NFR-sec-01 | 非機能 | 単体 | `docker-proxy/main_test.go::TestValidateContainerCreate_BlocksDangerousCaps`, `::TestValidateContainerCreate_BlocksDevices`, `::TestValidateExecCreate_BlocksPrivileged`, `::TestValidateContainerCreate_AllowsSafeCaps` | 実装済み |

## 機能間連携仕様書 ⇄ テスト

| MODULE-ID | テスト識別子 | 状態 |
|---|---|---|
| MODULE-docker-proxy-serve | `docker-proxy/labels_test.go::TestValidateContainerCreate_InjectsOwnerLabels`, `docker-proxy/labels_test.go::TestValidateContainerCreate_InjectsOwnerLabelsWithoutHostConfig`, `docker-proxy/labels_test.go::TestValidateContainerCreate_InjectionLeavesOtherFieldsIntact`, `docker-proxy/labels_test.go::TestValidateContainerCreate_OverwritesUserSuppliedOwnerLabel`, `docker-proxy/labels_test.go::TestValidateContainerCreate_NoOwnerLabelWhenCallerUnknown`, `docker-proxy/labels_test.go::TestValidateContainerCreate_NoOwnerLabelWhenProjectDirEmpty`, `docker-proxy/labels_test.go::TestValidateContainerCreate_UnparseableBodyRelayedUnchanged`, `docker-proxy/labels_test.go::TestValidateContainerCreate_RejectedRequestIsNotLabelled`, `docker-proxy/labels_test.go::TestValidateContainerCreate_BindRewriteAndLabelShareOneReconstruction`, `docker-proxy/labels_test.go::TestValidateContainerCreate_LabelsIndependentOfBindSwitch`, `docker-proxy/labels_test.go::TestLabelNetworkCreate_InjectsOwnerLabels`, `docker-proxy/labels_test.go::TestLabelNetworkCreate_NoOwnerLeavesBodyUntouched`, `docker-proxy/labels_test.go::TestNetworkCreateRe`, `docker-proxy/labels_test.go::TestInjectOwnerLabels_EmptyOwnerIsNoop`, `docker-proxy/main_test.go::TestValidateContainerCreate_BlocksPrivileged`, `docker-proxy/main_test.go::TestValidateContainerCreate_BlocksPidHost`, `docker-proxy/main_test.go::TestValidateContainerCreate_BlocksNetworkHost`, `docker-proxy/main_test.go::TestValidateContainerCreate_BlocksUsernsHost`, `docker-proxy/main_test.go::TestValidateContainerCreate_BlocksDangerousCaps`, `docker-proxy/main_test.go::TestValidateContainerCreate_BlocksDevices`, `docker-proxy/main_test.go::TestValidateExecCreate_BlocksPrivileged`, `docker-proxy/main_test.go::TestContainerCreateRe`, `docker-proxy/main_test.go::TestHijackEndpointRe`, `docker-proxy/binds_test.go::TestContainWorkspacePath`, `docker-proxy/binds_test.go::TestContainWorkspacePath_LexicalOnly`, `docker-proxy/binds_test.go::TestRewriteBinds_RewritesUnderWorkspace`, `docker-proxy/binds_test.go::TestRewriteBinds_RejectsOutsideWorkspace`, `docker-proxy/binds_test.go::TestRewriteBinds_MountsBindOutsideRejected`, `docker-proxy/binds_test.go::TestValidateContainerCreate_RewritesWorkspaceBind`, `docker-proxy/main_test.go::TestValidateContainerCreate_BlocksHostBind`, `docker-proxy/main_test.go::TestValidateContainerCreate_BlocksBindMount`, `docker-proxy/main_test.go::TestValidateContainerCreate_AllowsSafeCaps`, `docker-proxy/main_test.go::TestValidateContainerCreate_AllowsEmptyBody`, `docker-proxy/main_test.go::TestValidateContainerCreate_AllowsNoHostConfig`, `docker-proxy/main_test.go::TestValidateContainerCreate_AllowsCleanRequest`, `docker-proxy/main_test.go::TestValidateContainerCreate_AllowsNamedVolume`, `docker-proxy/main_test.go::TestValidateExecCreate_AllowsNormal`, `docker-proxy/binds_test.go::TestRewriteBinds_MountsBind`, `docker-proxy/binds_test.go::TestRewriteBinds_EmptyProjectRejectsAbsolute`, `docker-proxy/labels_test.go::TestValidateContainerCreate_LogsReasonWhenNotLabelled`, `docker-proxy/labels_test.go::TestValidateContainerCreate_NoReasonLogWhenLabelled` | 実装済み |

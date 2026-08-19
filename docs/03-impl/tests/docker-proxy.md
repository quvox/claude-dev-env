---
id: docker-proxy
version: 1.4.1
updated: 2026-08-19
scope: MOD-docker-proxy
source:
  - docs/01-requirements/functional.md
  - docs/02-design/system.md
summary: MOD-docker-proxy(Docker API の検査と中継)の受入基準⇄テスト対応
keywords: [テスト]
verified:
  at: 2026-08-19
  version: 1.4.1
  against:
    - {doc: docs/01-requirements/functional.md, version: 1.19.0}
    - {doc: docs/02-design/system.md, version: 2.15.0}
---

# MOD-docker-proxy のテスト対応

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
| FR-env-07-11 | 正常系 | 単体 | `docker-proxy/labels_test.go::TestValidateContainerCreate_InjectsOwnerLabels`, `::TestValidateContainerCreate_InjectsOwnerLabelsWithoutHostConfig`, `::TestValidateContainerCreate_InjectionLeavesOtherFieldsIntact`, `::TestValidateContainerCreate_OverwritesUserSuppliedOwnerLabel`, `::TestValidateContainerCreate_RejectedRequestIsNotLabelled`, `::TestValidateContainerCreate_BindRewriteAndLabelShareOneReconstruction`, `::TestValidateContainerCreate_LabelsIndependentOfBindSwitch`, `::TestLabelNetworkCreate_InjectsOwnerLabels`, `::TestNetworkCreateRe`, `::TestLabelVolumeCreate_InjectsOwnerLabels`, `::TestLabelVolumeCreate_OverwritesUserSuppliedOwnerLabel`, `::TestVolumeCreateRe` | 実装済み |
| FR-env-07-12 | 境界値 | 単体 | `docker-proxy/labels_test.go::TestValidateContainerCreate_NoOwnerLabelWhenCallerUnknown`, `::TestValidateContainerCreate_NoOwnerLabelWhenProjectDirEmpty`, `::TestValidateContainerCreate_UnparseableBodyRelayedUnchanged`, `::TestLabelNetworkCreate_NoOwnerLeavesBodyUntouched`, `::TestLabelVolumeCreate_NoOwnerLeavesBodyUntouched`, `::TestInjectOwnerLabels_EmptyOwnerIsNoop`, `::TestValidateContainerCreate_LogsReasonWhenNotLabelled`, `::TestValidateContainerCreate_NoReasonLogWhenLabelled` | 実装済み |
| NFR-sec-01 | 非機能 | 単体 | `docker-proxy/main_test.go::TestValidateContainerCreate_BlocksDangerousCaps`, `::TestValidateContainerCreate_BlocksDevices`, `::TestValidateExecCreate_BlocksPrivileged`, `::TestValidateContainerCreate_AllowsSafeCaps` | 実装済み |

## 契約の結合テスト

| 契約 ID | 相手 | テスト識別子 | 状態 |
|---|---|---|---|
| CTR-docker-api | Claude コンテナ | `cd docker-proxy && go test ./...`(検査ロジック一式) | 実装済み |

## 機能間連携仕様書 ⇄ テスト

| MODULE-ID | テスト識別子 | 状態 |
|---|---|---|
| MODULE-docker-proxy-serve | `docker-proxy/labels_test.go::TestValidateContainerCreate_InjectsOwnerLabels`, `docker-proxy/labels_test.go::TestValidateContainerCreate_InjectsOwnerLabelsWithoutHostConfig`, `docker-proxy/labels_test.go::TestValidateContainerCreate_InjectionLeavesOtherFieldsIntact`, `docker-proxy/labels_test.go::TestValidateContainerCreate_OverwritesUserSuppliedOwnerLabel`, `docker-proxy/labels_test.go::TestValidateContainerCreate_NoOwnerLabelWhenCallerUnknown`, `docker-proxy/labels_test.go::TestValidateContainerCreate_NoOwnerLabelWhenProjectDirEmpty`, `docker-proxy/labels_test.go::TestValidateContainerCreate_UnparseableBodyRelayedUnchanged`, `docker-proxy/labels_test.go::TestValidateContainerCreate_RejectedRequestIsNotLabelled`, `docker-proxy/labels_test.go::TestValidateContainerCreate_BindRewriteAndLabelShareOneReconstruction`, `docker-proxy/labels_test.go::TestValidateContainerCreate_LabelsIndependentOfBindSwitch`, `docker-proxy/labels_test.go::TestLabelNetworkCreate_InjectsOwnerLabels`, `docker-proxy/labels_test.go::TestLabelNetworkCreate_NoOwnerLeavesBodyUntouched`, `docker-proxy/labels_test.go::TestNetworkCreateRe`, `docker-proxy/labels_test.go::TestInjectOwnerLabels_EmptyOwnerIsNoop`, `docker-proxy/main_test.go::TestValidateContainerCreate_BlocksPrivileged`, `docker-proxy/main_test.go::TestValidateContainerCreate_BlocksPidHost`, `docker-proxy/main_test.go::TestValidateContainerCreate_BlocksNetworkHost`, `docker-proxy/main_test.go::TestValidateContainerCreate_BlocksUsernsHost`, `docker-proxy/main_test.go::TestValidateContainerCreate_BlocksDangerousCaps`, `docker-proxy/main_test.go::TestValidateContainerCreate_BlocksDevices`, `docker-proxy/main_test.go::TestValidateExecCreate_BlocksPrivileged`, `docker-proxy/main_test.go::TestContainerCreateRe`, `docker-proxy/main_test.go::TestHijackEndpointRe`, `docker-proxy/binds_test.go::TestContainWorkspacePath`, `docker-proxy/binds_test.go::TestContainWorkspacePath_LexicalOnly`, `docker-proxy/binds_test.go::TestRewriteBinds_RewritesUnderWorkspace`, `docker-proxy/binds_test.go::TestRewriteBinds_RejectsOutsideWorkspace`, `docker-proxy/binds_test.go::TestRewriteBinds_MountsBindOutsideRejected`, `docker-proxy/binds_test.go::TestValidateContainerCreate_RewritesWorkspaceBind`, `docker-proxy/main_test.go::TestValidateContainerCreate_BlocksHostBind`, `docker-proxy/main_test.go::TestValidateContainerCreate_BlocksBindMount`, `docker-proxy/main_test.go::TestValidateContainerCreate_AllowsSafeCaps`, `docker-proxy/main_test.go::TestValidateContainerCreate_AllowsEmptyBody`, `docker-proxy/main_test.go::TestValidateContainerCreate_AllowsNoHostConfig`, `docker-proxy/main_test.go::TestValidateContainerCreate_AllowsCleanRequest`, `docker-proxy/main_test.go::TestValidateContainerCreate_AllowsNamedVolume`, `docker-proxy/main_test.go::TestValidateExecCreate_AllowsNormal`, `docker-proxy/binds_test.go::TestRewriteBinds_MountsBind`, `docker-proxy/binds_test.go::TestRewriteBinds_EmptyProjectRejectsAbsolute`, `docker-proxy/labels_test.go::TestValidateContainerCreate_LogsReasonWhenNotLabelled`, `docker-proxy/labels_test.go::TestValidateContainerCreate_NoReasonLogWhenLabelled`, `docker-proxy/labels_test.go::TestLabelVolumeCreate_InjectsOwnerLabels`, `docker-proxy/labels_test.go::TestLabelVolumeCreate_NoOwnerLeavesBodyUntouched`, `docker-proxy/labels_test.go::TestLabelVolumeCreate_OverwritesUserSuppliedOwnerLabel`, `docker-proxy/labels_test.go::TestVolumeCreateRe` | 実装済み |

## テスト設計の判断

- [DS-01] 単体テストは呼び出し元の解決を**スタブへ差し替えて**「特定できた / できない」の分岐を作り、実 Docker を起動しない(差し替えられる形にするという実装側の決定は `MODULE-docker-proxy-serve` の実装上の判断が持つ) — 理由: 所有者ラベルの付与は呼び出し元の解決の結果だけで決まるので、ここ1点を固定すれば `FR-env-07-11` と `-12` の両方を単体で覆える。DS-01 のガードレール「外部ネットワークに出ない」を満たす唯一の接合点でもある / 見直す条件: 呼び出し元の解決が複数の関数に分かれ、1点の差し替えでは固定できなくなったとき
- [DS-01] 新規14本を既存の `docker-proxy/main_test.go` に足さず **`docker-proxy/labels_test.go` を新設**する — 理由: 既存25本は拒否判定と bind の書き換えの試験であり、所有者ラベルの注入は関心が違う。ファイル名で「印付けの試験」を引けるようにする / 見直す条件: 注入が独立した関数でなくなり、拒否判定と同じ関数の分岐でしか試験できなくなったとき
- [DS-01] 検証は**書き戻された要求ボディを JSON として読み直す**形にする(注入関数の戻り値やモックの呼び出し記録を見ない) — 理由: `CTR-docker-api` が保証するのは中継されるボディそのもので、`Content-Length` の整合や他フィールドの不変も同じ見方で確かめられる / 見直す条件: 中継がボディの書き戻しではなくストリーム変換になったとき
- [DS-01] 14本を条項ごとに1関数へ分け、テーブル駆動にしない(`strategy.md`「命名と配置の規約」の既定に対する例外) — 理由: 失敗時にどの条項が壊れたかがテスト名だけで分かる(`FR-env-07-11` は付与される側9本、`-12` は付与しない側5本)。表の1行を増やす手軽さより、対応表の識別子欄に**関数名をそのまま並べられる**ことを採った / 見直す条件: 同じ形の試験が20本を超え、関数名の列挙が対応表で読めなくなったとき

- [DS-01] **既存の単体テストは全件を回帰として流し、覆う条件を減らさない**(所有者ラベルの注入は bind の書き換えと同じボディ再構成の経路に手を入れるため、拒否判定 — 特権・ホスト名前空間の共有・bind・ケーパビリティ・デバイス — の退行がありうる) — 理由: 分解の仕方は変えてよいが、**注入が動くことだけを確かめると既存の拒否判定の退行を見逃す** / 見直す条件: 注入の経路が拒否判定と完全に分離され、同じボディ再構成を共有しなくなったとき。**回帰の範囲は本数ではなく `cd docker-proxy && go test ./...` の全件成功で確かめる**(`MODULE-docker-proxy-serve` の `tests:` の 45 件とコード上のテスト関数 45 本は 2026-08-19 に一致させた〈`binds_test.go` 8 / `labels_test.go` 20 / `main_test.go` 17〉。2026-08-07 に 39 件 / 39 本で一致させて以降、ボリューム経路の4本ほかを足した。この一致を追跡していた issue は 2026-08-07 に解消して削除した)
- [DS-01] **ボリューム作成経路の試験を、ネットワーク作成経路と同じ4本の型に揃える**(注入される / 所有者が空なら素通し / 利用者の同名ラベルを上書きする / 版接頭辞つきのパスに一致する) — 理由: 注入の本体(`injectOwnerLabels`)は3経路で共通なので、経路ごとに確かめるべきは「その経路が注入を呼ぶか」だけである。同じ型に揃えると読み手が差分だけを見られる(既存9本+5本の並びがそのまま対応表の識別子欄に載る)/ 見直す条件: 経路ごとに注入の内容が変わるようになったとき
- [DS-01] **`labelCreateRequest` の `kind` 引数そのものを試験しない** — 理由: `kind` はログの文言にしか使われず、ログの文言は `DS-03` の委任範囲である(条項が課しているのは「付与しなかった理由を出す」ことで、資源名の語ではない)。既存の未付与ログの試験がその条項を覆っている / 見直す条件: 資源の種別が条項に現れるようになったとき

## 未検証(テスト未実装)の全件

| # | 対象 | なぜ未実装か | 解消の条件 |
|---|---|---|---|
| 1 | FR-env-07-9(異常系) | Go の自動テストは書ける領域だが未実装。中継の失敗と起動時の中断は実プロセスと実ソケットを要するため、現状は E2E-03 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 2 | FR-env-07-10(異常系) | Go の自動テストは書ける領域だが未実装。中継の失敗と起動時の中断は実プロセスと実ソケットを要するため、現状は E2E-03 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |


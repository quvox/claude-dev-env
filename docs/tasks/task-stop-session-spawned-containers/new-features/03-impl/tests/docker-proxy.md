---
target: docs/03-impl/tests/docker-proxy.md
change: replace
sections:
  - "## 受入基準 ⇄ テスト対応表"
  - "## テスト設計の判断"
  - "## 未検証(テスト未実装)の全件"
anchors:
  - { section: "## テスト設計の判断", after: "## 機能間連携仕様書 ⇄ テスト" }
deletes: []
reason: '`FR-env-07` に追加した条項2件(`FR-env-07-11`(所有者ラベルの付与)/ `FR-env-07-12`(付与できないときは付与せずに中継する))に行を作る。**このモジュールは Go 実装で自動テストを持てる領域なので、レベルは `単体` とし、テスト識別子には実装時に追加する予定のテスト名を書かない**(実装前に具体的なシンボル名を発明しない。`.claude/directions/03-impl.md`)。したがって現時点の状態は両方とも `未検証(テスト未実装)` で、テスト識別子は `-` とする。未検証の全件に2件を追加し、**解消の条件を「このタスクの実装で単体テストを追加した時点」と書く**(自動化の予定が無い他の行と違い、ここは同じタスクの中で解消できる)。既存の8行と2件は変えない。(2) **`/implement`(2026-08-07)で単体テスト14本を追加したので、`FR-env-07-11` / `FR-env-07-12` の状態を `実装済み` にし、テスト識別子を実シンボル名で埋めた**(`docker-proxy/labels_test.go` を新設。11 は付与される・HostConfig 無しでも付く・他フィールドが変わらない・利用者の同名ラベルを上書きする・拒否された要求には付けない・bind の書き換えと再構成が1回に収まる・bind スイッチに依存しない・ネットワークにも付く・経路の正規表現、12 は呼び出し元不明・ラベル値が空・ボディ不正・ネットワークで付かない場合・所有者が空なら no-op)。**あわせて「未検証(テスト未実装)の全件」から 3・4 の行を削除した**(解消の条件「所有者ラベルの注入の実装と同時に単体テストを追加した時点」が満たされたため)。**表の行数は変わらない**ので `03-impl/tests/strategy.md` の集計(209 条項 / 224 行 / 222 件)は動かない。(3) **規範の更新(`.claude/directions/delegation.md` §3・検査 CS19)により「## テスト設計の判断」を新設した** — 14本をどう作ったか(実 Docker を起動しない差し替え点・ファイル分割・検証の見方)は `DS-01` の委任で決めたことであり、開示行が無いままだとテストの形の理由がテストコードを読んで想像するしかなくなる'
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

## テスト設計の判断

- [DS-01] 単体テストは呼び出し元の解決を**スタブへ差し替えて**「特定できた / できない」の分岐を作り、実 Docker を起動しない(差し替えられる形にするという実装側の決定は `MODULE-docker-proxy-serve` の実装上の判断が持つ) — 理由: 所有者ラベルの付与は呼び出し元の解決の結果だけで決まるので、ここ1点を固定すれば `FR-env-07-11` と `-12` の両方を単体で覆える。DS-01 のガードレール「外部ネットワークに出ない」を満たす唯一の接合点でもある / 見直す条件: 呼び出し元の解決が複数の関数に分かれ、1点の差し替えでは固定できなくなったとき
- [DS-01] 新規14本を既存の `docker-proxy/main_test.go` に足さず **`docker-proxy/labels_test.go` を新設**する — 理由: 既存25本は拒否判定と bind の書き換えの試験であり、所有者ラベルの注入は関心が違う。ファイル名で「印付けの試験」を引けるようにする / 見直す条件: 注入が独立した関数でなくなり、拒否判定と同じ関数の分岐でしか試験できなくなったとき
- [DS-01] 検証は**書き戻された要求ボディを JSON として読み直す**形にする(注入関数の戻り値やモックの呼び出し記録を見ない) — 理由: `CTR-docker-api` が保証するのは中継されるボディそのもので、`Content-Length` の整合や他フィールドの不変も同じ見方で確かめられる / 見直す条件: 中継がボディの書き戻しではなくストリーム変換になったとき
- [DS-01] 14本を条項ごとに1関数へ分け、テーブル駆動にしない(`strategy.md`「命名と配置の規約」の既定に対する例外) — 理由: 失敗時にどの条項が壊れたかがテスト名だけで分かる(`FR-env-07-11` は付与される側9本、`-12` は付与しない側5本)。表の1行を増やす手軽さより、対応表の識別子欄に**関数名をそのまま並べられる**ことを採った / 見直す条件: 同じ形の試験が20本を超え、関数名の列挙が対応表で読めなくなったとき

- [DS-01] **既存の単体テストは全件を回帰として流し、覆う条件を減らさない**(所有者ラベルの注入は bind の書き換えと同じボディ再構成の経路に手を入れるため、拒否判定 — 特権・ホスト名前空間の共有・bind・ケーパビリティ・デバイス — の退行がありうる) — 理由: 分解の仕方は変えてよいが、**注入が動くことだけを確かめると既存の拒否判定の退行を見逃す** / 見直す条件: 注入の経路が拒否判定と完全に分離され、同じボディ再構成を共有しなくなったとき。**本数で管理しない**(`tests:` の列挙件数とコード上のテスト関数の数が一致していないため。`docs/issues/082` が追跡する)

## 未検証(テスト未実装)の全件

| # | 対象 | なぜ未実装か | 解消の条件 |
|---|---|---|---|
| 1 | FR-env-07 — 受入基準 9(異常系) | Go の自動テストは書ける領域だが未実装。中継の失敗と起動時の中断は実プロセスと実ソケットを要するため、現状は E2E-03 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 2 | FR-env-07 — 受入基準 10(異常系) | Go の自動テストは書ける領域だが未実装。中継の失敗と起動時の中断は実プロセスと実ソケットを要するため、現状は E2E-03 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |

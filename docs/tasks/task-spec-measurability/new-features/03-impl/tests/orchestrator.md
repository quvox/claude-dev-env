---
target: docs/03-impl/tests/orchestrator.md
change: replace
sections:
  - "## 受入基準 ⇄ テスト対応表"
  - "## 未検証(テスト未実装)の全件"
deletes: []
reason: >
  NFR-ops-01 の削除(決定シート概念#6)に伴い同 ID の行を落とし、NFR-ops-04 は 01 が
  第2文を「測らない」と明記したことに追随して対象を第1文に限る(docs/issues/043、論点1=案B)。
---

## 受入基準 ⇄ テスト対応表

| 要件 ID | 受入基準 # | 種別 | レベル | テスト識別子 | 状態 |
|---|---|---|---|---|---|
| FR-orch-01 | 2 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-01 | 3 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-01 | 4 | 正常系 | 単体 | `orchestrator/handoff_test.go::TestWaitConsume_ReturnsWhenControlAppears`, `::TestWaitConsume_UntilEndsWithoutControl` | 実装済み |
| FR-orch-01 | 5 | 境界値 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-01 | 6 | 境界値 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-01 | 7 | 異常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-02 | 1 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-02 | 2 | 正常系 | 単体 | `orchestrator/session_test.go::TestSessionNames`, `::TestExpectedWindows`, `::TestNewSessionManager_UsesComposeProjectName` | 実装済み |
| FR-orch-02 | 3 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-03 | 1 | 正常系 | 単体 | `orchestrator/state_test.go::TestWorktreePaths` | 実装済み |
| FR-orch-03 | 2 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-03 | 3 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-03 | 4 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-03 | 5 | 境界値 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-03 | 6 | 境界値 | 単体 | `orchestrator/plan_test.go::TestMarkBlockedByFailedDeps`, `::TestDependencyChainOrder` | 実装済み |
| FR-orch-03 | 7 | 異常系 | 単体 | `orchestrator/worker_stream_test.go::TestParseWorkerResultStreamJSON`, `::TestParseWorkerResultBare`, `::TestParseWorkerResultRealSample` | 実装済み |
| FR-orch-03 | 8 | 境界値 | 単体 | - | 未検証(テスト未実装) |
| FR-orch-03 | 9 | 境界値 | 単体 | - | 未検証(テスト未実装) |
| FR-orch-03 | 10 | 境界値 | 単体 | - | 未検証(テスト未実装) |
| FR-orch-03 | 11 | 境界値 | 単体 | - | 未検証(テスト未実装) |
| FR-orch-04 | 1 | 正常系 | 単体 | `orchestrator/trigger_test.go::TestEvaluate_NeedsHumanReasons`, `::TestEvaluate_PreDispatchIrreversible` | 実装済み |
| FR-orch-04 | 2 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-04 | 3 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-04 | 4 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-04 | 5 | 境界値 | 単体 | `orchestrator/trigger_test.go::TestEvaluate_StuckLimitBoundary`, `::TestEvaluate_StuckThisAttempt`, `::TestEvaluate_StuckTakesPrecedenceOverNeedsHuman` | 実装済み |
| FR-orch-04 | 6 | 異常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-04 | 7 | 境界値 | 単体 | `orchestrator/trigger_test.go::TestEvaluate_PreDispatchIrreversible` | 実装済み |
| FR-orch-04 | 8 | 境界値 | 単体 | `orchestrator/trigger_test.go::TestEvaluate_PreDispatchApprovedIrreversibleDoesNotFire`, `orchestrator/controller_test.go::TestIntervene_ResolveApprovesIrreversible` | 実装済み |
| FR-orch-04 | 9 | 境界値 | 単体 | - | 未検証(テスト未実装) |
| FR-orch-05 | 1 | 正常系 | 単体 | `orchestrator/archive_test.go::TestArchiveRun_MovesNotDeletes`, `::TestArchiveRun_NoState` | 実装済み |
| FR-orch-05 | 2 | 正常系 | 単体 | - | 未検証(テスト未実装) |
| FR-orch-05 | 3 | 正常系 | 単体 | `orchestrator/plan_test.go::TestStatusTransition_HappyPath`, `::TestReviseDoesNotIncrementAttempts`, `::TestAllDoneAndSettled` | 実装済み |
| FR-orch-05 | 4 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-05 | 5 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-05 | 6 | 境界値 | 単体 | `orchestrator/state_test.go::TestStateRoundTrip`, `::TestPlanRoundTrip`, `::TestControlRoundTripAndDelete`, `::TestSidecarRoundTrip` | 実装済み |
| FR-orch-05 | 7 | 異常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-05 | 8 | 境界値 | 単体 | - | 未検証(テスト未実装) |
| FR-orch-05 | 9 | 境界値 | 単体 | - | 未検証(テスト未実装) |
| FR-orch-05 | 10 | 異常系 | 単体 | `orchestrator/state_test.go::TestLoadStateMissing` | 実装済み |
| FR-orch-06 | 1 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-06 | 2 | 正常系 | 単体 | - | 未検証(テスト未実装) |
| FR-orch-06 | 3 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-06 | 4 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-06 | 5 | 境界値 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-06 | 6 | 境界値 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-06 | 7 | 異常系 | 単体 | `orchestrator/accept_test.go::TestReview_ReformatsProseToJSON`, `orchestrator/review_parse_test.go::TestFindReviewResultJSON_StrictAndTolerant` | 実装済み |
| FR-orch-07 | 1 | 正常系 | 単体 | `orchestrator/models_test.go::TestTaskKindProfile`, `::TestWorkerTaskProfile`, `::TestRoleProfiles` | 実装済み |
| FR-orch-07 | 2 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-07 | 3 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-07 | 4 | 境界値 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-08 | 1 | 正常系 | 単体 | `orchestrator/dashtui_test.go::TestDashCursor_MovesAndClamps`, `::TestDashEnter_OnWaitingHumanSendsResolve`, `::TestDashView_BrainstormingIsCursorSelect`, `::TestDashQuit_SendsQuit` | 実装済み |
| FR-orch-08 | 2 | 正常系 | 単体 | `orchestrator/term_test.go::TestBuildQuestion_NumbersOptions`, `::TestResolveMenu_NumberImmediate` | 実装済み |
| FR-orch-08 | 3 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-08 | 4 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-08 | 5 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-08 | 6 | 境界値 | 単体 | `orchestrator/term_test.go::TestSelectMenu_NonTTYReturnsDefault`, `::TestTerminalConfirm_NonTTYContinue`, `::TestResolveMenu_NoInputReturnsCurrent` | 実装済み |
| FR-orch-08 | 7 | 異常系 | 単体 | `orchestrator/dashboard_test.go::TestReadVMHealthBanner_StaleIgnored`, `::TestReadVMHealthBanner_WarnFresh`, `::TestReadVMHealthBanner_OKIsSilent` | 実装済み |
| FR-orch-08 | 8 | 異常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-09 | 2 | 正常系 | 単体 | `examples/orch-sample` の pytest 一式(`cd examples/orch-sample && pytest`) | 実装済み |
| NFR-perf-03 | — | 非機能 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| NFR-avail-01 | — | 非機能 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| NFR-sec-03 | — | 非機能 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| NFR-ops-04 | — | 非機能 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |

## 未検証(テスト未実装)の全件

**この表が数える範囲**: 上の3表(受入基準 ⇄ テスト対応表 / 契約の結合テスト /
機能間連携仕様書 ⇄ テスト)で**状態セルが「未検証(テスト未実装)」である 47 行**を列挙する。
**#37 だけは例外**で、状態セルは「実装済み」だが対象の一部しか覆っていないため、覆っていない範囲を
明示する目的で併記している(47 行には数えない)。したがって表の行数は 48 である。

| # | 対象 | なぜ未実装か | 閉じる予定 |
|---|---|---|---|
| 1 | FR-orch-01 — 受入基準 2(正常系) | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 2 | FR-orch-01 — 受入基準 3(正常系) | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 3 | FR-orch-01 — 受入基準 5(境界値) | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 4 | FR-orch-01 — 受入基準 6(境界値) | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 5 | FR-orch-01 — 受入基準 7(異常系) | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 6 | FR-orch-02 — 受入基準 1(正常系) | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 7 | FR-orch-02 — 受入基準 3(正常系) | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 8 | FR-orch-03 — 受入基準 2(正常系) | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 9 | FR-orch-03 — 受入基準 3(正常系) | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 10 | FR-orch-03 — 受入基準 4(正常系) | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 11 | FR-orch-03 — 受入基準 5(境界値) | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 12 | FR-orch-04 — 受入基準 2(正常系) | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 13 | FR-orch-04 — 受入基準 3(正常系) | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 14 | FR-orch-04 — 受入基準 4(正常系) | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 15 | FR-orch-04 — 受入基準 6(異常系) | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 16 | FR-orch-05 — 受入基準 4(正常系) | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 17 | FR-orch-05 — 受入基準 5(正常系) | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 18 | FR-orch-05 — 受入基準 7(異常系) | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 19 | FR-orch-06 — 受入基準 1(正常系) | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 20 | FR-orch-06 — 受入基準 3(正常系) | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 21 | FR-orch-06 — 受入基準 4(正常系) | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 22 | FR-orch-06 — 受入基準 5(境界値) | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 23 | FR-orch-06 — 受入基準 6(境界値) | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 24 | FR-orch-07 — 受入基準 2(正常系) | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 25 | FR-orch-07 — 受入基準 3(正常系) | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 26 | FR-orch-07 — 受入基準 4(境界値) | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 27 | FR-orch-08 — 受入基準 3(正常系) | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 28 | FR-orch-08 — 受入基準 4(正常系) | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 29 | FR-orch-08 — 受入基準 5(正常系) | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 30 | FR-orch-08 — 受入基準 8(異常系) | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 31 | NFR-perf-03 — worker の割り当て粒度 | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 32 | NFR-avail-01 — 端末破壊からの復旧 | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 33 | NFR-sec-03 — 秘密情報の到達範囲(**未検証なのは worker とレビューアーの2経路**) | worker とレビューアーは `orchestrator/claudebin.go` の `claudeChildEnv()` が通知トークンを外す共通経路だが、**これを固定する単体テストが無い**ため実 tmux・実エージェントを要する E2E-04 / E2E-05 の実機確認で代替している。**対話 Claude の経路だけは `orchestrator/mode_test.go` が起動スクリプトに `unset SLACK_BOT_TOKEN` が含まれることを固定している**(この行が「未検証」なのは残る2経路についてである) | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 34 | NFR-ops-04 — ポリシーの一元化(第1文のみ) | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している。**第2文(運用状態の読み書き主体)は 01 が「測らない」と明記したため、そもそもテストの対象ではない** | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 35 | MODULE-orchestrator-claude-exec — 機能全体 | claudebin.go に対応する単体テストが無く、E2E-04 の実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 36 | MODULE-orchestrator-config — 機能全体 | config.go に対応する単体テストが無い | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 37 | MODULE-orchestrator-main — フラグ解釈・ストア初期化・再開/新規の分岐 | `main.go` に対応する単体テストは `orchestrator/term_test.go::TestTerminalConfirm_NonTTYContinue`(`main.go:194` の `terminalConfirm` の非 TTY 分岐)の**1件だけ**で、フラグ解釈・ストア初期化・再開/新規の分岐は覆っていない。E2E-04 / E2E-05 の実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 38 | MODULE-orchestrator-slack — 機能全体 | slack.go に対応する単体テストが無い | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 39 | FR-orch-03 — 受入基準 8(境界値) | `config.go` に対応する単体テストが無い(設定の検証はコードにあるがテストで固定されていない) | `config.go` の単体テストを書く時点で閉じる(現時点で予定は未定) |
| 40 | FR-orch-03 — 受入基準 9(境界値) | `config.go` に対応する単体テストが無い(設定の検証はコードにあるがテストで固定されていない) | `config.go` の単体テストを書く時点で閉じる(現時点で予定は未定) |
| 41 | FR-orch-03 — 受入基準 10(境界値) | `config.go` に対応する単体テストが無い(設定の検証はコードにあるがテストで固定されていない) | `config.go` の単体テストを書く時点で閉じる(現時点で予定は未定) |
| 42 | FR-orch-03 — 受入基準 11(境界値) | `config.go` に対応する単体テストが無い(設定の検証はコードにあるがテストで固定されていない) | `config.go` の単体テストを書く時点で閉じる(現時点で予定は未定) |
| 43 | FR-orch-04 — 受入基準 9(境界値) | `stuck_limit` が 0 以下のときの分岐に対応するテストケースが無い | `trigger_test.go` にケースを足す時点で閉じる(現時点で予定は未定) |
| 44 | FR-orch-05 — 受入基準 8(境界値) | プロセスの異常終了を再現する自動テストが無く、実機確認でも再現手順が未整備(`docs/issues/006` / `docs/pendings.md` P-003) | 実機確認手順の整備(`docs/issues/006` と P-003 の QA レーン)で閉じる |
| 45 | FR-orch-05 — 受入基準 9(境界値) | プロセスの異常終了を再現する自動テストが無く、実機確認でも再現手順が未整備(`docs/issues/006` / `docs/pendings.md` P-003) | 実機確認手順の整備(`docs/issues/006` と P-003 の QA レーン)で閉じる |
| 46 | FR-orch-05 — 受入基準 2(正常系) | **「未完了 plan が残る状態で `orchestrate` したらその run を継続する」という分岐そのものが `orchestrator/main.go` の再開判定にあり、`main.go` に単体テストが無い**(`MODULE-orchestrator-main` の `tests` は `terminalConfirm` の1件だけ)。近いテスト(`archive_test.go::TestCountUndone` は未完了数の計算、`controller_test.go::TestResume_UsesResumeFlagAfterCrash` は同一 Attempt の `--resume` 継続)はこの基準の主張を覆っていない | `main.go` の再開判定に単体テストを足すタスクで閉じる(`docs/issues/004` の残件のうち「永続データモデルの記述」と同じ対象) |
| 47 | CTR-cli-orchestrator — 契約の結合テスト | `claude-dev orchestrate` とコントローラの境界はシェルと Go にまたがるため、どちらのモジュールにも自動の結合テストが無く、手順(`tests/e2e.md` E2E-04 / E2E-05)の実機確認だけで代替している | 実機確認手順の整備(`docs/issues/006` と `docs/pendings.md` P-003 の QA レーン)で閉じる |
| 48 | FR-orch-06 — 受入基準 2(正常系) | **採点基準が当該タスクの完了条件のみであること**(`D0-orch-05` のガードレール = プラン全体のゴールへフォールバックしない)を覆うテストが無い。従来この行が挙げていた `orchestrator/review_parse_test.go` は JSON の抽出と解釈を検証するもので、`buildReviewPrompt` が `Task.Completion` を渡すかどうかには触れていない(`docs/issues/059`) | **`buildReviewPrompt` が `Task.Completion` を渡し `Plan.Completion` へフォールバックしないことを固定する単体テストを書く時点で閉じる**(2026-08-05 に人間が案B で裁定。`docs/issues/059` が追跡し、コードを触るタスクで実施する) |

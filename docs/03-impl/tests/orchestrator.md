---
id: orchestrator
scope: MOD-orchestrator
version: 1.4.0
updated: 2026-08-05
source:
  - docs/01-requirements/functional.md
  - docs/02-design/system.md
summary: MOD-orchestrator(AIオーケストレーター)の受入基準⇄テスト対応
keywords: [テスト]
verified:
  at: 2026-08-05
  version: 1.3.0
  against:
    - doc: docs/01-requirements/functional.md
      version: 1.5.1
    - doc: docs/02-design/system.md
      version: 2.2.1
---

# MOD-orchestrator のテスト対応

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
| FR-orch-05 | 2 | 正常系 | 単体 | - | **未検証(テスト未実装)** |
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
| NFR-ops-01 | — | 非機能 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| NFR-ops-04 | — | 非機能 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |

## 契約の結合テスト

| 契約 ID | 相手 | テスト識別子 | 状態 |
|---|---|---|---|
| CTR-cli-orchestrator | MOD-cli-orchestrate | 手順のみ(`tests/e2e.md` E2E-04 / E2E-05) | 未検証(テスト未実装) |
| CTR-orchestrator-prompt | worker / 対話 Claude | `orchestrator/mode_test.go::TestWriteLaunchScript`, `orchestrator/policy_test.go::TestBuildPrompt_IncludesPolicyWhenPresent`, `::TestModeArgs_IncludePolicyWhenPresent`(生成側)。実プロセスとの結合は E2E-04 | 実装済み |

## 機能間連携仕様書 ⇄ テスト

| MODULE-ID | テスト識別子 | 状態 |
|---|---|---|
| MODULE-orchestrator-claude-exec | - | 未検証(テスト未実装) |
| MODULE-orchestrator-config | - | 未検証(テスト未実装) |
| MODULE-orchestrator-controller | `orchestrator/controller_test.go::TestExecuting_RespectsMaxWorkers`, `orchestrator/controller_test.go::TestExecuting_DependencyOrder`, `orchestrator/controller_test.go::TestExecuting_TriggerParksTaskPeersContinue`, `orchestrator/controller_test.go::TestExecuting_Trigger1Irreversible`, `orchestrator/controller_test.go::TestIntervene_ResolveApprovesIrreversible`, `orchestrator/controller_test.go::TestResume_UsesResumeFlagAfterCrash`, `orchestrator/controller_test.go::TestRunGate_ReviseDispatchErrorPreservesStuck`, `orchestrator/controller_test.go::TestExecuting_RecordsAssumptions`, `orchestrator/controller_test.go::TestReportNotExecutable_MissingCompletion`, `orchestrator/controller_test.go::TestReportNotExecutable_NotReady`, `orchestrator/controller_test.go::TestFreshDispatch_NewSession`, `orchestrator/controller_test.go::TestResolveOne`, `orchestrator/accept_test.go::TestReconcileAndAccept_MarksDoneAndMerges`, `orchestrator/accept_test.go::TestReconcileAndAccept_NoAnswerLeavesOpen`, `orchestrator/worker_stream_test.go::TestParseCompletionVerdict`, `orchestrator/term_test.go::TestBuildQuestion_NumbersOptions` | 実装済み |
| MODULE-orchestrator-dashboard | `orchestrator/dashtui_test.go::TestDashView_RendersTasksAndCursor`, `orchestrator/dashtui_test.go::TestDashCursor_MovesAndClamps`, `orchestrator/dashtui_test.go::TestDashEnter_OnWaitingHumanSendsResolve`, `orchestrator/dashtui_test.go::TestDashQuit_SendsQuit`, `orchestrator/dashtui_test.go::TestDashView_BrainstormingIsCursorSelect`, `orchestrator/dashboard_test.go::TestReadVMHealthBanner_WarnFresh`, `orchestrator/dashboard_test.go::TestReadVMHealthBanner_OKIsSilent`, `orchestrator/dashboard_test.go::TestReadVMHealthBanner_StaleIgnored`, `orchestrator/dashboard_test.go::TestReadVMHealthBanner_NonVMMode` | 実装済み |
| MODULE-orchestrator-handoff | `orchestrator/handoff_test.go::TestWaitConsume_ReturnsWhenControlAppears`, `orchestrator/handoff_test.go::TestWaitConsume_UntilEndsWithoutControl` | 実装済み |
| MODULE-orchestrator-main | `orchestrator/term_test.go::TestTerminalConfirm_NonTTYContinue` | 実装済み(**`main` そのものではなく `terminalConfirm` の非 TTY 分岐だけ**。起動判定と再開/新規の分岐は E2E-04 / E2E-05 の実機確認で代替する) |
| MODULE-orchestrator-mode | `orchestrator/mode_test.go::TestWriteLaunchScript`, `orchestrator/mode_test.go::TestWriteLaunchScript_NoPromptOmitsPositional`, `orchestrator/mode_test.go::TestShellSingleQuote`, `orchestrator/policy_test.go::TestModeArgs_IncludePolicyWhenPresent` | 実装済み |
| MODULE-orchestrator-plan | `orchestrator/plan_test.go::TestReadyTasks_DependencyResolution`, `orchestrator/plan_test.go::TestReadyTasks_ParallelLimit`, `orchestrator/plan_test.go::TestReadyTasks_FailedDepExcluded`, `orchestrator/plan_test.go::TestDependencyChainOrder`, `orchestrator/plan_test.go::TestMarkBlockedByFailedDeps`, `orchestrator/plan_test.go::TestAllDoneAndSettled`, `orchestrator/plan_test.go::TestStatusTransition_HappyPath`, `orchestrator/plan_test.go::TestReviseDoesNotIncrementAttempts` | 実装済み |
| MODULE-orchestrator-review | `orchestrator/accept_test.go::TestReview_ReformatsProseToJSON`, `orchestrator/review_parse_test.go::TestFindReviewResultJSON_StrictAndTolerant` | 実装済み |
| MODULE-orchestrator-session | `orchestrator/session_test.go::TestNormalizeCName`, `orchestrator/session_test.go::TestSessionNames`, `orchestrator/session_test.go::TestSplitTarget`, `orchestrator/session_test.go::TestExpectedWindows`, `orchestrator/session_test.go::TestNewSessionManager_UsesComposeProjectName` | 実装済み |
| MODULE-orchestrator-slack | - | 未検証(テスト未実装) |
| MODULE-orchestrator-state | `orchestrator/state_test.go::TestStateRoundTrip`, `orchestrator/state_test.go::TestPlanRoundTrip`, `orchestrator/state_test.go::TestWorktreePaths`, `orchestrator/archive_test.go::TestArchiveRun_MovesNotDeletes`, `orchestrator/archive_test.go::TestArchiveRun_NoState`, `orchestrator/archive_test.go::TestCountUndone`, `orchestrator/policy_test.go::TestLoadProjectPolicy_Present`, `orchestrator/policy_test.go::TestVMModePreamble_PrependedInVMMode` | 実装済み |
| MODULE-orchestrator-state-intervention | `orchestrator/state_test.go::TestControlRoundTripAndDelete`, `orchestrator/state_test.go::TestAuditAppend`, `orchestrator/state_test.go::TestSidecarRoundTrip` | 実装済み |
| MODULE-orchestrator-state-io | `orchestrator/state_test.go::TestStateRoundTrip`, `orchestrator/state_test.go::TestAuditAppend`, `orchestrator/state_test.go::TestSidecarRoundTrip` | 実装済み |
| MODULE-orchestrator-streamlog | `orchestrator/streamlog_test.go::TestFormatStreamLine`, `orchestrator/streamlog_test.go::TestStreamPrettyWriter_SplitsAndBuffersPartialLines` | 実装済み |
| MODULE-orchestrator-term | `orchestrator/term_test.go::TestResolveMenu_EnterPicksDefault`, `orchestrator/term_test.go::TestResolveMenu_ArrowThenEnter`, `orchestrator/term_test.go::TestResolveMenu_JKMovement`, `orchestrator/term_test.go::TestResolveMenu_NumberImmediate`, `orchestrator/term_test.go::TestResolveMenu_NoInputReturnsCurrent`, `orchestrator/term_test.go::TestSelectMenu_NonTTYReturnsDefault` | 実装済み |
| MODULE-orchestrator-trigger | `orchestrator/trigger_test.go::TestEvaluate_PreDispatchIrreversible`, `orchestrator/trigger_test.go::TestEvaluate_NeedsHumanReasons`, `orchestrator/trigger_test.go::TestEvaluate_StuckLimitBoundary`, `orchestrator/trigger_test.go::TestEvaluate_StuckThisAttempt`, `orchestrator/trigger_test.go::TestEvaluate_StuckTakesPrecedenceOverNeedsHuman` | 実装済み |
| MODULE-orchestrator-worker | `orchestrator/worker_stream_test.go::TestParseWorkerResultStreamJSON`, `orchestrator/worker_stream_test.go::TestParseWorkerResultBare`, `orchestrator/worker_stream_test.go::TestParseWorkerResultRealSample`, `orchestrator/policy_test.go::TestBuildPrompt_IncludesPolicyWhenPresent` | 実装済み |
| MODULE-orchestrator-worktree | `orchestrator/accept_test.go::TestReconcileAndAccept_MarksDoneAndMerges`, `orchestrator/state_test.go::TestWorktreePaths` | 実装済み |

## 未検証(テスト未実装)の全件

**この表が数える範囲**: 上の3表(受入基準 ⇄ テスト対応表 / 契約の結合テスト /
機能間連携仕様書 ⇄ テスト)で**状態セルが「未検証(テスト未実装)」である 48 行**を列挙する。
**#38 だけは例外**で、状態セルは「実装済み」だが対象の一部しか覆っていないため、覆っていない範囲を
明示する目的で併記している(48 行には数えない)。したがって表の行数は 49 である。

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
| 33 | NFR-sec-03 — 秘密情報の到達範囲 | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 34 | NFR-ops-01 — 運用補助と可観測性 | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 35 | NFR-ops-04 — ポリシーの一元化 | Go の自動テストは書ける領域だが未実装。実 tmux・実エージェント・実 git を要する振る舞いのため、現状は E2E-04 / E2E-05 の実機確認で代替している | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 36 | MODULE-orchestrator-claude-exec — 機能全体 | claudebin.go に対応する単体テストが無く、E2E-04 の実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 37 | MODULE-orchestrator-config — 機能全体 | config.go に対応する単体テストが無い | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 38 | MODULE-orchestrator-main — フラグ解釈・ストア初期化・再開/新規の分岐 | `main.go` に対応する単体テストは `orchestrator/term_test.go::TestTerminalConfirm_NonTTYContinue`(`main.go:194` の `terminalConfirm` の非 TTY 分岐)の**1件だけ**で、フラグ解釈・ストア初期化・再開/新規の分岐は覆っていない。E2E-04 / E2E-05 の実機確認で代替する | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 39 | MODULE-orchestrator-slack — 機能全体 | slack.go に対応する単体テストが無い | 自動化の予定は無い(方針を変える場合は 02 の `DSN-test-01` から見直す) |
| 40 | FR-orch-03 — 受入基準 8(境界値) | `config.go` に対応する単体テストが無い(設定の検証はコードにあるがテストで固定されていない) | `config.go` の単体テストを書く時点で閉じる(現時点で予定は未定) |
| 41 | FR-orch-03 — 受入基準 9(境界値) | `config.go` に対応する単体テストが無い(設定の検証はコードにあるがテストで固定されていない) | `config.go` の単体テストを書く時点で閉じる(現時点で予定は未定) |
| 42 | FR-orch-03 — 受入基準 10(境界値) | `config.go` に対応する単体テストが無い(設定の検証はコードにあるがテストで固定されていない) | `config.go` の単体テストを書く時点で閉じる(現時点で予定は未定) |
| 43 | FR-orch-03 — 受入基準 11(境界値) | `config.go` に対応する単体テストが無い(設定の検証はコードにあるがテストで固定されていない) | `config.go` の単体テストを書く時点で閉じる(現時点で予定は未定) |
| 44 | FR-orch-04 — 受入基準 9(境界値) | `stuck_limit` が 0 以下のときの分岐に対応するテストケースが無い | `trigger_test.go` にケースを足す時点で閉じる(現時点で予定は未定) |
| 45 | FR-orch-05 — 受入基準 8(境界値) | プロセスの異常終了を再現する自動テストが無く、実機確認でも再現手順が未整備(`docs/issues/006` / `docs/pendings.md` P-003) | 実機確認手順の整備(`docs/issues/006` と P-003 の QA レーン)で閉じる |
| 46 | FR-orch-05 — 受入基準 9(境界値) | プロセスの異常終了を再現する自動テストが無く、実機確認でも再現手順が未整備(`docs/issues/006` / `docs/pendings.md` P-003) | 実機確認手順の整備(`docs/issues/006` と P-003 の QA レーン)で閉じる |
| 47 | FR-orch-05 — 受入基準 2(正常系) | **「未完了 plan が残る状態で `orchestrate` したらその run を継続する」という分岐そのものが `orchestrator/main.go` の再開判定にあり、`main.go` に単体テストが無い**(`MODULE-orchestrator-main` の `tests` は `terminalConfirm` の1件だけ)。近いテスト(`archive_test.go::TestCountUndone` は未完了数の計算、`controller_test.go::TestResume_UsesResumeFlagAfterCrash` は同一 Attempt の `--resume` 継続)はこの基準の主張を覆っていない | `main.go` の再開判定に単体テストを足すタスクで閉じる(`docs/issues/004` の残件のうち「永続データモデルの記述」と同じ対象) |
| 48 | CTR-cli-orchestrator — 契約の結合テスト | `claude-dev orchestrate` とコントローラの境界はシェルと Go にまたがるため、どちらのモジュールにも自動の結合テストが無く、手順(`tests/e2e.md` E2E-04 / E2E-05)の実機確認だけで代替している | 実機確認手順の整備(`docs/issues/006` と `docs/pendings.md` P-003 の QA レーン)で閉じる |
| 49 | FR-orch-06 — 受入基準 2(正常系) | **採点基準が当該タスクの完了条件のみであること**(`D0-orch-05` のガードレール = プラン全体のゴールへフォールバックしない)を覆うテストが無い。従来この行が挙げていた `orchestrator/review_parse_test.go` は JSON の抽出と解釈を検証するもので、`buildReviewPrompt` が `Task.Completion` を渡すかどうかには触れていない(`docs/issues/059`) | **`buildReviewPrompt` が `Task.Completion` を渡し `Plan.Completion` へフォールバックしないことを固定する単体テストを書く時点で閉じる**(2026-08-05 に人間が案B で裁定。`docs/issues/059` が追跡し、コードを触るタスクで実施する) |

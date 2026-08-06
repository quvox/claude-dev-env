---
target: docs/03-impl/tests/orchestrator.md
change: replace
sections:
  - "## 受入基準 ⇄ テスト対応表"
deletes: []
reason: '旧2列形式(要件 ID + 受入基準 #)の対応表を条項 ID(FR-<domain>-nn-#)キーの5列形式へ移行する(docs/issues/060。決定シート論点1=A「30ファイルを今回まとめて移行」)。列の併合のみの機械的な置換で、行の増減・種別/レベル/テスト識別子/状態の値の変更は無い。非機能要件の行は条項に分けないため要件 ID のまま(受入基準 # の「—」を落とす)。'
---

## 受入基準 ⇄ テスト対応表


| 受入基準 ID | 種別 | レベル | テスト識別子 | 状態 |
|---|---|---|---|---|
| FR-orch-01-2 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-01-3 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-01-4 | 正常系 | 単体 | `orchestrator/handoff_test.go::TestWaitConsume_ReturnsWhenControlAppears`, `::TestWaitConsume_UntilEndsWithoutControl` | 実装済み |
| FR-orch-01-5 | 境界値 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-01-6 | 境界値 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-01-7 | 異常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-02-1 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-02-2 | 正常系 | 単体 | `orchestrator/session_test.go::TestSessionNames`, `::TestExpectedWindows`, `::TestNewSessionManager_UsesComposeProjectName` | 実装済み |
| FR-orch-02-3 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-03-1 | 正常系 | 単体 | `orchestrator/state_test.go::TestWorktreePaths` | 実装済み |
| FR-orch-03-2 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-03-3 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-03-4 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-03-5 | 境界値 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-03-6 | 境界値 | 単体 | `orchestrator/plan_test.go::TestMarkBlockedByFailedDeps`, `::TestDependencyChainOrder` | 実装済み |
| FR-orch-03-7 | 異常系 | 単体 | `orchestrator/worker_stream_test.go::TestParseWorkerResultStreamJSON`, `::TestParseWorkerResultBare`, `::TestParseWorkerResultRealSample` | 実装済み |
| FR-orch-03-8 | 境界値 | 単体 | - | 未検証(テスト未実装) |
| FR-orch-03-9 | 境界値 | 単体 | - | 未検証(テスト未実装) |
| FR-orch-03-10 | 境界値 | 単体 | - | 未検証(テスト未実装) |
| FR-orch-03-11 | 境界値 | 単体 | - | 未検証(テスト未実装) |
| FR-orch-04-1 | 正常系 | 単体 | `orchestrator/trigger_test.go::TestEvaluate_NeedsHumanReasons`, `::TestEvaluate_PreDispatchIrreversible` | 実装済み |
| FR-orch-04-2 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-04-3 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-04-4 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-04-5 | 境界値 | 単体 | `orchestrator/trigger_test.go::TestEvaluate_StuckLimitBoundary`, `::TestEvaluate_StuckThisAttempt`, `::TestEvaluate_StuckTakesPrecedenceOverNeedsHuman` | 実装済み |
| FR-orch-04-6 | 異常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-04-7 | 境界値 | 単体 | `orchestrator/trigger_test.go::TestEvaluate_PreDispatchIrreversible` | 実装済み |
| FR-orch-04-8 | 境界値 | 単体 | `orchestrator/trigger_test.go::TestEvaluate_PreDispatchApprovedIrreversibleDoesNotFire`, `orchestrator/controller_test.go::TestIntervene_ResolveApprovesIrreversible` | 実装済み |
| FR-orch-04-9 | 境界値 | 単体 | - | 未検証(テスト未実装) |
| FR-orch-05-1 | 正常系 | 単体 | `orchestrator/archive_test.go::TestArchiveRun_MovesNotDeletes`, `::TestArchiveRun_NoState` | 実装済み |
| FR-orch-05-2 | 正常系 | 単体 | - | 未検証(テスト未実装) |
| FR-orch-05-3 | 正常系 | 単体 | `orchestrator/plan_test.go::TestStatusTransition_HappyPath`, `::TestReviseDoesNotIncrementAttempts`, `::TestAllDoneAndSettled` | 実装済み |
| FR-orch-05-4 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-05-5 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-05-6 | 境界値 | 単体 | `orchestrator/state_test.go::TestStateRoundTrip`, `::TestPlanRoundTrip`, `::TestControlRoundTripAndDelete`, `::TestSidecarRoundTrip` | 実装済み |
| FR-orch-05-7 | 異常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-05-8 | 境界値 | 単体 | - | 未検証(テスト未実装) |
| FR-orch-05-9 | 境界値 | 単体 | - | 未検証(テスト未実装) |
| FR-orch-05-10 | 異常系 | 単体 | `orchestrator/state_test.go::TestLoadStateMissing` | 実装済み |
| FR-orch-06-1 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-06-2 | 正常系 | 単体 | - | 未検証(テスト未実装) |
| FR-orch-06-3 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-06-4 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-06-5 | 境界値 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-06-6 | 境界値 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-06-7 | 異常系 | 単体 | `orchestrator/accept_test.go::TestReview_ReformatsProseToJSON`, `orchestrator/review_parse_test.go::TestFindReviewResultJSON_StrictAndTolerant` | 実装済み |
| FR-orch-07-1 | 正常系 | 単体 | `orchestrator/models_test.go::TestTaskKindProfile`, `::TestWorkerTaskProfile`, `::TestRoleProfiles` | 実装済み |
| FR-orch-07-2 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-07-3 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-07-4 | 境界値 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-08-1 | 正常系 | 単体 | `orchestrator/dashtui_test.go::TestDashCursor_MovesAndClamps`, `::TestDashEnter_OnWaitingHumanSendsResolve`, `::TestDashView_BrainstormingIsCursorSelect`, `::TestDashQuit_SendsQuit` | 実装済み |
| FR-orch-08-2 | 正常系 | 単体 | `orchestrator/term_test.go::TestBuildQuestion_NumbersOptions`, `::TestResolveMenu_NumberImmediate` | 実装済み |
| FR-orch-08-3 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-08-4 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-08-5 | 正常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-08-6 | 境界値 | 単体 | `orchestrator/term_test.go::TestSelectMenu_NonTTYReturnsDefault`, `::TestTerminalConfirm_NonTTYContinue`, `::TestResolveMenu_NoInputReturnsCurrent` | 実装済み |
| FR-orch-08-7 | 異常系 | 単体 | `orchestrator/dashboard_test.go::TestReadVMHealthBanner_StaleIgnored`, `::TestReadVMHealthBanner_WarnFresh`, `::TestReadVMHealthBanner_OKIsSilent` | 実装済み |
| FR-orch-08-8 | 異常系 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| FR-orch-09-2 | 正常系 | 単体 | `examples/orch-sample` の pytest 一式(`cd examples/orch-sample && pytest`) | 実装済み |
| NFR-perf-03 | 非機能 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| NFR-avail-01 | 非機能 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| NFR-sec-03 | 非機能 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |
| NFR-ops-04 | 非機能 | E2E | E2E-04(実機確認手順) | 未検証(テスト未実装) |

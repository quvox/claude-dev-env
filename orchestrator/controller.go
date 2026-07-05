package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"strings"
	"sync"
	"time"

	tea "github.com/charmbracelet/bubbletea"
)

// errSuspended is returned by the executing loop when the human presses [q]
// ("中断"). It is NOT an error condition: the run state is left at executing so
// the next launch resumes. Run translates it into a clean exit.
var errSuspended = errors.New("suspended by user")

// Controller drives the state machine and run loop.
type Controller struct {
	Store    *Store
	Cfg      Config
	Mode     *Mode
	Handoff  *Handoff
	Worker   *Worker
	Reviewer *Reviewer
	Notifier Notifier

	// Sessions manages the per-component tmux sessions (独立ウィンドウ方式・
	// docs/impl/60「独立ウィンドウ方式（新アーキ）」). nil in tests/headless: all
	// session hooks below are nil-guarded and best-effort, so behavior is
	// unchanged when it is absent.
	Sessions *SessionManager

	// Confirm asks the human a brainstorming continuation question on the terminal
	// when control.json is missing/invalid. canExecute gates whether the "実行"
	// option is offered at all (only when the plan is actually ready+lint-clean;
	// otherwise ブレインストーミング is not finished and execute must not be presented). Returns
	// one of "continue", "execute", "done". Injectable for tests/headless.
	Confirm func(prompt string, canExecute bool) string

	// planMu guards all reads/writes of *Plan and Store mutations during the
	// concurrent execution phase. mergeMu serializes integrate() so concurrent
	// worktree merges into the working branch cannot race.
	planMu  sync.Mutex
	mergeMu sync.Mutex
}

// Run executes the full lifecycle starting from the persisted (or fresh) state.
func (c *Controller) Run(ctx context.Context) error {
	// tmux 常駐方式: コントローラは orch-<CNAME>-main セッションの中で回る。自分の
	// ウィンドウを "dashboard" に改名し、mouse off を確定する（worker/ブレインストーミングは同
	// セッションの別ウィンドウとしてぶら下げる。docs/06 §4.2）。best-effort。
	if c.Sessions != nil && tmuxAvailable() {
		c.Sessions.SetupMainSession(ctx)
	}
	st, err := c.Store.LoadState()
	if err != nil {
		return err
	}
	if st == nil {
		st = &State{Phase: PhaseBrainstorming, RunID: newRunID()}
		if err := c.Store.SaveState(st); err != nil {
			return err
		}
		_ = c.Store.AppendAudit(AuditEntry{Event: "run_start", Detail: map[string]any{"run_id": st.RunID}})
	} else if st.Phase == PhaseExecuting {
		// Resume: plan.json is canonical; ignore residual control.json.
		_ = c.Handoff.DiscardStale()
	}

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}
		switch st.Phase {
		case PhaseBrainstorming:
			if err := c.runBrainstorming(ctx, st); err != nil {
				return err
			}
		case PhaseExecuting:
			if err := c.runExecuting(ctx, st); err != nil {
				if errors.Is(err, errSuspended) {
					// User interrupted (Ctrl-C / [q]): state is left resumable; exit
					// cleanly so the next `claude-dev orchestrate` continues from here.
					return nil
				}
				return err
			}
		case PhaseDone:
			_ = c.Store.AppendAudit(AuditEntry{Event: "run_done", Detail: map[string]any{"run_id": st.RunID}})
			return nil
		default:
			return fmt.Errorf("unknown phase %q", st.Phase)
		}
	}
}

// ---- brainstorming ----

func (c *Controller) runBrainstorming(ctx context.Context, st *State) error {
	printModeBanner("brainstorming")
	var (
		ctrl *Control
		err  error
	)
	if c.Sessions != nil && tmuxAvailable() {
		// tmux 常駐方式：ブレインストーミングは brainstorming セッション内で動かし、control.json を
		// ポーリング監視する（自 pane＝main のダッシュボード枠を奪わない。docs/06 §4.2）。
		ctrl = c.runBrainstormingSession(ctx)
	} else {
		// Legacy fallback (no tmux / headless): foreground child in this pane.
		if rerr := c.Mode.RunInteractive(ctx, c.Mode.BrainstormingArgs()...); rerr != nil {
			_ = c.Store.AppendAudit(AuditEntry{Event: "brainstorming_exit", Detail: map[string]any{"err": rerr.Error()}})
		}
		ctrl, err = c.Handoff.Consume()
		if err != nil {
			return err
		}
	}
	plan, _ := c.Store.LoadPlan()

	if ctrl != nil {
		switch ctrl.Request {
		case ReqExecute:
			if plan != nil && plan.Ready && lintPlan(plan) == "" {
				c.closeBrainstormingSession()
				return c.transition(st, PhaseExecuting)
			}
			// execute requested but plan not executable (not ready or a task
			// lacks completion). Do NOT go silent and do NOT show the menu:
			// explain on the terminal and hand the reason back to the brain, then
			// stay in brainstorming so it fixes the plan next round (docs/06 §4.5/§8.1).
			c.reportNotExecutable(plan)
			return nil
		case ReqAbort:
			c.closeBrainstormingSession()
			return c.transition(st, PhaseDone)
		case ReqContinueBrainstorming:
			return nil // stay in brainstorming; loop re-runs interactive
		}
	}

	// No decisive control.json: ask the human via a cursor/number menu. The
	// "実行" option is offered ONLY when the plan is genuinely executable (ready +
	// every task has completion); otherwise ブレインストーミング is not finished, so we present
	// only 続ける/終了 (docs/06 §4.5).
	canExec := plan != nil && plan.Ready && lintPlan(plan) == ""
	switch c.confirm("ブレインストーミング: 次の操作を選んでください", canExec) {
	case "execute":
		if canExec {
			c.closeBrainstormingSession()
			return c.transition(st, PhaseExecuting)
		}
		c.reportNotExecutable(plan)
		return nil
	case "done":
		c.closeBrainstormingSession()
		return c.transition(st, PhaseDone)
	default:
		return nil // continue brainstorming
	}
}

// runBrainstormingSession launches the brainstorming brain in its OWN window and
// watches control.json until the human /exits (独立ウィンドウ方式・docs/06 §4.2/§5.9).
//
// The dashboard window stays the HOME view: we launch the brainstorming claude
// WITHOUT switching to its window (keep the dashboard active) and run the
// bubbletea dashboard TUI there in the brainstorming phase — the SAME
// cursor-select UI as executing, offering the brainstorming window as the single
// navigable target (↑↓/Enter, not raw `Ctrl-_ w`). The watch never forces the
// view. Returns the consumed Control (nil if the human exited without a handoff,
// which the caller resolves via the confirm menu).
func (c *Controller) runBrainstormingSession(ctx context.Context) *Control {
	name := c.Sessions.BrainstormingWindow()
	script, err := c.Mode.WriteLaunchScript("brainstorming", c.Mode.brainstormingInstr(), "")
	if err != nil {
		_ = c.Store.AppendAudit(AuditEntry{Event: "brainstorming_launch_error", Detail: map[string]any{"err": err.Error()}})
		return nil
	}
	// Run (not LaunchInteractive): create the brainstorming window with the claude
	// but do NOT select-window to it — Ensure uses `new-window -d`, so the
	// dashboard window remains current (home).
	_ = c.Sessions.Run(ctx, name, "sh "+shellSingleQuote(script))
	_ = c.Sessions.SwitchTo(ctx, c.Sessions.DashboardWindow())

	// Dashboard TUI in the brainstorming phase: the SAME cursor-select UI as
	// executing (docs/06 §5.3). It offers the brainstorming window as the single
	// navigable target — the human moves there with ↑↓/Enter, NOT raw `Ctrl-_ w`
	// (consistency was the point). Runs on the dashboard window's PTY, independent
	// of the claude in the brainstorming window.
	dash := &DashboardState{Phase: PhaseBrainstorming}
	if plan, _ := c.Store.LoadPlan(); plan != nil {
		dash.Goal = plan.Goal
	}
	actions := make(chan dashAction, 8)
	var prog *tea.Program
	if isTTY() {
		prog = newDashProgram(ctx, dash, c.Store, c.Sessions, actions)
		go func() { _, _ = prog.Run() }()
	}
	ctrl, _ := c.Handoff.WaitConsume(ctx, 500*time.Millisecond, func() bool {
		return !c.Sessions.Has(ctx, name) || c.Sessions.PaneDead(ctx, name) // /exit without a handoff
	})
	if prog != nil {
		prog.Quit()
	}
	_ = c.Sessions.SwitchTo(ctx, c.Sessions.DashboardWindow())
	return ctrl
}

// closeBrainstormingSession tears down the brainstorming session (best-effort) when
// leaving brainstorming (docs/06 §4.2: 実行フェーズでは不要なら閉じる).
func (c *Controller) closeBrainstormingSession() {
	if c.Sessions != nil {
		_ = c.Sessions.Kill(context.Background(), c.Sessions.BrainstormingWindow())
	}
}

// openWorkerSession creates this worker's tmux session (holder shell) and shows
// its live log via `tail -F` (独立ウィンドウ方式・docs/impl/60). Best-effort and
// nil-guarded: no-op when Sessions is unset (tests/headless) or tmux is absent.
// The session persists across the worker's claude -p → intervene → re-dispatch;
// only closeWorkerSession (on settle) tears it down.
func (c *Controller) openWorkerSession(taskID string) {
	if c.Sessions == nil {
		return
	}
	name := c.Sessions.WorkerWindow(taskID)
	_ = c.Sessions.Run(context.Background(), name, "tail -n +1 -F "+c.Store.WorkerLogPath(taskID))
}

// closeWorkerSession tears down this worker's session (called when the task
// settles: done/failed/blocked). waiting_human tasks keep their session for the
// in-session intervention (Phase③ 3c).
func (c *Controller) closeWorkerSession(taskID string) {
	if c.Sessions == nil {
		return
	}
	_ = c.Sessions.Kill(context.Background(), c.Sessions.WorkerWindow(taskID))
}

// reportNotExecutable explains on the terminal (never silently) why execution
// cannot start, records it to the audit log and Slack, and hands the reason to
// the next brainstorming brain via handoff_note.md so it fixes the plan without the
// human relaying it. The wording never asks the human to edit plan.json (that is
// the brain's job — docs/06 §4.3/§4.5). Japanese (docs/06 §5.7).
func (c *Controller) reportNotExecutable(plan *Plan) {
	var reason, note string
	switch {
	case plan == nil || len(plan.Tasks) == 0:
		reason = "plan がまだありません。ブレインストーミング（対話）でゴールとタスクを固めてください。"
		note = reason
	case !plan.Ready:
		reason = "plan がまだ ready ではありません。ブレインストーミングで詰めてから実行してください。"
		note = reason
	default:
		missing := lintPlan(plan)
		if missing == "" {
			return // actually executable; nothing to report
		}
		reason = fmt.Sprintf("各タスクに completion（受け入れ基準）が必要です。未設定: %s。ブレインストーミングに戻って対話で completion を補ってください（plan.json はブレインストーミング脳が更新します）。", missing)
		note = fmt.Sprintf("前回の実行差し戻し理由: 次のタスクに completion が未設定でした: %s。各タスクに具体的な completion を必ず付与してから ready=true にして execute してください。", missing)
	}
	_ = c.Store.AppendAudit(AuditEntry{Event: "plan_not_executable", Detail: map[string]any{"reason": reason}})
	if isTTY() {
		fmt.Fprintf(os.Stderr, "\n\x1b[1;33m⚠ 実行できません: %s\x1b[0m\n\n", reason)
	}
	goal := ""
	if plan != nil {
		goal = plan.Goal
	}
	c.Notifier.Notify(fmt.Sprintf("[%s] 実行不可: %s", goal, oneline(reason, 200)))
	_ = c.Store.WriteAtomicSidecar("handoff_note.md", note)
}

func (c *Controller) confirm(prompt string, canExecute bool) string {
	if c.Confirm != nil {
		return c.Confirm(prompt, canExecute)
	}
	// Headless / no confirm hook: default to continuing brainstorming (safe; the
	// human can re-attach). Never auto-execute.
	return "continue"
}

// ---- executing ----

func (c *Controller) runExecuting(ctx context.Context, st *State) error {
	plan, err := c.Store.LoadPlan()
	if err != nil {
		return err
	}
	if plan == nil {
		// No plan to execute; nothing to do.
		return c.transition(st, PhaseDone)
	}

	// Normalize stale in-flight statuses on (re)entry: running/review/revise are
	// reset to pending (and flagged to resume their session). done/failed/blocked
	// and waiting_human are preserved (completed work is never redone; parked
	// interventions stay parked).
	c.planMu.Lock()
	NormalizeForResume(plan)
	_ = c.Store.SavePlan(plan)
	c.planMu.Unlock()

	printModeBanner("executing")

	dash := &DashboardState{Phase: PhaseExecuting, Goal: plan.Goal}
	syncDashboard(dash, plan)
	c.refreshInterventionCount(dash)

	// workerCtx bounds the worker goroutines. It is cancelled only on suspend/
	// quit/abort — NEVER on an intervention. Interventions are per-task and must
	// not stop peer workers (the central fix).
	workerCtx, workerCancel := context.WithCancel(ctx)
	defer workerCancel()

	var (
		wg       sync.WaitGroup
		inflight = map[string]bool{}
	)

	// Dashboard: a bubbletea TUI on the `dashboard` window's own PTY (docs/06 §5.3).
	// It runs independently of the claude instances in the brainstorming/worker windows
	// (separate panes), so it keeps rendering while the human is switched away — no
	// stop/start dance needed. Only started on a TTY; headless/tests run the loop
	// with no UI. User actions needing the controller arrive on `actions`; cursor
	// movement, [p] pause (toggles dash.Paused) and [d] detail are handled in-model.
	actions := make(chan dashAction, 8)
	var prog *tea.Program
	if isTTY() {
		prog = newDashProgram(ctx, dash, c.Store, c.Sessions, actions)
		go func() { _, _ = prog.Run() }()
		defer prog.Quit()
	}

	scheduleTick := func() {
		var notifies []string
		c.planMu.Lock()
		ready := ReadyTasks(plan, len(plan.Tasks))
		for _, t := range ready {
			if len(inflight) >= c.Cfg.MaxWorkers {
				break
			}
			if inflight[t.ID] {
				continue
			}
			// Condition 1 (pre-dispatch): irreversible tasks are parked as
			// waiting_human and queued as a per-task intervention. Keep scheduling
			// the OTHER ready tasks (do not stop peers).
			if f, r := Evaluate(TriggerContext{Phase: PhasePreDispatch, Task: t, Plan: plan, State: st, Config: c.Cfg}); f {
				if msg := c.openInterventionLocked(plan, t, r); msg != "" {
					notifies = append(notifies, msg)
				}
				// 独立ウィンドウ方式: pre-dispatch で ⏸ になったタスクにも worker
				// セッションを起こし、セレクタから介入対話へ切り替えられるようにする
				// （⏸ のタスクには必ずセッションが在る不変条件。docs/06 §4.2）。
				c.openWorkerSession(t.ID)
				continue
			}
			// Reserve the slot. A resume continues the SAME attempt/session; a
			// fresh dispatch is a NEW attempt with a new session id. In the resume
			// case ResumeSession is left TRUE here so the plan snapshot taken in
			// runTaskPipeline carries it to the worker (--resume); it is cleared
			// there right after snapshotting so a later retry starts a new attempt.
			if t.ResumeSession && t.SessionID != "" {
				// same attempt: keep SessionID + ResumeSession, do NOT ++Attempts
			} else {
				t.Attempts++
				t.SessionID = newSessionID()
				t.ResumeSession = false
			}
			t.Status = TaskRunning
			inflight[t.ID] = true
			taskID := t.ID
			attempt := t.Attempts
			_ = c.Store.SavePlan(plan)
			_ = c.Store.AppendAudit(AuditEntry{Event: "dispatch", TaskID: taskID, Detail: map[string]any{"attempt": attempt}})
			c.openWorkerSession(taskID) // 独立セッション: この worker のビュー（ログ tail）を起こす
			wg.Add(1)
			go func() {
				defer wg.Done()
				c.runTaskPipeline(workerCtx, st, plan, taskID)
				c.planMu.Lock()
				delete(inflight, taskID)
				_ = c.Store.SavePlan(plan)
				settled := false
				if ft := findTask(plan, taskID); ft != nil {
					settled = ft.Status == TaskDone || ft.Status == TaskFailed || ft.Status == TaskBlocked
				}
				syncDashboard(dash, plan)
				c.planMu.Unlock()
				if settled {
					c.closeWorkerSession(taskID) // settle でセッションを閉じる（waiting_human は残す）
				}
			}()
		}
		syncDashboard(dash, plan)
		c.planMu.Unlock()
		for _, m := range notifies {
			c.Notifier.Notify(m)
		}
		c.refreshInterventionCount(dash)
	}

	// suspend stops workers (giving them their grace window to commit) and leaves
	// the run resumable. Used for both Ctrl-C and [q].
	suspend := func() error {
		workerCancel()
		wg.Wait()
		c.planMu.Lock()
		_ = c.Store.SavePlan(plan)
		c.planMu.Unlock()
		_ = c.Store.AppendAudit(AuditEntry{Event: "suspended", Detail: map[string]any{"run_id": st.RunID}})
		return errSuspended
	}

	var lastEnsure time.Time // throttle periodic session recovery (docs/06 §5.9)
	for {
		select {
		case <-ctx.Done():
			// Signal (Ctrl-C) or parent cancel: clean, resumable suspend (same as
			// [q]). Workers get their RunOpts grace window before force-kill.
			return suspend()
		case a := <-actions:
			// User actions from the TUI (docs/06 §5.3). Cursor/[p]/[d] are handled
			// in the model; only these reach the controller.
			switch a.kind {
			case "quit":
				return suspend()
			case "resolve", "intervene":
				// Enter on a ⏸ worker (resolve, carries taskID) or [i] (intervene =
				// first open). Both open the intervention in that worker's window;
				// the dashboard stays live, peers keep running.
				taskID := a.taskID
				if a.kind == "intervene" {
					items := c.Store.LoadOpenInterventions().Items
					if len(items) == 0 {
						continue
					}
					taskID = items[0].TaskID
				}
				aborted, rerr := c.resolveInterventionInSession(ctx, taskID)
				if rerr != nil {
					workerCancel()
					wg.Wait()
					return rerr
				}
				if aborted {
					workerCancel()
					wg.Wait()
					return c.transition(st, PhaseDone)
				}
				continue
			}
		default:
		}

		// 独立ウィンドウ方式: 誤って閉じられた worker セッションを実行中なら再構築
		// する（復旧。docs/06 §5.9）。tmux 呼び出しを抑えるため数秒に一度だけ。
		if c.Sessions != nil && time.Since(lastEnsure) > 5*time.Second {
			lastEnsure = time.Now()
			c.planMu.Lock()
			var active []string
			for i := range plan.Tasks {
				switch plan.Tasks[i].Status {
				case TaskRunning, TaskReview, TaskRevise, TaskWaitingHuman:
					active = append(active, plan.Tasks[i].ID)
				}
			}
			c.planMu.Unlock()
			for _, tid := range active {
				if !c.Sessions.Has(ctx, c.Sessions.WorkerWindow(tid)) {
					c.openWorkerSession(tid)
				}
			}
		}

		if dashPaused(dash) {
			time.Sleep(50 * time.Millisecond)
			continue
		}

		scheduleTick()

		c.planMu.Lock()
		anyInflight := len(inflight) > 0
		ready := ReadyTasks(plan, len(plan.Tasks))
		if len(ready) == 0 && !anyInflight {
			MarkBlockedByFailedDeps(plan)
			_ = c.Store.SavePlan(plan)
			settled := AllSettled(plan)
			c.planMu.Unlock()
			if settled {
				break // no dispatchable work and no parked interventions -> complete
			}
			// Nothing to dispatch but not settled: waiting_human tasks remain
			// (AllSettled is false while any task is waiting_human). Idle-wait for
			// the human to press [i] (or [q]).
			time.Sleep(50 * time.Millisecond)
			continue
		}
		c.planMu.Unlock()
		time.Sleep(20 * time.Millisecond)
	}

	// All tasks settled with no open interventions: verify completion.
	workerCancel()
	wg.Wait()
	c.planMu.Lock()
	_ = c.Store.SavePlan(plan)
	syncDashboard(dash, plan)
	c.planMu.Unlock()
	if prog != nil {
		prog.Quit() // tear down the TUI before the (headless) completion check
	}

	return c.verifyCompletion(ctx, st, plan)
}

// runTaskPipeline runs worker -> review -> revise for one task. A fired trigger
// parks the task as waiting_human via the intervention queue and returns; peers
// are never stopped. On cancellation the task is reset to pending (with its
// session preserved for --resume).
func (c *Controller) runTaskPipeline(ctx context.Context, st *State, plan *Plan, taskID string) {
	if ctx.Err() != nil {
		c.resetToPending(plan, taskID)
		return
	}

	c.planMu.Lock()
	st.CurrentTask = taskID
	_ = c.Store.SaveState(st)
	snap := snapshotPlan(plan)
	t := findTask(plan, taskID)
	if t == nil {
		c.planMu.Unlock()
		return
	}
	feedback := attemptFeedback(t)
	// The snapshot above carries ResumeSession for this dispatch (so the worker
	// runs --resume). Consume it on the live task now so that if THIS attempt
	// fails and is retried, the retry starts a fresh session/new attempt.
	t.ResumeSession = false
	_ = c.Store.SavePlan(plan)
	c.planMu.Unlock()

	snapTask := findTask(snap, taskID)

	res, err := c.Worker.Dispatch(ctx, snap, snapTask, feedback)
	if err != nil {
		if ctx.Err() != nil {
			c.resetToPending(plan, taskID)
			return
		}
		c.planMu.Lock()
		_ = c.Store.AppendAudit(AuditEntry{Event: "dispatch_error", TaskID: taskID, Detail: map[string]any{"err": err.Error()}})
		t := findTask(plan, taskID)
		if reason, stuck := c.evalStuck(t); stuck {
			msg := c.openInterventionLocked(plan, t, reason)
			c.planMu.Unlock()
			c.notify(msg)
			return
		}
		t.Status = TaskPending // retry as a new Attempt next scheduling tick
		c.planMu.Unlock()
		return
	}

	// Record assumptions and result under the lock.
	c.planMu.Lock()
	t = findTask(plan, taskID)
	t.Result = res
	for _, a := range res.Assumptions {
		_ = c.Store.AppendAssumption(Assumption{TaskID: taskID, Description: a})
	}
	c.planMu.Unlock()

	// Post-dispatch triggers (2/4/5) and stuck (3).
	c.planMu.Lock()
	t = findTask(plan, taskID)
	if f, r := Evaluate(TriggerContext{Phase: PhasePostDispatch, Task: t, Plan: plan, State: st, Result: res, Config: c.Cfg}); f {
		msg := c.openInterventionLocked(plan, t, r)
		c.planMu.Unlock()
		c.notify(msg)
		return
	}
	c.planMu.Unlock()

	if !res.Done {
		c.planMu.Lock()
		t = findTask(plan, taskID)
		if reason, stuck := c.evalStuck(t); stuck {
			msg := c.openInterventionLocked(plan, t, reason)
			c.planMu.Unlock()
			c.notify(msg)
			return
		}
		t.Status = TaskPending
		c.planMu.Unlock()
		return
	}

	// Quality gate: review/revise loop within this Attempt (against snapshot).
	outcome, rerr := c.Reviewer.RunGate(ctx, snap, snapTask)
	if rerr != nil {
		if ctx.Err() != nil {
			c.resetToPending(plan, taskID)
			return
		}
		c.planMu.Lock()
		_ = c.Store.AppendAudit(AuditEntry{Event: "review_error", TaskID: taskID, Detail: map[string]any{"err": rerr.Error()}})
		findTask(plan, taskID).Status = TaskPending
		c.planMu.Unlock()
		return
	}

	// Reviewer format defect (unparseable output N times): escalate as a gate
	// defect WITHOUT re-running the worker (the implementation is already done).
	if outcome.FormatError {
		c.planMu.Lock()
		t = findTask(plan, taskID)
		t.ReviewFormatErrors = outcome.FormatErrorCount
		msg := c.openInterventionLocked(plan, t, TriggerReviewGateDefect)
		c.planMu.Unlock()
		c.notify(msg)
		return
	}

	// Mirror any revise-produced result back to the live task; clear the format
	// error run (a content verdict was obtained).
	c.planMu.Lock()
	t = findTask(plan, taskID)
	if snapTask.Result != nil {
		t.Result = snapTask.Result
	}
	t.ReviewFormatErrors = 0
	c.planMu.Unlock()

	if outcome.Passed {
		// Integrate the worktree commits into the working branch. Serialize all
		// merges to avoid concurrent merge conflicts on the working branch.
		c.mergeMu.Lock()
		ierr := c.integrate(ctx, taskID)
		c.mergeMu.Unlock()
		c.planMu.Lock()
		t = findTask(plan, taskID)
		if ierr != nil {
			_ = c.Store.AppendAudit(AuditEntry{Event: "merge_error", TaskID: taskID, Detail: map[string]any{"err": ierr.Error()}})
			t.Status = TaskPending // retry as a new Attempt
			c.planMu.Unlock()
			return
		}
		t.Status = TaskDone
		t.SessionID = "" // attempt complete; no session to resume
		t.ResumeSession = false
		_ = c.Store.AppendAudit(AuditEntry{Event: "task_done", TaskID: taskID})
		c.updateSummaryLocked(plan)
		c.planMu.Unlock()
		return
	}

	// Severe findings remain after max_review_rounds: stuck (condition 3b).
	c.planMu.Lock()
	t = findTask(plan, taskID)
	if f, r := Evaluate(TriggerContext{Phase: PhasePostDispatch, Task: t, Plan: plan, State: st, Config: c.Cfg, StuckThisAttempt: true}); f {
		msg := c.openInterventionLocked(plan, t, r)
		c.planMu.Unlock()
		c.notify(msg)
		return
	}
	t.Status = TaskPending
	c.planMu.Unlock()
}

// notify sends a Slack message if non-empty (helper to keep callers terse).
func (c *Controller) notify(msg string) {
	if msg != "" {
		c.Notifier.Notify(msg)
	}
}

// evalStuck evaluates only the stuck (condition 3) trigger for a task. Caller
// must hold planMu. Returns (reason, true) when stuck.
func (c *Controller) evalStuck(t *Task) (string, bool) {
	if f, r := Evaluate(TriggerContext{Phase: PhasePostDispatch, Task: t, State: &State{}, Plan: &Plan{}, Config: c.Cfg}); f {
		return r, true
	}
	return "", false
}

// resetToPending marks a task pending under the lock (used on cancellation).
// It preserves the session and flags a resume so the interrupted attempt
// continues via --resume on the next dispatch (no work redone).
func (c *Controller) resetToPending(plan *Plan, taskID string) {
	c.planMu.Lock()
	defer c.planMu.Unlock()
	if t := findTask(plan, taskID); t != nil && t.Status != TaskDone && t.Status != TaskWaitingHuman {
		t.Status = TaskPending
		if t.SessionID != "" {
			t.ResumeSession = true
		}
	}
	_ = c.Store.SavePlan(plan)
}

// integrate merges the task worktree branch into the working branch. Callers
// must hold mergeMu so concurrent merges into the working branch are serialized.
func (c *Controller) integrate(ctx context.Context, taskID string) error {
	branch := "orch/" + taskID
	return c.Worker.Git.Merge(ctx, c.Worker.Workspace, branch, c.Cfg.MergeStrategy)
}

// openInterventionLocked parks a task as waiting_human and enqueues a per-task
// intervention (question.md + open.json + audit). Caller MUST hold planMu.
// Returns a Slack notification string to send AFTER releasing the lock (so
// network I/O never happens under planMu). Idempotent for an already-parked task.
func (c *Controller) openInterventionLocked(plan *Plan, t *Task, reason string) string {
	if t.Status == TaskWaitingHuman && t.OpenInterventionID != "" {
		return ""
	}
	id := newInterventionID()
	q := buildQuestion(t, reason)
	_ = c.Store.WriteQuestion(id, q)
	_ = c.Store.AppendIntervention(Intervention{ID: id, TaskID: t.ID, TriggerReason: reason, Question: q})
	_ = c.Store.AddOpenIntervention(OpenIntervention{ID: id, TaskID: t.ID, TriggerReason: reason})
	t.Status = TaskWaitingHuman
	t.OpenInterventionID = id
	_ = c.Store.SavePlan(plan)
	_ = c.Store.AppendAudit(AuditEntry{Event: "intervention_open", TaskID: t.ID, Detail: map[string]any{"id": id, "reason": reason}})
	n := len(c.Store.LoadOpenInterventions().Items)
	return fmt.Sprintf("[%s] 要判断 %d 件: %s。attach し [i] で対応してください（実行は継続中）。", plan.Goal, n, oneline(q, 80))
}

// openInterventionCount returns the number of unresolved interventions.
func (c *Controller) openInterventionCount() int {
	return len(c.Store.LoadOpenInterventions().Items)
}

// refreshInterventionCount publishes the open-intervention count to the dashboard.
func (c *Controller) refreshInterventionCount(dash *DashboardState) {
	q := c.Store.LoadOpenInterventions()
	taskIDs := make([]string, 0, len(q.Items))
	for _, it := range q.Items {
		taskIDs = append(taskIDs, it.TaskID)
	}
	dash.Set(func(s *DashboardState) {
		s.InterventionsOpen = len(taskIDs)
		titles := make([]string, 0, len(taskIDs))
		for _, tid := range taskIDs {
			label := tid
			for _, dt := range s.Tasks {
				if dt.ID == tid && dt.Title != "" {
					label = tid + " " + dt.Title
					break
				}
			}
			titles = append(titles, label)
		}
		s.OpenTitles = titles
	})
}

// ---- interventions (resolution) ----

// resolveInterventions launches the interactive brain to answer the open queue,
// then reconciles: each intervention that now has an answer is recorded and its
// task returned to pending for re-dispatch. Returns aborted=true if the human
// requested abort. It does NOT stop peer workers (they run in the background
// while the interactive session holds the foreground).
func (c *Controller) resolveInterventions(ctx context.Context, st *State, plan *Plan) (aborted bool, err error) {
	q := c.Store.LoadOpenInterventions()
	if len(q.Items) == 0 {
		return false, nil
	}
	ids := make([]string, 0, len(q.Items))
	for _, it := range q.Items {
		ids = append(ids, it.ID)
	}
	printModeBanner("intervene")
	if rerr := c.Mode.RunInteractive(ctx, c.Mode.ResolveArgs(ids)...); rerr != nil {
		_ = c.Store.AppendAudit(AuditEntry{Event: "intervene_exit", Detail: map[string]any{"err": rerr.Error()}})
	}
	ctrl, cerr := c.Handoff.Consume()
	if cerr != nil {
		return false, cerr
	}
	if ctrl != nil && ctrl.Request == ReqAbort {
		return true, nil
	}
	// Reconcile answered interventions.
	c.planMu.Lock()
	defer c.planMu.Unlock()
	for _, it := range q.Items {
		c.reconcileOne(plan, it.ID, it.TaskID)
	}
	_ = c.Store.SavePlan(plan)
	return false, nil
}

// reconcileOne applies a single answered intervention: if answer.md is non-empty,
// it records the answer, removes the entry from the open queue, and returns the
// task to pending for a fresh re-dispatch (docs/06 §5.5). Returns true when it
// was resolved (an answer was present); false leaves the intervention open (the
// human exited before recording — safe, per docs/06 §5.2③). Caller MUST hold
// planMu. Shared by the batch path (resolveInterventions) and the per-worker
// session path (resolveOne / selector, Phase③ 3d).
func (c *Controller) reconcileOne(plan *Plan, id, taskID string) bool {
	ans, _ := c.Store.ReadAnswer(id)
	if strings.TrimSpace(ans) == "" {
		return false
	}
	_ = c.Store.AppendIntervention(Intervention{ID: id, TaskID: taskID, Answer: ans})
	_ = c.Store.RemoveOpenIntervention(id)
	if t := findTask(plan, taskID); t != nil && t.Status != TaskDone {
		if t.Irreversible {
			t.IrrevApproved = true // approved: pre-dispatch trigger1 won't re-fire
		}
		t.Status = TaskPending
		t.OpenInterventionID = ""
		// Re-approach with the human's guidance as a fresh attempt.
		t.SessionID = ""
		t.ResumeSession = false
	}
	_ = c.Store.AppendAudit(AuditEntry{Event: "intervention_resolved", TaskID: taskID, Detail: map[string]any{"id": id}})
	return true
}

// resolveOne reconciles a single intervention after its in-session dialogue
// (独立ウィンドウ方式・per-worker。docs/06 §5.5). It locks, loads the plan,
// reconciles the one entry, and saves. Returns true if resolved. Used by the
// worker-selector path (Phase③ 3d) after the human answers in that worker's
// session; the intervene launch + handoff watch land with the daemon watch-model
// (Phase③ 3e).
func (c *Controller) resolveOne(id, taskID string) bool {
	c.planMu.Lock()
	defer c.planMu.Unlock()
	plan, err := c.Store.LoadPlan()
	if err != nil || plan == nil {
		return false
	}
	if c.reconcileOne(plan, id, taskID) {
		_ = c.Store.SavePlan(plan)
		return true
	}
	return false
}

// resolveInterventionInSession runs a single intervention inside its worker's
// tmux session (独立ウィンドウ方式・docs/06 §5.3/§6.3): it injects the intervene
// brain (seeded with that one question) into orch-<CNAME>-main:w-<taskID>, switches
// the client there, watches control.json until the human /exits, switches back
// to main, then reconciles the answer (→ pending → re-dispatch). Peers keep
// running; the dashboard stays live in main. Returns aborted=true if the human
// requested abort. When the task has no open intervention it just views the
// session. Requires c.Sessions (guarded by callers).
func (c *Controller) resolveInterventionInSession(ctx context.Context, taskID string) (bool, error) {
	if c.Sessions == nil {
		return false, nil
	}
	name := c.Sessions.WorkerWindow(taskID)
	id := c.openIDForTask(taskID)
	if id == "" {
		_ = c.Sessions.SwitchTo(ctx, name) // nothing to resolve: just show it
		return false, nil
	}
	sys, prompt := c.Mode.IntervenePrompt(id)
	script, err := c.Mode.WriteLaunchScript("w-"+taskID, sys, prompt)
	if err != nil {
		_ = c.Store.AppendAudit(AuditEntry{Event: "intervene_launch_error", TaskID: taskID, Detail: map[string]any{"err": err.Error()}})
		return false, nil
	}
	printModeBanner("intervene")
	_ = c.Sessions.LaunchInteractive(ctx, name, script)
	ctrl, cerr := c.Handoff.WaitConsume(ctx, 500*time.Millisecond, func() bool {
		return !c.Sessions.Has(ctx, name) || c.Sessions.PaneDead(ctx, name)
	})
	_ = c.Sessions.SwitchTo(ctx, c.Sessions.DashboardWindow())
	if cerr != nil {
		return false, cerr
	}
	if ctrl != nil && ctrl.Request == ReqAbort {
		return true, nil
	}
	c.resolveOne(id, taskID) // reconcile answer.md → pending (re-dispatched next tick)
	return false, nil
}

// openIDForTask returns the open intervention id for a task, or "" if none.
func (c *Controller) openIDForTask(taskID string) string {
	for _, it := range c.Store.LoadOpenInterventions().Items {
		if it.TaskID == taskID {
			return it.ID
		}
	}
	return ""
}

// lintPlan returns a comma-joined list of task IDs missing a task-specific
// completion criterion (empty string == lint clean). docs/06 §8.1.
func lintPlan(plan *Plan) string {
	var missing []string
	for i := range plan.Tasks {
		if strings.TrimSpace(plan.Tasks[i].Completion) == "" {
			missing = append(missing, plan.Tasks[i].ID)
		}
	}
	return strings.Join(missing, ", ")
}

// ---- completion ----

func (c *Controller) verifyCompletion(ctx context.Context, st *State, plan *Plan) error {
	if !AllDone(plan) {
		// Some tasks failed/blocked; we cannot satisfy completion. Finish.
		c.Notifier.Notify(fmt.Sprintf("[%s] 実行終了（未完了タスクあり）", plan.Goal))
		_ = c.Store.AppendAudit(AuditEntry{Event: "finished_incomplete"})
		return c.transition(st, PhaseDone)
	}
	c.updateSummary(plan)
	// Advisory natural-language completion check against plan.Completion. It never
	// blocks completion (a flaky/absent check just finishes the run); when it
	// finds the criteria unmet it enriches the notification so the human knows to
	// look. Auto-creating follow-up tasks is intentionally out of scope.
	satisfied, missing := c.checkCompletion(ctx, plan)
	if !satisfied {
		_ = c.Store.AppendAudit(AuditEntry{Event: "completion_unmet", Detail: map[string]any{"missing": missing}})
		c.Notifier.Notify(fmt.Sprintf("[%s] 全タスク完了。ただし完了基準の未充足の可能性: %s 最終確認をお願いします。",
			plan.Goal, oneline(missing, 200)))
	} else {
		c.Notifier.Notify(fmt.Sprintf("[%s] 完了。最終確認をお願いします。", plan.Goal))
	}
	_ = c.Store.AppendAudit(AuditEntry{Event: "completed", Detail: map[string]any{"completion_satisfied": satisfied}})
	return c.transition(st, PhaseDone)
}

// checkCompletion runs an advisory claude -p verification of plan.Completion
// against the completed work. Best-effort and read-only by intent: on empty
// criteria, any error, or an unparseable answer it returns (true, "") so a flaky
// check never blocks the run from finishing.
func (c *Controller) checkCompletion(ctx context.Context, plan *Plan) (bool, string) {
	if strings.TrimSpace(plan.Completion) == "" || c.Worker == nil || c.Worker.Claude == nil {
		return true, ""
	}
	out, err := c.Worker.Claude.RunPrompt(ctx, c.Worker.Workspace, c.Cfg.WorkerModel, buildCompletionPrompt(plan), "", RunOpts{})
	if err != nil {
		return true, ""
	}
	return parseCompletionVerdict(out)
}

// ---- helpers ----

func (c *Controller) transition(st *State, phase string) error {
	from := st.Phase
	st.Phase = phase
	if err := c.Store.SaveState(st); err != nil {
		return err
	}
	_ = c.Store.AppendAudit(AuditEntry{Event: "transition", Detail: map[string]any{"from": from, "to": phase}})
	return nil
}

func (c *Controller) updateSummary(plan *Plan) {
	md := renderSummary(plan)
	_ = c.Store.WriteSummary(md)
	c.Notifier.Notify(md)
}

// updateSummaryLocked is updateSummary for callers already holding planMu (it
// only reads plan, then writes the store and notifies).
func (c *Controller) updateSummaryLocked(plan *Plan) {
	c.updateSummary(plan)
}

// snapshotPlan returns a deep copy of plan suitable for passing to external
// calls (Dispatch/RunGate) without holding planMu. Tasks and their results are
// copied by value so peer goroutines mutating the live plan cannot race the
// snapshot. Caller must hold planMu while snapshotting.
func snapshotPlan(plan *Plan) *Plan {
	cp := *plan
	cp.Tasks = make([]Task, len(plan.Tasks))
	for i := range plan.Tasks {
		t := plan.Tasks[i]
		if len(t.Deps) > 0 {
			deps := make([]string, len(t.Deps))
			copy(deps, t.Deps)
			t.Deps = deps
		}
		if t.Result != nil {
			r := *t.Result
			t.Result = &r
		}
		cp.Tasks[i] = t
	}
	return &cp
}

func renderSummary(plan *Plan) string {
	var b strings.Builder
	fmt.Fprintf(&b, "## %s\n\n", plan.Goal)
	done, total := 0, len(plan.Tasks)
	for _, t := range plan.Tasks {
		if t.Status == TaskDone {
			done++
		}
		fmt.Fprintf(&b, "- [%s] %s (%s)\n", statusMark(t.Status), t.Title, t.Status)
	}
	fmt.Fprintf(&b, "\n進捗: %d/%d\n", done, total)
	return b.String()
}

func statusMark(status string) string {
	switch status {
	case TaskDone:
		return "x"
	case TaskFailed, TaskBlocked:
		return "!"
	default:
		return " "
	}
}

func buildQuestion(t *Task, reason string) string {
	var b strings.Builder
	fmt.Fprintf(&b, "# 要判断: %s\n\n", t.Title)
	fmt.Fprintf(&b, "トリガー: %s\n\n", reason)
	if strings.TrimSpace(t.Completion) != "" {
		fmt.Fprintf(&b, "このタスクの完了基準:\n%s\n\n", t.Completion)
	}
	if reason == TriggerReviewGateDefect {
		// The implementation is likely finished; only the gate malfunctioned.
		// Seed a first-pass artifact-existence check (docs/06 §8.2).
		b.WriteString("レビュー結果が繰り返し解析不能でした（ゲート不具合。実装は完了している可能性が高い）。\n")
		b.WriteString("まず成果物が上記の完了基準を満たすかを一次確認し、満たしていれば done として受理、\n")
		b.WriteString("そうでなければ具体的な指摘を answer.md に記してください。\n\n")
	}
	if t.Result != nil && t.Result.NeedsHuman != nil {
		nh := t.Result.NeedsHuman
		fmt.Fprintf(&b, "%s\n", nh.Question)
		if len(nh.Options) > 0 {
			b.WriteString("\n選択肢:\n")
			for i, o := range nh.Options {
				fmt.Fprintf(&b, "%d. %s\n", i+1, o)
			}
		}
	} else {
		fmt.Fprintf(&b, "タスク %q について判断が必要です。\n", t.ID)
	}
	b.WriteString("\n回答を intervention/<id>/answer.md と plan.json/該当タスクへ反映し、")
	b.WriteString("control.json に {\"request\":\"resume\"} を書いて終了してください。\n")
	return b.String()
}

// buildCompletionPrompt asks an independent claude -p to judge whether the
// plan's completion criteria are met by the work done, read-only, replying with
// a single JSON line {"satisfied":bool,"missing":string}.
func buildCompletionPrompt(plan *Plan) string {
	var b strings.Builder
	b.WriteString("You are verifying whether a project's completion criteria are satisfied. ")
	b.WriteString("DO NOT modify any files; only inspect the repository and answer.\n\n")
	b.WriteString("# Goal\n")
	b.WriteString(plan.Goal)
	b.WriteString("\n\n# Completion criteria\n")
	b.WriteString(plan.Completion)
	b.WriteString("\n\n# Completed tasks\n")
	for i := range plan.Tasks {
		t := &plan.Tasks[i]
		summary := ""
		if t.Result != nil {
			summary = t.Result.Summary
		}
		fmt.Fprintf(&b, "- [%s] %s: %s\n", t.Status, t.Title, oneline(summary, 160))
	}
	b.WriteString("\nInspect the working tree as needed, then print a SINGLE JSON object on the final line, nothing after it:\n")
	b.WriteString(`{"satisfied":bool,"missing":"short description of what is still missing, or empty if satisfied"}`)
	b.WriteString("\n")
	return b.String()
}

// parseCompletionVerdict extracts {"satisfied":bool,"missing":string} from a
// claude -p (stream-json or json) output. Returns (true,"") when no usable
// verdict is found, so completion is never blocked by an unparseable answer.
func parseCompletionVerdict(out []byte) (bool, string) {
	text := string(out)
	if inner := resultFromStream(text); inner != "" {
		text = inner
	} else if inner := extractFromClaudeEnvelope(text); inner != "" {
		text = inner
	}
	lines := strings.Split(strings.TrimRight(text, "\n"), "\n")
	for i := len(lines) - 1; i >= 0; i-- {
		line := strings.TrimSpace(lines[i])
		if !strings.HasPrefix(line, "{") || !strings.HasSuffix(line, "}") || !strings.Contains(line, "\"satisfied\"") {
			continue
		}
		var v struct {
			Satisfied bool   `json:"satisfied"`
			Missing   string `json:"missing"`
		}
		if err := json.Unmarshal([]byte(line), &v); err == nil {
			return v.Satisfied, v.Missing
		}
	}
	return true, ""
}

func attemptFeedback(t *Task) string {
	if t.Attempts <= 1 || t.Result == nil {
		return ""
	}
	return "Previous attempt summary: " + t.Result.Summary
}

func dashPaused(d *DashboardState) bool {
	d.mu.Lock()
	defer d.mu.Unlock()
	return d.Paused
}

func syncDashboard(d *DashboardState, plan *Plan) {
	d.Set(func(s *DashboardState) {
		// Preserve the Started timestamp of tasks that are already active so the
		// elapsed time keeps growing across syncs (instead of resetting to 0).
		prev := make(map[string]time.Time, len(s.Tasks))
		for _, r := range s.Tasks {
			prev[r.ID] = r.Started
		}
		rows := make([]DashTask, 0, len(plan.Tasks))
		for i := range plan.Tasks {
			t := &plan.Tasks[i]
			row := DashTask{ID: t.ID, Title: t.Title, Vendor: "claude", Status: t.Status, Attempts: t.Attempts}
			if t.Status == TaskRunning || t.Status == TaskReview || t.Status == TaskRevise {
				if ts, ok := prev[t.ID]; ok && !ts.IsZero() {
					row.Started = ts
				} else {
					row.Started = time.Now()
				}
			}
			rows = append(rows, row)
		}
		s.Tasks = rows
		s.Goal = plan.Goal
	})
}

func findTask(plan *Plan, id string) *Task {
	for i := range plan.Tasks {
		if plan.Tasks[i].ID == id {
			return &plan.Tasks[i]
		}
	}
	return nil
}

func newRunID() string { return "run-" + time.Now().UTC().Format("20060102-150405") }

// newInterventionID includes a random suffix so concurrent interventions opened
// within the same second get distinct ids (and distinct question dirs / queue
// entries).
func newInterventionID() string {
	return "iv-" + time.Now().UTC().Format("20060102-150405") + "-" + newSessionID()[:8]
}

// ---- plan scheduling (pure functions, unit-tested in plan_test.go) ----

// depsDone reports whether all dependencies of t are in TaskDone.
func depsDone(plan *Plan, t *Task) bool {
	byID := taskIndex(plan)
	for _, dep := range t.Deps {
		d, ok := byID[dep]
		if !ok || d.Status != TaskDone {
			return false
		}
	}
	return true
}

// depsFailed reports whether any dependency is failed or blocked (so t cannot
// ever run).
func depsFailed(plan *Plan, t *Task) bool {
	byID := taskIndex(plan)
	for _, dep := range t.Deps {
		d, ok := byID[dep]
		if !ok {
			return true // missing dependency: unsatisfiable
		}
		if d.Status == TaskFailed || d.Status == TaskBlocked {
			return true
		}
	}
	return false
}

func taskIndex(plan *Plan) map[string]*Task {
	m := make(map[string]*Task, len(plan.Tasks))
	for i := range plan.Tasks {
		m[plan.Tasks[i].ID] = &plan.Tasks[i]
	}
	return m
}

// ReadyTasks returns up to `limit` pending tasks whose dependencies are all
// done, in plan order. limit<=0 means no cap.
func ReadyTasks(plan *Plan, limit int) []*Task {
	var out []*Task
	for i := range plan.Tasks {
		t := &plan.Tasks[i]
		if t.Status != TaskPending {
			continue
		}
		if depsFailed(plan, t) {
			continue // will be marked blocked separately
		}
		if !depsDone(plan, t) {
			continue
		}
		out = append(out, t)
		if limit > 0 && len(out) >= limit {
			break
		}
	}
	return out
}

// MarkBlockedByFailedDeps sets pending tasks whose deps are failed/blocked to
// TaskBlocked.
func MarkBlockedByFailedDeps(plan *Plan) {
	for i := range plan.Tasks {
		t := &plan.Tasks[i]
		if t.Status == TaskPending && depsFailed(plan, t) {
			t.Status = TaskBlocked
		}
	}
}

// AllDone reports whether every task is TaskDone.
func AllDone(plan *Plan) bool {
	for i := range plan.Tasks {
		if plan.Tasks[i].Status != TaskDone {
			return false
		}
	}
	return true
}

// AllSettled reports whether no task can make further progress (every task is
// done, failed, or blocked).
func AllSettled(plan *Plan) bool {
	for i := range plan.Tasks {
		switch plan.Tasks[i].Status {
		case TaskDone, TaskFailed, TaskBlocked:
		default:
			return false
		}
	}
	return true
}

// NormalizeForResume resets in-flight statuses (running/review/revise) to
// pending so they are re-dispatched after a crash/resume. done/failed/blocked
// and waiting_human are preserved. When such a task still has a SessionID, its
// ResumeSession flag is set so the re-dispatch continues the SAME attempt via
// --resume (no white-slate redo) — this covers a hard crash where the graceful
// resetToPending path did not run.
func NormalizeForResume(plan *Plan) {
	for i := range plan.Tasks {
		switch plan.Tasks[i].Status {
		case TaskRunning, TaskReview, TaskRevise:
			plan.Tasks[i].Status = TaskPending
			if plan.Tasks[i].SessionID != "" {
				plan.Tasks[i].ResumeSession = true
			}
		case "":
			plan.Tasks[i].Status = TaskPending
		}
	}
}

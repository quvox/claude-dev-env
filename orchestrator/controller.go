package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"sync"
	"time"
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

	// Confirm asks the human a wallbounce continuation question on the terminal
	// when control.json is missing/invalid. Returns one of "continue",
	// "execute", "done". Injectable for tests/headless.
	Confirm func(prompt string) string

	// planMu guards all reads/writes of *Plan and Store mutations during the
	// concurrent execution phase. mergeMu serializes integrate() so concurrent
	// worktree merges into the working branch cannot race.
	planMu  sync.Mutex
	mergeMu sync.Mutex
}

// fired records a trigger that one task raised during concurrent execution.
type fired struct {
	taskID string
	reason string
	abort  bool
}

// Run executes the full lifecycle starting from the persisted (or fresh) state.
func (c *Controller) Run(ctx context.Context) error {
	st, err := c.Store.LoadState()
	if err != nil {
		return err
	}
	if st == nil {
		st = &State{Phase: PhaseWallbounce, RunID: newRunID()}
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
		case PhaseWallbounce:
			if err := c.runWallbounce(ctx, st); err != nil {
				return err
			}
		case PhaseExecuting:
			if err := c.runExecuting(ctx, st); err != nil {
				if errors.Is(err, errSuspended) {
					// User interrupted: state is left resumable; exit cleanly so
					// the next `claude-dev orchestrate` continues from here.
					return nil
				}
				return err
			}
		case PhaseIntervene:
			if err := c.runIntervene(ctx, st); err != nil {
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

// ---- wallbounce ----

func (c *Controller) runWallbounce(ctx context.Context, st *State) error {
	if err := c.Mode.RunInteractive(ctx, c.Mode.WallbounceArgs()...); err != nil {
		// Interactive session ending non-zero (e.g. /exit) is not fatal; we
		// still inspect control.json.
		_ = c.Store.AppendAudit(AuditEntry{Event: "wallbounce_exit", Detail: map[string]any{"err": err.Error()}})
	}
	ctrl, err := c.Handoff.Consume()
	if err != nil {
		return err
	}
	plan, _ := c.Store.LoadPlan()

	if ctrl != nil {
		switch ctrl.Request {
		case ReqExecute:
			if plan != nil && plan.Ready {
				return c.transition(st, PhaseExecuting)
			}
			// execute requested but plan not ready: fall through to confirm.
		case ReqAbort:
			return c.transition(st, PhaseDone)
		case ReqContinueWallbounce:
			return nil // stay in wallbounce; loop re-runs interactive
		}
	}

	// No decisive control: ask the human explicitly (safe side).
	switch c.confirm("壁打ち: 続ける(continue)/実行(execute)/終了(done)?") {
	case "execute":
		return c.transition(st, PhaseExecuting)
	case "done":
		return c.transition(st, PhaseDone)
	default:
		return nil // continue wallbounce
	}
}

func (c *Controller) confirm(prompt string) string {
	if c.Confirm != nil {
		return c.Confirm(prompt)
	}
	// Headless / no confirm hook: default to continuing wallbounce (safe; the
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

	// Normalize stale in-flight statuses on (re)entry: tasks left running/
	// review/revise are reset to pending for re-dispatch.
	c.planMu.Lock()
	NormalizeForResume(plan)
	_ = c.Store.SavePlan(plan)
	c.planMu.Unlock()

	dash := &DashboardState{Goal: plan.Goal}
	syncDashboard(dash, plan)
	d := NewDashboard(dash, c.Store)
	dctx, dcancel := context.WithCancel(ctx)
	go d.Run(dctx)
	defer dcancel()

	// runCtx bounds the worker goroutines. Cancelling it (on a trigger fire or
	// quit) stops new scheduling and signals in-flight goroutines to stop.
	runCtx, runCancel := context.WithCancel(ctx)
	defer runCancel()

	var (
		wg       sync.WaitGroup
		firedMu  sync.Mutex
		fires    []fired // collected triggers (deterministically reduced to one)
		inflight = map[string]bool{}
	)

	recordFire := func(f fired) {
		firedMu.Lock()
		fires = append(fires, f)
		firedMu.Unlock()
		runCancel() // stop scheduling and signal peers to wind down
	}

	scheduleTick := func() {
		c.planMu.Lock()
		ready := ReadyTasks(plan, len(plan.Tasks))
		launched := 0
		for _, t := range ready {
			if len(inflight) >= c.Cfg.MaxWorkers {
				break
			}
			if inflight[t.ID] {
				continue
			}
			// Condition 1: pre-dispatch gate for irreversible tasks. Evaluated
			// before reserving a slot so the worker never runs an unapproved
			// irreversible task. The task stays pending (NOT blocked) so it can
			// be dispatched after the intervention approves it.
			if f, r := Evaluate(TriggerContext{Phase: PhasePreDispatch, Task: t, Plan: plan, State: st, Config: c.Cfg}); f {
				recordFire(fired{taskID: t.ID, reason: r})
				break
			}
			// Reserve the slot: mark running and increment Attempts (new Attempt)
			// under the lock so the cap and Attempts counting are race-free.
			t.Attempts++
			t.Status = TaskRunning
			inflight[t.ID] = true
			taskID := t.ID
			attempt := t.Attempts
			_ = c.Store.SavePlan(plan)
			_ = c.Store.AppendAudit(AuditEntry{Event: "dispatch", TaskID: taskID, Detail: map[string]any{"attempt": attempt}})
			launched++
			wg.Add(1)
			go func() {
				defer wg.Done()
				f := c.runTaskPipeline(runCtx, st, plan, taskID)
				c.planMu.Lock()
				delete(inflight, taskID)
				_ = c.Store.SavePlan(plan)
				syncDashboard(dash, plan)
				c.planMu.Unlock()
				if f != nil {
					recordFire(*f)
				}
			}()
		}
		// Reflect newly-running tasks on the dashboard immediately (otherwise the
		// screen keeps showing "pending" until a worker finishes).
		syncDashboard(dash, plan)
		c.planMu.Unlock()
	}

	for {
		select {
		case <-ctx.Done():
			runCancel()
			wg.Wait()
			c.planMu.Lock()
			_ = c.Store.SavePlan(plan)
			c.planMu.Unlock()
			return ctx.Err()
		case k := <-d.Keys:
			switch k {
			case KeyPause:
				dash.Set(func(s *DashboardState) { s.Paused = !s.Paused })
				continue
			case KeyQuit:
				// "中断": stop the workers but DO NOT mark the run done. Leave the
				// phase at executing and reset in-flight tasks to pending so the
				// next launch resumes from here (work in worktrees is preserved).
				runCancel()
				wg.Wait()
				c.planMu.Lock()
				_ = c.Store.SavePlan(plan)
				c.planMu.Unlock()
				_ = c.Store.AppendAudit(AuditEntry{Event: "suspended", Detail: map[string]any{"run_id": st.RunID}})
				return errSuspended
			case KeyDetail:
				// Toggle the live worker-output detail view.
				dash.Set(func(s *DashboardState) { s.Detail = !s.Detail })
				continue
			}
		default:
		}

		// A fire has been recorded: stop scheduling, drain, and handle it.
		if runCtx.Err() != nil {
			break
		}

		if dashPaused(dash) {
			time.Sleep(50 * time.Millisecond)
			continue
		}

		scheduleTick()

		// Determine whether we can make further progress.
		c.planMu.Lock()
		anyInflight := len(inflight) > 0
		ready := ReadyTasks(plan, len(plan.Tasks))
		if len(ready) == 0 && !anyInflight {
			MarkBlockedByFailedDeps(plan)
			_ = c.Store.SavePlan(plan)
			settled := AllSettled(plan)
			c.planMu.Unlock()
			if settled {
				break
			}
			time.Sleep(20 * time.Millisecond)
			continue
		}
		c.planMu.Unlock()
		time.Sleep(20 * time.Millisecond)
	}

	// Stop scheduling and wait for all in-flight goroutines to wind down.
	runCancel()
	wg.Wait()
	c.planMu.Lock()
	_ = c.Store.SavePlan(plan)
	syncDashboard(dash, plan)
	c.planMu.Unlock()
	dcancel()

	// If any trigger fired, deterministically pick one (task ID ascending) and
	// open the intervention (or abort).
	if f := reduceFires(fires); f != nil {
		if f.abort {
			return c.transition(st, PhaseDone)
		}
		c.planMu.Lock()
		t := findTask(plan, f.taskID)
		c.planMu.Unlock()
		return c.fireIntervention(st, plan, t, f.reason)
	}

	// All tasks settled with no trigger: verify completion criteria.
	return c.verifyCompletion(ctx, st, plan)
}

// reduceFires deterministically selects a single fired trigger: an abort takes
// precedence, otherwise the lowest task ID.
func reduceFires(fires []fired) *fired {
	var chosen *fired
	for i := range fires {
		f := fires[i]
		if f.abort {
			return &f
		}
		if chosen == nil || f.taskID < chosen.taskID {
			c := f
			chosen = &c
		}
	}
	return chosen
}

// runTaskPipeline runs worker -> review -> revise for one task identified by
// taskID. It returns a *fired when an intervention must open (nil otherwise).
//
// Concurrency contract: the task is already marked TaskRunning with Attempts
// incremented by the scheduler under planMu. This function takes planMu only
// for short state mutations; long external calls (Dispatch/RunGate) run against
// an immutable plan snapshot so they do not race with peer goroutines.
func (c *Controller) runTaskPipeline(ctx context.Context, st *State, plan *Plan, taskID string) *fired {
	// Honour cancellation promptly (peer fired, or quit/abort).
	if ctx.Err() != nil {
		c.resetToPending(plan, taskID)
		return nil
	}

	c.planMu.Lock()
	st.CurrentTask = taskID
	_ = c.Store.SaveState(st)
	snap := snapshotPlan(plan)
	t := findTask(plan, taskID)
	if t == nil {
		c.planMu.Unlock()
		return nil
	}
	feedback := attemptFeedback(t)
	c.planMu.Unlock()

	snapTask := findTask(snap, taskID)

	res, err := c.Worker.Dispatch(ctx, snap, snapTask, feedback)
	if err != nil {
		if ctx.Err() != nil {
			c.resetToPending(plan, taskID)
			return nil
		}
		c.planMu.Lock()
		_ = c.Store.AppendAudit(AuditEntry{Event: "dispatch_error", TaskID: taskID, Detail: map[string]any{"err": err.Error()}})
		t := findTask(plan, taskID)
		if f := c.evalStuck(t); f != nil {
			c.planMu.Unlock()
			return f
		}
		t.Status = TaskPending // retry as a new Attempt next scheduling tick
		c.planMu.Unlock()
		return nil
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
		c.planMu.Unlock()
		return &fired{taskID: taskID, reason: r}
	}
	c.planMu.Unlock()

	if !res.Done {
		c.planMu.Lock()
		t = findTask(plan, taskID)
		t.Status = TaskPending
		if f := c.evalStuck(t); f != nil {
			c.planMu.Unlock()
			return f
		}
		c.planMu.Unlock()
		return nil
	}

	// Quality gate: review/revise loop within this Attempt (against snapshot).
	passed, _, rerr := c.Reviewer.RunGate(ctx, snap, snapTask)
	if rerr != nil {
		if ctx.Err() != nil {
			c.resetToPending(plan, taskID)
			return nil
		}
		c.planMu.Lock()
		_ = c.Store.AppendAudit(AuditEntry{Event: "review_error", TaskID: taskID, Detail: map[string]any{"err": rerr.Error()}})
		findTask(plan, taskID).Status = TaskPending
		c.planMu.Unlock()
		return nil
	}
	// Mirror any revise-produced result back to the live task.
	c.planMu.Lock()
	t = findTask(plan, taskID)
	if snapTask.Result != nil {
		t.Result = snapTask.Result
	}
	c.planMu.Unlock()

	if passed {
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
			return nil
		}
		t.Status = TaskDone
		_ = c.Store.AppendAudit(AuditEntry{Event: "task_done", TaskID: taskID})
		c.updateSummaryLocked(plan)
		c.planMu.Unlock()
		return nil
	}

	// Severe findings remain after max_review_rounds: stuck (condition 3b).
	c.planMu.Lock()
	t = findTask(plan, taskID)
	if f, r := Evaluate(TriggerContext{Phase: PhasePostDispatch, Task: t, Plan: plan, State: st, Config: c.Cfg, StuckThisAttempt: true}); f {
		c.planMu.Unlock()
		return &fired{taskID: taskID, reason: r}
	}
	t.Status = TaskPending
	c.planMu.Unlock()
	return nil
}

// evalStuck evaluates only the stuck (condition 3) trigger for a task. Caller
// must hold planMu. Returns a *fired when stuck.
func (c *Controller) evalStuck(t *Task) *fired {
	if f, r := Evaluate(TriggerContext{Phase: PhasePostDispatch, Task: t, State: &State{}, Plan: &Plan{}, Config: c.Cfg}); f {
		return &fired{taskID: t.ID, reason: r}
	}
	return nil
}

// resetToPending marks a task pending under the lock (used on cancellation so
// the task is re-dispatched after the intervention resolves / on resume).
func (c *Controller) resetToPending(plan *Plan, taskID string) {
	c.planMu.Lock()
	defer c.planMu.Unlock()
	if t := findTask(plan, taskID); t != nil && t.Status != TaskDone {
		t.Status = TaskPending
	}
	_ = c.Store.SavePlan(plan)
}

// integrate merges the task worktree branch into the working branch. Callers
// must hold mergeMu so concurrent merges into the working branch are serialized.
func (c *Controller) integrate(ctx context.Context, taskID string) error {
	branch := "orch/" + taskID
	return c.Worker.Git.Merge(ctx, c.Worker.Workspace, branch, c.Cfg.MergeStrategy)
}

// fireIntervention transitions to intervening, writing the question and
// alerting Slack.
func (c *Controller) fireIntervention(st *State, plan *Plan, t *Task, reason string) error {
	id := newInterventionID()
	q := buildQuestion(t, reason)
	_ = c.Store.WriteQuestion(id, q)
	_ = c.Store.AppendIntervention(Intervention{ID: id, TaskID: t.ID, TriggerReason: reason, Question: q})
	c.Notifier.Notify(fmt.Sprintf("[%s] 要判断: %s。attach してください。", plan.Goal, oneline(q, 80)))
	st.CurrentTask = t.ID
	// Stash the open intervention id in state via a sentinel file.
	_ = c.Store.WriteAtomicSidecar("open_intervention", id)
	return c.transition(st, PhaseIntervene)
}

// ---- intervening ----

func (c *Controller) runIntervene(ctx context.Context, st *State) error {
	id, _ := c.Store.ReadAtomicSidecar("open_intervention")
	if err := c.Mode.RunInteractive(ctx, c.Mode.InterveneArgs(id)...); err != nil {
		_ = c.Store.AppendAudit(AuditEntry{Event: "intervene_exit", Detail: map[string]any{"err": err.Error()}})
	}
	ctrl, err := c.Handoff.Consume()
	if err != nil {
		return err
	}
	if ctrl != nil && ctrl.Request == ReqAbort {
		return c.transition(st, PhaseDone)
	}
	// resume (or any non-abort): record answer and return to executing.
	answer, _ := c.Store.ReadAnswer(id)
	if id != "" {
		_ = c.Store.AppendIntervention(Intervention{ID: id, TaskID: st.CurrentTask, Answer: answer})
	}
	_ = c.Store.RemoveSidecar("open_intervention")
	// Reset the paused task so it is re-dispatched with the new guidance.
	if plan, _ := c.Store.LoadPlan(); plan != nil {
		if t := findTask(plan, st.CurrentTask); t != nil && t.Status != TaskDone {
			// If this was an irreversible task gated by trigger1, the human has
			// now approved it: mark it approved so the pre-dispatch gate does not
			// re-fire and the task can finally be dispatched.
			if t.Irreversible {
				t.IrrevApproved = true
			}
			t.Status = TaskPending
			_ = c.Store.SavePlan(plan)
		}
	}
	return c.transition(st, PhaseExecuting)
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
	out, err := c.Worker.Claude.RunPrompt(ctx, c.Worker.Workspace, c.Cfg.WorkerModel, buildCompletionPrompt(plan), "")
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
	if t.Result != nil && t.Result.NeedsHuman != nil {
		nh := t.Result.NeedsHuman
		fmt.Fprintf(&b, "%s\n", nh.Question)
		if len(nh.Options) > 0 {
			b.WriteString("\n選択肢:\n")
			for _, o := range nh.Options {
				fmt.Fprintf(&b, "- %s\n", o)
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

func newRunID() string          { return "run-" + time.Now().UTC().Format("20060102-150405") }
func newInterventionID() string { return "iv-" + time.Now().UTC().Format("20060102-150405") }

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
// are preserved.
func NormalizeForResume(plan *Plan) {
	for i := range plan.Tasks {
		switch plan.Tasks[i].Status {
		case TaskRunning, TaskReview, TaskRevise:
			plan.Tasks[i].Status = TaskPending
		case "":
			plan.Tasks[i].Status = TaskPending
		}
	}
}

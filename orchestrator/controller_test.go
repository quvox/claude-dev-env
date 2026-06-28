package main

import (
	"context"
	"encoding/json"
	"os"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

// ---- mocks ----

// mockClaude is a controllable ClaudeRunner. It returns a worker result for
// dispatch prompts and a (clean) review result for review prompts. It tracks
// concurrent in-flight worker calls so tests can assert the max_workers cap and
// honors ctx cancellation.
type mockClaude struct {
	mu        sync.Mutex
	inflight  int
	maxSeen   int
	order     []string // task ids in dispatch order (worker calls only)
	delay     time.Duration
	workerFn  func(taskID string) WorkerResult // optional per-task override
	reviewFn  func(taskID string) ReviewResult // optional per-task override
	dispatchN int32
}

func (m *mockClaude) RunPrompt(ctx context.Context, dir, model, prompt, logPath string) ([]byte, error) {
	isReview := strings.Contains(prompt, "independent code reviewer")
	taskID := taskIDFromDir(dir)

	if !isReview {
		atomic.AddInt32(&m.dispatchN, 1)
		m.mu.Lock()
		m.inflight++
		if m.inflight > m.maxSeen {
			m.maxSeen = m.inflight
		}
		m.order = append(m.order, taskID)
		m.mu.Unlock()
		defer func() {
			m.mu.Lock()
			m.inflight--
			m.mu.Unlock()
		}()
	}

	// Simulate work, honoring cancellation.
	if m.delay > 0 {
		select {
		case <-time.After(m.delay):
		case <-ctx.Done():
			return nil, ctx.Err()
		}
	}
	if ctx.Err() != nil {
		return nil, ctx.Err()
	}

	if isReview {
		rr := ReviewResult{Findings: []Finding{}}
		if m.reviewFn != nil {
			rr = m.reviewFn(taskID)
		}
		b, _ := json.Marshal(rr)
		return b, nil
	}
	wr := WorkerResult{Done: true, Summary: "done " + taskID}
	if m.workerFn != nil {
		wr = m.workerFn(taskID)
	}
	b, _ := json.Marshal(wr)
	return b, nil
}

// taskIDFromDir extracts the task id from a worktree dir path.
func taskIDFromDir(dir string) string {
	idx := strings.LastIndex(dir, "/worktrees/")
	if idx < 0 {
		return dir
	}
	return dir[idx+len("/worktrees/"):]
}

// mockGit is a no-op GitRunner that records merges.
type mockGit struct {
	mu     sync.Mutex
	merges []string
}

func (g *mockGit) WorktreeAdd(ctx context.Context, repoDir, path, branch, base string) error {
	return nil
}
func (g *mockGit) WorktreeRemove(ctx context.Context, repoDir, path string) error { return nil }
func (g *mockGit) Merge(ctx context.Context, repoDir, branch, strategy string) error {
	g.mu.Lock()
	g.merges = append(g.merges, branch)
	g.mu.Unlock()
	return nil
}
func (g *mockGit) HasCommits(ctx context.Context, repoDir, branch, base string) (bool, error) {
	return true, nil
}
func (g *mockGit) CurrentBranch(ctx context.Context, repoDir string) (string, error) {
	return "main", nil
}

type captureNotifier struct {
	mu   sync.Mutex
	msgs []string
}

func (n *captureNotifier) Notify(text string) {
	n.mu.Lock()
	n.msgs = append(n.msgs, text)
	n.mu.Unlock()
}

// newTestController wires a controller with mocks against a temp store.
func newTestController(t *testing.T, cfg Config, mc *mockClaude, mg *mockGit) (*Controller, *Store) {
	t.Helper()
	store, err := NewStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	worker := &Worker{Store: store, Claude: mc, Git: mg, Cfg: cfg, Workspace: store.Root + "/.."}
	reviewer := &Reviewer{Store: store, Claude: mc, Cfg: cfg, Worker: worker}
	ctrl := &Controller{
		Store:    store,
		Cfg:      cfg,
		Worker:   worker,
		Reviewer: reviewer,
		Notifier: &captureNotifier{},
	}
	return ctrl, store
}

func testCfg() Config {
	c := DefaultConfig()
	c.MaxWorkers = 2
	return c
}

// ---- tests ----

// TestExecuting_RespectsMaxWorkers verifies concurrency is capped.
func TestExecuting_RespectsMaxWorkers(t *testing.T) {
	cfg := testCfg()
	cfg.MaxWorkers = 2
	mc := &mockClaude{delay: 30 * time.Millisecond}
	mg := &mockGit{}
	ctrl, store := newTestController(t, cfg, mc, mg)

	plan := &Plan{Goal: "g", Completion: "c", Ready: true, Tasks: []Task{
		{ID: "t1", Status: TaskPending},
		{ID: "t2", Status: TaskPending},
		{ID: "t3", Status: TaskPending},
		{ID: "t4", Status: TaskPending},
		{ID: "t5", Status: TaskPending},
	}}
	if err := store.SavePlan(plan); err != nil {
		t.Fatal(err)
	}
	st := &State{Phase: PhaseExecuting, RunID: "r"}
	if err := store.SaveState(st); err != nil {
		t.Fatal(err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := ctrl.runExecuting(ctx, st); err != nil {
		t.Fatalf("runExecuting: %v", err)
	}

	mc.mu.Lock()
	maxSeen := mc.maxSeen
	mc.mu.Unlock()
	if maxSeen > cfg.MaxWorkers {
		t.Fatalf("concurrency %d exceeded max_workers %d", maxSeen, cfg.MaxWorkers)
	}
	if maxSeen < 2 {
		t.Fatalf("expected real concurrency (>=2), saw %d", maxSeen)
	}

	out, _ := store.LoadPlan()
	if !AllDone(out) {
		t.Fatalf("all tasks should be done, got %+v", taskStatuses(out))
	}
	if len(mg.merges) != 5 {
		t.Fatalf("expected 5 merges, got %d", len(mg.merges))
	}
}

// TestExecuting_DependencyOrder verifies a dependent task runs only after its
// prerequisite is done.
func TestExecuting_DependencyOrder(t *testing.T) {
	cfg := testCfg()
	cfg.MaxWorkers = 4
	mc := &mockClaude{delay: 10 * time.Millisecond}
	mg := &mockGit{}
	ctrl, store := newTestController(t, cfg, mc, mg)

	plan := &Plan{Goal: "g", Ready: true, Tasks: []Task{
		{ID: "a", Status: TaskPending},
		{ID: "b", Status: TaskPending, Deps: []string{"a"}},
		{ID: "c", Status: TaskPending, Deps: []string{"b"}},
	}}
	_ = store.SavePlan(plan)
	st := &State{Phase: PhaseExecuting, RunID: "r"}
	_ = store.SaveState(st)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := ctrl.runExecuting(ctx, st); err != nil {
		t.Fatal(err)
	}

	mc.mu.Lock()
	order := append([]string(nil), mc.order...)
	mc.mu.Unlock()
	pos := map[string]int{}
	for i, id := range order {
		if _, ok := pos[id]; !ok {
			pos[id] = i
		}
	}
	if !(pos["a"] < pos["b"] && pos["b"] < pos["c"]) {
		t.Fatalf("dependency order violated: %v", order)
	}
}

// TestExecuting_TriggerFiresIntervening verifies a worker NeedsHuman ambiguity
// fires a trigger and the controller enters intervening.
func TestExecuting_TriggerFiresIntervening(t *testing.T) {
	cfg := testCfg()
	cfg.MaxWorkers = 3
	mc := &mockClaude{
		delay: 5 * time.Millisecond,
		workerFn: func(taskID string) WorkerResult {
			if taskID == "t2" {
				return WorkerResult{Done: false, NeedsHuman: &NeedsHuman{
					Reason: ReasonAmbiguity, Question: "which?"}}
			}
			return WorkerResult{Done: true, Summary: "ok"}
		},
	}
	mg := &mockGit{}
	ctrl, store := newTestController(t, cfg, mc, mg)

	plan := &Plan{Goal: "g", Ready: true, Tasks: []Task{
		{ID: "t1", Status: TaskPending},
		{ID: "t2", Status: TaskPending},
		{ID: "t3", Status: TaskPending},
	}}
	_ = store.SavePlan(plan)
	st := &State{Phase: PhaseExecuting, RunID: "r"}
	_ = store.SaveState(st)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := ctrl.runExecuting(ctx, st); err != nil {
		t.Fatal(err)
	}

	got, _ := store.LoadState()
	if got.Phase != PhaseIntervene {
		t.Fatalf("expected phase intervening, got %s", got.Phase)
	}
	// An open intervention id should be recorded.
	if id, _ := store.ReadAtomicSidecar("open_intervention"); id == "" {
		t.Fatalf("expected open_intervention sidecar set")
	}
}

// TestExecuting_Trigger1Irreversible verifies an irreversible task fires the
// pre-dispatch gate WITHOUT being dispatched, and stays pending (not blocked).
func TestExecuting_Trigger1Irreversible(t *testing.T) {
	cfg := testCfg()
	cfg.MaxWorkers = 2
	mc := &mockClaude{}
	mg := &mockGit{}
	ctrl, store := newTestController(t, cfg, mc, mg)

	plan := &Plan{Goal: "g", Ready: true, Tasks: []Task{
		{ID: "t1", Status: TaskPending, Irreversible: true},
	}}
	_ = store.SavePlan(plan)
	st := &State{Phase: PhaseExecuting, RunID: "r"}
	_ = store.SaveState(st)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := ctrl.runExecuting(ctx, st); err != nil {
		t.Fatal(err)
	}

	got, _ := store.LoadState()
	if got.Phase != PhaseIntervene {
		t.Fatalf("expected intervening, got %s", got.Phase)
	}
	out, _ := store.LoadPlan()
	tk := findTask(out, "t1")
	if tk.Status == TaskBlocked {
		t.Fatalf("irreversible task must NOT be blocked (so it can dispatch after approval)")
	}
	if atomic.LoadInt32(&mc.dispatchN) != 0 {
		t.Fatalf("irreversible task must not be dispatched pre-approval, dispatchN=%d", mc.dispatchN)
	}
}

// TestIntervene_ResumeApprovesIrreversible verifies the full path:
// trigger1 -> intervening -> resume (approve) -> executing -> dispatch.
func TestIntervene_ResumeApprovesIrreversible(t *testing.T) {
	cfg := testCfg()
	cfg.MaxWorkers = 1
	mc := &mockClaude{}
	mg := &mockGit{}
	ctrl, store := newTestController(t, cfg, mc, mg)
	// Inject an interactive mode mock: writes answer + resume control on "run".
	ctrl.Mode = &Mode{Store: store, Workspace: store.Root + "/.."}
	ctrl.Handoff = &Handoff{Store: store}

	plan := &Plan{Goal: "g", Ready: true, Tasks: []Task{
		{ID: "t1", Status: TaskPending, Irreversible: true},
	}}
	_ = store.SavePlan(plan)
	st := &State{Phase: PhaseExecuting, RunID: "r"}
	_ = store.SaveState(st)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	// Phase 1: execute -> should enter intervening.
	if err := ctrl.runExecuting(ctx, st); err != nil {
		t.Fatal(err)
	}
	if st.Phase != PhaseIntervene {
		t.Fatalf("expected intervening, got %s", st.Phase)
	}

	// Simulate the human/interactive claude: write answer + resume control.
	id, _ := store.ReadAtomicSidecar("open_intervention")
	_ = store.WriteAtomicSidecar("intervention/"+id+"/answer.md", "approved")
	// Stub RunInteractive by directly invoking the resume handling: we call
	// runIntervene but first place a resume control so Consume returns resume.
	_ = store.SaveControl(&Control{Request: ReqResume, InterventionID: id})
	// runIntervene exec's claude; replace with a no-op by using a Mode whose
	// RunInteractive is short-circuited. Since we cannot exec claude here, drive
	// the resume logic directly:
	if err := driveResume(ctrl, st, id); err != nil {
		t.Fatal(err)
	}
	if st.Phase != PhaseExecuting {
		t.Fatalf("expected executing after resume, got %s", st.Phase)
	}
	out, _ := store.LoadPlan()
	tk := findTask(out, "t1")
	if !tk.IrrevApproved {
		t.Fatalf("task should be marked IrrevApproved after resume")
	}
	if tk.Status != TaskPending {
		t.Fatalf("task should be pending for re-dispatch, got %s", tk.Status)
	}

	// Phase 2: execute again -> now the approved task should dispatch & finish.
	if err := ctrl.runExecuting(ctx, st); err != nil {
		t.Fatal(err)
	}
	if atomic.LoadInt32(&mc.dispatchN) != 1 {
		t.Fatalf("approved task should be dispatched exactly once, dispatchN=%d", mc.dispatchN)
	}
	out, _ = store.LoadPlan()
	if findTask(out, "t1").Status != TaskDone {
		t.Fatalf("approved task should be done after re-execution")
	}
}

// driveResume reproduces runIntervene's post-RunInteractive logic without
// exec'ing the real claude (which is unavailable in tests).
func driveResume(c *Controller, st *State, id string) error {
	ctrl, err := c.Handoff.Consume()
	if err != nil {
		return err
	}
	if ctrl != nil && ctrl.Request == ReqAbort {
		return c.transition(st, PhaseDone)
	}
	answer, _ := c.Store.ReadAnswer(id)
	if id != "" {
		_ = c.Store.AppendIntervention(Intervention{ID: id, TaskID: st.CurrentTask, Answer: answer})
	}
	_ = c.Store.RemoveSidecar("open_intervention")
	if plan, _ := c.Store.LoadPlan(); plan != nil {
		if t := findTask(plan, st.CurrentTask); t != nil && t.Status != TaskDone {
			if t.Irreversible {
				t.IrrevApproved = true
			}
			t.Status = TaskPending
			_ = c.Store.SavePlan(plan)
		}
	}
	return c.transition(st, PhaseExecuting)
}

// TestRunGate_ReviseDispatchErrorPreservesStuck verifies that a Dispatch error
// during a revise round does not lose the trigger3 signal: lastSevere is kept
// and passed=false so the controller fires StuckThisAttempt.
func TestRunGate_ReviseDispatchErrorPreservesStuck(t *testing.T) {
	cfg := DefaultConfig()
	cfg.MaxReviewRounds = 3
	store, _ := NewStore(t.TempDir())
	// reviewer always returns a severe finding; the revise dispatch errors.
	mc := &mockClaude{
		reviewFn: func(taskID string) ReviewResult {
			return ReviewResult{Findings: []Finding{{Severity: SeverityMajor, Message: "bad"}}}
		},
		workerFn: func(taskID string) WorkerResult { return WorkerResult{Done: true} },
	}
	// Make worker.Dispatch fail by using a claude that errors on worker calls.
	errClaude := &errOnWorkerClaude{review: mc}
	worker := &Worker{Store: store, Claude: errClaude, Git: &mockGit{}, Cfg: cfg, Workspace: store.Root + "/.."}
	rv := &Reviewer{Store: store, Claude: mc, Cfg: cfg, Worker: worker}

	plan := &Plan{Tasks: []Task{{ID: "t1", Status: TaskReview, Attempts: 1}}}
	tk := &plan.Tasks[0]
	passed, lastSevere, err := rv.RunGate(context.Background(), plan, tk)
	if err != nil {
		t.Fatalf("RunGate should not bubble dispatch error, got %v", err)
	}
	if passed {
		t.Fatalf("expected not passed")
	}
	if lastSevere == "" {
		t.Fatalf("lastSevere must be preserved across revise dispatch error")
	}
}

// errOnWorkerClaude returns an error on worker (non-review) dispatch but
// delegates review calls to the embedded reviewer mock.
type errOnWorkerClaude struct{ review *mockClaude }

func (e *errOnWorkerClaude) RunPrompt(ctx context.Context, dir, model, prompt, logPath string) ([]byte, error) {
	if strings.Contains(prompt, "independent code reviewer") {
		return e.review.RunPrompt(ctx, dir, model, prompt, logPath)
	}
	return nil, context.DeadlineExceeded // simulate worker crash/timeout
}

// TestExecuting_RecordsAssumptions verifies WorkerResult.Assumptions are
// appended to assumptions.jsonl by the controller.
func TestExecuting_RecordsAssumptions(t *testing.T) {
	cfg := testCfg()
	cfg.MaxWorkers = 1
	mc := &mockClaude{
		workerFn: func(taskID string) WorkerResult {
			return WorkerResult{Done: true, Summary: "ok",
				Assumptions: []string{"assumed UTF-8", "assumed port 8080"}}
		},
	}
	mg := &mockGit{}
	ctrl, store := newTestController(t, cfg, mc, mg)

	plan := &Plan{Goal: "g", Ready: true, Tasks: []Task{{ID: "t1", Status: TaskPending}}}
	_ = store.SavePlan(plan)
	st := &State{Phase: PhaseExecuting, RunID: "r"}
	_ = store.SaveState(st)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := ctrl.runExecuting(ctx, st); err != nil {
		t.Fatal(err)
	}

	n := countJSONL(t, store, "assumptions.jsonl")
	if n != 2 {
		t.Fatalf("expected 2 assumptions recorded, got %d", n)
	}
}

// ---- helpers ----

func taskStatuses(p *Plan) map[string]string {
	m := map[string]string{}
	for _, t := range p.Tasks {
		m[t.ID] = t.Status
	}
	return m
}

func countJSONL(t *testing.T, s *Store, name string) int {
	t.Helper()
	data, err := os.ReadFile(s.path(name))
	if err != nil {
		return 0
	}
	n := 0
	for _, line := range strings.Split(strings.TrimRight(string(data), "\n"), "\n") {
		if strings.TrimSpace(line) != "" {
			n++
		}
	}
	return n
}

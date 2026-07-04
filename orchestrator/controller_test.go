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
	// resumeByTask/sessionByTask record the RunOpts of the LAST worker dispatch
	// per task so tests can assert --resume / --session-id behavior.
	resumeByTask  map[string]bool
	sessionByTask map[string]string
}

func (m *mockClaude) RunPrompt(ctx context.Context, dir, model, prompt, logPath string, opts RunOpts) ([]byte, error) {
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
		if m.resumeByTask == nil {
			m.resumeByTask = map[string]bool{}
			m.sessionByTask = map[string]string{}
		}
		m.resumeByTask[taskID] = opts.Resume
		m.sessionByTask[taskID] = opts.SessionID
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
func (g *mockGit) WorktreeAddExisting(ctx context.Context, repoDir, path, branch string) error {
	return nil
}
func (g *mockGit) BranchExists(ctx context.Context, repoDir, branch string) (bool, error) {
	return false, nil
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

// waitFor polls cond until true or the timeout elapses (test helper).
func waitFor(t *testing.T, timeout time.Duration, cond func() bool) bool {
	t.Helper()
	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		if cond() {
			return true
		}
		time.Sleep(5 * time.Millisecond)
	}
	return cond()
}

// TestExecuting_TriggerParksTaskPeersContinue verifies a worker NeedsHuman
// ambiguity parks ONLY that task as waiting_human (queued as a per-task
// intervention) while its peers keep running to completion (no stop-the-world).
func TestExecuting_TriggerParksTaskPeersContinue(t *testing.T) {
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

	// runExecuting does NOT return on an intervention (per-task model): it keeps
	// running until the human resolves via [i] or the run is suspended. Run it
	// async, wait until t2 is parked and its peers are done, then suspend.
	ctx, cancel := context.WithCancel(context.Background())
	errc := make(chan error, 1)
	go func() { errc <- ctrl.runExecuting(ctx, st) }()

	ok := waitFor(t, 3*time.Second, func() bool {
		out, _ := store.LoadPlan()
		return ctrl.openInterventionCount() >= 1 &&
			findTask(out, "t1").Status == TaskDone &&
			findTask(out, "t3").Status == TaskDone
	})
	cancel()
	<-errc
	if !ok {
		t.Fatalf("expected t2 parked (open intervention) and peers t1/t3 done: %+v", taskStatuses(mustPlan(store)))
	}

	out, _ := store.LoadPlan()
	if findTask(out, "t2").Status != TaskWaitingHuman {
		t.Fatalf("t2 should be waiting_human, got %s", findTask(out, "t2").Status)
	}
	q := store.LoadOpenInterventions()
	if len(q.Items) != 1 || q.Items[0].TaskID != "t2" {
		t.Fatalf("expected one open intervention for t2, got %+v", q.Items)
	}
	// Phase must stay executing (no top-level intervening state anymore).
	if got, _ := store.LoadState(); got.Phase != PhaseExecuting {
		t.Fatalf("phase should remain executing, got %s", got.Phase)
	}
}

// TestExecuting_Trigger1Irreversible verifies an irreversible task fires the
// pre-dispatch gate WITHOUT being dispatched, is parked waiting_human (not
// blocked), and does not stop the run's phase.
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

	ctx, cancel := context.WithCancel(context.Background())
	errc := make(chan error, 1)
	go func() { errc <- ctrl.runExecuting(ctx, st) }()
	ok := waitFor(t, 3*time.Second, func() bool { return ctrl.openInterventionCount() >= 1 })
	cancel()
	<-errc
	if !ok {
		t.Fatalf("expected pre-dispatch gate to open an intervention")
	}

	out, _ := store.LoadPlan()
	tk := findTask(out, "t1")
	if tk.Status != TaskWaitingHuman {
		t.Fatalf("irreversible task should be waiting_human, got %s", tk.Status)
	}
	if tk.Status == TaskBlocked {
		t.Fatalf("irreversible task must NOT be blocked")
	}
	if atomic.LoadInt32(&mc.dispatchN) != 0 {
		t.Fatalf("irreversible task must not be dispatched pre-approval, dispatchN=%d", mc.dispatchN)
	}
}

// TestIntervene_ResolveApprovesIrreversible verifies the full path:
// trigger1 -> waiting_human -> resolveInterventions (approve) -> pending ->
// re-dispatch -> done. resolveInterventions tolerates a failing RunInteractive
// (no real claude in tests) and reconciles from the pre-written answer.md.
func TestIntervene_ResolveApprovesIrreversible(t *testing.T) {
	cfg := testCfg()
	cfg.MaxWorkers = 1
	mc := &mockClaude{}
	mg := &mockGit{}
	ctrl, store := newTestController(t, cfg, mc, mg)
	ctrl.Mode = &Mode{Store: store, Workspace: store.Root + "/.."}
	ctrl.Handoff = &Handoff{Store: store}

	plan := &Plan{Goal: "g", Ready: true, Tasks: []Task{
		{ID: "t1", Status: TaskPending, Irreversible: true},
	}}
	_ = store.SavePlan(plan)
	st := &State{Phase: PhaseExecuting, RunID: "r"}
	_ = store.SaveState(st)

	// Phase 1: run until t1 is parked waiting_human.
	ctx, cancel := context.WithCancel(context.Background())
	errc := make(chan error, 1)
	go func() { errc <- ctrl.runExecuting(ctx, st) }()
	if !waitFor(t, 3*time.Second, func() bool { return ctrl.openInterventionCount() >= 1 }) {
		cancel()
		<-errc
		t.Fatal("t1 was not parked as an intervention")
	}
	cancel()
	<-errc

	// Simulate the human: write the answer for the open intervention + resume.
	q := store.LoadOpenInterventions()
	if len(q.Items) != 1 {
		t.Fatalf("expected one open intervention, got %d", len(q.Items))
	}
	id := q.Items[0].ID
	_ = store.WriteAtomicSidecar("intervention/"+id+"/answer.md", "approved")
	_ = store.SaveControl(&Control{Request: ReqResume, InterventionID: id})

	plan, _ = store.LoadPlan()
	aborted, err := ctrl.resolveInterventions(context.Background(), st, plan)
	if err != nil {
		t.Fatal(err)
	}
	if aborted {
		t.Fatal("did not expect abort")
	}
	out, _ := store.LoadPlan()
	tk := findTask(out, "t1")
	if !tk.IrrevApproved {
		t.Fatalf("task should be IrrevApproved after resolve")
	}
	if tk.Status != TaskPending {
		t.Fatalf("task should be pending for re-dispatch, got %s", tk.Status)
	}
	if len(store.LoadOpenInterventions().Items) != 0 {
		t.Fatalf("intervention queue should be empty after resolve")
	}

	// Phase 2: execute again -> approved task dispatches once and finishes.
	ctx2, cancel2 := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel2()
	if err := ctrl.runExecuting(ctx2, st); err != nil {
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

// TestResume_UsesResumeFlagAfterCrash verifies that a task left "running" with a
// SessionID (a hard crash mid-attempt) is re-dispatched with --resume on the
// SAME session and WITHOUT bumping Attempts — i.e. no white-slate redo. This is
// the NormalizeForResume -> scheduleTick -> snapshot path; a regression here
// (clearing ResumeSession before the worker snapshot) silently drops --resume.
func TestResume_UsesResumeFlagAfterCrash(t *testing.T) {
	cfg := testCfg()
	cfg.MaxWorkers = 1
	mc := &mockClaude{}
	mg := &mockGit{}
	ctrl, store := newTestController(t, cfg, mc, mg)

	plan := &Plan{Goal: "g", Ready: true, Tasks: []Task{
		// Crashed mid-attempt: still "running" with a session id, attempts=1.
		{ID: "t1", Status: TaskRunning, SessionID: "S1", Attempts: 1},
	}}
	_ = store.SavePlan(plan)
	st := &State{Phase: PhaseExecuting, RunID: "r"}
	_ = store.SaveState(st)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := ctrl.runExecuting(ctx, st); err != nil {
		t.Fatal(err)
	}

	out, _ := store.LoadPlan()
	tk := findTask(out, "t1")
	if tk.Status != TaskDone {
		t.Fatalf("t1 should be done, got %s", tk.Status)
	}
	if tk.Attempts != 1 {
		t.Fatalf("resume must NOT bump Attempts (same attempt), got %d", tk.Attempts)
	}
	mc.mu.Lock()
	resumed := mc.resumeByTask["t1"]
	sess := mc.sessionByTask["t1"]
	mc.mu.Unlock()
	if !resumed {
		t.Fatalf("resumed attempt must dispatch with --resume (Resume=true)")
	}
	if sess != "S1" {
		t.Fatalf("resume must reuse the crashed session id S1, got %q", sess)
	}
}

// TestFreshDispatch_NewSession verifies a fresh pending task (no session) is
// dispatched with a NEW session id (not --resume).
func TestFreshDispatch_NewSession(t *testing.T) {
	cfg := testCfg()
	cfg.MaxWorkers = 1
	mc := &mockClaude{}
	ctrl, store := newTestController(t, cfg, mc, &mockGit{})
	plan := &Plan{Goal: "g", Ready: true, Tasks: []Task{{ID: "t1", Status: TaskPending}}}
	_ = store.SavePlan(plan)
	st := &State{Phase: PhaseExecuting, RunID: "r"}
	_ = store.SaveState(st)
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := ctrl.runExecuting(ctx, st); err != nil {
		t.Fatal(err)
	}
	mc.mu.Lock()
	resumed := mc.resumeByTask["t1"]
	sess := mc.sessionByTask["t1"]
	mc.mu.Unlock()
	if resumed {
		t.Fatalf("fresh task must NOT use --resume")
	}
	if sess == "" {
		t.Fatalf("fresh task must get a generated session id")
	}
}

// mustPlan loads the plan or returns an empty one (for error messages).
func mustPlan(s *Store) *Plan {
	p, _ := s.LoadPlan()
	if p == nil {
		return &Plan{}
	}
	return p
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
	outcome, err := rv.RunGate(context.Background(), plan, tk)
	if err != nil {
		t.Fatalf("RunGate should not bubble dispatch error, got %v", err)
	}
	if outcome.Passed {
		t.Fatalf("expected not passed")
	}
	if outcome.FormatError {
		t.Fatalf("a severe-content finding is not a format error")
	}
	if outcome.LastSevere == "" {
		t.Fatalf("lastSevere must be preserved across revise dispatch error")
	}
}

// errOnWorkerClaude returns an error on worker (non-review) dispatch but
// delegates review calls to the embedded reviewer mock.
type errOnWorkerClaude struct{ review *mockClaude }

func (e *errOnWorkerClaude) RunPrompt(ctx context.Context, dir, model, prompt, logPath string, opts RunOpts) ([]byte, error) {
	if strings.Contains(prompt, "independent code reviewer") {
		return e.review.RunPrompt(ctx, dir, model, prompt, logPath, opts)
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

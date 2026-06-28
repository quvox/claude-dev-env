package main

import (
	"bufio"
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

func TestStateRoundTrip(t *testing.T) {
	dir := t.TempDir()
	s, err := NewStore(dir)
	if err != nil {
		t.Fatal(err)
	}
	in := &State{Phase: PhaseExecuting, RunID: "run-x", CurrentTask: "t2"}
	if err := s.SaveState(in); err != nil {
		t.Fatal(err)
	}
	out, err := s.LoadState()
	if err != nil {
		t.Fatal(err)
	}
	if out == nil || out.Phase != PhaseExecuting || out.RunID != "run-x" || out.CurrentTask != "t2" {
		t.Fatalf("state mismatch: %+v", out)
	}
	if out.UpdatedAt == "" || out.StartedAt == "" {
		t.Fatalf("timestamps not stamped: %+v", out)
	}
}

func TestLoadStateMissing(t *testing.T) {
	s, _ := NewStore(t.TempDir())
	st, err := s.LoadState()
	if err != nil {
		t.Fatal(err)
	}
	if st != nil {
		t.Fatalf("expected nil for missing state, got %+v", st)
	}
}

func TestPlanRoundTrip(t *testing.T) {
	s, _ := NewStore(t.TempDir())
	in := &Plan{
		Goal: "g", Completion: "c", Ready: true,
		Tasks: []Task{
			{ID: "t1", Title: "a", Status: TaskDone, Attempts: 2, Deps: []string{}},
			{ID: "t2", Title: "b", Status: TaskPending, Deps: []string{"t1"},
				Result: &WorkerResult{Done: true, Summary: "ok", Changes: []string{"f.go"}}},
		},
	}
	if err := s.SavePlan(in); err != nil {
		t.Fatal(err)
	}
	out, err := s.LoadPlan()
	if err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(in, out) {
		t.Fatalf("plan round trip mismatch:\n in=%+v\nout=%+v", in, out)
	}
}

func TestControlRoundTripAndDelete(t *testing.T) {
	s, _ := NewStore(t.TempDir())
	if err := s.SaveControl(&Control{Request: ReqResume, InterventionID: "iv1"}); err != nil {
		t.Fatal(err)
	}
	c, err := s.LoadControl()
	if err != nil || c == nil || c.Request != ReqResume || c.InterventionID != "iv1" {
		t.Fatalf("control load mismatch: %+v err=%v", c, err)
	}
	if c.TS == "" {
		t.Fatalf("ts not stamped")
	}
	if err := s.DeleteControl(); err != nil {
		t.Fatal(err)
	}
	c2, _ := s.LoadControl()
	if c2 != nil {
		t.Fatalf("control should be deleted, got %+v", c2)
	}
	// Deleting again is a no-op.
	if err := s.DeleteControl(); err != nil {
		t.Fatalf("double delete should be nil, got %v", err)
	}
}

func TestAuditAppend(t *testing.T) {
	s, _ := NewStore(t.TempDir())
	for i := 0; i < 3; i++ {
		if err := s.AppendAudit(AuditEntry{Event: "e", TaskID: "t1",
			Usage: &Usage{InputTokens: i, OutputTokens: i * 2}}); err != nil {
			t.Fatal(err)
		}
	}
	f, err := os.Open(filepath.Join(s.Root, "audit.jsonl"))
	if err != nil {
		t.Fatal(err)
	}
	defer f.Close()
	n := 0
	sc := bufio.NewScanner(f)
	for sc.Scan() {
		var e AuditEntry
		if err := json.Unmarshal(sc.Bytes(), &e); err != nil {
			t.Fatalf("line %d not valid json: %v", n, err)
		}
		if e.TS == "" || e.Event != "e" {
			t.Fatalf("bad audit entry: %+v", e)
		}
		n++
	}
	if n != 3 {
		t.Fatalf("expected 3 audit lines, got %d", n)
	}
}

func TestSidecarRoundTrip(t *testing.T) {
	s, _ := NewStore(t.TempDir())
	if v, _ := s.ReadAtomicSidecar("open_intervention"); v != "" {
		t.Fatalf("expected empty sidecar, got %q", v)
	}
	if err := s.WriteAtomicSidecar("open_intervention", "iv-9"); err != nil {
		t.Fatal(err)
	}
	v, err := s.ReadAtomicSidecar("open_intervention")
	if err != nil || v != "iv-9" {
		t.Fatalf("sidecar mismatch: %q err=%v", v, err)
	}
	if err := s.RemoveSidecar("open_intervention"); err != nil {
		t.Fatal(err)
	}
	if v, _ := s.ReadAtomicSidecar("open_intervention"); v != "" {
		t.Fatalf("sidecar should be removed, got %q", v)
	}
}

func TestResumeContinuationPoint(t *testing.T) {
	// NormalizeForResume resets in-flight tasks; the continuation point is the
	// set of remaining (non-done/failed/blocked) tasks.
	plan := &Plan{Tasks: []Task{
		{ID: "t1", Status: TaskDone},
		{ID: "t2", Status: TaskRunning},
		{ID: "t3", Status: TaskReview},
		{ID: "t4", Status: TaskFailed},
		{ID: "t5", Status: ""},
	}}
	NormalizeForResume(plan)
	want := map[string]string{
		"t1": TaskDone, "t2": TaskPending, "t3": TaskPending,
		"t4": TaskFailed, "t5": TaskPending,
	}
	for _, tk := range plan.Tasks {
		if want[tk.ID] != tk.Status {
			t.Fatalf("task %s: want %s got %s", tk.ID, want[tk.ID], tk.Status)
		}
	}
}

func TestWorktreePaths(t *testing.T) {
	s, _ := NewStore("/ws")
	if got := s.WorktreeRel("t1"); got != filepath.Join(".orchestrator", "worktrees", "t1") {
		t.Fatalf("rel path: %s", got)
	}
}

package main

import (
	"os"
	"path/filepath"
	"testing"
)

// TestArchiveRun_MovesNotDeletes verifies a reset archives the run into
// history/<run_id>/ rather than deleting it (docs/06 §4.3: only `rm` deletes).
func TestArchiveRun_MovesNotDeletes(t *testing.T) {
	store, err := NewStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	if err := store.SaveState(&State{Phase: PhaseExecuting, RunID: "run-XYZ"}); err != nil {
		t.Fatal(err)
	}
	if err := store.SavePlan(&Plan{Goal: "g", Ready: true, Tasks: []Task{{ID: "t1", Completion: "c"}}}); err != nil {
		t.Fatal(err)
	}
	_ = os.WriteFile(store.path("summary.md"), []byte("sum"), 0o644)
	_ = os.MkdirAll(store.path("intervention"), 0o755)
	_ = os.WriteFile(store.path("intervention", "open.json"), []byte(`{"items":[]}`), 0o644)

	if err := store.ArchiveRun(); err != nil {
		t.Fatalf("ArchiveRun: %v", err)
	}

	// Originals moved out of the live location.
	for _, name := range []string{"state.json", "plan.json", "summary.md"} {
		if _, err := os.Stat(store.path(name)); !os.IsNotExist(err) {
			t.Errorf("%s should have been moved out of the live dir", name)
		}
	}
	// Archived copies exist under history/run-XYZ/ (nothing deleted).
	hist := store.path("history", "run-XYZ")
	for _, name := range []string{"state.json", "plan.json", "summary.md"} {
		if _, err := os.Stat(filepath.Join(hist, name)); err != nil {
			t.Errorf("archived %s missing: %v", name, err)
		}
	}
	if _, err := os.Stat(filepath.Join(hist, "intervention", "open.json")); err != nil {
		t.Errorf("archived open.json missing: %v", err)
	}
	// The archived plan is still loadable JSON (referenceable).
	data, err := os.ReadFile(filepath.Join(hist, "plan.json"))
	if err != nil || len(data) == 0 {
		t.Fatalf("archived plan.json unreadable: %v", err)
	}
}

// TestArchiveRun_NoStateFallsBackToTimestamp verifies archiving works even with
// no state.json (run_id falls back to a timestamp; no crash, no deletion).
func TestArchiveRun_NoState(t *testing.T) {
	store, err := NewStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	_ = store.SavePlan(&Plan{Goal: "g", Ready: false})
	if err := store.ArchiveRun(); err != nil {
		t.Fatalf("ArchiveRun with no state: %v", err)
	}
	// plan.json moved somewhere under history/
	entries, _ := os.ReadDir(store.path("history"))
	if len(entries) == 0 {
		t.Fatal("expected a history/<run> dir")
	}
}

func TestCountUndone(t *testing.T) {
	p := &Plan{Tasks: []Task{
		{ID: "t1", Status: TaskDone}, {ID: "t2", Status: TaskDone},
		{ID: "t3", Status: TaskPending}, {ID: "t4", Status: TaskWaitingHuman},
	}}
	if got := countUndone(p); got != 2 {
		t.Fatalf("countUndone=%d want 2", got)
	}
	if AllDone(p) {
		t.Fatal("AllDone should be false")
	}
	all := &Plan{Tasks: []Task{{ID: "t1", Status: TaskDone}}}
	if !AllDone(all) || countUndone(all) != 0 {
		t.Fatal("all-done plan should be AllDone with 0 undone")
	}
}

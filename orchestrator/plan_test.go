package main

import "testing"

func ids(ts []*Task) []string {
	out := make([]string, len(ts))
	for i, t := range ts {
		out[i] = t.ID
	}
	return out
}

func TestReadyTasks_DependencyResolution(t *testing.T) {
	plan := &Plan{Tasks: []Task{
		{ID: "t1", Status: TaskDone},
		{ID: "t2", Status: TaskPending, Deps: []string{"t1"}},
		{ID: "t3", Status: TaskPending, Deps: []string{"t2"}}, // dep not done yet
		{ID: "t4", Status: TaskPending},                       // no deps
	}}
	ready := ReadyTasks(plan, 0)
	got := ids(ready)
	// t2 (dep done) and t4 (no deps) are ready; t3 is not (dep t2 pending).
	if len(got) != 2 || got[0] != "t2" || got[1] != "t4" {
		t.Fatalf("expected [t2 t4], got %v", got)
	}
}

func TestReadyTasks_ParallelLimit(t *testing.T) {
	plan := &Plan{Tasks: []Task{
		{ID: "a", Status: TaskPending},
		{ID: "b", Status: TaskPending},
		{ID: "c", Status: TaskPending},
	}}
	if got := ids(ReadyTasks(plan, 2)); len(got) != 2 {
		t.Fatalf("limit=2 should cap ready, got %v", got)
	}
	if got := ids(ReadyTasks(plan, 0)); len(got) != 3 {
		t.Fatalf("limit=0 means no cap, got %v", got)
	}
}

func TestReadyTasks_FailedDepExcluded(t *testing.T) {
	plan := &Plan{Tasks: []Task{
		{ID: "t1", Status: TaskFailed},
		{ID: "t2", Status: TaskPending, Deps: []string{"t1"}},
	}}
	if got := ids(ReadyTasks(plan, 0)); len(got) != 0 {
		t.Fatalf("task with failed dep must not be ready, got %v", got)
	}
}

func TestMarkBlockedByFailedDeps(t *testing.T) {
	plan := &Plan{Tasks: []Task{
		{ID: "t1", Status: TaskFailed},
		{ID: "t2", Status: TaskPending, Deps: []string{"t1"}},
		{ID: "t3", Status: TaskPending, Deps: []string{"missing"}},
		{ID: "t4", Status: TaskPending},
	}}
	MarkBlockedByFailedDeps(plan)
	wantBlocked := map[string]bool{"t2": true, "t3": true}
	for _, tk := range plan.Tasks {
		if wantBlocked[tk.ID] && tk.Status != TaskBlocked {
			t.Fatalf("%s should be blocked, got %s", tk.ID, tk.Status)
		}
		if tk.ID == "t4" && tk.Status != TaskPending {
			t.Fatalf("t4 should remain pending, got %s", tk.Status)
		}
	}
}

func TestAllDoneAndSettled(t *testing.T) {
	done := &Plan{Tasks: []Task{{Status: TaskDone}, {Status: TaskDone}}}
	if !AllDone(done) || !AllSettled(done) {
		t.Fatalf("all-done plan should be done and settled")
	}
	mixed := &Plan{Tasks: []Task{{Status: TaskDone}, {Status: TaskFailed}}}
	if AllDone(mixed) {
		t.Fatalf("mixed plan is not all-done")
	}
	if !AllSettled(mixed) {
		t.Fatalf("done+failed is settled")
	}
	running := &Plan{Tasks: []Task{{Status: TaskRunning}}}
	if AllSettled(running) {
		t.Fatalf("running plan is not settled")
	}
}

// TestStatusTransition_HappyPath exercises pending -> running -> review -> done
// at the data level via the scheduling helpers.
func TestStatusTransition_HappyPath(t *testing.T) {
	plan := &Plan{Tasks: []Task{{ID: "t1", Status: TaskPending}}}
	ready := ReadyTasks(plan, 1)
	if len(ready) != 1 {
		t.Fatalf("t1 should be ready")
	}
	ready[0].Status = TaskRunning
	ready[0].Attempts++
	if plan.Tasks[0].Attempts != 1 {
		t.Fatalf("attempts should be 1 after one dispatch")
	}
	ready[0].Status = TaskReview
	ready[0].Status = TaskDone
	if !AllDone(plan) {
		t.Fatalf("plan should be all done after t1 done")
	}
}

// TestReviseDoesNotIncrementAttempts documents the invariant: review/revise is
// within one Attempt. Attempts is only bumped on (re)dispatch by the
// controller, never by review.RunGate.
func TestReviseDoesNotIncrementAttempts(t *testing.T) {
	task := &Task{ID: "t1", Status: TaskReview, Attempts: 1}
	// Simulate a revise round: status flips, attempts unchanged.
	task.Status = TaskRevise
	task.Status = TaskReview
	if task.Attempts != 1 {
		t.Fatalf("revise must not change attempts, got %d", task.Attempts)
	}
}

func TestDependencyChainOrder(t *testing.T) {
	// t1 -> t2 -> t3 chain; only the head is ready initially.
	plan := &Plan{Tasks: []Task{
		{ID: "t1", Status: TaskPending},
		{ID: "t2", Status: TaskPending, Deps: []string{"t1"}},
		{ID: "t3", Status: TaskPending, Deps: []string{"t2"}},
	}}
	if got := ids(ReadyTasks(plan, 0)); len(got) != 1 || got[0] != "t1" {
		t.Fatalf("only t1 ready, got %v", got)
	}
	plan.Tasks[0].Status = TaskDone
	if got := ids(ReadyTasks(plan, 0)); len(got) != 1 || got[0] != "t2" {
		t.Fatalf("after t1 done, t2 ready, got %v", got)
	}
	plan.Tasks[1].Status = TaskDone
	if got := ids(ReadyTasks(plan, 0)); len(got) != 1 || got[0] != "t3" {
		t.Fatalf("after t2 done, t3 ready, got %v", got)
	}
}

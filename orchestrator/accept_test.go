package main

import (
	"context"
	"os"
	"testing"
)

// TestReconcileAndAccept_MarksDoneAndMerges verifies that accepting a task during
// an intervention marks it done + integrates its worktree (instead of bouncing it
// back to pending, which caused the resolve→re-fail→re-intervene loop).
func TestReconcileAndAccept_MarksDoneAndMerges(t *testing.T) {
	mg := &mockGit{}
	ctrl, store := newTestController(t, testCfg(), &mockClaude{}, mg)
	id := "iv-accept-1"
	_ = store.WriteQuestion(id, "レビューゲート不具合")
	_ = store.AddOpenIntervention(OpenIntervention{ID: id, TaskID: "t1", TriggerReason: TriggerReviewGateDefect})
	plan := &Plan{Goal: "g", Ready: true, Tasks: []Task{
		{ID: "t1", Status: TaskWaitingHuman, OpenInterventionID: id, Completion: "c"},
	}}
	if err := store.SavePlan(plan); err != nil {
		t.Fatal(err)
	}
	dir := store.path("intervention", id)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(store.path("intervention", id, "answer.md"), []byte("done として受理"), 0o644); err != nil {
		t.Fatal(err)
	}

	ctrl.reconcileAndAccept(context.Background(), plan, id, "t1")

	if plan.Tasks[0].Status != TaskDone {
		t.Fatalf("t1 status=%q want done (in-memory)", plan.Tasks[0].Status)
	}
	got, _ := store.LoadPlan()
	if got.Tasks[0].Status != TaskDone {
		t.Fatalf("t1 status=%q want done (persisted)", got.Tasks[0].Status)
	}
	if got.Tasks[0].OpenInterventionID != "" {
		t.Fatalf("OpenInterventionID not cleared: %q", got.Tasks[0].OpenInterventionID)
	}
	if q := store.LoadOpenInterventions(); len(q.Items) != 0 {
		t.Fatalf("open queue not empty: %d", len(q.Items))
	}
	mg.mu.Lock()
	defer mg.mu.Unlock()
	if len(mg.merges) != 1 || mg.merges[0] != "orch/t1" {
		t.Fatalf("expected merge of orch/t1, got %v", mg.merges)
	}
}

// TestReconcileAndAccept_NoAnswerLeavesOpen verifies accept without a recorded
// answer is a no-op (the intervention stays open, safe to retry).
func TestReconcileAndAccept_NoAnswerLeavesOpen(t *testing.T) {
	ctrl, store := newTestController(t, testCfg(), &mockClaude{}, &mockGit{})
	id := "iv-accept-2"
	_ = store.WriteQuestion(id, "q")
	_ = store.AddOpenIntervention(OpenIntervention{ID: id, TaskID: "t1", TriggerReason: TriggerReviewGateDefect})
	plan := &Plan{Goal: "g", Ready: true, Tasks: []Task{
		{ID: "t1", Status: TaskWaitingHuman, OpenInterventionID: id, Completion: "c"},
	}}
	_ = store.SavePlan(plan)

	ctrl.reconcileAndAccept(context.Background(), plan, id, "t1")

	if plan.Tasks[0].Status != TaskWaitingHuman {
		t.Fatalf("t1 status=%q want waiting_human (no answer → no-op)", plan.Tasks[0].Status)
	}
	if q := store.LoadOpenInterventions(); len(q.Items) != 1 {
		t.Fatalf("open queue should still hold 1, got %d", len(q.Items))
	}
}

// reformatClaude returns prose on the review call and JSON on the reformat call.
type reformatClaude struct{ calls int }

func (r *reformatClaude) RunPrompt(ctx context.Context, dir, model, prompt, logPath string, opts RunOpts) ([]byte, error) {
	r.calls++
	if r.calls == 1 {
		// First call = the review: narrate a prose conclusion (no JSON).
		return []byte(`{"type":"result","subtype":"success","result":"Review complete — no critical or major findings."}`), nil
	}
	// Second call = the reformat: emit the required JSON.
	return []byte(`{"type":"result","subtype":"success","result":"{\"findings\":[]}"}`), nil
}

// TestReview_ReformatsProseToJSON verifies a prose review verdict is recovered via
// the follow-up JSON reformat call, so it does not escalate as a gate defect.
func TestReview_ReformatsProseToJSON(t *testing.T) {
	rc := &reformatClaude{}
	store, err := NewStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	worker := &Worker{Store: store, Claude: rc, Git: &mockGit{}, Cfg: testCfg(), Workspace: store.Root + "/.."}
	rv := &Reviewer{Store: store, Claude: rc, Cfg: testCfg(), Worker: worker}
	p := &Plan{Goal: "g"}
	tk := &Task{ID: "t1", Title: "t", Completion: "c"}
	res, err := rv.Review(context.Background(), p, tk)
	if err != nil {
		t.Fatalf("Review returned error (should have recovered via reformat): %v", err)
	}
	if res == nil || res.HasSevere() {
		t.Fatalf("expected a clean (no-severe) result, got %+v", res)
	}
	if rc.calls != 2 {
		t.Fatalf("expected 2 claude calls (review + reformat), got %d", rc.calls)
	}
}

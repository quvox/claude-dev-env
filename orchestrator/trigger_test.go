package main

import "testing"

func baseCfg() Config {
	c := DefaultConfig()
	c.StuckLimit = 3
	c.MaxReviewRounds = 3
	return c
}

func TestEvaluate_PreDispatchIrreversible(t *testing.T) {
	task := &Task{ID: "t1", Irreversible: true, Status: TaskPending}
	fire, reason := Evaluate(TriggerContext{
		Phase: PhasePreDispatch, Task: task, Plan: &Plan{}, State: &State{}, Config: baseCfg(),
	})
	if !fire || reason != TriggerIrreversible {
		t.Fatalf("expected irreversible fire, got fire=%v reason=%q", fire, reason)
	}
}

func TestEvaluate_PreDispatchNonIrreversible(t *testing.T) {
	task := &Task{ID: "t1", Irreversible: false}
	fire, _ := Evaluate(TriggerContext{
		Phase: PhasePreDispatch, Task: task, Plan: &Plan{}, State: &State{}, Config: baseCfg(),
	})
	if fire {
		t.Fatalf("expected no fire for non-irreversible pre-dispatch")
	}
}

func TestEvaluate_PreDispatchApprovedIrreversibleDoesNotFire(t *testing.T) {
	// After a human approves an irreversible task, the gate must not re-fire so
	// the task can finally be dispatched (no infinite re-fire on resume).
	task := &Task{ID: "t1", Irreversible: true, IrrevApproved: true}
	fire, _ := Evaluate(TriggerContext{
		Phase: PhasePreDispatch, Task: task, Plan: &Plan{}, State: &State{}, Config: baseCfg(),
	})
	if fire {
		t.Fatalf("approved irreversible task must not re-fire trigger1")
	}
}

func TestEvaluate_NeedsHumanReasons(t *testing.T) {
	cases := []struct {
		reason     string
		wantReason string
	}{
		{ReasonAmbiguity, TriggerAmbiguity},
		{ReasonPolicyBranch, TriggerPolicyBranch},
		{ReasonPrerequisiteBroke, TriggerPrerequisite},
		{ReasonCriticalDecision, TriggerIrreversible},
	}
	for _, c := range cases {
		res := &WorkerResult{Done: false, NeedsHuman: &NeedsHuman{Reason: c.reason}}
		fire, reason := Evaluate(TriggerContext{
			Phase: PhasePostDispatch, Task: &Task{ID: "t1", Attempts: 1},
			Plan: &Plan{}, State: &State{}, Result: res, Config: baseCfg(),
		})
		if !fire || reason != c.wantReason {
			t.Fatalf("reason %q: expected fire with %q, got fire=%v reason=%q",
				c.reason, c.wantReason, fire, reason)
		}
	}
}

func TestEvaluate_NoNeedsHumanNoFire(t *testing.T) {
	res := &WorkerResult{Done: true}
	fire, _ := Evaluate(TriggerContext{
		Phase: PhasePostDispatch, Task: &Task{ID: "t1", Attempts: 1},
		Plan: &Plan{}, State: &State{}, Result: res, Config: baseCfg(),
	})
	if fire {
		t.Fatalf("expected no fire for clean done result")
	}
}

func TestEvaluate_StuckLimitBoundary(t *testing.T) {
	cfg := baseCfg() // StuckLimit=3
	// Attempts just below the limit: no fire.
	fire, _ := Evaluate(TriggerContext{
		Phase: PhasePostDispatch, Task: &Task{ID: "t1", Attempts: 2},
		Plan: &Plan{}, State: &State{}, Config: cfg,
	})
	if fire {
		t.Fatalf("attempts=2 < limit=3 should not fire")
	}
	// Attempts at the limit: fire stuck.
	fire, reason := Evaluate(TriggerContext{
		Phase: PhasePostDispatch, Task: &Task{ID: "t1", Attempts: 3},
		Plan: &Plan{}, State: &State{}, Config: cfg,
	})
	if !fire || reason != TriggerStuck {
		t.Fatalf("attempts=3 == limit should fire stuck, got fire=%v reason=%q", fire, reason)
	}
}

func TestEvaluate_StuckThisAttempt(t *testing.T) {
	fire, reason := Evaluate(TriggerContext{
		Phase: PhasePostDispatch, Task: &Task{ID: "t1", Attempts: 1},
		Plan: &Plan{}, State: &State{}, Config: baseCfg(), StuckThisAttempt: true,
	})
	if !fire || reason != TriggerStuck {
		t.Fatalf("StuckThisAttempt should fire stuck, got fire=%v reason=%q", fire, reason)
	}
}

func TestEvaluate_StuckTakesPrecedenceOverNeedsHuman(t *testing.T) {
	// At stuck limit AND a NeedsHuman: stuck is checked first.
	res := &WorkerResult{NeedsHuman: &NeedsHuman{Reason: ReasonAmbiguity}}
	fire, reason := Evaluate(TriggerContext{
		Phase: PhasePostDispatch, Task: &Task{ID: "t1", Attempts: 3},
		Plan: &Plan{}, State: &State{}, Result: res, Config: baseCfg(),
	})
	if !fire || reason != TriggerStuck {
		t.Fatalf("expected stuck precedence, got fire=%v reason=%q", fire, reason)
	}
}

func TestEvaluate_NilTask(t *testing.T) {
	if fire, _ := Evaluate(TriggerContext{Phase: PhasePostDispatch, Config: baseCfg()}); fire {
		t.Fatalf("nil task should not fire")
	}
}

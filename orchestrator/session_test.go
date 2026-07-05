package main

import "testing"

func TestNormalizeCName(t *testing.T) {
	cases := map[string]string{
		"hisol-work":   "hisol-work",
		"My Project":   "my-project",
		"a/b:c":        "a-b-c",
		"UPPER_case-1": "upper_case-1",
		"  spaced  ":   "spaced",
		"":             "project",
		"---":          "project",
		"日本語proj":      "proj", // non [a-z0-9_-] collapse to '-', trimmed
	}
	for in, want := range cases {
		if got := normalizeCName(in); got != want {
			t.Errorf("normalizeCName(%q)=%q want %q", in, got, want)
		}
	}
}

func TestSessionNames(t *testing.T) {
	m := &SessionManager{Prefix: "orch-hisol-work"}
	if got := m.MainSession(); got != "orch-hisol-work-main" {
		t.Errorf("MainSession=%q", got)
	}
	if got := m.WallbounceSession(); got != "orch-hisol-work-wallbounce" {
		t.Errorf("WallbounceSession=%q", got)
	}
	if got := m.WorkerSession("t3"); got != "orch-hisol-work-w-t3" {
		t.Errorf("WorkerSession=%q", got)
	}
}

func TestNewSessionManager_UsesComposeProjectName(t *testing.T) {
	t.Setenv("COMPOSE_PROJECT_NAME", "Some Proj")
	m := NewSessionManager()
	if m.Prefix != "orch-some-proj" {
		t.Fatalf("Prefix=%q want orch-some-proj", m.Prefix)
	}
}

func TestExpectedSessions(t *testing.T) {
	m := &SessionManager{Prefix: "orch-p"}
	plan := &Plan{Tasks: []Task{
		{ID: "t1", Status: TaskRunning},
		{ID: "t2", Status: TaskPending}, // not expected
		{ID: "t3", Status: TaskWaitingHuman},
		{ID: "t4", Status: TaskDone}, // not expected
	}}
	// wallbounce phase: main + wallbounce (+ any active workers)
	wb := m.ExpectedSessions(PhaseWallbounce, nil)
	if len(wb) != 2 || wb[0] != "orch-p-main" || wb[1] != "orch-p-wallbounce" {
		t.Fatalf("wallbounce expected [main wallbounce], got %v", wb)
	}
	// executing phase: main + worker sessions for active tasks only
	ex := m.ExpectedSessions(PhaseExecuting, plan)
	want := map[string]bool{"orch-p-main": true, "orch-p-w-t1": true, "orch-p-w-t3": true}
	if len(ex) != len(want) {
		t.Fatalf("executing expected 3 sessions, got %v", ex)
	}
	for _, n := range ex {
		if !want[n] {
			t.Fatalf("unexpected session %q in %v", n, ex)
		}
	}
}

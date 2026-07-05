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
	// Everything else is a WINDOW under the main session (session:window target).
	if got := m.DashboardWindow(); got != "orch-hisol-work-main:dashboard" {
		t.Errorf("DashboardWindow=%q", got)
	}
	if got := m.WallbounceWindow(); got != "orch-hisol-work-main:wallbounce" {
		t.Errorf("WallbounceWindow=%q", got)
	}
	if got := m.WorkerWindow("t3"); got != "orch-hisol-work-main:w-t3" {
		t.Errorf("WorkerWindow=%q", got)
	}
}

func TestSplitTarget(t *testing.T) {
	cases := map[string][2]string{
		"orch-p-main:w-t3":      {"orch-p-main", "w-t3"},
		"orch-p-main:dashboard": {"orch-p-main", "dashboard"},
		"orch-p-main":           {"orch-p-main", ""},
	}
	for in, want := range cases {
		s, w := splitTarget(in)
		if s != want[0] || w != want[1] {
			t.Errorf("splitTarget(%q)=(%q,%q) want (%q,%q)", in, s, w, want[0], want[1])
		}
	}
}

func TestNewSessionManager_UsesComposeProjectName(t *testing.T) {
	t.Setenv("COMPOSE_PROJECT_NAME", "Some Proj")
	m := NewSessionManager()
	if m.Prefix != "orch-some-proj" {
		t.Fatalf("Prefix=%q want orch-some-proj", m.Prefix)
	}
}

func TestExpectedWindows(t *testing.T) {
	m := &SessionManager{Prefix: "orch-p"}
	plan := &Plan{Tasks: []Task{
		{ID: "t1", Status: TaskRunning},
		{ID: "t2", Status: TaskPending}, // not expected
		{ID: "t3", Status: TaskWaitingHuman},
		{ID: "t4", Status: TaskDone}, // not expected
	}}
	// wallbounce phase: the wallbounce window (dashboard is the controller's own).
	wb := m.ExpectedWindows(PhaseWallbounce, nil)
	if len(wb) != 1 || wb[0] != "orch-p-main:wallbounce" {
		t.Fatalf("wallbounce expected [main:wallbounce], got %v", wb)
	}
	// executing phase: worker windows for active tasks only.
	ex := m.ExpectedWindows(PhaseExecuting, plan)
	want := map[string]bool{"orch-p-main:w-t1": true, "orch-p-main:w-t3": true}
	if len(ex) != len(want) {
		t.Fatalf("executing expected 2 windows, got %v", ex)
	}
	for _, n := range ex {
		if !want[n] {
			t.Fatalf("unexpected window %q in %v", n, ex)
		}
	}
}

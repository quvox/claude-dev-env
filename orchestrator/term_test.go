package main

import (
	"strings"
	"testing"
)

var menu3 = []menuItem{
	{Value: "continue", Label: "1. 続ける"},
	{Value: "execute", Label: "2. 実行"},
	{Value: "done", Label: "3. 終了"},
}

func TestResolveMenu_EnterPicksDefault(t *testing.T) {
	if got := resolveMenu(menu3, 0, []byte("\r")); got != "continue" {
		t.Fatalf("Enter at default 0 => %q, want continue", got)
	}
	if got := resolveMenu(menu3, 1, []byte("\n")); got != "execute" {
		t.Fatalf("Enter at default 1 => %q, want execute", got)
	}
}

func TestResolveMenu_ArrowThenEnter(t *testing.T) {
	// down, down, Enter from default 0 => index 2 (done)
	if got := resolveMenu(menu3, 0, []byte("\x1b[B\x1b[B\r")); got != "done" {
		t.Fatalf("down down Enter => %q, want done", got)
	}
	// up wraps from 0 to 2
	if got := resolveMenu(menu3, 0, []byte("\x1b[A\r")); got != "done" {
		t.Fatalf("up (wrap) Enter => %q, want done", got)
	}
}

func TestResolveMenu_JKMovement(t *testing.T) {
	if got := resolveMenu(menu3, 0, []byte("j\r")); got != "execute" {
		t.Fatalf("j Enter => %q, want execute", got)
	}
	if got := resolveMenu(menu3, 2, []byte("k\r")); got != "execute" {
		t.Fatalf("k Enter => %q, want execute", got)
	}
}

func TestResolveMenu_NumberImmediate(t *testing.T) {
	// number keys confirm immediately (no Enter needed)
	if got := resolveMenu(menu3, 0, []byte("2")); got != "execute" {
		t.Fatalf("'2' => %q, want execute", got)
	}
	if got := resolveMenu(menu3, 0, []byte("3")); got != "done" {
		t.Fatalf("'3' => %q, want done", got)
	}
	// out-of-range digit is ignored; falls through to current selection
	if got := resolveMenu(menu3, 0, []byte("9")); got != "continue" {
		t.Fatalf("'9' (out of range) => %q, want continue (current)", got)
	}
}

func TestResolveMenu_NoInputReturnsCurrent(t *testing.T) {
	if got := resolveMenu(menu3, 2, nil); got != "done" {
		t.Fatalf("no input => %q, want done (default)", got)
	}
}

func TestSelectMenu_NonTTYReturnsDefault(t *testing.T) {
	// In tests stdin is not a TTY, so selectMenu must return the default value
	// without reading keys (never auto-advances).
	if got := selectMenu("t", menu3, 1); got != "execute" {
		t.Fatalf("non-TTY selectMenu => %q, want execute (default)", got)
	}
}

func TestTerminalConfirm_NonTTYContinue(t *testing.T) {
	if got := terminalConfirm("x"); got != "continue" {
		t.Fatalf("non-TTY terminalConfirm => %q, want continue", got)
	}
}

func TestBuildQuestion_NumbersOptions(t *testing.T) {
	task := &Task{
		ID:         "t1",
		Title:      "認証方式の決定",
		Completion: "OAuth か API キーかを決めて実装する",
		Result: &WorkerResult{
			NeedsHuman: &NeedsHuman{
				Reason:   ReasonPolicyBranch,
				Question: "認証方式が決め切れません。どちらにしますか？",
				Options:  []string{"OAuth", "API キー"},
			},
		},
	}
	q := buildQuestion(task, ReasonPolicyBranch)
	if !strings.Contains(q, "1. OAuth") || !strings.Contains(q, "2. API キー") {
		t.Fatalf("options not numbered:\n%s", q)
	}
	if strings.Contains(q, "- OAuth") {
		t.Fatalf("options still bulleted with '- ':\n%s", q)
	}
	if !strings.Contains(q, "認証方式の決定") {
		t.Fatalf("task title missing from question:\n%s", q)
	}
}

func TestRenderSelectorNumbers(t *testing.T) {
	st := &DashboardState{
		Goal: "g",
		Tasks: []DashTask{
			{ID: "t1", Title: "A", Status: TaskDone},         // not selectable
			{ID: "t2", Title: "B", Status: TaskRunning},      // selector ‹1›, ordinal [2/5]
			{ID: "t3", Title: "C", Status: TaskPending},      // not selectable
			{ID: "t4", Title: "D", Status: TaskWaitingHuman}, // selector ‹2›, ordinal [4/5]
			{ID: "t5", Title: "E", Status: TaskReview},       // selector ‹3›, ordinal [5/5]
		},
	}
	// Sessions non-nil so the key hint is advertised.
	d := &Dashboard{State: st, Sessions: &SessionManager{Prefix: "orch-x"}}
	out := d.renderString()

	// Selector number is a separate column from the task ordinal and only the
	// selectable rows carry it — here ‹2› sits on the [4/5] task (they differ).
	if !strings.Contains(out, "‹1› [2/5]") {
		t.Errorf("running row missing selector ‹1› on ordinal [2/5]:\n%s", out)
	}
	if !strings.Contains(out, "‹2› [4/5]") {
		t.Errorf("waiting_human row missing selector ‹2› on ordinal [4/5]:\n%s", out)
	}
	if !strings.Contains(out, "‹3› [5/5]") {
		t.Errorf("review row missing selector ‹3› on ordinal [5/5]:\n%s", out)
	}
	// Non-selectable rows must NOT get a selector number.
	if strings.Contains(out, "‹4›") {
		t.Errorf("selector counter leaked past selectable workers:\n%s", out)
	}
	// The pending/done ordinals ([1/5],[3/5]) must render without a ‹k› prefix.
	if !strings.Contains(out, "    [1/5]") { // 3-space pad + leading space
		t.Errorf("done row should be blank-padded (no selector):\n%s", out)
	}
	// Key hint advertises the number selector when selectable workers exist.
	if !strings.Contains(out, "[1-9]worker画面へ") {
		t.Errorf("key hint missing worker selector advice:\n%s", out)
	}
}

func TestRenderNoSelectorHintWhenNoneSelectable(t *testing.T) {
	st := &DashboardState{Goal: "g", Tasks: []DashTask{
		{ID: "t1", Title: "A", Status: TaskDone},
		{ID: "t2", Title: "B", Status: TaskPending},
	}}
	d := &Dashboard{State: st, Sessions: &SessionManager{Prefix: "orch-x"}}
	out := d.renderString()
	if strings.Contains(out, "[1-9]worker画面へ") {
		t.Errorf("selector hint shown with no selectable workers:\n%s", out)
	}
	if strings.Contains(out, "‹1›") {
		t.Errorf("selector number shown with no selectable workers:\n%s", out)
	}
}

func TestRenderNoSelectorHintWithoutSessions(t *testing.T) {
	// Sessions nil (tmux absent / legacy path): number keys do nothing, so the
	// hint must not be advertised even though a worker is selectable.
	st := &DashboardState{Goal: "g", Tasks: []DashTask{
		{ID: "t2", Title: "B", Status: TaskRunning},
	}}
	d := &Dashboard{State: st, Sessions: nil}
	out := d.renderString()
	if strings.Contains(out, "[1-9]worker画面へ") {
		t.Errorf("selector hint shown with nil Sessions:\n%s", out)
	}
	// The selector number column is still drawn (harmless, aids the [d] view).
	if !strings.Contains(out, "‹1›") {
		t.Errorf("selector number should still render for selectable worker:\n%s", out)
	}
}

func TestSelectableWorkerID(t *testing.T) {
	tasks := []DashTask{
		{ID: "t1", Status: TaskDone},         // not selectable
		{ID: "t2", Status: TaskRunning},      // #1
		{ID: "t3", Status: TaskPending},      // not selectable
		{ID: "t4", Status: TaskWaitingHuman}, // #2
		{ID: "t5", Status: TaskReview},       // #3
	}
	cases := map[int]string{0: "", 1: "t2", 2: "t4", 3: "t5", 4: ""}
	for n, want := range cases {
		if got := selectableWorkerID(tasks, n); got != want {
			t.Errorf("selectableWorkerID(n=%d)=%q want %q", n, got, want)
		}
	}
}

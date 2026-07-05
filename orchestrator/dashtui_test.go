package main

import (
	"strings"
	"testing"

	tea "github.com/charmbracelet/bubbletea"
)

func newTestDashModel(cursor int, tasks []DashTask) (dashModel, chan dashAction) {
	st := &DashboardState{Goal: "g", Tasks: tasks}
	actions := make(chan dashAction, 4)
	return dashModel{st: st, actions: actions, cursor: cursor}, actions
}

func TestDashView_RendersTasksAndCursor(t *testing.T) {
	m, _ := newTestDashModel(1, []DashTask{
		{ID: "t1", Title: "A", Status: TaskDone},           // not selectable
		{ID: "t2", Title: "Bee", Status: TaskRunning},      // selectable #0
		{ID: "t3", Title: "C", Status: TaskPending},        // not selectable
		{ID: "t4", Title: "Dee", Status: TaskWaitingHuman}, // selectable #1 (cursor)
	})
	out := m.View()
	// Goal + every task title present, all tasks listed with ordinals.
	for _, want := range []string{"goal: g", "[1/4]", "[2/4]", "[4/4]", "Bee", "Dee"} {
		if !strings.Contains(out, want) {
			t.Errorf("View missing %q:\n%s", want, out)
		}
	}
	// A cursor marker is drawn (on the selectable row at index 1 = t4).
	if !strings.Contains(out, "❯") {
		t.Errorf("View has no cursor marker:\n%s", out)
	}
	if strings.Count(out, "❯") != 1 {
		t.Errorf("expected exactly one cursor marker, got %d:\n%s", strings.Count(out, "❯"), out)
	}
}

func TestDashCursor_MovesAndClamps(t *testing.T) {
	tasks := []DashTask{
		{ID: "t2", Status: TaskRunning},      // selectable #0
		{ID: "t4", Status: TaskWaitingHuman}, // selectable #1
	} // 2 selectable rows
	m, _ := newTestDashModel(0, tasks)

	down := tea.KeyMsg{Type: tea.KeyDown}
	up := tea.KeyMsg{Type: tea.KeyUp}

	// down once -> 1, down again clamps at 1 (only 2 selectable)
	mm, _ := m.Update(down)
	m = mm.(dashModel)
	if m.cursor != 1 {
		t.Fatalf("after down cursor=%d want 1", m.cursor)
	}
	mm, _ = m.Update(down)
	m = mm.(dashModel)
	if m.cursor != 1 {
		t.Fatalf("down at end must clamp to 1, got %d", m.cursor)
	}
	// up twice clamps at 0
	mm, _ = m.Update(up)
	m = mm.(dashModel)
	mm, _ = m.Update(up)
	m = mm.(dashModel)
	if m.cursor != 0 {
		t.Fatalf("up at top must clamp to 0, got %d", m.cursor)
	}
}

func TestDashEnter_OnWaitingHumanSendsResolve(t *testing.T) {
	tasks := []DashTask{
		{ID: "t2", Status: TaskRunning},      // #0
		{ID: "t4", Status: TaskWaitingHuman}, // #1
	}
	m, actions := newTestDashModel(1, tasks) // cursor on the ⏸ worker
	m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	select {
	case a := <-actions:
		if a.kind != "resolve" || a.taskID != "t4" {
			t.Fatalf("got action %+v, want {resolve t4}", a)
		}
	default:
		t.Fatal("Enter on ⏸ worker did not emit a resolve action")
	}
}

func TestDashQuit_SendsQuit(t *testing.T) {
	m, actions := newTestDashModel(0, []DashTask{{ID: "t2", Status: TaskRunning}})
	m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'q'}})
	select {
	case a := <-actions:
		if a.kind != "quit" {
			t.Fatalf("got %+v want quit", a)
		}
	default:
		t.Fatal("q did not emit quit")
	}
}

func TestDashView_BrainstormingIsCursorSelect(t *testing.T) {
	st := &DashboardState{Phase: PhaseBrainstorming, Goal: "g"}
	m := dashModel{st: st, actions: make(chan dashAction, 4)}
	rows := m.selectable()
	if len(rows) != 1 || rows[0].status != PhaseBrainstorming {
		t.Fatalf("brainstorming selectable = %+v, want 1 brainstorming row", rows)
	}
	out := m.View()
	for _, want := range []string{"ブレインストーミング中", "brainstorming ウィンドウ", "❯", "Enter 移動"} {
		if !strings.Contains(out, want) {
			t.Errorf("brainstorming View missing %q:\n%s", want, out)
		}
	}
	if strings.Contains(out, "Ctrl-_ → w") || strings.Contains(out, "Ctrl-b") {
		t.Errorf("brainstorming View still instructs raw tmux nav (should be cursor-select):\n%s", out)
	}
}

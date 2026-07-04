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

package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestWriteLaunchScript(t *testing.T) {
	dir := t.TempDir()
	store, err := NewStore(dir)
	if err != nil {
		t.Fatal(err)
	}
	m := &Mode{Store: store, Workspace: dir}

	script, err := m.WriteLaunchScript("w-t3", "SYS-INSTR", "QUESTION-PROMPT")
	if err != nil {
		t.Fatal(err)
	}
	if filepath.Base(script) != "w-t3.sh" {
		t.Fatalf("script path = %q, want …/w-t3.sh", script)
	}
	// Sidecar files carry the (possibly multi-KB) prompt content verbatim.
	sys, _ := os.ReadFile(filepath.Join(dir, ".orchestrator", "sessions", "w-t3.sys"))
	if string(sys) != "SYS-INSTR" {
		t.Errorf("sys file = %q", sys)
	}
	prm, _ := os.ReadFile(filepath.Join(dir, ".orchestrator", "sessions", "w-t3.prompt"))
	if string(prm) != "QUESTION-PROMPT" {
		t.Errorf("prompt file = %q", prm)
	}
	body, _ := os.ReadFile(script)
	s := string(body)
	// Env is normalized: VM env sourced, Slack token stripped, cd to workspace.
	for _, want := range []string{
		"/etc/claude-dev/vm.env",
		"unset SLACK_BOT_TOKEN",
		"cd ",
		"--append-system-prompt \"$(cat ",
		"w-t3.sys",
		"w-t3.prompt",
		"exec ",
	} {
		if !strings.Contains(s, want) {
			t.Errorf("script missing %q:\n%s", want, s)
		}
	}
}

func TestWriteLaunchScript_NoPromptOmitsPositional(t *testing.T) {
	dir := t.TempDir()
	store, _ := NewStore(dir)
	m := &Mode{Store: store, Workspace: dir}
	script, err := m.WriteLaunchScript("wallbounce", "SYS", "")
	if err != nil {
		t.Fatal(err)
	}
	body, _ := os.ReadFile(script)
	s := string(body)
	if !strings.Contains(s, "--append-system-prompt") {
		t.Errorf("expected system prompt flag:\n%s", s)
	}
	// With an empty prompt, no trailing positional `"$(cat …prompt)"` is emitted.
	if strings.Contains(s, "wallbounce.prompt") {
		t.Errorf("empty prompt must not be passed as positional:\n%s", s)
	}
}

func TestShellSingleQuote(t *testing.T) {
	cases := map[string]string{
		"/a/b": "'/a/b'",
		"a b":  "'a b'",
		"it's": `'it'\''s'`,
		"":     "''",
	}
	for in, want := range cases {
		if got := shellSingleQuote(in); got != want {
			t.Errorf("shellSingleQuote(%q)=%q want %q", in, got, want)
		}
	}
}

func TestSelectableWorkerStatus(t *testing.T) {
	tasks := []DashTask{
		{ID: "t1", Status: TaskDone},         // not selectable
		{ID: "t2", Status: TaskRunning},      // #1 -> view switch
		{ID: "t3", Status: TaskPending},      // not selectable
		{ID: "t4", Status: TaskWaitingHuman}, // #2 -> resolve
		{ID: "t5", Status: TaskReview},       // #3 -> view switch
	}
	type want struct {
		id, status string
	}
	cases := map[int]want{
		0: {"", ""},
		1: {"t2", TaskRunning},
		2: {"t4", TaskWaitingHuman},
		3: {"t5", TaskReview},
		4: {"", ""},
	}
	for n, w := range cases {
		id, status := selectableWorker(tasks, n)
		if id != w.id || status != w.status {
			t.Errorf("selectableWorker(n=%d)=(%q,%q) want (%q,%q)", n, id, status, w.id, w.status)
		}
	}
}

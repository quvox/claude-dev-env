package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

const policyHeading = "# プロジェクト固有の判断基準（ORCHESTRATOR.md）"

func writeOrchestratorMD(t *testing.T, dir, body string) {
	t.Helper()
	if err := os.WriteFile(filepath.Join(dir, "ORCHESTRATOR.md"), []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
}

func TestLoadProjectPolicy_Present(t *testing.T) {
	dir := t.TempDir()
	writeOrchestratorMD(t, dir, "本番DBには触れないこと。")
	got := LoadProjectPolicy(dir)
	if !strings.HasPrefix(got, policyHeading) {
		t.Fatalf("policy should start with heading, got %q", got)
	}
	if !strings.Contains(got, "本番DBには触れないこと。") {
		t.Fatalf("policy should contain body, got %q", got)
	}
	if !strings.HasSuffix(got, "\n\n") {
		t.Fatalf("policy should end with a blank line, got %q", got)
	}
}

func TestLoadProjectPolicy_Absent(t *testing.T) {
	if got := LoadProjectPolicy(t.TempDir()); got != "" {
		t.Fatalf("absent ORCHESTRATOR.md should yield empty string, got %q", got)
	}
}

func TestLoadProjectPolicy_Empty(t *testing.T) {
	dir := t.TempDir()
	writeOrchestratorMD(t, dir, "")
	if got := LoadProjectPolicy(dir); got != "" {
		t.Fatalf("empty ORCHESTRATOR.md should yield empty string, got %q", got)
	}
}

func TestBuildPrompt_IncludesPolicyWhenPresent(t *testing.T) {
	ws := t.TempDir()
	writeOrchestratorMD(t, ws, "コスト発生は必ず人間に確認。")
	w := &Worker{Workspace: ws, Cfg: DefaultConfig()}
	p := &Plan{Goal: "g", Completion: "c"}
	tk := &Task{ID: "t1", Title: "title", Description: "desc"}
	prompt := w.BuildPrompt(p, tk, "")
	if !strings.HasPrefix(prompt, policyHeading) {
		t.Fatalf("worker prompt should start with policy heading, got %q", prompt[:min(80, len(prompt))])
	}
	if !strings.Contains(prompt, "コスト発生は必ず人間に確認。") {
		t.Fatalf("worker prompt should contain policy body")
	}
	// The original prompt content must still be present after the policy.
	if !strings.Contains(prompt, "# Goal") || !strings.Contains(prompt, "desc") {
		t.Fatalf("worker prompt should still contain the task content")
	}
}

func TestBuildPrompt_NoPolicyWhenAbsent(t *testing.T) {
	w := &Worker{Workspace: t.TempDir(), Cfg: DefaultConfig()}
	p := &Plan{Goal: "g", Completion: "c"}
	tk := &Task{ID: "t1", Title: "title", Description: "desc"}
	prompt := w.BuildPrompt(p, tk, "")
	if strings.Contains(prompt, policyHeading) {
		t.Fatalf("worker prompt should NOT contain policy heading when ORCHESTRATOR.md is absent")
	}
	if !strings.HasPrefix(prompt, "# Goal") {
		t.Fatalf("worker prompt should start with # Goal when no policy")
	}
}

func TestBuildReviewPrompt_IncludesPolicyWhenPresent(t *testing.T) {
	ws := t.TempDir()
	writeOrchestratorMD(t, ws, "セキュリティ指摘は critical 扱い。")
	w := &Worker{Workspace: ws, Cfg: DefaultConfig()}
	rv := &Reviewer{Cfg: DefaultConfig(), Worker: w}
	prompt := rv.buildReviewPrompt(&Plan{Goal: "g", Completion: "c"}, &Task{ID: "t1", Title: "x", Description: "d"})
	if !strings.HasPrefix(prompt, policyHeading) {
		t.Fatalf("review prompt should start with policy heading")
	}
	if !strings.Contains(prompt, "セキュリティ指摘は critical 扱い。") {
		t.Fatalf("review prompt should contain policy body")
	}
}

func TestBuildReviewPrompt_NoPolicyWhenAbsent(t *testing.T) {
	w := &Worker{Workspace: t.TempDir(), Cfg: DefaultConfig()}
	rv := &Reviewer{Cfg: DefaultConfig(), Worker: w}
	prompt := rv.buildReviewPrompt(&Plan{Goal: "g"}, &Task{ID: "t1", Title: "x", Description: "d"})
	if strings.Contains(prompt, policyHeading) {
		t.Fatalf("review prompt should not contain policy heading when absent")
	}
}

func TestModeArgs_IncludePolicyWhenPresent(t *testing.T) {
	ws := t.TempDir()
	writeOrchestratorMD(t, ws, "壁打ちでは必ず完了基準を確認。")
	store, _ := NewStore(ws)
	m := &Mode{Store: store, Workspace: ws}

	wbArgs := m.WallbounceArgs()
	if !argsContainPolicy(wbArgs) {
		t.Fatalf("wallbounce args should include policy: %v", wbArgs)
	}
	// Seed a question so InterveneArgs has the instruction assembled.
	_ = store.WriteQuestion("iv1", "詰まりました")
	ivArgs := m.InterveneArgs("iv1")
	if !argsContainPolicy(ivArgs) {
		t.Fatalf("intervene args should include policy: %v", ivArgs)
	}
}

func TestModeArgs_NoPolicyWhenAbsent(t *testing.T) {
	ws := t.TempDir()
	store, _ := NewStore(ws)
	m := &Mode{Store: store, Workspace: ws}
	// No ORCHESTRATOR.md and no instruction templates (localInstrDir unset, the
	// baked /usr/local path won't exist in tests) -> no --append-system-prompt.
	if argsContainPolicy(m.WallbounceArgs()) {
		t.Fatalf("wallbounce args should not include policy when absent")
	}
}

func argsContainPolicy(args []string) bool {
	for i, a := range args {
		if a == "--append-system-prompt" && i+1 < len(args) {
			if strings.Contains(args[i+1], policyHeading) {
				return true
			}
		}
	}
	return false
}

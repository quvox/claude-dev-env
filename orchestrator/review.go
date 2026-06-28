package main

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
)

// Finding is one review remark.
type Finding struct {
	Severity string `json:"severity"` // critical|major|minor
	File     string `json:"file"`
	Message  string `json:"message"`
	Aspect   string `json:"aspect"` // requirements|security etc.
}

// ReviewResult is the structured reviewer output.
type ReviewResult struct {
	Findings []Finding `json:"findings"`
	Usage    *Usage    `json:"usage,omitempty"`
}

// HasSevere reports whether any finding is critical or major.
func (r *ReviewResult) HasSevere() bool {
	for _, f := range r.Findings {
		if f.Severity == SeverityCritical || f.Severity == SeverityMajor {
			return true
		}
	}
	return false
}

// SevereSummary renders the severe findings as feedback for a revise round.
func (r *ReviewResult) SevereSummary() string {
	var b strings.Builder
	for _, f := range r.Findings {
		if f.Severity == SeverityCritical || f.Severity == SeverityMajor {
			fmt.Fprintf(&b, "- [%s][%s] %s: %s\n", f.Severity, f.Aspect, f.File, f.Message)
		}
	}
	return b.String()
}

// Reviewer runs the quality gate: an independent reviewer worker plus the
// revise loop. It does not increment Task.Attempts (revise stays within one
// Attempt; the controller owns Attempts).
type Reviewer struct {
	Store  *Store
	Claude ClaudeRunner
	Cfg    Config
	Worker *Worker
}

const reviewGuide = `
You are an independent code reviewer (NOT the implementer). Review the diff in
this worktree against the task requirements. Evaluate BOTH aspects in a single
pass: (1) requirements satisfaction & behavior, (2) security, error handling,
maintainability. Print a single JSON object on the final line:
{"findings":[{"severity":"critical|major|minor","file":string,"message":string,"aspect":"requirements|security"}],"usage":{"input_tokens":int,"output_tokens":int}|null}
Use severity critical/major only for issues that block acceptance.`

// Review runs a single reviewer pass on the task worktree.
func (rv *Reviewer) Review(ctx context.Context, p *Plan, t *Task) (*ReviewResult, error) {
	prompt := rv.buildReviewPrompt(p, t)
	dir := rv.Store.WorktreeAbs(t.ID)
	logPath := rv.Store.WorkerLogPath(t.ID + ".review")
	out, err := rv.Claude.RunPrompt(ctx, dir, rv.Cfg.WorkerModel, prompt, logPath)
	if err != nil {
		return nil, err
	}
	res, perr := ParseReviewResult(out)
	if perr != nil {
		return nil, perr
	}
	if res.Usage != nil {
		_ = rv.Store.AppendAudit(AuditEntry{
			Event: "review_result", TaskID: t.ID,
			Detail: map[string]any{"findings": len(res.Findings)}, Usage: res.Usage,
		})
	}
	return res, nil
}

func (rv *Reviewer) buildReviewPrompt(p *Plan, t *Task) string {
	var b strings.Builder
	// Project-specific decision policy (ORCHESTRATOR.md, if any) goes first so
	// the reviewer judges findings within it.
	if rv.Worker != nil {
		b.WriteString(LoadProjectPolicy(rv.Worker.Workspace))
	}
	b.WriteString("# Task under review: ")
	b.WriteString(t.Title)
	b.WriteString("\n")
	b.WriteString(t.Description)
	b.WriteString("\n\n# Goal\n")
	b.WriteString(p.Goal)
	b.WriteString("\n\n# Completion criteria\n")
	b.WriteString(p.Completion)
	b.WriteString("\n")
	b.WriteString(reviewGuide)
	return b.String()
}

// RunGate executes review -> revise loop for one Attempt.
//
// Returns:
//   - passed=true when no severe findings remain (task may be marked done).
//   - passed=false when max_review_rounds is reached and severe findings remain
//     (caller treats this as a stuck condition -> trigger 3).
//
// Attempts is NOT modified here.
func (rv *Reviewer) RunGate(ctx context.Context, p *Plan, t *Task) (passed bool, lastSevere string, err error) {
	for round := 0; round < rv.Cfg.MaxReviewRounds; round++ {
		t.Status = TaskReview
		rev, rerr := rv.Review(ctx, p, t)
		if rerr != nil {
			return false, "", rerr
		}
		if !rev.HasSevere() {
			return true, "", nil
		}
		lastSevere = rev.SevereSummary()
		// Revise within the same Attempt: send findings back to implementer.
		if round == rv.Cfg.MaxReviewRounds-1 {
			break // do not revise past the last round
		}
		t.Status = TaskRevise
		feedback := "Address these review findings (this is a revise, not a new approach):\n" + lastSevere
		res, derr := rv.Worker.Dispatch(ctx, p, t, feedback)
		if derr != nil {
			// A revise dispatch failure (crash/timeout) is still within this
			// Attempt: we must NOT lose the trigger3 signal. Keep the last
			// severe findings and stop reviding; the loop falls through to the
			// terminal "passed=false, lastSevere" return so the controller's
			// StuckThisAttempt evaluation fires correctly. Surface the error in
			// the audit log via the caller; we do not bubble it (which would be
			// treated as a transient and re-dispatched, dropping the signal).
			_ = appendReviseError(rv, t, derr)
			break
		}
		t.Result = res
		if res.NeedsHuman != nil {
			// Escalation during revise: surface via the result; caller decides.
			return false, lastSevere, nil
		}
	}
	return false, lastSevere, nil
}

// appendReviseError records a revise-time dispatch error to the audit log.
func appendReviseError(rv *Reviewer, t *Task, err error) error {
	return rv.Store.AppendAudit(AuditEntry{
		Event:  "revise_error",
		TaskID: t.ID,
		Detail: map[string]any{"err": err.Error()},
	})
}

// ParseReviewResult extracts the ReviewResult JSON from raw reviewer output.
func ParseReviewResult(out []byte) (*ReviewResult, error) {
	text := string(out)
	if r := extractFromClaudeEnvelope(text); r != "" {
		text = r
	}
	lines := strings.Split(strings.TrimRight(text, "\n"), "\n")
	for i := len(lines) - 1; i >= 0; i-- {
		line := strings.TrimSpace(lines[i])
		if !strings.HasPrefix(line, "{") || !strings.HasSuffix(line, "}") {
			continue
		}
		var rr ReviewResult
		if err := json.Unmarshal([]byte(line), &rr); err == nil && rr.Findings != nil {
			return &rr, nil
		}
		// Allow an empty findings array shape too.
		var probe map[string]json.RawMessage
		if err := json.Unmarshal([]byte(line), &probe); err == nil {
			if _, ok := probe["findings"]; ok {
				var rr2 ReviewResult
				_ = json.Unmarshal([]byte(line), &rr2)
				return &rr2, nil
			}
		}
	}
	return nil, fmt.Errorf("no parseable ReviewResult JSON in output")
}

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
this worktree. Evaluate BOTH aspects in a single pass: (1) requirements
satisfaction & behavior, (2) security, error handling, maintainability.
SCOPE RULE (important): score ONLY against "This task's completion criteria"
below. Do NOT deduct for anything that is another task's responsibility —
whole-project coverage, other modules/aspects, integration, or cleanup are OUT
OF SCOPE for this task and must NOT produce critical/major findings here.
Print a single JSON object on the final line, nothing after it:
{"findings":[{"severity":"critical|major|minor","file":string,"message":string,"aspect":"requirements|security"}],"usage":{"input_tokens":int,"output_tokens":int}|null}
Use severity critical/major only for issues that block acceptance of THIS task's
completion criteria.`

// Review runs a single reviewer pass on the task worktree.
func (rv *Reviewer) Review(ctx context.Context, p *Plan, t *Task) (*ReviewResult, error) {
	prompt := rv.buildReviewPrompt(p, t)
	dir := rv.Store.WorktreeAbs(t.ID)
	logPath := rv.Store.WorkerLogPath(t.ID + ".review")
	out, err := rv.Claude.RunPrompt(ctx, dir, rv.Cfg.WorkerModel, prompt, logPath, RunOpts{GraceSeconds: rv.Cfg.WorkerGraceSeconds})
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
	// VM モードの周知（発見導線2）＋プロジェクト固有の判断基準（ORCHESTRATOR.md）を先頭へ。
	b.WriteString(VMModePreamble())
	if rv.Worker != nil {
		b.WriteString(LoadProjectPolicy(rv.Worker.Workspace))
	}
	b.WriteString("# Task under review: ")
	b.WriteString(t.Title)
	b.WriteString("\n")
	b.WriteString(t.Description)
	// The task-specific completion criterion is the ONLY scoring basis.
	b.WriteString("\n\n# This task's completion criteria (the ONLY scoring basis)\n")
	b.WriteString(t.Completion)
	// The plan goal is context ONLY — never a scoring basis (prevents scoring a
	// scoped subtask against the whole plan; docs/06 §8.1).
	b.WriteString("\n\n# Plan goal (context only — do NOT score against this)\n")
	b.WriteString(p.Goal)
	b.WriteString("\n")
	b.WriteString(reviewGuide)
	return b.String()
}

// GateOutcome is the structured result of RunGate.
type GateOutcome struct {
	Passed      bool   // no severe findings remain (task may be marked done)
	LastSevere  string // severe findings summary (for revise feedback / stuck)
	FormatError bool   // reviewer output was unparseable ReviewFormatErrorLimit
	// times in a row -> escalate as review_gate_defect (do NOT re-run worker)
	FormatErrorCount int
}

// RunGate executes the review -> revise loop for one Attempt.
//
//   - Passed=true when no severe findings remain.
//   - FormatError=true when the reviewer output could not be parsed the
//     configured number of times in a row (a gate malfunction). The caller must
//     escalate this as review_gate_defect WITHOUT re-dispatching the worker.
//   - Otherwise Passed=false with LastSevere set (caller treats as stuck -> t3).
//
// A non-nil err is returned only for context cancellation / a revise crash.
// Attempts is NOT modified here.
func (rv *Reviewer) RunGate(ctx context.Context, p *Plan, t *Task) (GateOutcome, error) {
	var lastSevere string
	formatErrs := 0
	limit := rv.Cfg.ReviewFormatErrorLimit
	if limit <= 0 {
		limit = 2
	}
	reviewRounds := 0
	for reviewRounds < rv.Cfg.MaxReviewRounds {
		t.Status = TaskReview
		rev, rerr := rv.Review(ctx, p, t)
		if rerr != nil {
			if ctx.Err() != nil {
				return GateOutcome{}, rerr // hard: cancellation
			}
			// Unparseable reviewer output = FORMAT error, not a content failure.
			// The implementation is already done, so retry the REVIEW only (do
			// NOT re-dispatch the worker). At the limit, signal review_gate_defect.
			formatErrs++
			_ = rv.Store.AppendAudit(AuditEntry{
				Event: "review_format_error", TaskID: t.ID,
				Detail: map[string]any{"count": formatErrs, "err": rerr.Error()},
			})
			if formatErrs >= limit {
				return GateOutcome{FormatError: true, FormatErrorCount: formatErrs}, nil
			}
			continue // retry review; does not consume a review round
		}
		formatErrs = 0 // a parseable content verdict resets the format-error run
		reviewRounds++
		if !rev.HasSevere() {
			return GateOutcome{Passed: true}, nil
		}
		lastSevere = rev.SevereSummary()
		// Revise within the same Attempt: send findings back to implementer.
		if reviewRounds >= rv.Cfg.MaxReviewRounds {
			break // do not revise past the last round
		}
		t.Status = TaskRevise
		feedback := "Address these review findings (this is a revise, not a new approach):\n" + lastSevere
		res, derr := rv.Worker.Dispatch(ctx, p, t, feedback)
		if derr != nil {
			if ctx.Err() != nil {
				return GateOutcome{LastSevere: lastSevere}, derr
			}
			// A revise dispatch failure (crash/timeout) is still within this
			// Attempt: keep lastSevere so the controller's StuckThisAttempt path
			// fires. Record but do not bubble (bubbling would re-dispatch as a
			// transient and drop the signal).
			_ = appendReviseError(rv, t, derr)
			break
		}
		t.Result = res
		if res.NeedsHuman != nil {
			// Escalation during revise: surface via the result; caller decides.
			return GateOutcome{LastSevere: lastSevere}, nil
		}
	}
	return GateOutcome{LastSevere: lastSevere}, nil
}

// appendReviseError records a revise-time dispatch error to the audit log.
func appendReviseError(rv *Reviewer, t *Task, err error) error {
	return rv.Store.AppendAudit(AuditEntry{
		Event:  "revise_error",
		TaskID: t.ID,
		Detail: map[string]any{"err": err.Error()},
	})
}

// ParseReviewResult extracts the ReviewResult JSON from raw reviewer output. It
// mirrors ParseWorkerResult and supports the same three shapes: stream-json
// (the reviewer runs with --output-format stream-json, so the JSON lives inside
// the final result event's "result" text), a single json envelope, and a bare
// object.
func ParseReviewResult(out []byte) (*ReviewResult, error) {
	text := string(out)
	if inner := resultFromStream(text); inner != "" {
		if rr := findReviewResultJSON(inner); rr != nil {
			return rr, nil
		}
	}
	if inner := extractFromClaudeEnvelope(text); inner != "" {
		if rr := findReviewResultJSON(inner); rr != nil {
			return rr, nil
		}
	}
	if rr := findReviewResultJSON(text); rr != nil {
		return rr, nil
	}
	return nil, fmt.Errorf("no parseable ReviewResult JSON in output")
}

// findReviewResultJSON scans lines from the end for a single-line JSON object
// that has a "findings" field and decodes it (an empty findings array is valid).
func findReviewResultJSON(text string) *ReviewResult {
	lines := strings.Split(strings.TrimRight(text, "\n"), "\n")
	for i := len(lines) - 1; i >= 0; i-- {
		line := strings.TrimSpace(lines[i])
		if !strings.HasPrefix(line, "{") || !strings.HasSuffix(line, "}") {
			continue
		}
		var probe map[string]json.RawMessage
		if err := json.Unmarshal([]byte(line), &probe); err != nil {
			continue
		}
		if _, ok := probe["findings"]; !ok {
			continue
		}
		var rr ReviewResult
		if err := json.Unmarshal([]byte(line), &rr); err == nil {
			return &rr
		}
	}
	return nil
}

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
Use severity critical/major only for issues that block acceptance of THIS task's
completion criteria.

OUTPUT FORMAT — MANDATORY. The automated gate parses your reply as JSON; if you
answer in prose the whole task is escalated to a human as a false "gate defect".
So your VERY LAST message must be EXACTLY ONE JSON object and NOTHING ELSE —
no prose conclusion, no summary sentence, no markdown code fence, no text before
or after it. The JSON object IS your conclusion; do not also describe it in words.
  - If nothing blocks acceptance, output exactly: {"findings":[]}
  - Otherwise: {"findings":[{"severity":"critical|major|minor","file":"path","message":"...","aspect":"requirements|security"}]}
Put the entire object on a single line.`

// Review runs a single reviewer pass on the task worktree.
func (rv *Reviewer) Review(ctx context.Context, p *Plan, t *Task) (*ReviewResult, error) {
	prompt := rv.buildReviewPrompt(p, t)
	dir := rv.Store.WorktreeAbs(t.ID)
	logPath := rv.Store.WorkerLogPath(t.ID + ".review")
	prof := reviewerProfile() // models.go policy table
	out, err := rv.Claude.RunPrompt(ctx, dir, prof.Model, prompt, logPath, RunOpts{GraceSeconds: rv.Cfg.WorkerGraceSeconds, Effort: prof.Effort})
	if err != nil {
		return nil, err
	}
	res, perr := ParseReviewResult(out)
	if perr != nil {
		// The reviewer answered in prose instead of the required JSON. Before
		// counting a format error (which escalates to a human as a gate defect),
		// ask a cheap follow-up to CONVERT its own prose verdict into the JSON
		// schema. This recovers the common "narrated conclusion" case without
		// bothering a human (docs/06 §8.2).
		if r2 := rv.reformatToJSON(ctx, dir, out); r2 != nil {
			res, perr = r2, nil
			_ = rv.Store.AppendAudit(AuditEntry{Event: "review_reformat_ok", TaskID: t.ID})
		}
	}
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

// reformatToJSON asks a cheap follow-up call to convert the reviewer's prose
// verdict into the required JSON schema. Pure text transformation (feeds the
// prose back in the prompt), so it does not need the worktree/tools and cannot
// change the verdict — it only re-serializes it. Returns nil if it still can't
// produce parseable JSON (the caller then counts a real format error). Uses a
// small model (haiku) and no log file (the display log already holds the review).
func (rv *Reviewer) reformatToJSON(ctx context.Context, dir string, reviewOut []byte) *ReviewResult {
	prose := resultFromStream(string(reviewOut))
	if strings.TrimSpace(prose) == "" {
		prose = string(reviewOut) // fall back to raw output
	}
	prompt := "以下はコードレビューの結論（散文）です。内容は一切変えず、指摘だけを規定の JSON に" +
		"変換して JSON オブジェクト 1 個だけを出力してください（説明・コードフェンス・前後の文は禁止）。\n" +
		"重大/中程度の指摘が無ければ {\"findings\":[]}。\n" +
		"それ以外は {\"findings\":[{\"severity\":\"critical|major|minor\",\"file\":\"path\",\"message\":\"...\",\"aspect\":\"requirements|security\"}]}。\n\n" +
		"----- レビュー結論 -----\n" + prose
	// Pure prose→JSON transform: a small model at low effort is enough and cheap.
	out, err := rv.Claude.RunPrompt(ctx, dir, "haiku", prompt, "", RunOpts{GraceSeconds: rv.Cfg.WorkerGraceSeconds, Effort: "low"})
	if err != nil {
		return nil
	}
	res, perr := ParseReviewResult(out)
	if perr != nil {
		return nil
	}
	return res
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
	// Fast path: a line that is exactly the JSON object (the instructed format).
	lines := strings.Split(strings.TrimRight(text, "\n"), "\n")
	for i := len(lines) - 1; i >= 0; i-- {
		line := strings.TrimSpace(lines[i])
		if rr := tryReviewResult(line); rr != nil {
			return rr
		}
	}
	// Tolerant path: the model wrapped the object in a ```json fence or prepended
	// prose on the same line (e.g. `Result: {"findings":[]}`). Scan the whole text
	// for the LAST balanced {...} block that contains a "findings" key and parses.
	for _, cand := range findJSONObjects(text) {
		if rr := tryReviewResult(cand); rr != nil {
			return rr
		}
	}
	return nil
}

// tryReviewResult parses s as a ReviewResult if it is a JSON object carrying a
// "findings" key (rejecting unrelated objects). Returns nil otherwise.
func tryReviewResult(s string) *ReviewResult {
	s = strings.TrimSpace(s)
	if !strings.HasPrefix(s, "{") || !strings.HasSuffix(s, "}") {
		return nil
	}
	var probe map[string]json.RawMessage
	if err := json.Unmarshal([]byte(s), &probe); err != nil {
		return nil
	}
	if _, ok := probe["findings"]; !ok {
		return nil
	}
	var rr ReviewResult
	if err := json.Unmarshal([]byte(s), &rr); err != nil {
		return nil
	}
	return &rr
}

// findJSONObjects returns every brace-balanced {...} substring in text, in order
// of their closing brace (so the caller can prefer later/last matches). Brace
// counting ignores braces inside JSON string literals (with escape handling), so
// objects that contain `}` inside string values are captured whole. Best-effort:
// it is only used as a fallback when the strict line match fails.
func findJSONObjects(text string) []string {
	var out []string
	depth := 0
	start := -1
	inStr := false
	esc := false
	for i := 0; i < len(text); i++ {
		c := text[i]
		if inStr {
			switch {
			case esc:
				esc = false
			case c == '\\':
				esc = true
			case c == '"':
				inStr = false
			}
			continue
		}
		switch c {
		case '"':
			inStr = true
		case '{':
			if depth == 0 {
				start = i
			}
			depth++
		case '}':
			if depth > 0 {
				depth--
				if depth == 0 && start >= 0 {
					out = append(out, text[start:i+1])
					start = -1
				}
			}
		}
	}
	// Prefer the last object first (the reviewer's conclusion comes last).
	for l, r := 0, len(out)-1; l < r; l, r = l+1, r-1 {
		out[l], out[r] = out[r], out[l]
	}
	return out
}

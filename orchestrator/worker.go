package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"strings"
)

// ---- External-process interfaces (mockable in tests) ----

// ClaudeRunner runs a headless `claude -p` worker and returns its raw stdout.
// Implementations must not require a TTY (workers are background children).
type ClaudeRunner interface {
	// RunPrompt executes claude -p with the given prompt and model, with CWD
	// set to dir, returning combined stdout. logPath, if non-empty, receives a
	// tee of the raw output.
	RunPrompt(ctx context.Context, dir, model, prompt, logPath string) ([]byte, error)
}

// GitRunner abstracts the git operations the orchestrator performs.
type GitRunner interface {
	// WorktreeAdd creates a worktree at path on a new branch from base.
	WorktreeAdd(ctx context.Context, repoDir, path, branch, base string) error
	// WorktreeRemove removes a worktree (best effort).
	WorktreeRemove(ctx context.Context, repoDir, path string) error
	// Merge integrates branch into the current branch of repoDir using
	// strategy "merge" or "rebase".
	Merge(ctx context.Context, repoDir, branch, strategy string) error
	// HasCommits reports whether the worktree branch has commits beyond base.
	HasCommits(ctx context.Context, repoDir, branch, base string) (bool, error)
	// CurrentBranch returns the active branch name of repoDir.
	CurrentBranch(ctx context.Context, repoDir string) (string, error)
}

// Notifier sends an out-of-band message (Slack). Failures are swallowed.
type Notifier interface {
	Notify(text string)
}

// ---- Worker dispatch ----

// Worker dispatches a single task to a claude -p worker on a git worktree.
type Worker struct {
	Store  *Store
	Claude ClaudeRunner
	Git    GitRunner
	Cfg    Config
	// Workspace is the repository root (CWD of the controller).
	Workspace string
}

// workerPromptSchema is appended to every worker prompt so the worker emits a
// machine-parseable result envelope on its final line.
const workerResultGuide = `
You are a headless implementation worker. You CANNOT ask the human anything
directly. When you finish, you MUST commit your work inside this worktree, then
print a single JSON object on the final line of your output with this schema:
{"done":bool,"summary":string,"changes":[string],"assumptions":[string],"needs_human":{"reason":string,"question":string,"options":[string]}|null,"usage":{"input_tokens":int,"output_tokens":int}|null}
Judgment rule: for MINOR decisions, proceed with the most reasonable assumption
and record it in "assumptions" (do NOT escalate). Escalate ONLY when one of the
following blocks you: set done=false and needs_human.reason to one of
critical_decision|ambiguity|policy_branch|prerequisite_broken:
- critical_decision: irreversible/important (customer commitment, cost incurred,
  production release, data deletion, external send)
- ambiguity: requirement is unclear and guessing is risky
- policy_branch: a choice that affects the whole and you lack info to decide
- prerequisite_broken: an initial assumption no longer holds
Do NOT perform irreversible operations (push/deploy/delete/external send).`

// PrepareWorktree creates the git worktree for a task and records its relative
// path on the task.
func (w *Worker) PrepareWorktree(ctx context.Context, t *Task) error {
	rel := w.Store.WorktreeRel(t.ID)
	abs := w.Store.WorktreeAbs(t.ID)
	branch := "orch/" + t.ID
	base, err := w.Git.CurrentBranch(ctx, w.Workspace)
	if err != nil {
		base = "HEAD"
	}
	// If the worktree dir already exists (resume), reuse it.
	if _, statErr := os.Stat(abs); statErr == nil {
		t.Worktree = rel
		return nil
	}
	if err := w.Git.WorktreeAdd(ctx, w.Workspace, abs, branch, base); err != nil {
		return err
	}
	t.Worktree = rel
	return nil
}

// BuildPrompt composes the worker prompt from the task description, prior
// attempt feedback (if any), and context from the plan.
func (w *Worker) BuildPrompt(p *Plan, t *Task, feedback string) string {
	var b strings.Builder
	// Project-specific decision policy (ORCHESTRATOR.md, if any) goes first so
	// the worker frames its assumptions/escalations within it.
	b.WriteString(LoadProjectPolicy(w.Workspace))
	b.WriteString("# Goal\n")
	b.WriteString(p.Goal)
	b.WriteString("\n\n# Completion criteria\n")
	b.WriteString(p.Completion)
	b.WriteString("\n\n# Task: ")
	b.WriteString(t.Title)
	b.WriteString("\n")
	b.WriteString(t.Description)
	b.WriteString("\n")
	// Prior task summaries (dependencies) for context.
	if deps := dependencySummaries(p, t); deps != "" {
		b.WriteString("\n# Context from prerequisite tasks\n")
		b.WriteString(deps)
		b.WriteString("\n")
	}
	if feedback != "" {
		b.WriteString("\n# Feedback from previous attempt (try a different approach)\n")
		b.WriteString(feedback)
		b.WriteString("\n")
	}
	b.WriteString(workerResultGuide)
	return b.String()
}

// dependencySummaries returns concatenated result summaries of completed deps.
func dependencySummaries(p *Plan, t *Task) string {
	byID := map[string]*Task{}
	for i := range p.Tasks {
		byID[p.Tasks[i].ID] = &p.Tasks[i]
	}
	var lines []string
	for _, dep := range t.Deps {
		if d := byID[dep]; d != nil && d.Result != nil && d.Result.Summary != "" {
			lines = append(lines, fmt.Sprintf("- %s: %s", d.ID, d.Result.Summary))
		}
	}
	return strings.Join(lines, "\n")
}

// Dispatch runs one implementation attempt for the task: builds the prompt,
// runs the worker on its worktree, and parses the structured result. The caller
// is responsible for incrementing Attempts before calling this.
func (w *Worker) Dispatch(ctx context.Context, p *Plan, t *Task, feedback string) (*WorkerResult, error) {
	if err := w.PrepareWorktree(ctx, t); err != nil {
		return nil, fmt.Errorf("worktree: %w", err)
	}
	prompt := w.BuildPrompt(p, t, feedback)
	dir := w.Store.WorktreeAbs(t.ID)
	logPath := w.Store.WorkerLogPath(t.ID)
	out, err := w.Claude.RunPrompt(ctx, dir, w.Cfg.WorkerModel, prompt, logPath)
	if err != nil {
		return nil, err
	}
	res, perr := ParseWorkerResult(out)
	if perr != nil {
		return nil, perr
	}
	if res.Usage != nil {
		_ = w.Store.AppendAudit(AuditEntry{
			Event:  "worker_result",
			TaskID: t.ID,
			Detail: map[string]any{"done": res.Done},
			Usage:  res.Usage,
		})
	}
	return res, nil
}

// ParseWorkerResult extracts the WorkerResult JSON from raw worker output. It
// supports two shapes:
//   - claude -p --output-format json wraps the result; we look for an embedded
//     object or the last JSON line.
//   - a bare WorkerResult JSON object.
//
// The strategy: scan lines from the end and return the first that decodes into
// a WorkerResult with at least a recognizable field.
func ParseWorkerResult(out []byte) (*WorkerResult, error) {
	text := string(out)
	// Try claude -p json envelope first: {"type":"result","result":"<text>"...}
	if r := extractFromClaudeEnvelope(text); r != "" {
		text = r
	}
	lines := strings.Split(strings.TrimRight(text, "\n"), "\n")
	for i := len(lines) - 1; i >= 0; i-- {
		line := strings.TrimSpace(lines[i])
		if !strings.HasPrefix(line, "{") || !strings.HasSuffix(line, "}") {
			continue
		}
		var wr WorkerResult
		if err := json.Unmarshal([]byte(line), &wr); err == nil {
			return &wr, nil
		}
	}
	return nil, fmt.Errorf("no parseable WorkerResult JSON in output")
}

// extractFromClaudeEnvelope, given claude -p --output-format json stdout,
// returns the inner assistant text (the "result" field) so the embedded
// WorkerResult can be parsed from it. Returns "" if not an envelope.
func extractFromClaudeEnvelope(text string) string {
	trimmed := strings.TrimSpace(text)
	if !strings.HasPrefix(trimmed, "{") {
		return ""
	}
	var env struct {
		Type   string `json:"type"`
		Result string `json:"result"`
	}
	if err := json.Unmarshal([]byte(trimmed), &env); err != nil {
		return ""
	}
	if env.Result != "" {
		return env.Result
	}
	return ""
}

// ---- exec-backed implementations (production) ----

// ExecClaude runs the real `claude` binary.
type ExecClaude struct{}

func (ExecClaude) RunPrompt(ctx context.Context, dir, model, prompt, logPath string) ([]byte, error) {
	args := []string{"-p", prompt, "--output-format", "json"}
	if model != "" {
		args = append(args, "--model", model)
	}
	cmd := exec.CommandContext(ctx, "claude", args...)
	cmd.Dir = dir
	// Explicitly strip SLACK_BOT_TOKEN from the worker environment (technical
	// control: workers must not be able to send Slack).
	cmd.Env = stripEnv(os.Environ(), "SLACK_BOT_TOKEN")
	out, err := cmd.CombinedOutput()
	if logPath != "" {
		_ = os.WriteFile(logPath, out, 0o644)
	}
	return out, err
}

// stripEnv returns env with any entry whose key equals key removed.
func stripEnv(env []string, key string) []string {
	prefix := key + "="
	out := env[:0:0]
	for _, e := range env {
		if strings.HasPrefix(e, prefix) {
			continue
		}
		out = append(out, e)
	}
	return out
}

// ExecGit runs the real `git` binary.
type ExecGit struct{}

func (ExecGit) run(ctx context.Context, dir string, args ...string) ([]byte, error) {
	cmd := exec.CommandContext(ctx, "git", args...)
	cmd.Dir = dir
	return cmd.CombinedOutput()
}

func (g ExecGit) WorktreeAdd(ctx context.Context, repoDir, path, branch, base string) error {
	_, err := g.run(ctx, repoDir, "worktree", "add", path, "-b", branch, base)
	return err
}

func (g ExecGit) WorktreeRemove(ctx context.Context, repoDir, path string) error {
	_, err := g.run(ctx, repoDir, "worktree", "remove", "--force", path)
	return err
}

func (g ExecGit) Merge(ctx context.Context, repoDir, branch, strategy string) error {
	switch strategy {
	case "rebase":
		_, err := g.run(ctx, repoDir, "rebase", branch)
		return err
	default: // merge
		_, err := g.run(ctx, repoDir, "merge", "--no-edit", branch)
		return err
	}
}

func (g ExecGit) HasCommits(ctx context.Context, repoDir, branch, base string) (bool, error) {
	out, err := g.run(ctx, repoDir, "rev-list", "--count", base+".."+branch)
	if err != nil {
		return false, err
	}
	n := strings.TrimSpace(string(out))
	return n != "" && n != "0", nil
}

func (g ExecGit) CurrentBranch(ctx context.Context, repoDir string) (string, error) {
	out, err := g.run(ctx, repoDir, "rev-parse", "--abbrev-ref", "HEAD")
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(string(out)), nil
}

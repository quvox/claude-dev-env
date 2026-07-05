package main

import (
	"bytes"
	"context"
	"crypto/rand"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

// newSessionID returns a random RFC 4122 v4 UUID string for a claude -p
// --session-id. stdlib only (crypto/rand); no external uuid dependency.
func newSessionID() string {
	var b [16]byte
	_, _ = rand.Read(b[:])
	b[6] = (b[6] & 0x0f) | 0x40 // version 4
	b[8] = (b[8] & 0x3f) | 0x80 // variant 10
	return fmt.Sprintf("%x-%x-%x-%x-%x", b[0:4], b[4:6], b[6:8], b[8:10], b[10:16])
}

// ---- External-process interfaces (mockable in tests) ----

// RunOpts carries optional per-invocation controls for a claude -p run.
type RunOpts struct {
	// SessionID, when set, is passed as --session-id (fresh session with a
	// caller-chosen id) unless Resume is true, in which case it is passed as
	// --resume (continue an interrupted session). Empty means neither flag.
	SessionID string
	Resume    bool
	// GraceSeconds, when >0, sends SIGINT (not SIGKILL) to the child on ctx
	// cancellation and waits up to that long before force-killing, so the worker
	// can commit its work-in-progress on suspend.
	GraceSeconds int
	// Effort, when set, is passed as --effort (low|medium|high|xhigh|max). Chosen
	// per work type via the models.go policy table.
	Effort string
}

// ClaudeRunner runs a headless `claude -p` worker and returns its raw stdout.
// Implementations must not require a TTY (workers are background children).
type ClaudeRunner interface {
	// RunPrompt executes claude -p with the given prompt and model, with CWD
	// set to dir, returning combined stdout. logPath, if non-empty, receives a
	// tee of the raw output. opts carries session/grace controls.
	RunPrompt(ctx context.Context, dir, model, prompt, logPath string, opts RunOpts) ([]byte, error)
}

// GitRunner abstracts the git operations the orchestrator performs.
type GitRunner interface {
	// WorktreeAdd creates a worktree at path on a new branch from base.
	WorktreeAdd(ctx context.Context, repoDir, path, branch, base string) error
	// WorktreeAddExisting attaches a worktree at path to an already-existing
	// branch (no new branch created). Used to re-attach to a surviving task
	// branch when only its worktree directory was removed.
	WorktreeAddExisting(ctx context.Context, repoDir, path, branch string) error
	// BranchExists reports whether a local branch exists.
	BranchExists(ctx context.Context, repoDir, branch string) (bool, error)
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
Commit your work to THIS worktree incrementally at meaningful checkpoints (not
only at the very end) so an interruption preserves committed progress.
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
	// The worktree dir is gone but its branch may have survived (interrupted run,
	// or a manually pruned worktree). Re-attach to the existing branch instead of
	// `add -b`, which would fail with "a branch named 'orch/<id>' already exists"
	// and wedge the task into an endless retry/stuck loop.
	if exists, _ := w.Git.BranchExists(ctx, w.Workspace, branch); exists {
		if err := w.Git.WorktreeAddExisting(ctx, w.Workspace, abs, branch); err != nil {
			return err
		}
		t.Worktree = rel
		return nil
	}
	if err := w.Git.WorktreeAdd(ctx, w.Workspace, abs, branch, base); err != nil {
		return err
	}
	t.Worktree = rel
	return nil
}

// CleanOrchWorktrees removes every orchestrator task worktree under
// worktreesDir and deletes the matching orch/* branches from repoDir
// (best-effort). A fresh run calls this so re-used task IDs (t1, t2, …) do not
// collide with a previous run's leftover branches/worktrees.
func CleanOrchWorktrees(ctx context.Context, repoDir, worktreesDir string) {
	g := ExecGit{}
	if entries, err := os.ReadDir(worktreesDir); err == nil {
		for _, e := range entries {
			_ = g.WorktreeRemove(ctx, repoDir, filepath.Join(worktreesDir, e.Name()))
		}
	}
	_, _ = g.run(ctx, repoDir, "worktree", "prune")
	out, _ := g.run(ctx, repoDir, "for-each-ref", "--format=%(refname:short)", "refs/heads/orch/")
	for _, b := range strings.Split(strings.TrimSpace(string(out)), "\n") {
		if b = strings.TrimSpace(b); b != "" {
			_, _ = g.run(ctx, repoDir, "branch", "-D", b)
		}
	}
	_ = os.RemoveAll(worktreesDir)
}

// BuildPrompt composes the worker prompt from the task description, prior
// attempt feedback (if any), and context from the plan.
func (w *Worker) BuildPrompt(p *Plan, t *Task, feedback string) string {
	var b strings.Builder
	// VM モードの周知（発見導線2）＋プロジェクト固有の判断基準（ORCHESTRATOR.md）を
	// 先頭に置き、worker が docker の向き先や bind の制約・方針を踏まえて動くようにする。
	b.WriteString(VMModePreamble())
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
	if strings.TrimSpace(t.Completion) != "" {
		b.WriteString("\n# This task's completion criteria (scope-limited; deliver exactly this)\n")
		b.WriteString(t.Completion)
		b.WriteString("\n")
	}
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
	// Model/effort by task kind (models.go policy table).
	prof := workerTaskProfile(t)
	opts := RunOpts{SessionID: t.SessionID, Resume: t.ResumeSession, GraceSeconds: w.Cfg.WorkerGraceSeconds, Effort: prof.Effort}
	out, err := w.Claude.RunPrompt(ctx, dir, prof.Model, prompt, logPath, opts)
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
// supports three shapes:
//   - stream-json: many event lines; the final {"type":"result","result":…}
//     event's "result" field holds the assistant's final text, which contains
//     the WorkerResult JSON.
//   - --output-format json: a single {"type":"result","result":…} object.
//   - a bare WorkerResult JSON object/line.
func ParseWorkerResult(out []byte) (*WorkerResult, error) {
	text := string(out)
	// stream-json: pull the inner assistant text out of the result event line.
	if inner := resultFromStream(text); inner != "" {
		if wr := findWorkerResultJSON(inner); wr != nil {
			return wr, nil
		}
	}
	// single-object json envelope.
	if inner := extractFromClaudeEnvelope(text); inner != "" {
		if wr := findWorkerResultJSON(inner); wr != nil {
			return wr, nil
		}
	}
	// bare WorkerResult somewhere in the raw text.
	if wr := findWorkerResultJSON(text); wr != nil {
		return wr, nil
	}
	return nil, fmt.Errorf("no parseable WorkerResult JSON in output")
}

// findWorkerResultJSON scans lines from the end for a single-line JSON object
// that looks like a WorkerResult (it must mention "done") and decodes it. The
// "done" guard avoids matching unrelated JSON (e.g. stream events).
func findWorkerResultJSON(text string) *WorkerResult {
	lines := strings.Split(strings.TrimRight(text, "\n"), "\n")
	for i := len(lines) - 1; i >= 0; i-- {
		line := strings.TrimSpace(lines[i])
		if !strings.HasPrefix(line, "{") || !strings.HasSuffix(line, "}") {
			continue
		}
		if !strings.Contains(line, "\"done\"") {
			continue
		}
		var wr WorkerResult
		if err := json.Unmarshal([]byte(line), &wr); err == nil {
			return &wr
		}
	}
	return nil
}

// resultFromStream scans stream-json output for the final result event and
// returns its "result" field (the assistant's final text). Returns "" if none.
func resultFromStream(text string) string {
	lines := strings.Split(strings.TrimRight(text, "\n"), "\n")
	for i := len(lines) - 1; i >= 0; i-- {
		line := strings.TrimSpace(lines[i])
		if !strings.HasPrefix(line, "{") || !strings.Contains(line, "\"type\":\"result\"") {
			continue
		}
		var e struct {
			Type   string `json:"type"`
			Result string `json:"result"`
		}
		if err := json.Unmarshal([]byte(line), &e); err == nil && e.Type == "result" {
			return e.Result
		}
	}
	return ""
}

// extractFromClaudeEnvelope, given a single-object claude -p --output-format
// json stdout, returns the inner assistant text (the "result" field). Returns
// "" if the whole text is not such an envelope.
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
type ExecClaude struct {
	// PermissionMode is passed as --permission-mode when non-empty. Headless
	// workers cannot answer permission prompts, so this must be a
	// non-interactive mode (e.g. bypassPermissions) or every edit is denied.
	PermissionMode string
}

func (e ExecClaude) RunPrompt(ctx context.Context, dir, model, prompt, logPath string, opts RunOpts) ([]byte, error) {
	// stream-json (requires --verbose in -p mode) emits one JSON event per line
	// as work happens, so the log file grows live and the dashboard detail view
	// can show what the worker is doing. The final {"type":"result",…} event
	// carries the worker's WorkerResult JSON, which ParseWorkerResult extracts.
	args := []string{"-p", prompt, "--output-format", "stream-json", "--verbose"}
	if model != "" {
		args = append(args, "--model", model)
	}
	if opts.Effort != "" {
		args = append(args, "--effort", opts.Effort)
	}
	if e.PermissionMode != "" {
		args = append(args, "--permission-mode", e.PermissionMode)
	}
	// Session continuity: --resume continues an interrupted session; otherwise
	// --session-id starts a fresh session with a caller-chosen id so a later
	// interruption can resume it (docs/impl/60 §worker ディスパッチ).
	if opts.SessionID != "" {
		if opts.Resume {
			args = append(args, "--resume", opts.SessionID)
		} else {
			args = append(args, "--session-id", opts.SessionID)
		}
	}
	cmd := exec.CommandContext(ctx, claudePath(), args...)
	cmd.Dir = dir
	// On suspend, give the worker a grace window to commit WIP: send SIGINT
	// (not the default SIGKILL) and wait up to GraceSeconds before force-killing.
	if opts.GraceSeconds > 0 {
		cmd.Cancel = func() error { return cmd.Process.Signal(os.Interrupt) }
		cmd.WaitDelay = time.Duration(opts.GraceSeconds) * time.Second
	}
	// Strip SLACK_BOT_TOKEN (technical control: workers must not send Slack) and
	// ensure the claude bin dir is on PATH so a non-interactive launch can run
	// claude -p.
	cmd.Env = claudeChildEnv()

	var buf bytes.Buffer
	var w io.Writer = &buf
	if logPath != "" {
		// Truncate+create the log up front and tee live so the detail view shows
		// progress as it streams (CombinedOutput would only reveal it at the end).
		// The RAW stream-json goes to buf (for ParseWorkerResult); the log file
		// receives a Claude-Code-like readable rendering via streamPrettyWriter so
		// the worker window / [d] view is human-readable, not raw JSON (streamlog.go).
		if f, ferr := os.Create(logPath); ferr == nil {
			defer f.Close()
			w = io.MultiWriter(&buf, newStreamPrettyWriter(f))
		}
	}
	cmd.Stdout = w
	cmd.Stderr = w
	err := cmd.Run()
	return buf.Bytes(), err
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

func (g ExecGit) WorktreeAddExisting(ctx context.Context, repoDir, path, branch string) error {
	_, err := g.run(ctx, repoDir, "worktree", "add", path, branch)
	return err
}

func (g ExecGit) BranchExists(ctx context.Context, repoDir, branch string) (bool, error) {
	// `rev-parse --verify --quiet` exits non-zero (no output) when the ref is
	// absent, so a run error here means "does not exist", not a hard failure.
	out, err := g.run(ctx, repoDir, "rev-parse", "--verify", "--quiet", "refs/heads/"+branch)
	if err != nil {
		return false, nil
	}
	return strings.TrimSpace(string(out)) != "", nil
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

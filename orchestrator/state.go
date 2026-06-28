package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"
)

// LoadProjectPolicy reads the optional project-specific decision policy from
// <workspace>/ORCHESTRATOR.md (a committed file, distinct from the gitignored
// .orchestrator/ runtime state and independent of CLAUDE.md). If present, it is
// returned wrapped in a labelled heading with a trailing blank line so it can
// be prepended to any prompt/instruction; if absent (or unreadable) it returns
// "" for a complete no-op.
func LoadProjectPolicy(workspace string) string {
	data, err := os.ReadFile(filepath.Join(workspace, "ORCHESTRATOR.md"))
	if err != nil {
		return ""
	}
	body := string(data)
	if body == "" {
		return ""
	}
	return "# プロジェクト固有の判断基準（ORCHESTRATOR.md）\n" + body + "\n\n"
}

// Phase constants for the state machine.
const (
	PhaseWallbounce = "wallbounce"
	PhaseExecuting  = "executing"
	PhaseIntervene  = "intervening"
	PhaseDone       = "done"
)

// Task.Status constants.
const (
	TaskPending = "pending"
	TaskRunning = "running"
	TaskReview  = "review"
	TaskRevise  = "revise"
	TaskBlocked = "blocked"
	TaskDone    = "done"
	TaskFailed  = "failed"
)

// Control.Request constants (handoff requests from the interactive claude).
const (
	ReqExecute            = "execute"
	ReqResume             = "resume"
	ReqContinueWallbounce = "continue_wallbounce"
	ReqAbort              = "abort"
)

// NeedsHuman.Reason constants. trigger3 (stuck) is controller-detected and does
// not use NeedsHuman.
const (
	ReasonCriticalDecision  = "critical_decision"   // trigger 1
	ReasonAmbiguity         = "ambiguity"           // trigger 2
	ReasonPolicyBranch      = "policy_branch"       // trigger 4
	ReasonPrerequisiteBroke = "prerequisite_broken" // trigger 5
)

// Review severities.
const (
	SeverityCritical = "critical"
	SeverityMajor    = "major"
	SeverityMinor    = "minor"
)

// State is the content of state.json.
type State struct {
	Phase       string `json:"phase"` // wallbounce|executing|intervening|done
	RunID       string `json:"run_id"`
	CurrentTask string `json:"current_task"` // 実行中タスクID（任意）
	StartedAt   string `json:"started_at"`   // RFC3339
	UpdatedAt   string `json:"updated_at"`
}

// Plan is the content of plan.json.
type Plan struct {
	Goal       string `json:"goal"`
	Completion string `json:"completion"`
	Ready      bool   `json:"ready"`
	Tasks      []Task `json:"tasks"`
}

// Task is one unit of work in the plan.
type Task struct {
	ID           string   `json:"id"`
	Title        string   `json:"title"`
	Description  string   `json:"description"`
	Deps         []string `json:"deps"`
	Status       string   `json:"status"`
	Attempts     int      `json:"attempts"`
	Worktree     string   `json:"worktree"`
	Irreversible bool     `json:"irreversible,omitempty"` // trigger1: planning-time mark
	// IrrevApproved records that a human approved this irreversible task during
	// an intervention. Once true the pre-dispatch trigger1 no longer fires, so
	// the task can finally be dispatched (prevents infinite re-fire on resume).
	IrrevApproved bool          `json:"irrev_approved,omitempty"`
	Result        *WorkerResult `json:"result,omitempty"`
}

// WorkerResult is the structured output a worker (claude -p) must emit.
type WorkerResult struct {
	Done        bool        `json:"done"`
	Summary     string      `json:"summary"`
	Changes     []string    `json:"changes"`
	Assumptions []string    `json:"assumptions,omitempty"` // 軽微な仮定: controller が assumptions.jsonl へ追記
	NeedsHuman  *NeedsHuman `json:"needs_human,omitempty"`
	Usage       *Usage      `json:"usage,omitempty"`
}

// NeedsHuman is a worker's escalation request.
type NeedsHuman struct {
	Reason   string   `json:"reason"`
	Question string   `json:"question"`
	Options  []string `json:"options,omitempty"`
}

// Usage is token accounting (best effort; mirrors claude -p json output).
type Usage struct {
	InputTokens  int `json:"input_tokens"`
	OutputTokens int `json:"output_tokens"`
}

// Control is the content of control.json (interactive claude -> controller).
type Control struct {
	Request        string `json:"request"`
	InterventionID string `json:"intervention_id,omitempty"`
	TS             string `json:"ts"`
}

// Assumption is one line of assumptions.jsonl.
type Assumption struct {
	TaskID      string `json:"task_id"`
	Description string `json:"description"`
	Rationale   string `json:"rationale"`
	TS          string `json:"ts"`
}

// Intervention is one line of interventions.jsonl.
type Intervention struct {
	ID            string `json:"id"`
	TaskID        string `json:"task_id"`
	TriggerReason string `json:"trigger_reason"`
	Question      string `json:"question"`
	Answer        string `json:"answer"`
	TS            string `json:"ts"`
}

// AuditEntry is one line of audit.jsonl.
type AuditEntry struct {
	TS     string         `json:"ts"`
	Event  string         `json:"event"`
	TaskID string         `json:"task_id"`
	Detail map[string]any `json:"detail,omitempty"`
	Usage  *Usage         `json:"usage,omitempty"`
}

// Store owns the on-disk state directory <workspace>/.orchestrator/.
type Store struct {
	Root string // absolute path to .orchestrator
}

// NewStore returns a Store rooted at <workspace>/.orchestrator and ensures the
// base directory layout exists.
func NewStore(workspace string) (*Store, error) {
	root := filepath.Join(workspace, ".orchestrator")
	s := &Store{Root: root}
	for _, d := range []string{"", "intervention", "workers", "worktrees"} {
		if err := os.MkdirAll(filepath.Join(root, d), 0o755); err != nil {
			return nil, err
		}
	}
	return s, nil
}

// path joins relative elements under the store root.
func (s *Store) path(elem ...string) string {
	return filepath.Join(append([]string{s.Root}, elem...)...)
}

// nowRFC3339 is a package-level clock so tests can be deterministic if needed.
var nowRFC3339 = func() string { return time.Now().UTC().Format(time.RFC3339) }

// ---- atomic write helpers ----

// writeAtomic writes data to path via a temp file + rename (atomic on POSIX).
func writeAtomic(path string, data []byte) error {
	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return err
	}
	tmp, err := os.CreateTemp(dir, ".tmp-*")
	if err != nil {
		return err
	}
	tmpName := tmp.Name()
	if _, err := tmp.Write(data); err != nil {
		tmp.Close()
		os.Remove(tmpName)
		return err
	}
	if err := tmp.Sync(); err != nil {
		tmp.Close()
		os.Remove(tmpName)
		return err
	}
	if err := tmp.Close(); err != nil {
		os.Remove(tmpName)
		return err
	}
	return os.Rename(tmpName, path)
}

func writeJSONAtomic(path string, v any) error {
	data, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return err
	}
	data = append(data, '\n')
	return writeAtomic(path, data)
}

func readJSON(path string, v any) error {
	data, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	return json.Unmarshal(data, v)
}

// appendJSONL appends one JSON-encoded record as a line to path.
func appendJSONL(path string, v any) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	data, err := json.Marshal(v)
	if err != nil {
		return err
	}
	data = append(data, '\n')
	f, err := os.OpenFile(path, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o644)
	if err != nil {
		return err
	}
	defer f.Close()
	_, err = f.Write(data)
	return err
}

// ---- State ----

// LoadState reads state.json. Returns (nil, nil) if it does not exist.
func (s *Store) LoadState() (*State, error) {
	var st State
	err := readJSON(s.path("state.json"), &st)
	if os.IsNotExist(err) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return &st, nil
}

// SaveState writes state.json atomically, stamping UpdatedAt.
func (s *Store) SaveState(st *State) error {
	st.UpdatedAt = nowRFC3339()
	if st.StartedAt == "" {
		st.StartedAt = st.UpdatedAt
	}
	return writeJSONAtomic(s.path("state.json"), st)
}

// ---- Plan ----

// LoadPlan reads plan.json. Returns (nil, nil) if it does not exist.
func (s *Store) LoadPlan() (*Plan, error) {
	var p Plan
	err := readJSON(s.path("plan.json"), &p)
	if os.IsNotExist(err) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return &p, nil
}

// SavePlan writes plan.json atomically.
func (s *Store) SavePlan(p *Plan) error {
	return writeJSONAtomic(s.path("plan.json"), p)
}

// ---- Control (handoff) ----

// LoadControl reads control.json. Returns (nil, nil) if absent.
func (s *Store) LoadControl() (*Control, error) {
	var c Control
	err := readJSON(s.path("control.json"), &c)
	if os.IsNotExist(err) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return &c, nil
}

// SaveControl writes control.json atomically (used in tests / by tooling).
func (s *Store) SaveControl(c *Control) error {
	if c.TS == "" {
		c.TS = nowRFC3339()
	}
	return writeJSONAtomic(s.path("control.json"), c)
}

// DeleteControl removes control.json after the controller consumes it.
func (s *Store) DeleteControl() error {
	err := os.Remove(s.path("control.json"))
	if os.IsNotExist(err) {
		return nil
	}
	return err
}

// ---- logs ----

func (s *Store) AppendAssumption(a Assumption) error {
	if a.TS == "" {
		a.TS = nowRFC3339()
	}
	return appendJSONL(s.path("assumptions.jsonl"), a)
}

func (s *Store) AppendIntervention(i Intervention) error {
	if i.TS == "" {
		i.TS = nowRFC3339()
	}
	return appendJSONL(s.path("interventions.jsonl"), i)
}

func (s *Store) AppendAudit(e AuditEntry) error {
	if e.TS == "" {
		e.TS = nowRFC3339()
	}
	return appendJSONL(s.path("audit.jsonl"), e)
}

// ---- summary ----

// WriteSummary writes summary.md (also the body Slack receives).
func (s *Store) WriteSummary(md string) error {
	return writeAtomic(s.path("summary.md"), []byte(md))
}

// ---- intervention question/answer ----

// WriteQuestion writes intervention/<id>/question.md.
func (s *Store) WriteQuestion(id, md string) error {
	return writeAtomic(s.path("intervention", id, "question.md"), []byte(md))
}

// ReadAnswer reads intervention/<id>/answer.md. Returns "" if absent.
func (s *Store) ReadAnswer(id string) (string, error) {
	data, err := os.ReadFile(s.path("intervention", id, "answer.md"))
	if os.IsNotExist(err) {
		return "", nil
	}
	if err != nil {
		return "", err
	}
	return string(data), nil
}

// WorkerLogPath returns the path of a worker's raw log file.
func (s *Store) WorkerLogPath(taskID string) string {
	return s.path("workers", fmt.Sprintf("%s.log", taskID))
}

// ---- sidecar (small single-value state files, e.g. open intervention id) ----

// WriteAtomicSidecar writes a small named value file under the store root.
func (s *Store) WriteAtomicSidecar(name, value string) error {
	return writeAtomic(s.path(name), []byte(value))
}

// ReadAtomicSidecar reads a sidecar value. Returns "" if absent.
func (s *Store) ReadAtomicSidecar(name string) (string, error) {
	data, err := os.ReadFile(s.path(name))
	if os.IsNotExist(err) {
		return "", nil
	}
	if err != nil {
		return "", err
	}
	return string(data), nil
}

// RemoveSidecar deletes a sidecar value file.
func (s *Store) RemoveSidecar(name string) error {
	err := os.Remove(s.path(name))
	if os.IsNotExist(err) {
		return nil
	}
	return err
}

// WorktreePath returns the relative path (from workspace) of a task worktree.
func (s *Store) WorktreeRel(taskID string) string {
	return filepath.Join(".orchestrator", "worktrees", taskID)
}

// WorktreeAbs returns the absolute path of a task worktree.
func (s *Store) WorktreeAbs(taskID string) string {
	return s.path("worktrees", taskID)
}

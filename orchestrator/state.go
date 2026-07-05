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

// VMModePreamble returns a short pointer prepended to brain/worker prompts when
// running under VM モード (env CLAUDE_DEV_VM=1), so they know `docker` targets the
// guest VM daemon and bind mounts must live under /workspace. Returns "" (no-op)
// otherwise. This is the orchestrator side of VM モードの発見導線2 (docs/impl/80,
// docs/08 §3.6); CLAUDE.md is never touched.
func VMModePreamble() string {
	if os.Getenv("CLAUDE_DEV_VM") != "1" {
		return ""
	}
	return "# VM モード\n" +
		"`docker` はゲスト VM の daemon を指す（DOCKER_HOST 設定済）。" +
		"bind mount の source は /workspace 配下のみ有効（virtiofs で同一パス共有・ホスト編集はライブ反映）。" +
		"詳細は /workspace/VM_DEV.md を参照。\n\n"
}

// Phase constants for the state machine. The former top-level "intervening"
// phase is abolished: interventions are handled per-task inside "executing".
const (
	PhaseWallbounce = "wallbounce"
	PhaseExecuting  = "executing"
	PhaseDone       = "done"
)

// Task.Status constants.
const (
	TaskPending      = "pending"
	TaskRunning      = "running"
	TaskReview       = "review"
	TaskRevise       = "revise"
	TaskWaitingHuman = "waiting_human" // parked awaiting a human decision (per-task intervention)
	TaskBlocked      = "blocked"
	TaskDone         = "done"
	TaskFailed       = "failed"
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
	Phase       string `json:"phase"` // wallbounce|executing|done（intervening は廃止）
	RunID       string `json:"run_id"`
	CurrentTask string `json:"current_task"` // 最後に着手したタスクID（情報用・並行実行のため一意でない）
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
	ID          string `json:"id"`
	Title       string `json:"title"`
	Description string `json:"description"`
	// Completion is the task-specific acceptance criterion. Reviews are scored
	// against THIS only (never the plan goal); an empty Completion is rejected by
	// plan lint before executing (docs/impl/60 §品質ゲート 8.1).
	Completion   string   `json:"completion"`
	Deps         []string `json:"deps"`
	Status       string   `json:"status"`
	Attempts     int      `json:"attempts"`
	Worktree     string   `json:"worktree"`
	Irreversible bool     `json:"irreversible,omitempty"` // trigger1: planning-time mark
	// IrrevApproved records that a human approved this irreversible task during
	// an intervention. Once true the pre-dispatch trigger1 no longer fires, so
	// the task can finally be dispatched (prevents infinite re-fire on resume).
	IrrevApproved bool `json:"irrev_approved,omitempty"`
	// SessionID is the claude -p session id for the CURRENT attempt. A fresh
	// attempt generates a new id (passed via --session-id); an interrupted
	// same-attempt resume reuses it (via --resume) so the worker continues
	// instead of starting from scratch.
	SessionID string `json:"session_id,omitempty"`
	// ResumeSession is set by NormalizeForResume when a running/review/revise
	// task is reset to pending after an interruption. It tells the scheduler to
	// re-dispatch the SAME attempt (--resume, no Attempts++) rather than start a
	// new attempt. Cleared once the resuming dispatch is launched.
	ResumeSession bool `json:"resume_session,omitempty"`
	// OpenInterventionID is non-empty only while the task is waiting_human; it
	// links to the open intervention queue entry.
	OpenInterventionID string `json:"open_intervention_id,omitempty"`
	// ReviewFormatErrors counts consecutive unparseable reviewer outputs (format
	// violations). Reset on a content-based verdict. At the configured limit the
	// task escalates as a review_gate_defect WITHOUT re-running the worker.
	ReviewFormatErrors int           `json:"review_format_errors,omitempty"`
	Result             *WorkerResult `json:"result,omitempty"`
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

// OpenInterventions is the content of intervention/open.json: the queue of
// unresolved human-decision requests. Multiple may be open at once (per-task).
type OpenInterventions struct {
	Items []OpenIntervention `json:"items"`
}

// OpenIntervention is one queued, unresolved intervention.
type OpenIntervention struct {
	ID            string `json:"id"`
	TaskID        string `json:"task_id"`
	TriggerReason string `json:"trigger_reason"`
	OpenedAt      string `json:"opened_at"`
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
	for _, d := range []string{"", "intervention", "workers", "worktrees", "sessions"} {
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

// ResetRun discards the run state of a previous session so a new run can start
// cleanly from wallbounce: it removes state.json, plan.json, control.json and
// the open-intervention sidecar. Append-only logs (audit/assumptions/
// interventions JSONL) and summary.md are kept as history. Missing files are
// not an error.
func (s *Store) ResetRun() error {
	for _, name := range []string{"state.json", "plan.json", "control.json"} {
		if err := os.Remove(s.path(name)); err != nil && !os.IsNotExist(err) {
			return err
		}
	}
	// Clear the per-task intervention queue too (new-model side-channel).
	if err := os.Remove(s.path("intervention", "open.json")); err != nil && !os.IsNotExist(err) {
		return err
	}
	return nil
}

// ---- intervention queue (intervention/open.json) ----

// LoadOpenInterventions reads the intervention queue. Returns an empty (non-nil)
// set if the file is absent or unreadable.
func (s *Store) LoadOpenInterventions() *OpenInterventions {
	var q OpenInterventions
	if err := readJSON(s.path("intervention", "open.json"), &q); err != nil {
		return &OpenInterventions{}
	}
	return &q
}

// SaveOpenInterventions writes the intervention queue atomically.
func (s *Store) SaveOpenInterventions(q *OpenInterventions) error {
	return writeJSONAtomic(s.path("intervention", "open.json"), q)
}

// AddOpenIntervention appends an entry to the queue (idempotent on ID).
func (s *Store) AddOpenIntervention(oi OpenIntervention) error {
	if oi.OpenedAt == "" {
		oi.OpenedAt = nowRFC3339()
	}
	q := s.LoadOpenInterventions()
	for _, it := range q.Items {
		if it.ID == oi.ID {
			return nil
		}
	}
	q.Items = append(q.Items, oi)
	return s.SaveOpenInterventions(q)
}

// RemoveOpenIntervention drops the entry with the given ID from the queue.
func (s *Store) RemoveOpenIntervention(id string) error {
	q := s.LoadOpenInterventions()
	out := q.Items[:0]
	for _, it := range q.Items {
		if it.ID != id {
			out = append(out, it)
		}
	}
	q.Items = out
	return s.SaveOpenInterventions(q)
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

package main

import (
	"context"
	"os"
	"os/exec"
	"regexp"
	"strings"
)

// SessionManager manages the orchestrator's tmux layout for the tmux-resident
// architecture (docs/06 §4.2/§5.3/§5.9, docs/impl/60「独立ウィンドウ方式（新アーキ）」).
//
// There is a SINGLE tmux session, `orch-<CNAME>-main`, and every component is a
// WINDOW hanging under it (親子関係＝1 セッション・複数ウィンドウ):
//
//	orch-<CNAME>-main:dashboard   メインループ/ダッシュボード＝worker セレクタ（コントローラ本体）
//	orch-<CNAME>-main:brainstorming  ブレインストーミング（対話 claude）
//	orch-<CNAME>-main:w-<taskID>  worker ごと（保持ウィンドウ。claude -p の tail → 介入対話 → …）
//
// The controller itself runs in the `dashboard` window; it opens/closes the
// other windows and drives commands into them. Navigation is intra-session
// (`select-window`), so `prefix+w` lists every worker and the number-key
// selector switches windows. Each non-dashboard window is created with
// remain-on-exit ON so an interactive claude exiting (/exit) does not destroy
// the window — the controller can then drive claude -p → intervene → re-dispatch
// in the same window. All tmux operations are best-effort: on a host without
// tmux (or non-TTY headless runs) they degrade to no-ops.
type SessionManager struct {
	Prefix string // "orch-<CNAME>"
}

var sessionTokenRe = regexp.MustCompile(`[^a-z0-9_-]+`)

// normalizeCName mirrors entrypoint's COMPOSE_PROJECT_NAME rule
// (lowercase, non [a-z0-9_-] -> '-').
func normalizeCName(s string) string {
	s = sessionTokenRe.ReplaceAllString(strings.ToLower(strings.TrimSpace(s)), "-")
	s = strings.Trim(s, "-")
	if s == "" {
		s = "project"
	}
	return s
}

// NewSessionManager derives a stable per-project prefix from
// COMPOSE_PROJECT_NAME (set by claude-dev/entrypoint) or, failing that, the
// hostname (= container name).
func NewSessionManager() *SessionManager {
	name := os.Getenv("COMPOSE_PROJECT_NAME")
	if strings.TrimSpace(name) == "" {
		if h, err := os.Hostname(); err == nil {
			name = h
		}
	}
	return &SessionManager{Prefix: "orch-" + normalizeCName(name)}
}

// dashboardWindowName is the controller's own window; the controller renames its
// window to this on startup (SetupMainSession) so SwitchTo can return to it.
const dashboardWindowName = "dashboard"

// MainSession is the single tmux session everything hangs under.
func (m *SessionManager) MainSession() string { return m.Prefix + "-main" }

// DashboardWindow / BrainstormingWindow / WorkerWindow return `session:window`
// targets for the respective windows under the main session.
func (m *SessionManager) DashboardWindow() string { return m.MainSession() + ":" + dashboardWindowName }

// BrainstormingWindow is the ブレインストーミング window. Its tmux window NAME is "brainstorming"
// (human-facing label; the internal identifiers keep the brainstorming name).
func (m *SessionManager) BrainstormingWindow() string { return m.MainSession() + ":brainstorming" }
func (m *SessionManager) WorkerWindow(taskID string) string {
	return m.MainSession() + ":w-" + taskID
}

// splitTarget splits a `session:window` target into its parts.
func splitTarget(target string) (session, window string) {
	if i := strings.Index(target, ":"); i >= 0 {
		return target[:i], target[i+1:]
	}
	return target, ""
}

// tmuxRun runs a tmux subcommand against the default server; success == nil err.
func tmuxRun(ctx context.Context, args ...string) error {
	return exec.CommandContext(ctx, "tmux", args...).Run()
}

// tmuxAvailable reports whether tmux is on PATH. The session-based interactive
// flow (LaunchInteractive + WaitConsume) is gated on this; without tmux the
// controller falls back to the legacy foreground RunInteractive path.
func tmuxAvailable() bool {
	_, err := exec.LookPath("tmux")
	return err == nil
}

// SetupMainSession, run once at controller startup, disables mouse on the main
// session (docs/06 §5.9: mouse off avoids the mouse-as-keyboard corruption) and
// renames the controller's own window to `dashboard`. Best-effort; no-op without
// tmux / outside a tmux pane.
func (m *SessionManager) SetupMainSession(ctx context.Context) {
	_ = tmuxRun(ctx, "set-option", "-t", m.MainSession(), "mouse", "off")
	_ = tmuxRun(ctx, "rename-window", dashboardWindowName) // renames the current (controller's) window
}

// Has reports whether the target window exists. It lists the session's windows
// and matches the window name exactly — NOT `display-message -t session:window`,
// which silently falls back to the session's current window (returning success)
// when the named window is absent, so it can never detect a missing window.
func (m *SessionManager) Has(ctx context.Context, target string) bool {
	sess, win := splitTarget(target)
	if win == "" {
		return tmuxRun(ctx, "has-session", "-t", sess) == nil
	}
	out, err := exec.CommandContext(ctx, "tmux", "list-windows", "-t", sess, "-F", "#{window_name}").Output()
	if err != nil {
		return false
	}
	for _, ln := range strings.Split(strings.TrimSpace(string(out)), "\n") {
		if ln == win {
			return true
		}
	}
	return false
}

// Ensure creates the target window under the main session if absent, with
// remain-on-exit ON so an in-window command exiting (interactive claude /exit)
// leaves the window intact for the controller to respawn the next command.
// Idempotent. The dashboard window is never created here (it is the controller's
// own window, created by claude-dev orchestrate).
func (m *SessionManager) Ensure(ctx context.Context, target string) error {
	sess, win := splitTarget(target)
	if m.Has(ctx, target) {
		_ = tmuxRun(ctx, "set-option", "-t", target, "-w", "remain-on-exit", "on")
		return nil
	}
	if err := tmuxRun(ctx, "new-window", "-d", "-t", sess, "-n", win); err != nil {
		return err
	}
	_ = tmuxRun(ctx, "set-option", "-t", target, "-w", "remain-on-exit", "on")
	return nil
}

// PaneDead reports whether the target window's active pane has a dead process
// (its command exited while remain-on-exit kept the pane). Used as the fallback
// signal that an interactive claude ended without writing control.json. A
// missing window or query error reads as NOT dead so WaitConsume keeps polling
// (the Has() check in the caller handles a truly gone window).
func (m *SessionManager) PaneDead(ctx context.Context, target string) bool {
	out, err := exec.CommandContext(ctx, "tmux", "list-panes", "-t", target, "-F", "#{pane_dead}").Output()
	if err != nil {
		return false
	}
	return strings.Contains(string(out), "1")
}

// LaunchInteractive (re)ensures the target window, injects an interactive claude
// via a launcher script into its pane, and selects that window so the attached
// client sees it (独立ウィンドウ方式: 対話 claude をウィンドウ内へ投入。docs/impl/60).
// Best-effort; no-op semantics when tmux is absent.
func (m *SessionManager) LaunchInteractive(ctx context.Context, target, scriptPath string) error {
	if err := m.Ensure(ctx, target); err != nil {
		return err
	}
	if err := tmuxRun(ctx, "respawn-pane", "-k", "-t", target, "sh "+shellSingleQuote(scriptPath)); err != nil {
		return err
	}
	return m.SwitchTo(ctx, target)
}

// Run injects a command into the target window's pane, replacing whatever ran
// before (`respawn-pane -k`). The window persists across commands, so the
// controller can drive: `tail -F` (view) -> interactive `claude` (intervene) ->
// `tail -F` (re-dispatch view) all in the same worker window.
func (m *SessionManager) Run(ctx context.Context, target, command string) error {
	if err := m.Ensure(ctx, target); err != nil {
		return err
	}
	return tmuxRun(ctx, "respawn-pane", "-k", "-t", target, command)
}

// Kill closes the target window (worker settle / cleanup). Best-effort. Never
// call this on the dashboard window (it would kill the controller).
func (m *SessionManager) Kill(ctx context.Context, target string) error {
	return tmuxRun(ctx, "kill-window", "-t", target)
}

// SwitchTo selects the target window within the main session so the attached
// client views it (worker selector / intervene navigation: docs/06 §5.3).
func (m *SessionManager) SwitchTo(ctx context.Context, target string) error {
	return tmuxRun(ctx, "select-window", "-t", target)
}

// ExpectedWindows returns the non-dashboard windows the controller should keep
// alive for the given phase/plan (docs/06 §5.9 recovery): the brainstorming window
// while in brainstorming; and a worker window for every task that has live work
// (running/review/revise or waiting_human). The dashboard window is the
// controller's own and is not listed. Pure/testable; EnsureAll materializes them.
func (m *SessionManager) ExpectedWindows(phase string, plan *Plan) []string {
	var targets []string
	if phase == PhaseBrainstorming {
		targets = append(targets, m.BrainstormingWindow())
	}
	if plan != nil {
		for i := range plan.Tasks {
			switch plan.Tasks[i].Status {
			case TaskRunning, TaskReview, TaskRevise, TaskWaitingHuman:
				targets = append(targets, m.WorkerWindow(plan.Tasks[i].ID))
			}
		}
	}
	return targets
}

// EnsureAll (re)creates any missing expected windows (recovery: docs/06 §5.9).
// Best-effort; no-op when tmux is absent.
func (m *SessionManager) EnsureAll(ctx context.Context, phase string, plan *Plan) {
	for _, target := range m.ExpectedWindows(phase, plan) {
		_ = m.Ensure(ctx, target)
	}
}

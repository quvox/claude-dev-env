package main

import (
	"context"
	"os"
	"os/exec"
	"regexp"
	"strings"
)

// SessionManager creates and manages the orchestrator's per-component tmux
// sessions for the independent-session architecture (docs/06 §4.2/§5.3/§5.9,
// docs/impl/60「独立セッション方式（新アーキ）」):
//
//	orch-<CNAME>-main        メインループ/ダッシュボード＝worker セレクタ（常設）
//	orch-<CNAME>-wallbounce   壁打ち（対話 claude）
//	orch-<CNAME>-w-<taskID>   worker ごと（保持シェル。claude -p → 介入対話 → 再 claude -p）
//
// The controller runs as a detached daemon (it does not occupy the human's
// terminal) and drives commands into these sessions, so a broken terminal or an
// accidentally-closed session never takes work down: sessions are disposable
// views rebuilt from state. Each session is created as a long-lived holder shell
// (NOT `new-session "<cmd>"`, which would die when the command exits) so a
// worker's `claude -p` can be followed by an interactive intervene `claude` in
// the same session. All tmux operations are best-effort: on a host without tmux
// (or non-TTY headless runs) they degrade to no-ops.
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

func (m *SessionManager) MainSession() string       { return m.Prefix + "-main" }
func (m *SessionManager) WallbounceSession() string { return m.Prefix + "-wallbounce" }
func (m *SessionManager) WorkerSession(taskID string) string {
	return m.Prefix + "-w-" + taskID
}

// tmuxRun runs a tmux subcommand against the default server; success == nil err.
func tmuxRun(ctx context.Context, args ...string) error {
	return exec.CommandContext(ctx, "tmux", args...).Run()
}

// Has reports whether the named session exists.
func (m *SessionManager) Has(ctx context.Context, name string) bool {
	return tmuxRun(ctx, "has-session", "-t", name) == nil
}

// Ensure creates the session as a long-lived holder shell if absent, with mouse
// disabled (docs/06 §5.9: mouse off avoids the mouse-as-keyboard corruption that
// forces closing the terminal). Idempotent.
func (m *SessionManager) Ensure(ctx context.Context, name string) error {
	if m.Has(ctx, name) {
		return nil
	}
	if err := tmuxRun(ctx, "new-session", "-d", "-s", name); err != nil {
		return err
	}
	_ = tmuxRun(ctx, "set-option", "-t", name, "mouse", "off")
	return nil
}

// Run injects a command into the session's holder pane, replacing whatever ran
// before (`respawn-pane -k`). The session persists across commands, so the
// controller can drive: `claude -p` (worker) -> interactive `claude` (intervene)
// -> `claude -p` (re-dispatch) all in the same worker session.
func (m *SessionManager) Run(ctx context.Context, name, command string) error {
	if err := m.Ensure(ctx, name); err != nil {
		return err
	}
	return tmuxRun(ctx, "respawn-pane", "-k", "-t", name, command)
}

// Kill tears down a session (worker settle / cleanup). Best-effort.
func (m *SessionManager) Kill(ctx context.Context, name string) error {
	return tmuxRun(ctx, "kill-session", "-t", name)
}

// SwitchTo switches the attached client to the named session (worker selector
// on the main session: docs/06 §5.3).
func (m *SessionManager) SwitchTo(ctx context.Context, name string) error {
	return tmuxRun(ctx, "switch-client", "-t", name)
}

// ExpectedSessions returns the set of sessions the controller should keep alive
// for the given phase/plan (docs/06 §5.9 recovery): always the main session; the
// wallbounce session while in wallbounce; and a worker session for every task
// that has live work (running/review/revise or waiting_human). Pure/testable;
// EnsureAll materializes them.
func (m *SessionManager) ExpectedSessions(phase string, plan *Plan) []string {
	names := []string{m.MainSession()}
	if phase == PhaseWallbounce {
		names = append(names, m.WallbounceSession())
	}
	if plan != nil {
		for i := range plan.Tasks {
			switch plan.Tasks[i].Status {
			case TaskRunning, TaskReview, TaskRevise, TaskWaitingHuman:
				names = append(names, m.WorkerSession(plan.Tasks[i].ID))
			}
		}
	}
	return names
}

// EnsureAll (re)creates any missing expected sessions (recovery: docs/06 §5.9).
// Best-effort; no-op when tmux is absent.
func (m *SessionManager) EnsureAll(ctx context.Context, phase string, plan *Plan) {
	for _, name := range m.ExpectedSessions(phase, plan) {
		_ = m.Ensure(ctx, name)
	}
}

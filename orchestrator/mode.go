package main

import (
	"context"
	"os"
	"os/exec"
	"path/filepath"
)

// instructionDir is where image-baked interactive instructions live.
const instructionDir = "/usr/local/share/claude-orchestrator"

// Mode owns the terminal foreground and switches what occupies it. Interactive
// (wallbounce/intervene) exec's a child `claude` sharing the controller's TTY
// and blocks until it exits; execution mode renders the dashboard.
type Mode struct {
	Store     *Store
	Workspace string
	// localInstrDir, if set, overrides instructionDir (used in tests/dev).
	localInstrDir string
}

// instructionPath returns the path to a named instruction template, preferring
// a local override directory if configured.
func (m *Mode) instructionPath(name string) string {
	if m.localInstrDir != "" {
		return filepath.Join(m.localInstrDir, name)
	}
	return filepath.Join(instructionDir, name)
}

// RunInteractive launches the interactive `claude` as a foreground child that
// shares the controller's TTY, blocking until it exits. `extraArgs` are passed
// verbatim. The controller loop naturally pauses while this runs.
//
// Wallbounce: launch with the wallbounce instruction.
// Intervene: fresh start (no --resume) with the intervention question seeded.
func (m *Mode) RunInteractive(ctx context.Context, args ...string) error {
	cmd := exec.CommandContext(ctx, "claude", args...)
	cmd.Dir = m.Workspace
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	// Interactive claude is allowed Slack? No: only the controller sends Slack.
	// We still strip the token so the interactive child cannot post either.
	cmd.Env = stripEnv(os.Environ(), "SLACK_BOT_TOKEN")
	return cmd.Run()
}

// WallbounceArgs returns the args for launching the wallbounce brain. The
// project policy (ORCHESTRATOR.md, if any) is prepended to the front of the
// instruction, which is passed via --append-system-prompt.
func (m *Mode) WallbounceArgs() []string {
	args := []string{}
	instr := LoadProjectPolicy(m.Workspace) + readFileOr(m.instructionPath("wallbounce.md"), "")
	if instr != "" {
		args = append(args, "--append-system-prompt", instr)
	}
	return args
}

// InterveneArgs returns the args for launching the intervention brain. It seeds
// the question and the intervention instruction as an initial prompt/system
// prompt. Uses a fresh start (no --resume) per 06 §6.2 ノブ1. The project
// policy (ORCHESTRATOR.md, if any) is prepended to the front of the instruction.
func (m *Mode) InterveneArgs(interventionID string) []string {
	args := []string{}
	instr := LoadProjectPolicy(m.Workspace) + readFileOr(m.instructionPath("intervene.md"), "")
	if instr != "" {
		args = append(args, "--append-system-prompt", instr)
	}
	q, _ := m.Store.ReadQuestion(interventionID)
	if q != "" {
		args = append(args, q)
	}
	return args
}

// ReadQuestion reads intervention/<id>/question.md (helper on the store).
func (s *Store) ReadQuestion(id string) (string, error) {
	data, err := os.ReadFile(s.path("intervention", id, "question.md"))
	if err != nil {
		return "", err
	}
	return string(data), nil
}

// readFileOr returns the file content or a fallback if the file is missing.
func readFileOr(path, fallback string) string {
	data, err := os.ReadFile(path)
	if err != nil {
		return fallback
	}
	return string(data)
}

// isTTY reports whether stdout is a terminal. Used to decide whether to render
// the ANSI dashboard and process keys, or run a headless fallback.
func isTTY() bool {
	fi, err := os.Stdout.Stat()
	if err != nil {
		return false
	}
	return (fi.Mode() & os.ModeCharDevice) != 0
}

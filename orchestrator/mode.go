package main

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
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
	cmd := exec.CommandContext(ctx, claudePath(), args...)
	cmd.Dir = m.Workspace
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	// Interactive claude is allowed Slack? No: only the controller sends Slack.
	// We still strip the token so the interactive child cannot post either. PATH
	// is augmented so a non-interactive launch (tmux `zsh -c`) can still find any
	// claude-adjacent binaries.
	cmd.Env = claudeChildEnv()
	err := cmd.Run()
	// The interactive `claude` TUI leaves the shared TTY in a non-canonical
	// ("raw") mode and does not restore it on exit. Restore a sane canonical
	// state so the controller's subsequent line reads (terminalConfirm) and the
	// dashboard work; without this, those reads block forever waiting for a
	// "\n" that raw-mode Enter never delivers.
	ttyRestoreSane()
	return err
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

// ResolveArgs returns the args for launching the intervention brain to resolve
// the open intervention queue. It seeds the intervention instruction (system
// prompt) plus ALL open questions (batched) as the initial prompt, so the human
// can answer them one by one in a single fresh session. Uses a fresh start (no
// --resume) per 06 §6.2. The project policy (ORCHESTRATOR.md, if any) is
// prepended to the instruction.
func (m *Mode) ResolveArgs(ids []string) []string {
	args := []string{}
	instr := LoadProjectPolicy(m.Workspace) + readFileOr(m.instructionPath("intervene.md"), "")
	if instr != "" {
		args = append(args, "--append-system-prompt", instr)
	}
	var b strings.Builder
	if len(ids) > 1 {
		fmt.Fprintf(&b, "未解決の要判断が %d 件あります。各件に順番に回答してください。\n\n", len(ids))
	}
	for _, id := range ids {
		if q, _ := m.Store.ReadQuestion(id); q != "" {
			fmt.Fprintf(&b, "===== 介入 %s =====\n%s\n\n", id, q)
		}
	}
	if s := b.String(); s != "" {
		args = append(args, s)
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

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
// (brainstorming/intervene) exec's a child `claude` sharing the controller's TTY
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
// Brainstorming: launch with the brainstorming instruction.
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

// brainstormingInstr assembles the brainstorming --append-system-prompt instruction:
// any consume-once lint-rejection note (handoff_note.md), the VM-mode preamble,
// the project policy (ORCHESTRATOR.md, if any) and the baked brainstorming.md.
// Shared by the legacy Args path and the session-launch path (docs/06 §4.5).
func (m *Mode) brainstormingInstr() string {
	// Consume-once: read then delete the handoff note.
	note, _ := m.Store.ReadAtomicSidecar("handoff_note.md")
	_ = os.Remove(m.Store.path("handoff_note.md"))
	preamble := ""
	if strings.TrimSpace(note) != "" {
		preamble = "【前回の実行差し戻し（handoff_note）】\n" + strings.TrimSpace(note) +
			"\n上記を最優先で解消し、全タスクに completion を付けてから実行してください。\n\n"
	}
	return preamble + VMModePreamble() + LoadProjectPolicy(m.Workspace) + readFileOr(m.instructionPath("brainstorming.md"), "")
}

// BrainstormingArgs returns the args for launching the brainstorming brain (legacy
// foreground path). The project policy is prepended to the instruction, passed
// via --append-system-prompt.
func (m *Mode) BrainstormingArgs() []string {
	if instr := m.brainstormingInstr(); instr != "" {
		return []string{"--append-system-prompt", instr}
	}
	return []string{}
}

// interveneInstr assembles the intervene --append-system-prompt instruction
// (VM-mode preamble + project policy + baked intervene.md). Shared by the batch
// (ResolveArgs) and per-worker (ResolveArgsOne / IntervenePrompt) paths.
func (m *Mode) interveneInstr() string {
	return VMModePreamble() + LoadProjectPolicy(m.Workspace) + readFileOr(m.instructionPath("intervene.md"), "")
}

// IntervenePrompt returns the (system prompt, initial prompt) pair for resolving
// a single intervention in its worker session (独立ウィンドウ方式・docs/06 §6.3).
// The initial prompt is that intervention's question.md.
func (m *Mode) IntervenePrompt(id string) (sys, prompt string) {
	sys = m.interveneInstr()
	prompt, _ = m.Store.ReadQuestion(id)
	return sys, prompt
}

// shellSingleQuote wraps s in single quotes for safe embedding in a /bin/sh
// command line (used for launcher script paths and env values).
func shellSingleQuote(s string) string {
	return "'" + strings.ReplaceAll(s, "'", `'\''`) + "'"
}

// WriteLaunchScript writes a /bin/sh launcher for an interactive claude into the
// store's sessions dir and returns the script path. key is a filesystem-safe
// token (the tmux session suffix, e.g. "brainstorming" or "w-t3"). The script
// normalizes the environment (source VM env, put claude on PATH, strip the Slack
// token so only the controller posts), cd's to the workspace, and exec's claude
// with the system prompt and optional initial prompt read from sidecar files —
// avoiding multi-KB argv/quoting through tmux (独立ウィンドウ方式・docs/impl/60).
func (m *Mode) WriteLaunchScript(key string, prof ModelProfile, sysPrompt, prompt string) (string, error) {
	dir := m.Store.path("sessions")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return "", err
	}
	sysFile := filepath.Join(dir, key+".sys")
	promptFile := filepath.Join(dir, key+".prompt")
	scriptFile := filepath.Join(dir, key+".sh")
	if err := writeAtomic(sysFile, []byte(sysPrompt)); err != nil {
		return "", err
	}
	if err := writeAtomic(promptFile, []byte(prompt)); err != nil {
		return "", err
	}
	var b strings.Builder
	b.WriteString("#!/bin/sh\n")
	b.WriteString("[ -f /etc/claude-dev/vm.env ] && . /etc/claude-dev/vm.env\n")
	if bin := localBinDir(); bin != "" {
		fmt.Fprintf(&b, "export PATH=%s:\"$PATH\"\n", shellSingleQuote(bin))
	}
	b.WriteString("unset SLACK_BOT_TOKEN\n")
	fmt.Fprintf(&b, "cd %s 2>/dev/null || true\n", shellSingleQuote(m.Workspace))
	fmt.Fprintf(&b, "exec %s", shellSingleQuote(claudePath()))
	// Model/effort by role (models.go policy table): brainstorming/intervene 用。
	if strings.TrimSpace(prof.Model) != "" {
		fmt.Fprintf(&b, " --model %s", shellSingleQuote(prof.Model))
	}
	if strings.TrimSpace(prof.Effort) != "" {
		fmt.Fprintf(&b, " --effort %s", shellSingleQuote(prof.Effort))
	}
	if strings.TrimSpace(sysPrompt) != "" {
		fmt.Fprintf(&b, " --append-system-prompt \"$(cat %s)\"", shellSingleQuote(sysFile))
	}
	if strings.TrimSpace(prompt) != "" {
		fmt.Fprintf(&b, " \"$(cat %s)\"", shellSingleQuote(promptFile))
	}
	b.WriteString("\n")
	if err := os.WriteFile(scriptFile, []byte(b.String()), 0o755); err != nil {
		return "", err
	}
	return scriptFile, nil
}

// ResolveArgs returns the args for launching the intervention brain to resolve
// the open intervention queue. It seeds the intervention instruction (system
// prompt) plus ALL open questions (batched) as the initial prompt, so the human
// can answer them one by one in a single fresh session. Uses a fresh start (no
// --resume) per 06 §6.2. The project policy (ORCHESTRATOR.md, if any) is
// prepended to the instruction.
func (m *Mode) ResolveArgs(ids []string) []string {
	args := []string{}
	instr := VMModePreamble() + LoadProjectPolicy(m.Workspace) + readFileOr(m.instructionPath("intervene.md"), "")
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

// ResolveArgsOne builds intervene args for a SINGLE intervention (独立ウィンドウ方式:
// 各 worker セッションで1件ずつ対応。docs/06 §5.5/§6.3、docs/impl/60「独立ウィンドウ方式」).
// Unlike ResolveArgs (batch), it seeds only that one question — the queue-wide
// "which/next" is shown by the main selector, so the intervene brain focuses on
// its single item.
func (m *Mode) ResolveArgsOne(id string) []string {
	args := []string{}
	if instr := m.interveneInstr(); instr != "" {
		args = append(args, "--append-system-prompt", instr)
	}
	if q, _ := m.Store.ReadQuestion(id); q != "" {
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

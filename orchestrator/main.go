// Command claude-orchestrator is the per-project AI orchestrator: a single
// process that owns the terminal foreground and drives a state machine
// (wallbounce -> executing -> intervening -> done), delegating implementation
// to headless `claude -p` workers on git worktrees, gating quality with an
// independent reviewer, and escalating to the human only on intervention
// triggers. See docs/impl/60_orchestrator.md (the source of truth) and
// docs/06_orchestration.md.
package main

import (
	"bufio"
	"context"
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"strings"
	"syscall"
)

func main() {
	var (
		workspace     = flag.String("workspace", defaultWorkspace(), "project workspace root")
		workersWindow = flag.Bool("workers-window", false, "enable Config B (workers log window; reserved)")
		instrDir      = flag.String("instructions", "", "override instruction template dir (dev/test)")
	)
	flag.Parse()
	_ = workersWindow // wiring reserved; tmux window is created by the CLI layer.

	goal := strings.TrimSpace(strings.Join(flag.Args(), " "))

	if err := run(*workspace, *instrDir, goal); err != nil {
		log.Fatalf("orchestrator: %v", err)
	}
}

func run(workspace, instrDir, goal string) error {
	store, err := NewStore(workspace)
	if err != nil {
		return fmt.Errorf("init store: %w", err)
	}
	cfg := LoadConfig(workspace)

	// If a goal is supplied and no plan exists yet, seed a minimal plan so the
	// wallbounce brain has a starting point (it may overwrite plan.json).
	if goal != "" {
		if p, _ := store.LoadPlan(); p == nil {
			_ = store.SavePlan(&Plan{Goal: goal, Ready: false})
		}
	}

	mode := &Mode{Store: store, Workspace: workspace, localInstrDir: instrDir}
	handoff := &Handoff{Store: store}
	notifier := NewSlackNotifier(cfg)

	worker := &Worker{
		Store:     store,
		Claude:    ExecClaude{},
		Git:       ExecGit{},
		Cfg:       cfg,
		Workspace: workspace,
	}
	reviewer := &Reviewer{
		Store:  store,
		Claude: ExecClaude{},
		Cfg:    cfg,
		Worker: worker,
	}

	ctrl := &Controller{
		Store:    store,
		Cfg:      cfg,
		Mode:     mode,
		Handoff:  handoff,
		Worker:   worker,
		Reviewer: reviewer,
		Notifier: notifier,
		Confirm:  terminalConfirm,
	}

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	// Flush state on signal so we can resume next time.
	sigc := make(chan os.Signal, 1)
	signal.Notify(sigc, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		<-sigc
		cancel()
	}()

	return ctrl.Run(ctx)
}

// terminalConfirm asks the human on the terminal when control.json is missing
// or invalid. On a non-TTY it returns "continue" (never auto-executes).
func terminalConfirm(prompt string) string {
	if !isTTY() {
		return "continue"
	}
	fmt.Printf("%s\n> ", prompt)
	r := bufio.NewReader(os.Stdin)
	line, err := r.ReadString('\n')
	if err != nil {
		return "continue"
	}
	switch strings.TrimSpace(strings.ToLower(line)) {
	case "execute", "e":
		return "execute"
	case "done", "q", "quit":
		return "done"
	default:
		return "continue"
	}
}

func defaultWorkspace() string {
	if wd, err := os.Getwd(); err == nil {
		return wd
	}
	return "/workspace"
}

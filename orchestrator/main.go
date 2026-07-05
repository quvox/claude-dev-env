// Command claude-orchestrator is the per-project AI orchestrator: a single
// process that owns the terminal foreground and drives a state machine
// (wallbounce -> executing -> done), delegating implementation to headless
// `claude -p` workers on git worktrees, gating quality with an independent
// reviewer, and escalating to the human per-task (waiting_human) only on
// intervention triggers. See docs/impl/60_orchestrator.md (the source of truth) and
// docs/06_orchestration.md.
package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"
)

func main() {
	var (
		workspace = flag.String("workspace", defaultWorkspace(), "project workspace root")
		instrDir  = flag.String("instructions", "", "override instruction template dir (dev/test)")
		fresh     = flag.Bool("fresh", false, "discard leftover run state and start a new session from wallbounce")
		startExec = flag.Bool("start-executing", false, "verification-only: if a ready seed plan.json exists, skip wallbounce and begin in executing")
		printSess = flag.Bool("print-main-session", false, "print the controller's main tmux session name (orch-<CNAME>-main) and exit")
	)
	flag.Parse()

	// claude-dev orchestrate calls this to learn the session name to has-session/
	// attach against (tmux 常駐方式・docs/impl/10_cli.md). Print and exit.
	if *printSess {
		fmt.Println(NewSessionManager().MainSession())
		return
	}

	goal := strings.TrimSpace(strings.Join(flag.Args(), " "))

	// A signal (Ctrl-C) cancels the context, which the controller turns into a
	// clean, resumable suspend. context.Canceled is therefore NOT a fatal error.
	if err := run(*workspace, *instrDir, goal, *fresh, *startExec); err != nil && !errors.Is(err, context.Canceled) {
		log.Fatalf("orchestrator: %v", err)
	}
}

func run(workspace, instrDir, goal string, fresh, startExec bool) error {
	// Resolve the workspace to an absolute path. Store paths (and thus the git
	// worktree paths) are derived from it and are passed to `git` runs whose
	// cmd.Dir is the workspace; a relative workspace would make git resolve the
	// worktree path relative to that dir and double-nest it (…/ws/ws/.orchestrator
	// /worktrees/…), which then fails with "already checked out"/exit 128 on retry.
	if abs, aerr := filepath.Abs(workspace); aerr == nil {
		workspace = abs
	}
	store, err := NewStore(workspace)
	if err != nil {
		return fmt.Errorf("init store: %w", err)
	}
	cfg := LoadConfig(workspace)

	// Decide whether the leftover state is resumable. Only a genuinely
	// interrupted run (executing) is resumed; a finished (done),
	// absent, or unrecognized state starts fresh from wallbounce. This prevents
	// two failure modes: (a) a finished run leaving Phase=done so the next launch
	// exits immediately, and (b) silently skipping wallbounce into a stale
	// executing run. --fresh forces a clean start even from an interrupted run.
	prev, _ := store.LoadState()
	switch {
	case !fresh && isResumable(prev):
		fmt.Printf("↩️  前回の %s フェーズから再開します\n", prev.Phase)
	case !fresh && startExec && seedPlanReady(store):
		// Verification affordance: a ready seed plan.json is present and no run is
		// in progress. Begin directly in executing, WITHOUT resetting (which would
		// delete the seed plan). docs/impl/70_sample-project.md.
		if err := store.SaveState(&State{Phase: PhaseExecuting, RunID: newRunID()}); err != nil {
			return fmt.Errorf("seed state: %w", err)
		}
		fmt.Println("▶ seed plan から直接 executing で開始します（--start-executing）")
	default:
		switch {
		case fresh && isResumable(prev):
			fmt.Println("🆕 前回の実行状態を破棄して新規セッションを開始します（--fresh）")
		case startExec:
			fmt.Println("⚠ --start-executing は ready な seed plan が無いため壁打ちから開始します")
		default:
			fmt.Println("🆕 新規セッションを開始します（壁打ちから）")
		}
		CleanOrchWorktrees(context.Background(), workspace, store.path("worktrees"))
		if err := store.ResetRun(); err != nil {
			return fmt.Errorf("reset run: %w", err)
		}
	}

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

	claudeRunner := ExecClaude{PermissionMode: cfg.WorkerPermissionMode}
	worker := &Worker{
		Store:     store,
		Claude:    claudeRunner,
		Git:       ExecGit{},
		Cfg:       cfg,
		Workspace: workspace,
	}
	reviewer := &Reviewer{
		Store:  store,
		Claude: claudeRunner,
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
		Sessions: NewSessionManager(),
	}

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	// Safety net: whatever path we exit by (normal, error, signal), leave the
	// terminal in a sane canonical state. The dashboard and interactive child
	// each restore on their own, but a signal can unwind before they do.
	defer ttyRestoreSane()
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
// or unclear, via a cursor/number-selectable menu (docs/06 §4.5/§5.6). On a
// non-TTY it returns "continue" (never auto-executes). Returns one of
// "continue"/"execute"/"done" (mapped by the controller to
// continue_wallbounce/execute/abort). Japanese labels (docs/06 §5.7).
func terminalConfirm(prompt string) string {
	return selectMenu(prompt, []menuItem{
		{Value: "continue", Label: "1. 続ける", Desc: "対話（壁打ち）に戻って要件・plan をさらに詰める（plan は保持）"},
		{Value: "execute", Label: "2. 実行", Desc: "plan の各タスクを worker に並行ディスパッチして実装を進める（要 ready＋全 completion）"},
		{Value: "done", Label: "3. 終了", Desc: "このオーケストレーション実行を終了する"},
	}, 0)
}

// isResumable reports whether a loaded state represents a genuinely interrupted
// run that should be resumed rather than restarted from wallbounce. Only
// executing is resumable (the former top-level intervening phase is abolished).
func isResumable(st *State) bool {
	return st != nil && st.Phase == PhaseExecuting
}

// seedPlanReady reports whether a ready seed plan.json is present (used by the
// --start-executing verification affordance).
func seedPlanReady(store *Store) bool {
	p, _ := store.LoadPlan()
	return p != nil && p.Ready && len(p.Tasks) > 0
}

func defaultWorkspace() string {
	if wd, err := os.Getwd(); err == nil {
		return wd
	}
	return "/workspace"
}

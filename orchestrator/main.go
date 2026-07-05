// Command claude-orchestrator is the per-project AI orchestrator: a single
// process that owns the terminal foreground and drives a state machine
// (brainstorming -> executing -> done), delegating implementation to headless
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
		fresh     = flag.Bool("fresh", false, "discard leftover run state and start a new session from brainstorming")
		startExec = flag.Bool("start-executing", false, "verification-only: if a ready seed plan.json exists, skip brainstorming and begin in executing")
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
	// absent, or unrecognized state starts fresh from brainstorming. This prevents
	// two failure modes: (a) a finished run leaving Phase=done so the next launch
	// exits immediately, and (b) silently skipping brainstorming into a stale
	// executing run. --fresh forces a clean start even from an interrupted run.
	// Resume/new decision is based on the PLAN's completion, not the phase
	// (docs/06 §4.3): an unfinished plan (some task not done) is CONTINUED —
	// whether it was interrupted mid-executing or ended via `abort` with pending
	// tasks left. Only a fully-done plan (or no plan) starts fresh. Crucially we
	// NEVER delete plan/state/history on startup: ArchiveRun MOVES them to
	// history/ so they stay referenceable; only a manual `rm` deletes.
	prev, _ := store.LoadState()
	plan, _ := store.LoadPlan()
	unfinished := plan != nil && !AllDone(plan)
	switch {
	case fresh:
		// Explicit reset: archive the current run (do NOT delete), remove worktrees
		// + orch/* branches, and start fresh from brainstorming.
		fmt.Println("🆕 --fresh: 前回 run を history/ に退避して新規セッションを開始します")
		CleanOrchWorktrees(context.Background(), workspace, store.path("worktrees"))
		if err := store.ArchiveRun(); err != nil {
			return fmt.Errorf("archive run: %w", err)
		}
	case startExec && seedPlanReady(store):
		// Verification affordance: a ready seed plan.json is present. Begin directly
		// in executing WITHOUT archiving (would move the seed plan). docs/impl/70.
		if err := store.SaveState(&State{Phase: PhaseExecuting, RunID: newRunID()}); err != nil {
			return fmt.Errorf("seed state: %w", err)
		}
		fmt.Println("▶ seed plan から直接 executing で開始します（--start-executing）")
	case unfinished && plan.Ready:
		// Unfinished executable plan → continue the remaining tasks (executing).
		st := prev
		if st == nil {
			st = &State{RunID: newRunID()}
		}
		st.Phase = PhaseExecuting
		if err := store.SaveState(st); err != nil {
			return fmt.Errorf("resume state: %w", err)
		}
		fmt.Printf("↩️  未完了の plan から継続します（残り %d タスク。中断/中止からの続き）\n", countUndone(plan))
	case unfinished && !plan.Ready:
		// Plan not ready yet (brainstorming unfinished) → keep the plan, continue
		// brainstorming rather than discarding it.
		st := prev
		if st == nil {
			st = &State{RunID: newRunID()}
		}
		st.Phase = PhaseBrainstorming
		if err := store.SaveState(st); err != nil {
			return fmt.Errorf("resume state: %w", err)
		}
		fmt.Println("↩️  ブレインストーミングを継続します（未確定の plan を保持）")
	default:
		// No plan, or every task done (genuinely complete) → start fresh. Archive a
		// completed prior run (move to history/, never delete).
		if prev != nil || plan != nil {
			fmt.Println("🆕 新規セッションを開始します（前回 run は history/ に退避）")
			if err := store.ArchiveRun(); err != nil {
				return fmt.Errorf("archive run: %w", err)
			}
		} else {
			fmt.Println("🆕 新規セッションを開始します（ブレインストーミングから）")
		}
	}

	// If a goal is supplied and no plan exists yet, seed a minimal plan so the
	// brainstorming brain has a starting point (it may overwrite plan.json).
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
// or unclear, via a cursor/number-selectable menu (docs/06 §4.5/§5.6). The "実行"
// option is offered ONLY when canExecute (the plan is ready + every task has
// completion); otherwise ブレインストーミング is not finished so only 続ける/終了 are shown —
// execute must not be presented for an unfinished plan. On a non-TTY it returns
// "continue" (never auto-executes). Returns "continue"/"execute"/"done" (mapped
// by the controller to continue_brainstorming/execute/abort). Japanese (docs/06 §5.7).
func terminalConfirm(prompt string, canExecute bool) string {
	items := []menuItem{
		{Value: "continue", Label: "1. 続ける", Desc: "対話（ブレインストーミング）に戻って要件・plan をさらに詰める（plan は保持）"},
	}
	if canExecute {
		items = append(items,
			menuItem{Value: "execute", Label: "2. 実行", Desc: "plan の各タスクを worker に並行ディスパッチして実装を進める（ready＋全 completion 済み）"},
			menuItem{Value: "done", Label: "3. 終了", Desc: "このオーケストレーション実行を終了する"},
		)
	} else {
		// ブレインストーミングが実行に足りていない（未 ready／completion 欠け）: 実行は出さない。
		items = append(items,
			menuItem{Value: "done", Label: "2. 終了", Desc: "このオーケストレーション実行を終了する"},
		)
	}
	return selectMenu(prompt, items, 0)
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

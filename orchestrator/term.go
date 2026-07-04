package main

import (
	"os"
	"os/exec"
)

// Terminal-mode handling.
//
// The interactive `claude` child (wallbounce/intervene) is a full-screen TUI
// that switches the shared controlling terminal into a non-canonical ("raw")
// mode and does NOT restore canonical mode when it exits. Because the
// controller shares that same TTY, every line-buffered read it performs
// afterwards (the dashboard key reader and the terminal confirm prompt) would
// otherwise block forever: in raw mode the Enter key delivers "\r", never the
// "\n" those readers wait for. The orchestrator must therefore own terminal
// mode itself — restore a sane canonical state after any interactive child,
// and enter its own key-reading mode for the dashboard.
//
// Implemented with the `stty` utility (stdlib-only: no external Go modules).
// All helpers are best-effort no-ops on a non-TTY or when `stty` is absent.

// rawKeyMode puts the controlling terminal into a non-canonical, no-echo mode
// tuned for single-keypress reads: VMIN=0/VTIME=1 means os.Stdin.Read returns a
// byte the instant one is typed and otherwise returns (0, io.EOF) after ~0.1s,
// so the reader can honour context cancellation promptly and never leaks a
// goroutine blocked on stdin. Signal generation (isig) is left enabled so
// Ctrl-C still reaches the controller's signal handler. It returns a restore
// func that returns the terminal to a sane canonical state; on failure it
// returns a no-op restore and ok=false.
func rawKeyMode() (restore func(), ok bool) {
	if !sttyRun("-icanon", "-echo", "min", "0", "time", "1") {
		return func() {}, false
	}
	return ttyRestoreSane, true
}

// ttyRestoreSane returns the controlling terminal to a sane canonical line
// discipline (echo on, line buffering on). Used after an interactive child
// exits and when the dashboard stops reading keys.
func ttyRestoreSane() { sttyRun("sane") }

// sttyRun runs `stty` against the controlling terminal (os.Stdin). It reports
// whether the command succeeded.
func sttyRun(args ...string) bool {
	if !isTTY() {
		return false
	}
	cmd := exec.Command("stty", args...)
	cmd.Stdin = os.Stdin
	return cmd.Run() == nil
}

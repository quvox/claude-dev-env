package main

import (
	"os"
	"strconv"
	"strings"
	"syscall"
)

// Daemon lifecycle helpers for the independent-session architecture (docs/06
// §4.1/§5.9, docs/impl/60「独立セッション方式（新アーキ）」). The controller runs
// as a detached daemon that owns the tmux session views; a pidfile lets
// `claude-dev orchestrate` detect a live controller and, if absent, (re)start it
// from state — the single-command recovery. The actual detachment (new session
// leader, no controlling terminal) is performed by the launcher (`claude-dev`
// via `setsid`); these helpers manage the pidfile and liveness probe.

// writePidfile records the current PID at path.
func writePidfile(path string) error {
	return os.WriteFile(path, []byte(strconv.Itoa(os.Getpid())+"\n"), 0o644)
}

// readPidfile returns the PID stored at path, or 0 if absent/invalid.
func readPidfile(path string) int {
	b, err := os.ReadFile(path)
	if err != nil {
		return 0
	}
	n, err := strconv.Atoi(strings.TrimSpace(string(b)))
	if err != nil || n <= 0 {
		return 0
	}
	return n
}

// processAlive reports whether pid names a live process (signal-0 probe).
func processAlive(pid int) bool {
	if pid <= 0 {
		return false
	}
	p, err := os.FindProcess(pid)
	if err != nil {
		return false
	}
	return p.Signal(syscall.Signal(0)) == nil
}

// controllerAlive reports whether a controller recorded at pidfile is running.
func controllerAlive(pidfile string) bool {
	return processAlive(readPidfile(pidfile))
}

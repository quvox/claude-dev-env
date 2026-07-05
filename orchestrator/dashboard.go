package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"
)

// dashboard.go holds the shared execution-mode dashboard STATE and small pure
// helpers. The interactive rendering + input is a bubbletea TUI in dashtui.go
// (docs/06 §5.3): the controller keeps updating DashboardState here; the TUI
// reads it to render, and cursor navigation lives in the model.

// vmHealthFreshSecs bounds how old a vm-healthd health file may be before the
// dashboard ignores it (the monitor writes every ~15s; see docs/impl/80 §7.2).
const vmHealthFreshSecs = 120

// readVMHealthBanner returns a one-line warning when the VM モード resource
// monitor (vm-healthd) reports sustained pressure, else "". Best-effort and
// read-only: any missing file / parse error / staleness yields "" (no banner).
func readVMHealthBanner() string {
	if os.Getenv("CLAUDE_DEV_VM") != "1" {
		return ""
	}
	home, err := os.UserHomeDir()
	if err != nil || home == "" {
		return ""
	}
	data, err := os.ReadFile(filepath.Join(home, ".claude-dev-vm", "health"))
	if err != nil {
		return ""
	}
	kv := map[string]string{}
	for _, ln := range strings.Split(string(data), "\n") {
		if i := strings.IndexByte(ln, '='); i > 0 {
			kv[ln[:i]] = ln[i+1:]
		}
	}
	if kv["STATE"] != "WARN" {
		return ""
	}
	ts, err := strconv.ParseInt(strings.TrimSpace(kv["TS"]), 10, 64)
	if err != nil || time.Now().Unix()-ts > vmHealthFreshSecs {
		return "" // stale or unparseable: monitor likely stopped
	}
	msg := kv["MSG"]
	if msg == "" {
		msg = fmt.Sprintf("VM資源逼迫の可能性（QEMU CPU %s%% / 上限 %s%%）。vm status を確認", kv["CPU"], kv["CEIL"])
	}
	return "⚠ " + oneline(msg, 100)
}

// DashboardState is a snapshot the controller publishes for the TUI to render.
type DashboardState struct {
	mu                sync.Mutex
	Goal              string
	Tasks             []DashTask
	LastSummary       string
	LastSummaryTS     string
	AssumptionsN      int
	InterventionsN    int
	InterventionsOpen int      // unresolved per-task interventions (open.json)
	OpenTitles        []string // task titles of open interventions (docs/06 §5.5)
	Paused            bool
}

// DashTask is a per-task row.
type DashTask struct {
	ID       string
	Title    string
	Vendor   string
	Status   string
	Attempts int
	Started  time.Time
}

// Set replaces the snapshot fields under lock.
func (d *DashboardState) Set(fn func(*DashboardState)) {
	d.mu.Lock()
	defer d.mu.Unlock()
	fn(d)
}

// selectableWorker returns the (task ID, status) of the n-th (1-indexed)
// selectable worker — those with a live tmux window (running/review/revise or
// waiting_human). Returns ("","") if n is out of range. Pure/testable.
func selectableWorker(tasks []DashTask, n int) (id, status string) {
	if n < 1 {
		return "", ""
	}
	i := 0
	for _, t := range tasks {
		switch t.Status {
		case TaskRunning, TaskReview, TaskRevise, TaskWaitingHuman:
			i++
			if i == n {
				return t.ID, t.Status
			}
		}
	}
	return "", ""
}

// selectableWorkerID is selectableWorker keeping only the ID.
func selectableWorkerID(tasks []DashTask, n int) string {
	id, _ := selectableWorker(tasks, n)
	return id
}

// SelectableWorker returns the task ID for selector index n under the state lock.
func (s *DashboardState) SelectableWorker(n int) string {
	s.mu.Lock()
	defer s.mu.Unlock()
	return selectableWorkerID(s.Tasks, n)
}

// SelectableWorkerStatus returns the (task ID, status) for selector index n
// under the state lock.
func (s *DashboardState) SelectableWorkerStatus(n int) (string, string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	return selectableWorker(s.Tasks, n)
}

// statusLabel maps an internal status to a short human label.
func statusLabel(status string) string {
	switch status {
	case TaskPending:
		return "待機中"
	case TaskRunning:
		return "実行中"
	case TaskReview:
		return "レビュー中"
	case TaskRevise:
		return "修正中"
	case TaskWaitingHuman:
		return "⏸ 要判断"
	case TaskDone:
		return "完了"
	case TaskFailed:
		return "失敗"
	case TaskBlocked:
		return "ブロック"
	default:
		return status
	}
}

// tailFile returns the last n non-empty lines of the file at path (best effort;
// empty string if the file is missing/unreadable/empty).
func tailFile(path string, n int) string {
	data, err := os.ReadFile(path)
	if err != nil || len(data) == 0 {
		return ""
	}
	lines := strings.Split(strings.TrimRight(string(data), "\n"), "\n")
	out := make([]string, 0, n)
	for i := len(lines) - 1; i >= 0 && len(out) < n; i-- {
		if strings.TrimSpace(lines[i]) == "" {
			continue
		}
		out = append([]string{lines[i]}, out...)
	}
	return strings.Join(out, "\n")
}

// oneline collapses whitespace and truncates s to max runes.
func oneline(s string, max int) string {
	s = strings.Join(strings.Fields(s), " ")
	if len([]rune(s)) > max {
		return string([]rune(s)[:max]) + "…"
	}
	return s
}

// formatDuration renders a short mm ss form.
func formatDuration(d time.Duration) string {
	d = d.Round(time.Second)
	m := int(d.Minutes())
	sec := int(d.Seconds()) % 60
	if m > 0 {
		return fmt.Sprintf("%dm%02ds", m, sec)
	}
	return fmt.Sprintf("%ds", sec)
}

package main

import (
	"bufio"
	"context"
	"fmt"
	"os"
	"strings"
	"sync"
	"time"
)

// DashboardState is a snapshot the controller publishes for rendering.
type DashboardState struct {
	mu             sync.Mutex
	Goal           string
	Tasks          []DashTask
	LastSummary    string
	LastSummaryTS  string
	AssumptionsN   int
	InterventionsN int
	Paused         bool
}

// DashTask is a per-task row.
type DashTask struct {
	ID      string
	Title   string
	Vendor  string
	Status  string
	Started time.Time
}

// KeyEvent is a dashboard key command emitted to the controller.
type KeyEvent int

const (
	KeyNone   KeyEvent = iota
	KeyDetail          // d
	KeyPause           // p
	KeyQuit            // q
)

// Set replaces the snapshot fields under lock.
func (d *DashboardState) Set(fn func(*DashboardState)) {
	d.mu.Lock()
	defer d.mu.Unlock()
	fn(d)
}

// Dashboard renders the execution-mode status screen with ANSI and reads keys.
// On non-TTY terminals it degrades gracefully: no ANSI drawing, no key reads.
type Dashboard struct {
	State *DashboardState
	Keys  chan KeyEvent
	tty   bool
}

// NewDashboard builds a dashboard. headless (non-TTY) is auto-detected.
func NewDashboard(st *DashboardState) *Dashboard {
	return &Dashboard{State: st, Keys: make(chan KeyEvent, 4), tty: isTTY()}
}

// Run renders periodically until ctx is cancelled. On a non-TTY it still loops
// (so the controller can run headless) but only prints occasional plain lines.
func (d *Dashboard) Run(ctx context.Context) {
	if d.tty {
		go d.readKeys(ctx)
	}
	ticker := time.NewTicker(1 * time.Second)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			if d.tty {
				d.render()
			}
		}
	}
}

// render draws the dashboard using ANSI escape codes.
func (d *Dashboard) render() {
	s := d.State
	s.mu.Lock()
	defer s.mu.Unlock()

	var b strings.Builder
	// Clear screen + home.
	b.WriteString("\x1b[2J\x1b[H")
	status := "● 実行中"
	if s.Paused {
		status = "⏸ 一時停止"
	}
	fmt.Fprintf(&b, "%s  goal: %s\n", status, oneline(s.Goal, 60))
	n := len(s.Tasks)
	done := 0
	for _, t := range s.Tasks {
		if t.Status == TaskDone {
			done++
		}
	}
	for i, t := range s.Tasks {
		elapsed := ""
		if !t.Started.IsZero() && (t.Status == TaskRunning || t.Status == TaskReview || t.Status == TaskRevise) {
			elapsed = formatDuration(time.Since(t.Started))
		}
		vendor := t.Vendor
		if vendor == "" {
			vendor = "claude"
		}
		fmt.Fprintf(&b, "[%d/%d] worker %s (%s): %s %s\n",
			i+1, n, oneline(t.Title, 28), vendor, t.Status, elapsed)
	}
	fmt.Fprintf(&b, "直近サマリ: %s", oneline(s.LastSummary, 50))
	if s.LastSummaryTS != "" {
		fmt.Fprintf(&b, " （Slack 送信済 %s）", s.LastSummaryTS)
	}
	b.WriteString("\n")
	fmt.Fprintf(&b, "仮定ログ %d / 介入 %d  （done %d/%d）\n",
		s.AssumptionsN, s.InterventionsN, done, n)
	b.WriteString("keys: [d]詳細 [p]一時停止 [q]中断\n")
	_, _ = os.Stdout.WriteString(b.String())
}

// readKeys reads single characters from stdin and emits KeyEvents. It is only
// started on a TTY. It is line-buffered (no raw mode) to keep stdlib-only and
// robust; the user presses the key + Enter.
func (d *Dashboard) readKeys(ctx context.Context) {
	r := bufio.NewReader(os.Stdin)
	for {
		select {
		case <-ctx.Done():
			return
		default:
		}
		line, err := r.ReadString('\n')
		if err != nil {
			return
		}
		switch strings.TrimSpace(line) {
		case "d":
			d.emit(KeyDetail)
		case "p":
			d.emit(KeyPause)
		case "q":
			d.emit(KeyQuit)
		}
	}
}

func (d *Dashboard) emit(k KeyEvent) {
	select {
	case d.Keys <- k:
	default:
	}
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
	s := int(d.Seconds()) % 60
	if m > 0 {
		return fmt.Sprintf("%dm%02ds", m, s)
	}
	return fmt.Sprintf("%ds", s)
}

package main

import (
	"context"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"
)

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

// DashboardState is a snapshot the controller publishes for rendering.
type DashboardState struct {
	mu                sync.Mutex
	Goal              string
	Tasks             []DashTask
	LastSummary       string
	LastSummaryTS     string
	AssumptionsN      int
	InterventionsN    int
	InterventionsOpen int      // unresolved per-task interventions (open.json)
	OpenTitles        []string // task titles of open interventions (for the list; docs/06 §5.5)
	Paused            bool
	Detail            bool // when true, render live worker output tails ([d] toggles)
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

// KeyEvent is a dashboard key command emitted to the controller.
type KeyEvent int

const (
	KeyNone      KeyEvent = iota
	KeyDetail             // d
	KeyPause              // p
	KeyQuit               // q
	KeyIntervene          // i
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
	State    *DashboardState
	Keys     chan KeyEvent
	Resolve  chan string     // taskID of a ⏸ worker selected by number key → controller opens in-session intervene (独立ウィンドウ方式・docs/06 §5.3/§6.3)
	Store    *Store          // for reading live worker logs in detail view
	Sessions *SessionManager // worker セレクタ: 数字キーで当該 worker セッションへ切替（独立ウィンドウ方式・docs/06 §5.3）。nil 可
	tty      bool
}

// NewDashboard builds a dashboard. headless (non-TTY) is auto-detected.
func NewDashboard(st *DashboardState, store *Store, sessions *SessionManager) *Dashboard {
	return &Dashboard{State: st, Keys: make(chan KeyEvent, 4), Resolve: make(chan string, 4), Store: store, Sessions: sessions, tty: isTTY()}
}

// selectableWorker returns the (task ID, status) of the n-th (1-indexed)
// selectable worker — those with a live tmux session (running/review/revise or
// waiting_human). Returns ("","") if n is out of range. Pure/testable (docs/06
// §5.3). The status lets the caller route ⏸ (waiting_human) to an in-session
// intervene vs a plain view switch.
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

// selectableWorkerID is selectableWorker keeping only the ID (kept for existing
// callers/tests).
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
	_, _ = os.Stdout.WriteString(d.renderString())
}

// renderString builds the full dashboard frame as a string (extracted from
// render so the layout — notably the selector-number column, docs/06 §5.3 — is
// unit-testable without a TTY). It takes the state lock itself.
func (d *Dashboard) renderString() string {
	s := d.State
	s.mu.Lock()
	defer s.mu.Unlock()

	var b strings.Builder
	// Clear screen + home.
	b.WriteString("\x1b[2J\x1b[H")
	// VM モード時のみ: vm-healthd の資源逼迫警告を最上部に赤バナー表示（読取専用・
	// ベストエフォート。docs/impl/80_vm-mode.md §7.2 / 60_orchestrator.md）。
	if banner := readVMHealthBanner(); banner != "" {
		fmt.Fprintf(&b, "\x1b[1;31m%s\x1b[0m\n", banner)
	}
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
	running := make([]DashTask, 0, len(s.Tasks))
	sel := 0 // selector counter: only selectable workers, 1-indexed (matches selectableWorkerID / docs/06 §5.3)
	for i, t := range s.Tasks {
		elapsed := ""
		active := t.Status == TaskRunning || t.Status == TaskReview || t.Status == TaskRevise
		if active && !t.Started.IsZero() {
			elapsed = formatDuration(time.Since(t.Started))
		}
		if active {
			running = append(running, t)
		}
		// A worker is selectable (has a live session to switch to) when it is
		// active or ⏸ waiting_human — the same set as selectableWorkerID. Its
		// selector number is a SEPARATE column from the task ordinal [i/n]
		// (which counts all tasks incl. pending/done), so the two intentionally
		// differ; showing the selector number prevents pressing the wrong key.
		selTag := "   " // 3 cols, keeps non-selectable rows aligned with ‹k›
		if active || t.Status == TaskWaitingHuman {
			sel++
			selTag = fmt.Sprintf("‹%d›", sel)
		}
		vendor := t.Vendor
		if vendor == "" {
			vendor = "claude"
		}
		att := ""
		if t.Attempts > 1 {
			att = fmt.Sprintf(" (試行%d)", t.Attempts)
		}
		fmt.Fprintf(&b, "%s [%d/%d] worker %s (%s): %s %s%s\n",
			selTag, i+1, n, oneline(t.Title, 28), vendor, statusLabel(t.Status), elapsed, att)
	}
	fmt.Fprintf(&b, "直近サマリ: %s", oneline(s.LastSummary, 50))
	if s.LastSummaryTS != "" {
		fmt.Fprintf(&b, " （Slack 送信済 %s）", s.LastSummaryTS)
	}
	b.WriteString("\n")
	fmt.Fprintf(&b, "仮定ログ %d / 要判断 %d 件  （done %d/%d, 実行中 %d）\n",
		s.AssumptionsN, s.InterventionsOpen, done, n, len(running))
	if len(s.OpenTitles) > 0 {
		items := make([]string, len(s.OpenTitles))
		for i, t := range s.OpenTitles {
			items[i] = fmt.Sprintf("(%d) %s", i+1, oneline(t, 36))
		}
		fmt.Fprintf(&b, "  要判断: %s ← [i]で対応\n", strings.Join(items, " / "))
	}
	ihint := ""
	if s.InterventionsOpen > 0 {
		ihint = " [i]介入対応"
	}
	// worker セレクタ案内（独立ウィンドウ方式・06 §5.3）：切替先セッションを持つ
	// worker が居て、かつ Sessions 注入時（tmux 有り）のみ数字キーを案内する。
	whint := ""
	if sel > 0 && d.Sessions != nil {
		whint = " [1-9]worker画面へ"
	}
	if s.Detail {
		d.renderDetail(&b, running)
		fmt.Fprintf(&b, "keys: [d]一覧に戻る [p]一時停止%s%s [q]中断(状態を保存し再開可)\n", whint, ihint)
	} else {
		fmt.Fprintf(&b, "keys: [d]worker出力を見る [p]一時停止%s%s [q]中断(状態を保存し再開可)\n", whint, ihint)
	}
	return b.String()
}

// renderDetail appends the tail of each running worker's live output log so the
// human can see what the workers are actually doing.
func (d *Dashboard) renderDetail(b *strings.Builder, running []DashTask) {
	b.WriteString("──── worker 出力（末尾） ────\n")
	if len(running) == 0 {
		b.WriteString("（実行中の worker はありません）\n")
		return
	}
	if d.Store == nil {
		b.WriteString("（ログを参照できません）\n")
		return
	}
	// Budget the visible lines across running workers so the screen stays stable.
	per := 8
	if len(running) > 2 {
		per = 4
	}
	for _, t := range running {
		fmt.Fprintf(b, "▸ %s [%s]\n", oneline(t.Title, 40), t.ID)
		tail := tailFile(d.Store.WorkerLogPath(t.ID), per)
		if tail == "" {
			b.WriteString("  …まだ出力がありません（起動直後/思考中）\n")
			continue
		}
		for _, ln := range strings.Split(tail, "\n") {
			fmt.Fprintf(b, "  %s\n", oneline(ln, 110))
		}
	}
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

// readKeys reads single keypresses from stdin and emits KeyEvents. It is only
// started on a TTY. It owns terminal mode for its lifetime: it switches the TTY
// into a non-canonical, no-echo mode (rawKeyMode) so a key registers the moment
// it is pressed — no Enter required — and restores a sane canonical state on
// exit. This is essential because the interactive `claude` child leaves the
// shared TTY in raw mode; a line-buffered reader here would wait forever for a
// "\n" that raw-mode Enter never sends. The VMIN=0/VTIME=1 timeout makes idle
// reads return (0, io.EOF) every ~0.1s, so context cancellation is honoured
// promptly and no goroutine is left blocked on stdin across phases.
func (d *Dashboard) readKeys(ctx context.Context) {
	restore, ok := rawKeyMode()
	if !ok {
		// Could not enter raw mode (no stty / not a TTY): fall back to leaving
		// the terminal canonical. Without a per-key read we cannot reliably
		// process keys, so just honour cancellation and return.
		<-ctx.Done()
		return
	}
	defer restore()

	buf := make([]byte, 1)
	for {
		select {
		case <-ctx.Done():
			return
		default:
		}
		n, err := os.Stdin.Read(buf)
		if n == 0 {
			// VTIME timeout surfaces as (0, io.EOF) on a quiet terminal; loop so
			// we re-check ctx. A genuine, non-EOF error means stdin is gone.
			if err != nil && err != io.EOF {
				return
			}
			continue
		}
		switch buf[0] {
		case 'd':
			d.emit(KeyDetail)
		case 'p':
			d.emit(KeyPause)
		case 'i':
			d.emit(KeyIntervene)
		case 'q':
			d.emit(KeyQuit)
		default:
			// worker セレクタ（独立ウィンドウ方式・docs/06 §5.3/§6.3）：数字キーで
			// n 番目の worker を選ぶ。⏸（waiting_human）なら Resolve へ流してコント
			// ローラがそのセッションで介入対話を起こす。実行中等はビュー切替のみ。
			// best-effort（nil/tmux 無しは無視）。
			if d.Sessions != nil && buf[0] >= '1' && buf[0] <= '9' {
				if id, status := d.State.SelectableWorkerStatus(int(buf[0] - '0')); id != "" {
					if status == TaskWaitingHuman {
						select {
						case d.Resolve <- id:
						default:
						}
					} else {
						_ = d.Sessions.SwitchTo(context.Background(), d.Sessions.WorkerWindow(id))
					}
				}
			}
		}
	}
}

func (d *Dashboard) emit(k KeyEvent) {
	select {
	case d.Keys <- k:
	default:
	}
}

// tailFile returns the last n non-empty lines of the file at path (best effort;
// empty string if the file is missing/unreadable/empty). It reads the whole
// file, which is fine for the modest worker logs shown here.
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
	s := int(d.Seconds()) % 60
	if m > 0 {
		return fmt.Sprintf("%dm%02ds", m, s)
	}
	return fmt.Sprintf("%ds", s)
}

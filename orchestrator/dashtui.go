package main

import (
	"context"
	"fmt"
	"strings"
	"time"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// dashtui.go — the execution-mode dashboard as a proper cursor-select TUI
// (bubbletea), replacing the old "clear-screen + full reprint every 1s" render
// (docs/06 §5.3). Key properties the human asked for:
//   - Never auto-moves the tmux window. The cursor (↑↓/jk) selects a target and
//     ONLY Enter navigates there (select-window; ⏸ → in-window intervene).
//   - Event-driven diff rendering (bubbletea), not a periodic full clear.
// The dashboard runs on the `dashboard` window's own PTY, independent of the
// claude instances in the brainstorming/worker windows (separate panes), so there
// is no TTY conflict — the program keeps running while the human is switched to
// another window.

// dashAction is a user action that only the controller can carry out (opening an
// intervention, quitting the run). Cursor movement, the [d] detail toggle and
// [p] pause are handled locally / via shared state and do not go here.
type dashAction struct {
	kind   string // "resolve" | "intervene" | "quit"
	taskID string // for "resolve": the ⏸ worker to open
}

type dashTickMsg struct{}

func dashTick() tea.Cmd {
	return tea.Tick(time.Second, func(time.Time) tea.Msg { return dashTickMsg{} })
}

// selRow is one navigable (selectable) worker row.
type selRow struct {
	id     string
	status string
}

// dashModel is the bubbletea model. It holds pointers to the shared state the
// controller updates (st), so View reflects live progress on each tick.
type dashModel struct {
	st       *DashboardState
	store    *Store
	sessions *SessionManager
	actions  chan dashAction
	cursor   int
	detail   bool
}

func newDashProgram(ctx context.Context, st *DashboardState, store *Store, sessions *SessionManager, actions chan dashAction) *tea.Program {
	m := dashModel{st: st, store: store, sessions: sessions, actions: actions}
	return tea.NewProgram(m, tea.WithAltScreen(), tea.WithContext(ctx))
}

func (m dashModel) Init() tea.Cmd { return dashTick() }

// selectable returns the navigable rows under the state lock. In brainstorming
// it is a single row (the brainstorming window) so navigation is the SAME
// cursor-select gesture as executing (no raw `Ctrl-_ w`). In executing it is the
// active worker rows (running/review/revise or ⏸ waiting_human).
func (m dashModel) selectable() []selRow {
	m.st.mu.Lock()
	defer m.st.mu.Unlock()
	if m.st.Phase == PhaseBrainstorming {
		return []selRow{{status: PhaseBrainstorming}}
	}
	var rows []selRow
	for _, t := range m.st.Tasks {
		switch t.Status {
		case TaskRunning, TaskReview, TaskRevise, TaskWaitingHuman:
			rows = append(rows, selRow{id: t.ID, status: t.Status})
		}
	}
	return rows
}

func (m dashModel) send(a dashAction) {
	select {
	case m.actions <- a:
	default:
	}
}

func (m dashModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case dashTickMsg:
		return m, dashTick()
	case tea.KeyMsg:
		rows := m.selectable()
		switch msg.String() {
		case "up", "k":
			if m.cursor > 0 {
				m.cursor--
			}
		case "down", "j":
			if m.cursor < len(rows)-1 {
				m.cursor++
			}
		case "enter":
			if m.cursor >= 0 && m.cursor < len(rows) {
				r := rows[m.cursor]
				switch {
				case r.status == TaskWaitingHuman:
					m.send(dashAction{kind: "resolve", taskID: r.id}) // in-window intervene (no tmux needed)
				case m.sessions == nil:
					// no tmux: cannot switch the view
				case r.status == PhaseBrainstorming:
					_ = m.sessions.SwitchTo(context.Background(), m.sessions.BrainstormingWindow())
				default:
					_ = m.sessions.SwitchTo(context.Background(), m.sessions.WorkerWindow(r.id)) // view only
				}
			}
		case "p":
			m.st.Set(func(s *DashboardState) { s.Paused = !s.Paused })
		case "d":
			m.detail = !m.detail
		case "i":
			m.send(dashAction{kind: "intervene"})
		case "q", "ctrl+c":
			m.send(dashAction{kind: "quit"})
			return m, tea.Quit
		}
		if m.cursor >= len(rows) { // keep cursor in range as workers settle/close
			m.cursor = len(rows) - 1
		}
		if m.cursor < 0 {
			m.cursor = 0
		}
		return m, nil
	}
	return m, nil
}

var (
	dashCursorStyle = lipgloss.NewStyle().Bold(true).Reverse(true)
	dashHeadStyle   = lipgloss.NewStyle().Bold(true)
	dashHintStyle   = lipgloss.NewStyle().Faint(true)
)

func (m dashModel) View() string {
	s := m.st
	s.mu.Lock()
	defer s.mu.Unlock()

	// Brainstorming home: the SAME cursor-select TUI, with the brainstorming
	// window as the single navigable target (Enter で移動). No raw `Ctrl-_ w`.
	if s.Phase == PhaseBrainstorming {
		goal := oneline(s.Goal, 56)
		if strings.TrimSpace(goal) == "" {
			goal = "（未確定 — ブレインストーミングで決めます）"
		}
		var b strings.Builder
		b.WriteString(dashHeadStyle.Render("● ブレインストーミング中（ダッシュボード＝ホーム）"))
		b.WriteByte('\n')
		fmt.Fprintf(&b, "goal: %s\n\n", goal)
		item := "brainstorming ウィンドウで AI と対話する"
		if m.cursor == 0 {
			b.WriteString(dashCursorStyle.Render("❯ " + item))
		} else {
			b.WriteString("  " + item)
		}
		b.WriteString("\n\n")
		// NOTE: keep the newline OUTSIDE lipgloss.Render — a `\n` inside a styled
		// segment spans the style across the line break and bubbletea's line-diff
		// then staircases the following lines. Style each line's text only.
		b.WriteString(dashHintStyle.Render("Enter でそのウィンドウへ移動 → AI と検討して plan を固める"))
		b.WriteByte('\n')
		b.WriteString(dashHintStyle.Render("対話で /exit すると：実行可能なら実行モードへ／未確定ならここで 続ける・終了 を選ぶ"))
		b.WriteByte('\n')
		b.WriteString(dashHintStyle.Render("↑↓/jk 選択 · Enter 移動"))
		return b.String()
	}

	var b strings.Builder
	if banner := readVMHealthBanner(); banner != "" {
		b.WriteString(lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("1")).Render(banner))
		b.WriteByte('\n')
	}
	status := "● 実行中"
	if s.Paused {
		status = "⏸ 一時停止"
	}
	b.WriteString(dashHeadStyle.Render(fmt.Sprintf("%s  goal: %s", status, oneline(s.Goal, 60))))
	b.WriteByte('\n')

	n := len(s.Tasks)
	done, running := 0, 0
	sel := -1 // selectable index as we walk
	for i := range s.Tasks {
		t := &s.Tasks[i]
		if t.Status == TaskDone {
			done++
		}
		active := t.Status == TaskRunning || t.Status == TaskReview || t.Status == TaskRevise
		if active {
			running++
		}
		selectable := active || t.Status == TaskWaitingHuman
		vendor := t.Vendor
		if vendor == "" {
			vendor = "claude"
		}
		elapsed := ""
		if active && !t.Started.IsZero() {
			elapsed = " " + formatDuration(time.Since(t.Started))
		}
		att := ""
		if t.Attempts > 1 {
			att = fmt.Sprintf(" (試行%d)", t.Attempts)
		}
		line := fmt.Sprintf("[%d/%d] worker %s (%s): %s%s%s",
			i+1, n, oneline(t.Title, 28), vendor, statusLabel(t.Status), elapsed, att)
		cursorHere := false
		if selectable {
			sel++
			if sel == m.cursor {
				cursorHere = true
			}
		}
		if cursorHere {
			b.WriteString(dashCursorStyle.Render("❯ " + line))
		} else {
			b.WriteString("  " + line)
		}
		b.WriteByte('\n')
	}

	fmt.Fprintf(&b, "直近サマリ: %s", oneline(s.LastSummary, 50))
	if s.LastSummaryTS != "" {
		fmt.Fprintf(&b, " （Slack 送信済 %s）", s.LastSummaryTS)
	}
	b.WriteByte('\n')
	fmt.Fprintf(&b, "仮定ログ %d / 要判断 %d 件  （done %d/%d, 実行中 %d）\n",
		s.AssumptionsN, s.InterventionsOpen, done, n, running)
	if len(s.OpenTitles) > 0 {
		items := make([]string, len(s.OpenTitles))
		for i, t := range s.OpenTitles {
			items[i] = fmt.Sprintf("(%d) %s", i+1, oneline(t, 36))
		}
		fmt.Fprintf(&b, "  要判断: %s ← [i]で対応\n", strings.Join(items, " / "))
	}

	if m.detail {
		b.WriteString(detailTails(m.store, s.Tasks))
	}

	ihint := ""
	if s.InterventionsOpen > 0 {
		ihint = " · i 介入"
	}
	detailHint := "d 出力表示"
	if m.detail {
		detailHint = "d 出力隠す"
	}
	b.WriteString(dashHintStyle.Render(fmt.Sprintf("↑↓/jk 選択 · Enter 移動 · %s · p 一時停止%s · q 中断", detailHint, ihint)))
	return b.String()
}

// detailTails renders the tail of each active worker's live log for the [d]
// detail view (moved out of the old renderDetail so the TUI can embed it).
func detailTails(store *Store, tasks []DashTask) string {
	var running []DashTask
	for _, t := range tasks {
		if t.Status == TaskRunning || t.Status == TaskReview || t.Status == TaskRevise {
			running = append(running, t)
		}
	}
	var b strings.Builder
	b.WriteString("──── worker 出力（末尾） ────\n")
	if len(running) == 0 {
		b.WriteString("（実行中の worker はありません）\n")
		return b.String()
	}
	if store == nil {
		b.WriteString("（ログを参照できません）\n")
		return b.String()
	}
	per := 8
	if len(running) > 2 {
		per = 4
	}
	for _, t := range running {
		fmt.Fprintf(&b, "▸ %s [%s]\n", oneline(t.Title, 40), t.ID)
		tail := tailFile(store.WorkerLogPath(t.ID), per)
		if tail == "" {
			b.WriteString("  …まだ出力がありません（起動直後/思考中）\n")
			continue
		}
		for _, ln := range strings.Split(tail, "\n") {
			fmt.Fprintf(&b, "  %s\n", oneline(ln, 110))
		}
	}
	return b.String()
}

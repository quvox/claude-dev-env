package main

import (
	"fmt"
	"io"
	"os"
	"os/exec"
	"strings"
)

// Terminal-mode handling.
//
// The interactive `claude` child (brainstorming/intervene) is a full-screen TUI
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

// printModeBanner prints a one-line labeled banner to stderr just before a mode
// change so the human always knows the current mode and how to leave it (docs/06
// §5.4). Printed just before launching the interactive claude (which occupies
// the alternate screen); it re-appears in scrollback after /exit. Japanese
// (docs/06 §5.7). The 終了メニュー is self-describing via selectMenu, so it has no
// banner here.
func printModeBanner(mode string) {
	var msg string
	switch mode {
	case "brainstorming":
		msg = "▶ ブレインストーミングモード：要件と plan を固め、済んだら /exit（Ctrl-D）で実行へ移ります"
	case "intervene":
		msg = "▶ 介入モード：要判断に回答し、済んだら /exit（Ctrl-D）でダッシュボードへ戻ります"
	case "executing":
		msg = "▶ 実行モード（ダッシュボード）"
	default:
		return
	}
	fmt.Fprintf(os.Stderr, "\n\x1b[1;36m%s\x1b[0m\n", msg)
}

// printBrainstormingHome renders a COMPLETE status screen in the dashboard
// window while brainstorming runs in its own window (独立ウィンドウ方式・docs/06
// §4.2). The controller then blocks in WaitConsume, so without this the dashboard
// window would show only a stray banner and look "stuck mid-render". This gives
// the human a finished screen that (a) confirms the dashboard is the home window
// and (b) tells them how to reach the brainstorming conversation. Japanese
// (docs/06 §5.7). Best-effort: no-op on a non-TTY.
func printBrainstormingHome(goal string) {
	if !isTTY() {
		return
	}
	if strings.TrimSpace(goal) == "" {
		goal = "（未確定 — ブレインストーミングで決めます）"
	}
	var b strings.Builder
	b.WriteString("\x1b[2J\x1b[H") // clear + home: a complete, stable screen
	b.WriteString("\x1b[1;36m● ブレインストーミング中（ダッシュボード）\x1b[0m\n")
	fmt.Fprintf(&b, "goal: %s\n\n", oneline(goal, 72))
	b.WriteString("対話は \x1b[1mbrainstorming\x1b[0m ウィンドウで行います。\n")
	b.WriteString("  移動: \x1b[1mCtrl-b → w\x1b[0m でウィンドウ一覧 → brainstorming を選択\n")
	b.WriteString("        （または \x1b[1mCtrl-b → 数字\x1b[0m でウィンドウ番号指定）\n\n")
	b.WriteString("AI と検討して plan を固め、対話で \x1b[1m/exit\x1b[0m すると：\n")
	b.WriteString("  ・plan が実行可能なら → 実行（ダッシュボード）へ自動遷移\n")
	b.WriteString("  ・未確定なら → ここで 続ける / 終了 を選ぶメニューを表示\n\n")
	b.WriteString("\x1b[2mこのウィンドウ（dashboard）が常にホームです。\x1b[0m\n")
	fmt.Fprint(os.Stdout, b.String())
}

// menuItem is one selectable option in selectMenu.
type menuItem struct {
	Value string // returned when chosen
	Label string // short human label (e.g. "1. 続ける")
	Desc  string // one-line explanation
}

// selectMenu presents an arrow/number selectable menu (↑/↓ or j/k to move, Enter
// to confirm, number keys 1..9 to pick immediately) with a one-line description
// per item, and returns the chosen item's Value. On a non-TTY (or if raw mode is
// unavailable) it returns the default item's Value without prompting (never
// auto-advances). Japanese labels (docs/06 §5.6/§5.7). Key semantics mirror
// resolveMenu (which is unit-tested).
func selectMenu(title string, items []menuItem, def int) string {
	if len(items) == 0 {
		return ""
	}
	if def < 0 || def >= len(items) {
		def = 0
	}
	if !isTTY() {
		return items[def].Value
	}
	restore, ok := rawKeyMode()
	if !ok {
		return items[def].Value
	}
	defer restore()

	sel := def
	draw := func(first bool) {
		var b strings.Builder
		if !first {
			fmt.Fprintf(&b, "\x1b[%dA", len(items)+2) // move to top of the block
		}
		fmt.Fprintf(&b, "\r\x1b[J%s\n", title)
		for i, it := range items {
			label := it.Label
			if label == "" {
				label = it.Value
			}
			if i == sel {
				fmt.Fprintf(&b, "  \x1b[1;36m❯ %s\x1b[0m — %s\n", label, it.Desc)
			} else {
				fmt.Fprintf(&b, "    %s — \x1b[2m%s\x1b[0m\n", label, it.Desc)
			}
		}
		b.WriteString("\x1b[2m  ↑/↓ で選択・番号キーで即決定・Enter で決定\x1b[0m\n")
		fmt.Fprint(os.Stdout, b.String())
	}
	draw(true)

	buf := make([]byte, 1)
	for {
		n, err := os.Stdin.Read(buf)
		if n == 0 {
			if err != nil && err != io.EOF {
				return items[sel].Value
			}
			continue
		}
		switch buf[0] {
		case 0x1b: // ESC: possible arrow sequence ESC '[' 'A'/'B'
			seq := make([]byte, 2)
			m, _ := os.Stdin.Read(seq)
			var code byte
			if m >= 2 && seq[0] == '[' {
				code = seq[1]
			} else if m == 1 && seq[0] == '[' {
				one := make([]byte, 1)
				if k, _ := os.Stdin.Read(one); k == 1 {
					code = one[0]
				}
			}
			if code == 'A' {
				sel = (sel - 1 + len(items)) % len(items)
				draw(false)
			} else if code == 'B' {
				sel = (sel + 1) % len(items)
				draw(false)
			}
		case 'k':
			sel = (sel - 1 + len(items)) % len(items)
			draw(false)
		case 'j':
			sel = (sel + 1) % len(items)
			draw(false)
		case '\r', '\n':
			fmt.Fprintln(os.Stdout)
			return items[sel].Value
		default:
			if buf[0] >= '1' && buf[0] <= '9' {
				if idx := int(buf[0] - '1'); idx < len(items) {
					fmt.Fprintln(os.Stdout)
					return items[idx].Value
				}
			}
		}
	}
}

// resolveMenu is the pure, unit-testable twin of selectMenu's key handling: it
// replays a byte stream of keypresses over items (starting at def) and returns
// the chosen Value. Recognizes arrow up/down (ESC '[' 'A'/'B'), j/k, digit 1..n
// (immediate confirm), and Enter (\r/\n) confirm. If the input exhausts with no
// confirm, returns the currently-selected Value.
func resolveMenu(items []menuItem, def int, in []byte) string {
	if len(items) == 0 {
		return ""
	}
	sel := def
	if sel < 0 || sel >= len(items) {
		sel = 0
	}
	for i := 0; i < len(in); i++ {
		b := in[i]
		switch {
		case b == 0x1b && i+2 < len(in) && in[i+1] == '[':
			switch in[i+2] {
			case 'A':
				sel = (sel - 1 + len(items)) % len(items)
			case 'B':
				sel = (sel + 1) % len(items)
			}
			i += 2
		case b == 'k':
			sel = (sel - 1 + len(items)) % len(items)
		case b == 'j':
			sel = (sel + 1) % len(items)
		case b == '\r' || b == '\n':
			return items[sel].Value
		default:
			if b >= '1' && b <= '9' {
				if idx := int(b - '1'); idx < len(items) {
					return items[idx].Value
				}
			}
		}
	}
	return items[sel].Value
}

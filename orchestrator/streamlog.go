package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"strings"
)

// streamlog.go renders a worker's `claude -p --output-format stream-json` output
// into a human-readable, Claude-Code-like log for display. The RAW stream-json is
// kept elsewhere (an in-memory buffer) for result parsing; this rendering is what
// the worker window's `tail -F` and the dashboard [d] detail view show, so a human
// can follow what the worker is doing instead of staring at JSON (docs/impl/60
// §worker ディスパッチ step3).

// streamPrettyWriter is an io.Writer that receives stream-json bytes, splits them
// on newlines, and writes a formatted rendering of each complete event line to the
// wrapped writer (the log file). Partial trailing bytes are buffered until the
// newline arrives. It never fails the Write (returns len(p)) so it is safe as one
// leg of an io.MultiWriter.
type streamPrettyWriter struct {
	out io.Writer
	buf []byte
}

func newStreamPrettyWriter(out io.Writer) *streamPrettyWriter {
	return &streamPrettyWriter{out: out}
}

func (w *streamPrettyWriter) Write(p []byte) (int, error) {
	w.buf = append(w.buf, p...)
	for {
		i := bytes.IndexByte(w.buf, '\n')
		if i < 0 {
			break
		}
		line := w.buf[:i]
		w.buf = append([]byte(nil), w.buf[i+1:]...)
		if s := formatStreamLine(line); s != "" {
			_, _ = io.WriteString(w.out, s)
			if !strings.HasSuffix(s, "\n") {
				_, _ = io.WriteString(w.out, "\n")
			}
		}
	}
	return len(p), nil
}

// streamEvent is the outer shape of a stream-json line.
type streamEvent struct {
	Type    string          `json:"type"`
	Subtype string          `json:"subtype"`
	Model   string          `json:"model"`
	Message json.RawMessage `json:"message"`
	Result  string          `json:"result"`
	IsError bool            `json:"is_error"`
}

type streamMessage struct {
	Model   string          `json:"model"`
	Content json.RawMessage `json:"content"` // string OR []contentBlock
}

type contentBlock struct {
	Type      string          `json:"type"`
	Text      string          `json:"text"`
	Name      string          `json:"name"`
	Input     json.RawMessage `json:"input"`
	Content   json.RawMessage `json:"content"` // for tool_result: string OR []contentBlock
	ToolUseID string          `json:"tool_use_id"`
}

// formatStreamLine converts one stream-json event line into a readable rendering
// (possibly multi-line, no trailing newline required). Returns "" for events that
// carry no useful human signal. A line that is not valid JSON is passed through
// verbatim so nothing is silently lost.
func formatStreamLine(line []byte) string {
	trimmed := bytes.TrimSpace(line)
	if len(trimmed) == 0 {
		return ""
	}
	var ev streamEvent
	if err := json.Unmarshal(trimmed, &ev); err != nil {
		return string(trimmed) // not JSON: show as-is
	}
	switch ev.Type {
	case "system":
		if ev.Subtype == "init" {
			m := ev.Model
			if m == "" {
				var msg streamMessage
				_ = json.Unmarshal(ev.Message, &msg)
				m = msg.Model
			}
			if m != "" {
				return dim(fmt.Sprintf("⏺ worker 起動（model: %s）", m))
			}
			return dim("⏺ worker 起動")
		}
		return ""
	case "assistant":
		return formatContent(ev.Message)
	case "user":
		return formatContent(ev.Message) // tool_result blocks
	case "result":
		if ev.IsError {
			return dim("──── worker 終了（エラー） ────")
		}
		return dim("──── worker 完了 ────")
	default:
		return ""
	}
}

// formatContent renders an assistant/user message's content blocks.
func formatContent(raw json.RawMessage) string {
	if len(raw) == 0 {
		return ""
	}
	var msg streamMessage
	if err := json.Unmarshal(raw, &msg); err != nil {
		return ""
	}
	// content may be a bare string (rare) or an array of blocks.
	var blocks []contentBlock
	if err := json.Unmarshal(msg.Content, &blocks); err != nil {
		var s string
		if json.Unmarshal(msg.Content, &s) == nil && strings.TrimSpace(s) != "" {
			return strings.TrimRight(s, "\n")
		}
		return ""
	}
	var lines []string
	for _, b := range blocks {
		switch b.Type {
		case "text":
			if t := strings.TrimRight(b.Text, "\n"); strings.TrimSpace(t) != "" {
				lines = append(lines, t)
			}
		case "tool_use":
			lines = append(lines, fmt.Sprintf("⏺ %s(%s)", b.Name, summarizeToolInput(b.Name, b.Input)))
		case "tool_result":
			lines = append(lines, formatToolResult(b.Content))
		}
	}
	return strings.Join(lines, "\n")
}

// formatToolResult renders a tool_result's content as a compact "  ⎿ …" line.
func formatToolResult(raw json.RawMessage) string {
	text := extractText(raw)
	text = strings.TrimRight(text, "\n")
	if strings.TrimSpace(text) == "" {
		return dim("  ⎿ (出力なし)")
	}
	all := strings.Split(text, "\n")
	first := oneline(all[0], 100)
	if len(all) > 1 {
		return dim(fmt.Sprintf("  ⎿ %s … (%d 行)", first, len(all)))
	}
	return dim("  ⎿ " + first)
}

// extractText pulls plain text out of a content field that is either a string or
// an array of {type:"text", text:"…"} blocks.
func extractText(raw json.RawMessage) string {
	if len(raw) == 0 {
		return ""
	}
	var s string
	if json.Unmarshal(raw, &s) == nil {
		return s
	}
	var blocks []contentBlock
	if json.Unmarshal(raw, &blocks) == nil {
		var parts []string
		for _, b := range blocks {
			if b.Text != "" {
				parts = append(parts, b.Text)
			}
		}
		return strings.Join(parts, "\n")
	}
	return ""
}

// summarizeToolInput picks the most meaningful field of a tool's input to show,
// mirroring how Claude Code labels a tool call (e.g. Bash by its command, file
// tools by their path). Falls back to a short JSON rendering.
func summarizeToolInput(name string, raw json.RawMessage) string {
	if len(raw) == 0 {
		return ""
	}
	var m map[string]any
	if err := json.Unmarshal(raw, &m); err != nil {
		return ""
	}
	pick := func(keys ...string) string {
		for _, k := range keys {
			if v, ok := m[k]; ok {
				if s, ok := v.(string); ok && strings.TrimSpace(s) != "" {
					return s
				}
			}
		}
		return ""
	}
	var val string
	switch name {
	case "Bash":
		val = pick("command")
	case "Read", "Write", "Edit", "NotebookEdit":
		val = pick("file_path", "notebook_path")
	case "Grep", "Glob":
		val = pick("pattern")
	case "Task", "Agent":
		val = pick("description", "prompt")
	case "WebFetch":
		val = pick("url")
	case "WebSearch":
		val = pick("query")
	default:
		val = pick("file_path", "command", "pattern", "path", "query", "url", "description")
		if val == "" {
			// compact JSON of the whole input as a last resort
			if compact, err := json.Marshal(m); err == nil {
				val = string(compact)
			}
		}
	}
	return oneline(val, 100)
}

// dim wraps s in faint ANSI so tool results/metadata read as secondary, matching
// the dashboard's muted style. Kept simple (no lipgloss) since this writes to a
// plain log file that tmux/terminals render directly.
func dim(s string) string { return "\x1b[2m" + s + "\x1b[0m" }

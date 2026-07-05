package main

import (
	"strings"
	"testing"
)

func TestFormatStreamLine(t *testing.T) {
	cases := []struct {
		name string
		line string
		want []string // substrings that must appear; "" entry means expect empty output
	}{
		{
			name: "assistant text",
			line: `{"type":"assistant","message":{"content":[{"type":"text","text":"実装を始めます。"}]}}`,
			want: []string{"実装を始めます。"},
		},
		{
			name: "tool_use bash",
			line: `{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Bash","input":{"command":"go test ./...","description":"run tests"}}]}}`,
			want: []string{"⏺ Bash(", "go test ./..."},
		},
		{
			name: "tool_use write shows path",
			line: `{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Write","input":{"file_path":"/workspace/main.go","content":"package main"}}]}}`,
			want: []string{"⏺ Write(", "/workspace/main.go"},
		},
		{
			name: "tool_result truncates",
			line: `{"type":"user","message":{"content":[{"type":"tool_result","content":[{"type":"text","text":"line1\nline2\nline3"}]}]}}`,
			want: []string{"⎿", "line1", "3 行"},
		},
		{
			name: "system init shows model",
			line: `{"type":"system","subtype":"init","model":"claude-sonnet-5"}`,
			want: []string{"起動", "claude-sonnet-5"},
		},
		{
			name: "result done",
			line: `{"type":"result","subtype":"success","is_error":false,"result":"{\"status\":\"ok\"}"}`,
			want: []string{"完了"},
		},
		{
			name: "non-json passthrough",
			line: `oops not json`,
			want: []string{"oops not json"},
		},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			got := formatStreamLine([]byte(c.line))
			for _, w := range c.want {
				if !strings.Contains(got, w) {
					t.Fatalf("formatStreamLine(%s)=%q, want substring %q", c.name, got, w)
				}
			}
		})
	}
}

func TestStreamPrettyWriter_SplitsAndBuffersPartialLines(t *testing.T) {
	var sb strings.Builder
	w := newStreamPrettyWriter(&sb)
	// A tool_use event delivered in two Writes (split mid-line) must still render once.
	full := `{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Bash","input":{"command":"ls"}}]}}` + "\n"
	_, _ = w.Write([]byte(full[:40]))
	_, _ = w.Write([]byte(full[40:]))
	out := sb.String()
	if !strings.Contains(out, "⏺ Bash(") || !strings.Contains(out, "ls") {
		t.Fatalf("expected rendered Bash line, got %q", out)
	}
	if strings.Count(out, "⏺ Bash(") != 1 {
		t.Fatalf("expected exactly one render, got %q", out)
	}
}

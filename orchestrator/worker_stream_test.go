package main

import (
	"os"
	"testing"
)

// TestParseWorkerResultStreamJSON verifies the parser extracts the WorkerResult
// from a representative stream-json event stream (the final result event's
// "result" field carries the assistant's final text containing the JSON).
func TestParseWorkerResultStreamJSON(t *testing.T) {
	stream := `{"type":"system","subtype":"init","session_id":"x"}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"working..."}]}}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"{\"done\":true,\"summary\":\"did the thing\",\"changes\":[\"a.go\"],\"assumptions\":[]}"}]}}
{"type":"result","subtype":"success","is_error":false,"result":"{\"done\":true,\"summary\":\"did the thing\",\"changes\":[\"a.go\"],\"assumptions\":[]}","session_id":"x"}`
	wr, err := ParseWorkerResult([]byte(stream))
	if err != nil {
		t.Fatalf("parse stream-json: %v", err)
	}
	if !wr.Done {
		t.Fatalf("expected done=true, got %+v", wr)
	}
	if wr.Summary != "did the thing" {
		t.Fatalf("summary mismatch: %q", wr.Summary)
	}
}

// TestParseWorkerResultBare keeps the bare-object path working.
func TestParseWorkerResultBare(t *testing.T) {
	wr, err := ParseWorkerResult([]byte("noise\n{\"done\":false,\"summary\":\"s\"}\n"))
	if err != nil {
		t.Fatalf("parse bare: %v", err)
	}
	if wr.Done || wr.Summary != "s" {
		t.Fatalf("unexpected: %+v", wr)
	}
}

// TestParseCompletionVerdict checks the advisory completion-check parser across
// stream-json, bare JSON, and unparseable inputs (the last must default to met).
func TestParseCompletionVerdict(t *testing.T) {
	stream := `{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"checking"}]}}
{"type":"result","subtype":"success","result":"{\"satisfied\":false,\"missing\":\"tests are absent\"}"}`
	if ok, missing := parseCompletionVerdict([]byte(stream)); ok || missing != "tests are absent" {
		t.Fatalf("stream verdict: ok=%v missing=%q", ok, missing)
	}
	if ok, _ := parseCompletionVerdict([]byte("{\"satisfied\":true,\"missing\":\"\"}")); !ok {
		t.Fatalf("bare satisfied verdict should be true")
	}
	// Unparseable / absent verdict must default to satisfied so it never blocks.
	if ok, _ := parseCompletionVerdict([]byte("no json here")); !ok {
		t.Fatalf("absent verdict must default to satisfied")
	}
}

// TestParseWorkerResultRealSample parses a captured real `claude -p
// --output-format stream-json --verbose` output if present (best effort).
func TestParseWorkerResultRealSample(t *testing.T) {
	data, err := os.ReadFile("testdata_streamsample.txt")
	if err != nil {
		t.Skip("no captured sample")
	}
	wr, err := ParseWorkerResult(data)
	if err != nil {
		t.Fatalf("parse real sample: %v", err)
	}
	if !wr.Done {
		t.Fatalf("expected done=true from real sample, got %+v", wr)
	}
	if wr.Summary == "" {
		t.Fatalf("expected non-empty summary from real sample")
	}
}

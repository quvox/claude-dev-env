package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

// writeHealth writes a vm-healthd-style health file under a temp HOME and
// points env at it. Returns nothing; callers assert via readVMHealthBanner.
func writeHealth(t *testing.T, state string, tsOffset time.Duration, msg string) {
	t.Helper()
	home := t.TempDir()
	t.Setenv("HOME", home)
	dir := filepath.Join(home, ".claude-dev-vm")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	ts := time.Now().Add(tsOffset).Unix()
	body := fmt.Sprintf("STATE=%s\nCPU=150\nCEIL=200\nTS=%d\nMSG=%s\n", state, ts, msg)
	if err := os.WriteFile(filepath.Join(dir, "health"), []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
}

func TestReadVMHealthBanner_WarnFresh(t *testing.T) {
	t.Setenv("CLAUDE_DEV_VM", "1")
	writeHealth(t, "WARN", -10*time.Second, "VM資源逼迫の可能性（QEMU CPU 150% / 上限 200%）")
	got := readVMHealthBanner()
	if got == "" || !strings.Contains(got, "VM資源逼迫") {
		t.Fatalf("expected warning banner, got %q", got)
	}
}

func TestReadVMHealthBanner_OKIsSilent(t *testing.T) {
	t.Setenv("CLAUDE_DEV_VM", "1")
	writeHealth(t, "OK", -10*time.Second, "ok")
	if got := readVMHealthBanner(); got != "" {
		t.Fatalf("expected no banner for OK state, got %q", got)
	}
}

func TestReadVMHealthBanner_StaleIgnored(t *testing.T) {
	t.Setenv("CLAUDE_DEV_VM", "1")
	writeHealth(t, "WARN", -(vmHealthFreshSecs+60)*time.Second, "old warning")
	if got := readVMHealthBanner(); got != "" {
		t.Fatalf("expected stale WARN to be ignored, got %q", got)
	}
}

func TestReadVMHealthBanner_NonVMMode(t *testing.T) {
	t.Setenv("CLAUDE_DEV_VM", "")
	writeHealth(t, "WARN", -10*time.Second, "warning")
	if got := readVMHealthBanner(); got != "" {
		t.Fatalf("expected no banner when not in VM mode, got %q", got)
	}
}

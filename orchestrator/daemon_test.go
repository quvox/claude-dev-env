package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestPidfileAndAlive(t *testing.T) {
	pf := filepath.Join(t.TempDir(), "controller.pid")
	if readPidfile(pf) != 0 {
		t.Fatal("absent pidfile should read 0")
	}
	if err := writePidfile(pf); err != nil {
		t.Fatal(err)
	}
	if got := readPidfile(pf); got != os.Getpid() {
		t.Fatalf("readPidfile=%d want %d", got, os.Getpid())
	}
	if !processAlive(os.Getpid()) {
		t.Fatal("current process should be alive")
	}
	if processAlive(0) || processAlive(2147483000) {
		t.Fatal("invalid/nonexistent pids should be dead")
	}
	if !controllerAlive(pf) {
		t.Fatal("controllerAlive should be true (pidfile = self)")
	}
}

package main

import (
	"context"
	"testing"
	"time"
)

func TestWaitConsume_ReturnsWhenControlAppears(t *testing.T) {
	store, err := NewStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	h := &Handoff{Store: store}
	go func() {
		time.Sleep(30 * time.Millisecond)
		_ = store.SaveControl(&Control{Request: ReqExecute, TS: "t"})
	}()
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	c, err := h.WaitConsume(ctx, 10*time.Millisecond, nil)
	if err != nil {
		t.Fatal(err)
	}
	if c == nil || c.Request != ReqExecute {
		t.Fatalf("expected execute control, got %+v", c)
	}
}

func TestWaitConsume_UntilEndsWithoutControl(t *testing.T) {
	store, err := NewStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	h := &Handoff{Store: store}
	ctx := context.Background()
	c, err := h.WaitConsume(ctx, 5*time.Millisecond, func() bool { return true })
	if err != nil || c != nil {
		t.Fatalf("until=true should return (nil,nil), got c=%v err=%v", c, err)
	}
}

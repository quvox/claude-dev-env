package main

import (
	"context"
	"time"
)

// Handoff wraps the control.json protocol between the interactive claude
// (brainstorming/intervene brain) and the controller. The interactive child
// writes control.json atomically before exiting; the controller consumes it
// (reads then deletes) when it regains the foreground.
type Handoff struct {
	Store *Store
}

// Consume reads control.json and deletes it. Returns (nil, nil) when absent or
// malformed (the controller then falls back to an explicit terminal prompt —
// never prompt-dependent on the unsafe side).
func (h *Handoff) Consume() (*Control, error) {
	c, err := h.Store.LoadControl()
	if err != nil {
		// Malformed/unreadable: treat as absent but still remove the file so a
		// stale bad control.json cannot wedge subsequent runs.
		_ = h.Store.DeleteControl()
		return nil, nil
	}
	if c == nil {
		return nil, nil
	}
	// Validate request value; unknown requests are treated as absent.
	switch c.Request {
	case ReqExecute, ReqResume, ReqContinueBrainstorming, ReqAbort, ReqAccept:
	default:
		_ = h.Store.DeleteControl()
		return nil, nil
	}
	if err := h.Store.DeleteControl(); err != nil {
		return nil, err
	}
	return c, nil
}

// WaitConsume polls for control.json and consumes it when it appears. In the
// daemon watch-model (独立ウィンドウ方式・Phase③ 3e) the controller launches an
// interactive claude into a tmux session and does NOT block on process exit;
// instead it watches for the brain's handoff here. Returns a non-nil Control
// when found, (nil,nil) when `until` reports the session ended without a
// handoff, or (nil, ctx.Err()) on cancel. poll defaults to 500ms.
func (h *Handoff) WaitConsume(ctx context.Context, poll time.Duration, until func() bool) (*Control, error) {
	if poll <= 0 {
		poll = 500 * time.Millisecond
	}
	t := time.NewTicker(poll)
	defer t.Stop()
	for {
		c, err := h.Consume()
		if err != nil {
			return nil, err
		}
		if c != nil {
			return c, nil
		}
		if until != nil && until() {
			return nil, nil // session/pane exited without writing control.json
		}
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		case <-t.C:
		}
	}
}

// DiscardStale removes any residual control.json without consuming its intent.
// Used on resume (Phase=executing) where plan.json is the source of truth.
func (h *Handoff) DiscardStale() error {
	return h.Store.DeleteControl()
}

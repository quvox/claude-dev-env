package main

// Handoff wraps the control.json protocol between the interactive claude
// (wallbounce/intervene brain) and the controller. The interactive child
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
	case ReqExecute, ReqResume, ReqContinueWallbounce, ReqAbort:
	default:
		_ = h.Store.DeleteControl()
		return nil, nil
	}
	if err := h.Store.DeleteControl(); err != nil {
		return nil, err
	}
	return c, nil
}

// DiscardStale removes any residual control.json without consuming its intent.
// Used on resume (Phase=executing) where plan.json is the source of truth.
func (h *Handoff) DiscardStale() error {
	return h.Store.DeleteControl()
}

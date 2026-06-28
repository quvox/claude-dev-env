package main

// Trigger reasons reported by Evaluate (mirror the 5 conditions in §介入トリガー判定).
const (
	TriggerIrreversible = "irreversible"  // condition 1 (pre-dispatch)
	TriggerAmbiguity    = "ambiguity"     // condition 2 (post-dispatch)
	TriggerStuck        = "stuck"         // condition 3 (controller-detected)
	TriggerPolicyBranch = "policy_branch" // condition 4 (post-dispatch)
	TriggerPrerequisite = "prerequisite"  // condition 5 (post-dispatch)
)

// TriggerPhase distinguishes the evaluation point.
type TriggerPhase int

const (
	// PhasePreDispatch is evaluated before launching the worker (condition 1).
	PhasePreDispatch TriggerPhase = iota
	// PhasePostDispatch is evaluated after the worker returns (conditions 2/4/5)
	// and also covers the stuck condition (3) the controller computes.
	PhasePostDispatch
)

// TriggerContext carries everything Evaluate needs. It is purely data so the
// decision is a deterministic function (no I/O, no reasoning).
type TriggerContext struct {
	Phase  TriggerPhase
	Task   *Task
	Plan   *Plan
	State  *State
	Result *WorkerResult // last worker result (post-dispatch only)
	Config Config

	// StuckThisAttempt indicates the current Attempt exhausted max_review_rounds
	// with severe findings still present (condition 3b).
	StuckThisAttempt bool
}

// Evaluate decides whether to fire an intervention. It returns fire and a
// stable reason string. It performs no I/O.
//
// Pre-dispatch (condition 1): an irreversible task fires before the worker runs.
// Post-dispatch (conditions 2/4/5): driven by the worker's NeedsHuman.Reason.
// Stuck (condition 3): Attempts >= stuck_limit, OR StuckThisAttempt.
func Evaluate(ctx TriggerContext) (fire bool, reason string) {
	if ctx.Task == nil {
		return false, ""
	}

	if ctx.Phase == PhasePreDispatch {
		// Condition 1: irreversible/critical operations are gated before any
		// worker runs. The worker itself must not perform them. Once a human has
		// approved the task during an intervention (IrrevApproved), the gate no
		// longer fires so the task can finally be dispatched (no infinite
		// re-fire on resume).
		if ctx.Task.Irreversible && !ctx.Task.IrrevApproved {
			return true, TriggerIrreversible
		}
		return false, ""
	}

	// PhasePostDispatch.

	// Condition 3 (stuck): controller-detected; checked first because it does
	// not depend on a NeedsHuman from the worker.
	if ctx.Config.StuckLimit > 0 && ctx.Task.Attempts >= ctx.Config.StuckLimit {
		return true, TriggerStuck
	}
	if ctx.StuckThisAttempt {
		return true, TriggerStuck
	}

	// Conditions 2/4/5: driven by the worker's escalation request.
	if ctx.Result != nil && ctx.Result.NeedsHuman != nil {
		switch ctx.Result.NeedsHuman.Reason {
		case ReasonAmbiguity:
			return true, TriggerAmbiguity
		case ReasonPolicyBranch:
			return true, TriggerPolicyBranch
		case ReasonPrerequisiteBroke:
			return true, TriggerPrerequisite
		case ReasonCriticalDecision:
			// A worker should not normally reach an irreversible op (it is gated
			// pre-dispatch), but if it escalates one, honor it as condition 1.
			return true, TriggerIrreversible
		}
	}

	return false, ""
}

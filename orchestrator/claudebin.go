package main

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

// Locating the `claude` binary.
//
// The orchestrator is normally launched by `claude-dev orchestrate`, which runs
// it in a tmux window via a non-interactive shell (`zsh -c`). Claude Code's
// native installer puts `claude` in $HOME/.local/bin and adds that directory to
// PATH only in the *interactive* shell rc (.zshrc), so a non-interactive launch
// does NOT have it on PATH. A bare exec.Command("claude", …) then fails with
// "executable file not found in $PATH", which would break brainstorming, intervene
// and every worker/reviewer. We therefore resolve claude explicitly and make
// sure its directory is on PATH for the child process.

// localBinDir is the standard Claude Code native-install bin directory.
func localBinDir() string {
	if home, err := os.UserHomeDir(); err == nil {
		return filepath.Join(home, ".local", "bin")
	}
	return ""
}

// claudePath resolves the `claude` executable: prefer $PATH, then fall back to
// the standard native-install location. Returns "claude" as a last resort so
// exec surfaces a clear error if it is genuinely absent.
func claudePath() string {
	if p, err := exec.LookPath("claude"); err == nil {
		return p
	}
	if bin := localBinDir(); bin != "" {
		cand := filepath.Join(bin, "claude")
		if st, err := os.Stat(cand); err == nil && !st.IsDir() {
			return cand
		}
	}
	return "claude"
}

// augmentPathForClaude ensures the claude bin directory is on PATH in env so the
// child claude process (and any tool it spawns) can resolve claude-adjacent
// binaries even under a non-interactive launch. It mutates/returns env.
func augmentPathForClaude(env []string) []string {
	bin := localBinDir()
	if bin == "" {
		return env
	}
	for i, e := range env {
		if strings.HasPrefix(e, "PATH=") {
			if !pathContains(e[len("PATH="):], bin) {
				env[i] = "PATH=" + bin + ":" + e[len("PATH="):]
			}
			return env
		}
	}
	return append(env, "PATH="+bin)
}

// pathContains reports whether a colon-separated PATH already lists dir.
func pathContains(path, dir string) bool {
	for _, p := range strings.Split(path, ":") {
		if p == dir {
			return true
		}
	}
	return false
}

// claudeChildEnv builds the environment for a child claude process: the current
// environment with SLACK_BOT_TOKEN stripped (only the controller may post to
// Slack) and the claude bin directory ensured on PATH.
func claudeChildEnv() []string {
	return augmentPathForClaude(stripEnv(os.Environ(), "SLACK_BOT_TOKEN"))
}

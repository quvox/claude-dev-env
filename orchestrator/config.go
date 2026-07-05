package main

import (
	"bufio"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

// Config holds tunables for the orchestrator. All values have built-in
// defaults and may be overridden by the user-global config file and then by
// the per-project config file (the latter being strongest).
//
// Merge precedence (weakest -> strongest):
//  1. built-in defaults (DefaultConfig)
//  2. ~/.config/claude-dev.yaml  (the `orchestrator:` section)
//  3. <workspace>/.orchestrator/config.yaml
type Config struct {
	MaxWorkers      int // 並行 worker 数
	StuckLimit      int // トリガー3 の規定回数（Attempt 総数の上限）
	MaxReviewRounds int // Attempt 内のレビュー反復上限
	// ReviewFormatErrorLimit is the number of consecutive unparseable reviewer
	// outputs after which the task escalates as a review_gate_defect (without
	// re-running the worker). docs/impl/60 §品質ゲート 8.2.
	ReviewFormatErrorLimit int
	// WorkerGraceSeconds is how long an in-flight worker is given to commit its
	// work-in-progress when the run is suspended (Ctrl-C/[q]) before it is hard
	// killed. docs/impl/60 §並行性・再開・エラー処理.
	WorkerGraceSeconds int
	WorkerModel        string // DEPRECATED: model/effort は models.go のポリシー表で工程別に決まる（本値は選択に使われない・互換のため解析のみ）
	ReviewerVendor     string // claude | codex
	MergeStrategy      string // merge | rebase
	// WorkerPermissionMode is the --permission-mode passed to worker/reviewer
	// `claude -p` calls. Headless workers have no human to answer permission
	// prompts, so without an explicit non-interactive mode every Write/Bash is
	// denied and the worker silently does nothing. Defaults to bypassPermissions
	// (06 §10: container isolation + FW + proxy + instruction constraints bound
	// the blast radius). Set to "" to pass no flag (rely on ambient settings).
	WorkerPermissionMode string

	// Environment (not part of the YAML file)
	SlackBotToken string
	SlackChannel  string
}

// DefaultSlackChannel mirrors scripts/sendslackmsg.sh's default.
const DefaultSlackChannel = "U5SJG0XEK"

// DefaultConfig returns the built-in defaults.
func DefaultConfig() Config {
	return Config{
		MaxWorkers:             5,
		StuckLimit:             3,
		MaxReviewRounds:        10,
		ReviewFormatErrorLimit: 2,
		WorkerGraceSeconds:     10,
		WorkerModel:            "sonnet",
		ReviewerVendor:         "claude",
		MergeStrategy:          "merge",
		WorkerPermissionMode:   "bypassPermissions",
		SlackChannel:           DefaultSlackChannel,
	}
}

// LoadConfig builds the effective configuration for the given workspace.
func LoadConfig(workspace string) Config {
	cfg := DefaultConfig()

	// 2. user-global ~/.config/claude-dev.yaml (orchestrator: section)
	if home, err := os.UserHomeDir(); err == nil {
		userPath := filepath.Join(home, ".config", "claude-dev.yaml")
		if kv, err := parseFlatYAMLSection(userPath, "orchestrator"); err == nil {
			applyConfigKV(&cfg, kv)
		}
	}

	// 3. project <workspace>/.orchestrator/config.yaml (flat, no section)
	projPath := filepath.Join(workspace, ".orchestrator", "config.yaml")
	if kv, err := parseFlatYAML(projPath); err == nil {
		applyConfigKV(&cfg, kv)
	}

	// Environment overlays (always strongest for Slack credentials)
	cfg.SlackBotToken = os.Getenv("SLACK_BOT_TOKEN")
	if ch := os.Getenv("SLACK_CHANNEL"); ch != "" {
		cfg.SlackChannel = ch
	}

	return cfg
}

// applyConfigKV applies recognized keys from a parsed key/value map.
func applyConfigKV(cfg *Config, kv map[string]string) {
	for k, v := range kv {
		switch k {
		case "max_workers":
			if n, err := strconv.Atoi(v); err == nil && n > 0 {
				cfg.MaxWorkers = n
			}
		case "stuck_limit":
			if n, err := strconv.Atoi(v); err == nil && n > 0 {
				cfg.StuckLimit = n
			}
		case "max_review_rounds":
			if n, err := strconv.Atoi(v); err == nil && n > 0 {
				cfg.MaxReviewRounds = n
			}
		case "review_format_error_limit":
			if n, err := strconv.Atoi(v); err == nil && n > 0 {
				cfg.ReviewFormatErrorLimit = n
			}
		case "worker_grace_seconds":
			if n, err := strconv.Atoi(v); err == nil && n >= 0 {
				cfg.WorkerGraceSeconds = n
			}
		case "worker_model":
			if v != "" {
				cfg.WorkerModel = v
			}
		case "reviewer_vendor":
			if v != "" {
				cfg.ReviewerVendor = v
			}
		case "merge_strategy":
			if v != "" {
				cfg.MergeStrategy = v
			}
		case "worker_permission_mode":
			cfg.WorkerPermissionMode = v // "" disables the flag intentionally
		}
	}
}

// parseFlatYAML reads a tiny "key: value" subset of YAML (no nesting). Lines
// that are blank or start with '#' are ignored. Returns an error only if the
// file cannot be opened.
func parseFlatYAML(path string) (map[string]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	kv := make(map[string]string)
	sc := bufio.NewScanner(f)
	for sc.Scan() {
		line := sc.Text()
		k, v, ok := splitKV(line)
		if !ok {
			continue
		}
		kv[k] = v
	}
	return kv, sc.Err()
}

// parseFlatYAMLSection reads keys nested one level under `section:`. Only the
// keys indented under that section (until the next unindented key) are
// returned. This supports the user-global file where orchestrator settings
// live under an `orchestrator:` mapping.
func parseFlatYAMLSection(path, section string) (map[string]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	kv := make(map[string]string)
	inSection := false
	sc := bufio.NewScanner(f)
	for sc.Scan() {
		raw := sc.Text()
		trimmed := strings.TrimSpace(raw)
		if trimmed == "" || strings.HasPrefix(trimmed, "#") {
			continue
		}
		indented := raw != strings.TrimLeft(raw, " \t")
		if !indented {
			// Top-level line: either the section header or some other key.
			name := strings.TrimSuffix(trimmed, ":")
			inSection = (name == section)
			continue
		}
		if !inSection {
			continue
		}
		if k, v, ok := splitKV(trimmed); ok {
			kv[k] = v
		}
	}
	return kv, sc.Err()
}

// splitKV parses a single "key: value" line. It strips inline comments and
// surrounding quotes from the value. Returns ok=false for non-kv lines.
func splitKV(line string) (key, val string, ok bool) {
	trimmed := strings.TrimSpace(line)
	if trimmed == "" || strings.HasPrefix(trimmed, "#") {
		return "", "", false
	}
	idx := strings.Index(trimmed, ":")
	if idx < 0 {
		return "", "", false
	}
	key = strings.TrimSpace(trimmed[:idx])
	val = strings.TrimSpace(trimmed[idx+1:])
	if key == "" {
		return "", "", false
	}
	// Strip inline comment (a '#' preceded by whitespace) when value is unquoted.
	if !strings.HasPrefix(val, "\"") && !strings.HasPrefix(val, "'") {
		if ci := strings.Index(val, " #"); ci >= 0 {
			val = strings.TrimSpace(val[:ci])
		}
	}
	val = strings.Trim(val, "\"'")
	return key, val, true
}

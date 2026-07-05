package main

import "testing"

func TestTaskKindProfile(t *testing.T) {
	deep := []string{"design", "Spec", " impl_spec ", "impl-spec", "requirements", "usecase", "adr", "doc", "docs", "review"}
	for _, k := range deep {
		if got := taskKindProfile(k); got != profileDeep {
			t.Errorf("kind %q → %+v, want deep %+v", k, got, profileDeep)
		}
	}
	def := []string{"", "implementation", "code", "test", "impl", "misc", "unknown"}
	for _, k := range def {
		if got := taskKindProfile(k); got != profileDefault {
			t.Errorf("kind %q → %+v, want default %+v", k, got, profileDefault)
		}
	}
}

func TestWorkerTaskProfile(t *testing.T) {
	if workerTaskProfile(nil) != profileDefault {
		t.Fatal("nil task should be default")
	}
	if got := workerTaskProfile(&Task{Kind: "design"}); got != profileDeep {
		t.Fatalf("design task → %+v, want deep", got)
	}
	if got := workerTaskProfile(&Task{Kind: "implementation"}); got != profileDefault {
		t.Fatalf("implementation task → %+v, want default", got)
	}
}

func TestRoleProfiles(t *testing.T) {
	for name, got := range map[string]ModelProfile{
		"brainstorming": brainstormingProfile(),
		"intervene":     interveneProfile(),
		"reviewer":      reviewerProfile(),
	} {
		if got != profileDeep {
			t.Errorf("%s profile = %+v, want deep", name, got)
		}
	}
	// Every profile must carry a valid effort level (guards against typos in the table).
	valid := map[string]bool{"low": true, "medium": true, "high": true, "xhigh": true, "max": true}
	for _, p := range []ModelProfile{profileDeep, profileDefault, completionProfile()} {
		if !valid[p.Effort] {
			t.Errorf("profile %+v has invalid effort", p)
		}
		if p.Model == "" {
			t.Errorf("profile %+v has empty model", p)
		}
	}
}

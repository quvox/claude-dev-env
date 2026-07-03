package main

import (
	"encoding/json"
	"io"
	"log"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestContainWorkspacePath(t *testing.T) {
	proj := t.TempDir()
	if err := os.MkdirAll(filepath.Join(proj, "sub"), 0o755); err != nil {
		t.Fatal(err)
	}

	cases := []struct {
		name    string
		src     string
		wantOK  bool
		wantOut string
	}{
		{"under workspace", "/workspace/sub", true, filepath.Join(proj, "sub")},
		{"workspace root", "/workspace", true, proj},
		{"nested new dir", "/workspace/a/b", true, filepath.Join(proj, "a/b")},
		{"outside path", "/etc", false, ""},
		{"prefix trick", "/workspaces/x", false, ""},
		{"dotdot escape", "/workspace/../etc", false, ""},
		{"empty projectDir", "/workspace/sub", false, ""}, // handled below via override
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			pd := proj
			if c.name == "empty projectDir" {
				pd = ""
			}
			out, ok := containWorkspacePath(pd, c.src)
			if ok != c.wantOK {
				t.Fatalf("ok=%v want %v (out=%q)", ok, c.wantOK, out)
			}
			if ok && out != c.wantOut {
				t.Fatalf("out=%q want %q", out, c.wantOut)
			}
		})
	}
}

// Containment is lexical only: the proxy has no view of the host filesystem, so
// symlink components are NOT resolved (documented residual risk). A symlink path
// is accepted lexically; ".." traversal is still rejected lexically.
func TestContainWorkspacePath_LexicalOnly(t *testing.T) {
	proj := t.TempDir()
	// A symlink-looking component under /workspace is accepted (not resolved).
	out, ok := containWorkspacePath(proj, "/workspace/link/secret")
	if !ok || out != filepath.Join(proj, "link/secret") {
		t.Fatalf("lexical accept failed: ok=%v out=%q", ok, out)
	}
	// ".." traversal is still rejected lexically.
	if _, ok := containWorkspacePath(proj, "/workspace/a/../../etc"); ok {
		t.Fatalf("expected .. traversal to be rejected")
	}
}

func TestRewriteBinds_RewritesUnderWorkspace(t *testing.T) {
	proj := t.TempDir()
	body := `{"Image":"x","HostConfig":{"Memory":123456,"Binds":["/workspace/app:/app:ro","myvol:/data"]}}`
	out, changed, err := rewriteBinds([]byte(body), proj)
	if err != nil {
		t.Fatal(err)
	}
	if !changed {
		t.Fatal("expected changed=true")
	}
	var top map[string]json.RawMessage
	if err := json.Unmarshal(out, &top); err != nil {
		t.Fatal(err)
	}
	// Root-level field preserved.
	if string(top["Image"]) != `"x"` {
		t.Fatalf("Image not preserved: %s", top["Image"])
	}
	var hc map[string]json.RawMessage
	_ = json.Unmarshal(top["HostConfig"], &hc)
	if string(hc["Memory"]) != "123456" {
		t.Fatalf("Memory not preserved: %s", hc["Memory"])
	}
	var binds []string
	_ = json.Unmarshal(hc["Binds"], &binds)
	want := filepath.Join(proj, "app") + ":/app:ro"
	if binds[0] != want {
		t.Fatalf("bind[0]=%q want %q", binds[0], want)
	}
	if binds[1] != "myvol:/data" {
		t.Fatalf("named volume mangled: %q", binds[1])
	}
}

func TestRewriteBinds_RejectsOutsideWorkspace(t *testing.T) {
	proj := t.TempDir()
	body := `{"HostConfig":{"Binds":["/etc:/etc"]}}`
	if _, _, err := rewriteBinds([]byte(body), proj); err == nil {
		t.Fatal("expected rejection of /etc bind")
	}
}

func TestRewriteBinds_MountsBind(t *testing.T) {
	proj := t.TempDir()
	body := `{"HostConfig":{"Mounts":[{"Type":"bind","Source":"/workspace/x","Target":"/x","ReadOnly":true}]}}`
	out, changed, err := rewriteBinds([]byte(body), proj)
	if err != nil || !changed {
		t.Fatalf("changed=%v err=%v", changed, err)
	}
	var top map[string]json.RawMessage
	_ = json.Unmarshal(out, &top)
	var hc map[string]json.RawMessage
	_ = json.Unmarshal(top["HostConfig"], &hc)
	var mounts []map[string]json.RawMessage
	_ = json.Unmarshal(hc["Mounts"], &mounts)
	var src string
	_ = json.Unmarshal(mounts[0]["Source"], &src)
	if src != filepath.Join(proj, "x") {
		t.Fatalf("Source=%q want %q", src, filepath.Join(proj, "x"))
	}
	// Sibling fields on the mount preserved.
	if string(mounts[0]["ReadOnly"]) != "true" {
		t.Fatalf("ReadOnly not preserved: %s", mounts[0]["ReadOnly"])
	}
}

func TestRewriteBinds_MountsBindOutsideRejected(t *testing.T) {
	proj := t.TempDir()
	body := `{"HostConfig":{"Mounts":[{"Type":"bind","Source":"/var/run/docker.sock","Target":"/s"}]}}`
	if _, _, err := rewriteBinds([]byte(body), proj); err == nil {
		t.Fatal("expected rejection of docker.sock bind mount")
	}
}

func TestRewriteBinds_EmptyProjectRejectsAbsolute(t *testing.T) {
	// Feature off / caller unknown: absolute binds rejected, named volumes pass.
	if _, _, err := rewriteBinds([]byte(`{"HostConfig":{"Binds":["/workspace/x:/x"]}}`), ""); err == nil {
		t.Fatal("expected rejection when projectDir is empty")
	}
	out, changed, err := rewriteBinds([]byte(`{"HostConfig":{"Binds":["vol:/x"]}}`), "")
	if err != nil || changed {
		t.Fatalf("named volume should pass unchanged: changed=%v err=%v out=%s", changed, err, out)
	}
}

func TestValidateContainerCreate_RewritesWorkspaceBind(t *testing.T) {
	proj := t.TempDir()
	orig := resolveProjectDir
	resolveProjectDir = func(_ string) (string, bool) { return proj, true }
	defer func() { resolveProjectDir = orig }()

	req := newRequest("POST", "/containers/create", `{"HostConfig":{"Binds":["/workspace/app:/app"]}}`)
	req.RemoteAddr = "172.20.0.9:5000"
	if err := validateContainerCreate(req, log.New(io.Discard, "", 0)); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	got, _ := io.ReadAll(req.Body)
	want := filepath.Join(proj, "app")
	if !strings.Contains(string(got), want) {
		t.Fatalf("rewritten body missing %q: %s", want, got)
	}
	if strings.Contains(string(got), `"/workspace/app`) {
		t.Fatalf("body still contains container-view path: %s", got)
	}
}

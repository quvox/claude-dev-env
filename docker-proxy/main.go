package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"net/http/httputil"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"
)

const (
	listenAddr = ":2375"
	socketPath = "/var/run/docker.sock"
	// workspaceMount is where each claude container mounts its project dir.
	workspaceMount = "/workspace"
	// projectCacheTTL bounds how long a resolved source-IP → PROJECT_DIR mapping
	// is trusted before re-querying the Docker API.
	projectCacheTTL = 60 * time.Second
)

// allowWorkspaceBinds enables rewriting/allowing bind mounts whose source is
// under the caller's /workspace (docs/03_security.md §5, docs/impl/50). Default
// on; set CLAUDE_DEV_ALLOW_WORKSPACE_BINDS=0/false/no to fall back to rejecting
// all host bind mounts.
var allowWorkspaceBinds = func() bool {
	switch strings.ToLower(os.Getenv("CLAUDE_DEV_ALLOW_WORKSPACE_BINDS")) {
	case "0", "false", "no", "off":
		return false
	}
	return true
}()

// resolveProjectDir maps a caller's source IP to its host PROJECT_DIR (the host
// path it mounts at /workspace), or ("", false) if unknown. It is a var so tests
// can inject a stub instead of hitting the Docker API.
var resolveProjectDir = cachedResolveProjectDir

// dockerHTTP talks to the host Docker socket for read-only lookups (container list).
var dockerHTTP = &http.Client{
	Timeout: 5 * time.Second,
	Transport: &http.Transport{
		DialContext: func(_ context.Context, _, _ string) (net.Conn, error) {
			return net.Dial("unix", socketPath)
		},
	},
}

type projectCacheEntry struct {
	dir string
	exp time.Time
}

var (
	projectCache   = map[string]projectCacheEntry{}
	projectCacheMu sync.Mutex
)

// cachedResolveProjectDir wraps lookupProjectDir with a short TTL cache.
func cachedResolveProjectDir(remoteIP string) (string, bool) {
	projectCacheMu.Lock()
	if e, ok := projectCache[remoteIP]; ok && time.Now().Before(e.exp) {
		projectCacheMu.Unlock()
		return e.dir, e.dir != ""
	}
	projectCacheMu.Unlock()

	dir := lookupProjectDir(remoteIP)

	projectCacheMu.Lock()
	projectCache[remoteIP] = projectCacheEntry{dir: dir, exp: time.Now().Add(projectCacheTTL)}
	projectCacheMu.Unlock()
	return dir, dir != ""
}

// lookupProjectDir asks the Docker daemon for the container whose network IP is
// remoteIP and returns the host source of its /workspace mount ("" if none).
func lookupProjectDir(remoteIP string) string {
	resp, err := dockerHTTP.Get("http://docker/containers/json")
	if err != nil {
		return ""
	}
	defer resp.Body.Close()
	var cs []struct {
		Mounts []struct {
			Destination string `json:"Destination"`
			Source      string `json:"Source"`
		} `json:"Mounts"`
		NetworkSettings struct {
			Networks map[string]struct {
				IPAddress string `json:"IPAddress"`
			} `json:"Networks"`
		} `json:"NetworkSettings"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&cs); err != nil {
		return ""
	}
	for _, c := range cs {
		match := false
		for _, n := range c.NetworkSettings.Networks {
			if n.IPAddress != "" && n.IPAddress == remoteIP {
				match = true
				break
			}
		}
		if !match {
			continue
		}
		for _, m := range c.Mounts {
			if m.Destination == workspaceMount {
				return m.Source
			}
		}
	}
	return ""
}

// containWorkspacePath validates that containerSrc (a path as seen inside the
// caller container) is /workspace or below, and returns the rewritten HOST path
// (projectDir/<rel>). Containment is LEXICAL: it rejects paths outside
// /workspace and ".." traversal. It intentionally does NOT resolve symlinks,
// because the proxy container has no view of the host filesystem (it holds only
// the Docker socket; mounting the host into the proxy would be unsafe since
// exec into the proxy is permitted). Consequence: a symlink placed inside the
// project that points outside is not detected here — a documented residual risk
// (docs/03_security.md §5 / 残存リスク).
func containWorkspacePath(projectDir, containerSrc string) (string, bool) {
	if projectDir == "" {
		return "", false
	}
	if containerSrc != workspaceMount && !strings.HasPrefix(containerSrc, workspaceMount+"/") {
		return "", false
	}
	rel := strings.TrimPrefix(containerSrc, workspaceMount) // "" or "/sub/dir"
	host := filepath.Clean(filepath.Join(projectDir, rel))
	pc := filepath.Clean(projectDir)
	if host != pc && !strings.HasPrefix(host, pc+string(filepath.Separator)) {
		return "", false // ".." traversal escaped the project dir
	}
	return host, true
}

// rewriteBinds rewrites /workspace-relative bind sources to host paths under
// projectDir, preserving all other request fields. It returns an error if any
// host bind mount is outside /workspace (or fails containment). When projectDir
// is "" (feature off or caller unknown), every absolute host bind is rejected
// and named volumes/tmpfs pass through — matching the pre-existing behavior.
func rewriteBinds(body []byte, projectDir string) ([]byte, bool, error) {
	var top map[string]json.RawMessage
	if err := json.Unmarshal(body, &top); err != nil {
		return body, false, nil // unparseable: let Docker validate (existing policy)
	}
	hcRaw, ok := top["HostConfig"]
	if !ok || len(hcRaw) == 0 || string(hcRaw) == "null" {
		return body, false, nil
	}
	var hc map[string]json.RawMessage
	if err := json.Unmarshal(hcRaw, &hc); err != nil {
		return body, false, nil
	}
	changed := false

	if raw, ok := hc["Binds"]; ok && string(raw) != "null" {
		var binds []string
		if err := json.Unmarshal(raw, &binds); err == nil {
			for i, b := range binds {
				parts := strings.SplitN(b, ":", 2)
				src := parts[0]
				if !strings.HasPrefix(src, "/") {
					continue // named volume
				}
				host, ok := containWorkspacePath(projectDir, src)
				if !ok {
					return nil, false, fmt.Errorf("host bind mount is not allowed: %s", b)
				}
				if host != src {
					if len(parts) == 2 {
						binds[i] = host + ":" + parts[1]
					} else {
						binds[i] = host
					}
					changed = true
				}
			}
			if changed {
				nb, err := json.Marshal(binds)
				if err != nil {
					return nil, false, err
				}
				hc["Binds"] = nb
			}
		}
	}

	if raw, ok := hc["Mounts"]; ok && string(raw) != "null" {
		var mounts []map[string]json.RawMessage
		if err := json.Unmarshal(raw, &mounts); err == nil {
			mchanged := false
			for _, m := range mounts {
				var typ string
				_ = json.Unmarshal(m["Type"], &typ)
				if typ != "bind" {
					continue
				}
				var src string
				_ = json.Unmarshal(m["Source"], &src)
				host, ok := containWorkspacePath(projectDir, src)
				if !ok {
					return nil, false, fmt.Errorf("bind mount is not allowed: source=%s", src)
				}
				if host != src {
					nb, err := json.Marshal(host)
					if err != nil {
						return nil, false, err
					}
					m["Source"] = nb
					mchanged = true
				}
			}
			if mchanged {
				nb, err := json.Marshal(mounts)
				if err != nil {
					return nil, false, err
				}
				hc["Mounts"] = nb
				changed = true
			}
		}
	}

	if !changed {
		return body, false, nil
	}
	nhc, err := json.Marshal(hc)
	if err != nil {
		return nil, false, err
	}
	top["HostConfig"] = nhc
	nbody, err := json.Marshal(top)
	if err != nil {
		return nil, false, err
	}
	return nbody, true, nil
}

// clientIP extracts the source IP from an http.Request's RemoteAddr.
func clientIP(remoteAddr string) string {
	if host, _, err := net.SplitHostPort(remoteAddr); err == nil {
		return host
	}
	return remoteAddr
}

// dangerousCapabilities is the set of Linux capabilities that must not be added.
var dangerousCapabilities = map[string]bool{
	"SYS_ADMIN":       true,
	"SYS_PTRACE":      true,
	"SYS_RAWIO":       true,
	"SYS_MODULE":      true,
	"DAC_READ_SEARCH": true,
}

// blockedEndpoints are completely blocked regardless of method.
var blockedPathPrefixes = []string{
	"/swarm",
	"/plugins",
	"/configs",
	"/secrets",
}

// containerCreateRe matches POST /containers/create and POST /v{version}/containers/create.
var containerCreateRe = regexp.MustCompile(`^(/v[\d.]+)?/containers/create`)

// containerExecCreateRe matches POST /containers/{id}/exec (exec create).
var containerExecCreateRe = regexp.MustCompile(`^(/v[\d.]+)?/containers/[^/]+/exec`)

// hijackEndpointRe matches endpoints that require HTTP connection hijacking:
//   - POST /exec/{id}/start — start an exec instance (stdin/stdout streaming)
//   - POST /containers/{id}/attach — attach to container (stdin/stdout streaming)
//   - POST /exec/{id}/resize — resize exec TTY
//   - POST /containers/{id}/resize — resize container TTY
var hijackEndpointRe = regexp.MustCompile(`^(/v[\d.]+)?/(exec/[^/]+/start|containers/[^/]+/attach|exec/[^/]+/resize|containers/[^/]+/resize)`)

func main() {
	logger := log.New(os.Stdout, "[docker-proxy] ", log.LstdFlags)

	// Verify the Docker socket exists.
	if _, err := os.Stat(socketPath); err != nil {
		logger.Fatalf("Docker socket not found at %s: %v", socketPath, err)
	}

	proxy := &httputil.ReverseProxy{
		Director: func(req *http.Request) {
			req.URL.Scheme = "http"
			req.URL.Host = "docker"
		},
		Transport: &http.Transport{
			DialContext: func(_ context.Context, _, _ string) (net.Conn, error) {
				return net.Dial("unix", socketPath)
			},
		},
		ErrorHandler: func(w http.ResponseWriter, r *http.Request, err error) {
			logger.Printf("proxy error: %s %s: %v", r.Method, r.URL.Path, err)
			http.Error(w, fmt.Sprintf("proxy error: %v", err), http.StatusBadGateway)
		},
	}

	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		path := r.URL.Path

		// Strip version prefix for matching (e.g., /v1.45/containers/create -> /containers/create).
		cleanPath := path
		if strings.HasPrefix(cleanPath, "/v") {
			if idx := strings.Index(cleanPath[1:], "/"); idx >= 0 {
				cleanPath = cleanPath[idx+1:]
			}
		}

		// Block forbidden endpoint prefixes.
		for _, prefix := range blockedPathPrefixes {
			if strings.HasPrefix(cleanPath, prefix) {
				logger.Printf("BLOCKED endpoint: %s %s", r.Method, path)
				http.Error(w, fmt.Sprintf("blocked: %s is not allowed", cleanPath), http.StatusForbidden)
				return
			}
		}

		// Inspect container create requests.
		if r.Method == http.MethodPost && containerCreateRe.MatchString(path) {
			if err := validateContainerCreate(r, logger); err != nil {
				logger.Printf("BLOCKED create: %s %s: %s", r.Method, path, err)
				http.Error(w, fmt.Sprintf("blocked: %s", err), http.StatusForbidden)
				return
			}
		}

		// Inspect exec create requests (for privileged exec).
		if r.Method == http.MethodPost && containerExecCreateRe.MatchString(path) {
			if err := validateExecCreate(r, logger); err != nil {
				logger.Printf("BLOCKED exec: %s %s: %s", r.Method, path, err)
				http.Error(w, fmt.Sprintf("blocked: %s", err), http.StatusForbidden)
				return
			}
		}

		// Handle endpoints that require HTTP connection hijacking (exec start, attach, resize).
		// Docker uses HTTP connection upgrade ("Upgrade: tcp") for streaming stdin/stdout.
		// httputil.ReverseProxy does not support this, so we handle it with raw TCP proxying.
		if r.Method == http.MethodPost && hijackEndpointRe.MatchString(path) {
			logger.Printf("HIJACK: %s %s", r.Method, path)
			handleHijack(w, r, logger)
			return
		}

		logger.Printf("ALLOW: %s %s", r.Method, path)
		proxy.ServeHTTP(w, r)
	})

	logger.Printf("Docker socket proxy listening on %s", listenAddr)
	logger.Printf("Forwarding to %s", socketPath)
	if err := http.ListenAndServe(listenAddr, handler); err != nil {
		logger.Fatalf("Failed to start server: %v", err)
	}
}

// closeWrite attempts to half-close the write side of a connection.
// Works with TCP, Unix, and any net.Conn that supports CloseWrite.
func closeWrite(conn net.Conn) {
	type closeWriter interface {
		CloseWrite() error
	}
	if cw, ok := conn.(closeWriter); ok {
		cw.CloseWrite()
	}
}

// handleHijack proxies a connection-hijacking Docker API request.
// It establishes a raw TCP connection to the Docker daemon via Unix socket,
// forwards the HTTP request, then bidirectionally proxies raw bytes.
func handleHijack(w http.ResponseWriter, r *http.Request, logger *log.Logger) {
	// Connect to Docker daemon.
	dockerConn, err := net.Dial("unix", socketPath)
	if err != nil {
		logger.Printf("hijack: failed to connect to Docker socket: %v", err)
		http.Error(w, "failed to connect to Docker daemon", http.StatusBadGateway)
		return
	}
	defer dockerConn.Close()

	// Hijack the client connection.
	hj, ok := w.(http.Hijacker)
	if !ok {
		logger.Printf("hijack: ResponseWriter does not support Hijack")
		http.Error(w, "hijack not supported", http.StatusInternalServerError)
		return
	}
	clientConn, clientBuf, err := hj.Hijack()
	if err != nil {
		logger.Printf("hijack: failed to hijack client connection: %v", err)
		return
	}
	defer clientConn.Close()

	// Forward the original HTTP request to Docker daemon.
	if err := r.Write(dockerConn); err != nil {
		logger.Printf("hijack: failed to write request to Docker: %v", err)
		return
	}

	// Bidirectional copy between client and Docker daemon.
	var wg sync.WaitGroup
	wg.Add(2)

	// Docker → Client
	go func() {
		defer wg.Done()
		defer func() {
			if r := recover(); r != nil {
				logger.Printf("hijack: recovered panic in docker→client copy: %v", r)
			}
		}()
		io.Copy(clientConn, dockerConn)
		closeWrite(clientConn)
	}()

	// Client → Docker
	// First drain any data buffered by the HTTP server's bufio.Reader,
	// then copy directly from the raw connection to avoid panics from
	// the HTTP server's internal connReader being closed.
	go func() {
		defer wg.Done()
		defer func() {
			if r := recover(); r != nil {
				logger.Printf("hijack: recovered panic in client→docker copy: %v", r)
			}
		}()
		// Drain buffered data first.
		if clientBuf.Reader.Buffered() > 0 {
			n := clientBuf.Reader.Buffered()
			buf := make([]byte, n)
			n, _ = clientBuf.Read(buf)
			if n > 0 {
				dockerConn.Write(buf[:n])
			}
		}
		// Then copy directly from the raw connection.
		io.Copy(dockerConn, clientConn)
		closeWrite(dockerConn)
	}()

	wg.Wait()
}

// containerCreateBody is a minimal representation of the Docker container create request body.
// Only the fields we need to inspect are included.
type containerCreateBody struct {
	HostConfig *hostConfig `json:"HostConfig"`
}

type hostConfig struct {
	Binds       []string          `json:"Binds"`
	Privileged  bool              `json:"Privileged"`
	PidMode     string            `json:"PidMode"`
	NetworkMode string            `json:"NetworkMode"`
	UsernsMode  string            `json:"UsernsMode"`
	CapAdd      []string          `json:"CapAdd"`
	Devices     []json.RawMessage `json:"Devices"`
	Mounts      []mount           `json:"Mounts"`
}

type mount struct {
	Type   string `json:"Type"`
	Source string `json:"Source"`
}

func validateContainerCreate(r *http.Request, logger *log.Logger) error {
	body, err := readAndRestoreBody(r)
	if err != nil {
		return fmt.Errorf("failed to read request body: %v", err)
	}

	var req containerCreateBody
	if err := json.Unmarshal(body, &req); err != nil {
		// If we can't parse the body, let it through — Docker will handle validation.
		logger.Printf("WARN: could not parse container create body: %v", err)
		return nil
	}

	if req.HostConfig == nil {
		return nil
	}

	hc := req.HostConfig

	// Check Privileged.
	if hc.Privileged {
		return fmt.Errorf("privileged containers are not allowed")
	}

	// Check host namespace modes.
	if hc.PidMode == "host" {
		return fmt.Errorf("PidMode=host is not allowed")
	}
	if hc.NetworkMode == "host" {
		return fmt.Errorf("NetworkMode=host is not allowed")
	}
	if hc.UsernsMode == "host" {
		return fmt.Errorf("UsernsMode=host is not allowed")
	}

	// Bind mounts (Binds + Mounts type=bind): allow only sources under the
	// caller's /workspace, rewriting them to the host PROJECT_DIR. When the
	// feature is off or the caller can't be resolved, projectDir stays "" and
	// rewriteBinds rejects every absolute host bind (pre-existing behavior).
	projectDir := ""
	if allowWorkspaceBinds {
		if pd, ok := resolveProjectDir(clientIP(r.RemoteAddr)); ok {
			projectDir = pd
		}
	}
	if newBody, changed, err := rewriteBinds(body, projectDir); err != nil {
		return err
	} else if changed {
		r.Body = io.NopCloser(bytes.NewReader(newBody))
		r.ContentLength = int64(len(newBody))
		r.Header.Set("Content-Length", strconv.Itoa(len(newBody)))
		logger.Printf("REWRITE binds: /workspace -> %s", projectDir)
	}

	// Check dangerous capabilities.
	for _, cap := range hc.CapAdd {
		if dangerousCapabilities[strings.ToUpper(cap)] {
			return fmt.Errorf("capability %s is not allowed", cap)
		}
	}

	// Check Devices.
	if len(hc.Devices) > 0 {
		return fmt.Errorf("device mappings are not allowed")
	}

	return nil
}

// execCreateBody is a minimal representation of the Docker exec create request body.
type execCreateBody struct {
	Privileged bool `json:"Privileged"`
}

func validateExecCreate(r *http.Request, logger *log.Logger) error {
	body, err := readAndRestoreBody(r)
	if err != nil {
		return fmt.Errorf("failed to read request body: %v", err)
	}

	var req execCreateBody
	if err := json.Unmarshal(body, &req); err != nil {
		logger.Printf("WARN: could not parse exec create body: %v", err)
		return nil
	}

	if req.Privileged {
		return fmt.Errorf("privileged exec is not allowed")
	}

	return nil
}

// readAndRestoreBody reads the request body and restores it so the proxy can forward it.
func readAndRestoreBody(r *http.Request) ([]byte, error) {
	if r.Body == nil {
		return nil, nil
	}
	body, err := io.ReadAll(r.Body)
	if err != nil {
		return nil, err
	}
	r.Body = io.NopCloser(bytes.NewReader(body))
	return body, nil
}

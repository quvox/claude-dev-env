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

	// Management labels (CTR-cli-container「管理ラベル」). projectDirLabel is put
	// on Claude containers by the host CLI and is READ here; the other two are
	// written by this proxy onto session-spawned containers and networks so that
	// `claude-dev stop` / `reset` can find them later (DSN-env-04).
	//
	// claude-dev.managed is deliberately NOT written: logout/reset select their
	// bulk-delete set by managed=1, so adding it would make `logout` delete
	// session-spawned resources — the opposite of D0-env-05 項2.
	projectDirLabel = "claude-dev.project-dir"
	roleLabel       = "claude-dev.role"
	ownerLabel      = "claude-dev.owner-project-dir"
	roleSpawned     = "spawned"
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

// resolveProjectDir maps a caller's source IP to TWO values, both taken from the
// same /containers/json response so the lookup stays one request:
//
//	workspaceSource — the host path the caller mounts at /workspace. Used to
//	                  rewrite binds. "" when the caller cannot be resolved.
//	ownerProjectDir — the value of the caller's claude-dev.project-dir label.
//	                  Copied verbatim into the owner label. "" when the caller
//	                  cannot be resolved OR carries no such label.
//
// The two are independent: a Claude container started before management labels
// existed yields a workspaceSource but no ownerProjectDir.
//
// The owner value deliberately comes from the LABEL, not from workspaceSource:
// `claude-dev stop` selects resources by a string comparison between
// claude-dev.owner-project-dir and claude-dev.project-dir, so taking both from
// the same single label makes the match a structural consequence rather than
// something that has to be verified (DSN-env-04).
//
// It is a var so tests can inject a stub instead of hitting the Docker API.
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
	workspaceSource string
	ownerProjectDir string
	exp             time.Time
}

var (
	projectCache   = map[string]projectCacheEntry{}
	projectCacheMu sync.Mutex
)

// cachedResolveProjectDir wraps lookupProjectDir with a short TTL cache.
// Both values are cached together because they come from one lookup.
func cachedResolveProjectDir(remoteIP string) (string, string) {
	projectCacheMu.Lock()
	if e, ok := projectCache[remoteIP]; ok && time.Now().Before(e.exp) {
		projectCacheMu.Unlock()
		return e.workspaceSource, e.ownerProjectDir
	}
	projectCacheMu.Unlock()

	src, owner := lookupProjectDir(remoteIP)

	projectCacheMu.Lock()
	projectCache[remoteIP] = projectCacheEntry{
		workspaceSource: src,
		ownerProjectDir: owner,
		exp:             time.Now().Add(projectCacheTTL),
	}
	projectCacheMu.Unlock()
	return src, owner
}

// lookupProjectDir asks the Docker daemon for the container whose network IP is
// remoteIP and returns (host source of its /workspace mount, value of its
// claude-dev.project-dir label). Either is "" when unavailable. One request
// yields both: the /containers/json response already carries Labels.
func lookupProjectDir(remoteIP string) (string, string) {
	resp, err := dockerHTTP.Get("http://docker/containers/json")
	if err != nil {
		return "", ""
	}
	defer resp.Body.Close()
	var cs []struct {
		Labels map[string]string `json:"Labels"`
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
		return "", ""
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
		src := ""
		for _, m := range c.Mounts {
			if m.Destination == workspaceMount {
				src = m.Source
				break
			}
		}
		// An empty label value counts as "not identified" (DSN-env-04): copying
		// it would produce a resource that `stop` cannot select but `reset` can
		// delete, which is exactly the split the single-label design prevents.
		return src, c.Labels[projectDirLabel]
	}
	return "", ""
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

// injectOwnerLabels writes the two owner labels into the TOP-LEVEL "Labels"
// object of a create request body (both container create and network create put
// Labels there). It returns (body, false) unchanged when owner is empty or the
// body cannot be parsed — never an error, because failing to mark a resource
// must not reject its creation (FR-env-07 受入基準12 / DSN-dp-01).
//
// A label the user set under the same key is overwritten: if the caller could
// choose the owner, `stop` could be pointed at another session's resources.
// Nothing else in the request is touched.
func injectOwnerLabels(body []byte, owner string) ([]byte, bool) {
	if owner == "" || len(body) == 0 {
		return body, false
	}
	var top map[string]json.RawMessage
	if err := json.Unmarshal(body, &top); err != nil {
		return body, false // unparseable: relay as-is (existing policy)
	}
	labels := map[string]string{}
	if raw, ok := top["Labels"]; ok && string(raw) != "null" {
		if err := json.Unmarshal(raw, &labels); err != nil {
			return body, false
		}
	}
	labels[roleLabel] = roleSpawned
	labels[ownerLabel] = owner

	nl, err := json.Marshal(labels)
	if err != nil {
		return body, false
	}
	top["Labels"] = nl
	nbody, err := json.Marshal(top)
	if err != nil {
		return body, false
	}
	return nbody, true
}

// writeBackBody replaces the request body exactly once, keeping ContentLength
// and the Content-Length header in step. Splitting this across two rewrites is
// what MODULE-docker-proxy-serve 判断8 forbids.
func writeBackBody(r *http.Request, body []byte) {
	r.Body = io.NopCloser(bytes.NewReader(body))
	r.ContentLength = int64(len(body))
	r.Header.Set("Content-Length", strconv.Itoa(len(body)))
}

// labelCreateRequest marks a create request with the caller's owner labels.
// Network and volume creation carry nothing that can endanger the host, so they
// have no rejection checks — only the marking. `kind` names the resource in the
// log lines; it is passed in rather than derived from the path because each
// route matches its own regexp, so the caller already knows which one fired.
//
// Volume creation joined this route on 2026-08-19: named volumes became part of
// the cleanup set (CTR-cli-container の規則 D). Anonymous volumes never reach
// here — they have no create request of their own; the daemon makes them while
// creating a container — so they are cleaned up by `docker rm -v` on the owning
// container instead.
func labelCreateRequest(r *http.Request, logger *log.Logger, kind string) {
	body, err := readAndRestoreBody(r)
	if err != nil {
		logger.Printf("WARN: could not read %s create body: %v", kind, err)
		return
	}
	_, owner := resolveProjectDir(clientIP(r.RemoteAddr))
	if owner == "" {
		logger.Printf("NO-OWNER-LABEL %s: caller not identified; relaying unlabelled", kind)
		return
	}
	nbody, changed := injectOwnerLabels(body, owner)
	if !changed {
		logger.Printf("NO-OWNER-LABEL %s: body not rewritable; relaying unlabelled", kind)
		return
	}
	writeBackBody(r, nbody)
	logger.Printf("OWNER-LABEL %s: owner=%s", kind, owner)
}

// labelNetworkCreate / labelVolumeCreate are the two routes' entry points.
func labelNetworkCreate(r *http.Request, logger *log.Logger) {
	labelCreateRequest(r, logger, "network")
}

func labelVolumeCreate(r *http.Request, logger *log.Logger) {
	labelCreateRequest(r, logger, "volume")
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

// networkCreateRe matches POST /networks/create, with or without the API
// version prefix — the same shape as containerCreateRe, because clients send
// both /networks/create and /v1.45/networks/create (判断9).
var networkCreateRe = regexp.MustCompile(`^(/v[\d.]+)?/networks/create`)

// volumeCreateRe matches POST /volumes/create, with or without the API version
// prefix. It is kept separate from networkCreateRe rather than folded into one
// alternation so that whichever regexp matches IS the resource kind for the log
// line — an alternation would mean re-deriving the kind from the path.
var volumeCreateRe = regexp.MustCompile(`^(/v[\d.]+)?/volumes/create`)

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

		// Network create requests carry nothing that can endanger the host, so
		// they have no rejection checks — the proxy only marks them so that
		// `stop` / `reset` can clean them up later (DSN-env-04).
		if r.Method == http.MethodPost && networkCreateRe.MatchString(path) {
			labelNetworkCreate(r, logger)
		}

		// Volume create requests are the same shape: no rejection checks, only
		// the marking, so that `stop --volumes` / `reset --volumes` can find
		// them later (DSN-env-04).
		if r.Method == http.MethodPost && volumeCreateRe.MatchString(path) {
			labelVolumeCreate(r, logger)
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

	// Resolve the caller ONCE; the bind rewrite and the owner label share it.
	workspaceSource, owner := resolveProjectDir(clientIP(r.RemoteAddr))

	newBody := body
	bindsChanged := false
	projectDir := ""

	// A body without HostConfig has nothing to reject and no bind to rewrite,
	// but it still gets an owner label below — `docker run alpine true` is the
	// most ordinary way to create a session-spawned container.
	if hc := req.HostConfig; hc != nil {
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
		// feature is off or the caller can't be resolved, projectDir stays ""
		// and rewriteBinds rejects every absolute host bind (pre-existing).
		//
		// Binds are judged BEFORE capabilities and devices on purpose: "you
		// brought something in from outside the workspace" is the reason users
		// hit most, so the contract returns it first (CTR-docker-api 判定の順序).
		if allowWorkspaceBinds {
			projectDir = workspaceSource
		}
		rewritten, changed, err := rewriteBinds(body, projectDir)
		if err != nil {
			return err
		}
		if changed {
			newBody, bindsChanged = rewritten, true
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
	}

	// --- every rejection check has passed from here on ---

	// Owner labels. Deliberately independent of allowWorkspaceBinds: turning
	// bind rewriting off must not silently stop marking resources, or `stop`
	// would find nothing to clean up (CTR-docker-api「検査する要素と判定」).
	// Marking a request that is about to be rejected would be pointless, and
	// putting the injection earlier would let its failure skip a rejection —
	// hence its position after the checks (判断5).
	labelled := false
	if owner != "" {
		if b, changed := injectOwnerLabels(newBody, owner); changed {
			newBody, labelled = b, true
		}
	}

	// One reconstruction per request (判断8): both rewrites are already folded
	// into newBody, so ContentLength is written exactly once.
	if bindsChanged || labelled {
		writeBackBody(r, newBody)
	}
	if bindsChanged {
		logger.Printf("REWRITE binds: /workspace -> %s", projectDir)
	}
	// Every path that relays without the owner label logs its reason
	// (FR-env-07 受入基準12 / 02-design/logging.md「所有者ラベルを付与せずに中継した」).
	// The network path already had both reasons; the container path used to have
	// only "caller not identified", so a resolvable owner whose injection failed
	// relayed silently and the resource dropped out of `stop`/`reset` cleanup
	// with nothing in the log to explain it.
	switch {
	case labelled:
		logger.Printf("OWNER-LABEL container: owner=%s", owner)
	case owner == "":
		logger.Printf("NO-OWNER-LABEL container: caller not identified; relaying unlabelled")
	default:
		logger.Printf("NO-OWNER-LABEL container: body not rewritable; relaying unlabelled")
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

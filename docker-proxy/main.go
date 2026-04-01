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
	"regexp"
	"strings"
	"sync"
)

const (
	listenAddr = ":2375"
	socketPath = "/var/run/docker.sock"
)

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

	// Check Binds (host path mounts).
	for _, bind := range hc.Binds {
		// Binds are in the format "hostPath:containerPath[:options]".
		// A named volume does not start with "/".
		parts := strings.SplitN(bind, ":", 2)
		if len(parts) >= 1 && strings.HasPrefix(parts[0], "/") {
			return fmt.Errorf("host bind mount is not allowed: %s", bind)
		}
	}

	// Check Mounts (alternative mount specification).
	for _, m := range hc.Mounts {
		if m.Type == "bind" {
			return fmt.Errorf("bind mount is not allowed: source=%s", m.Source)
		}
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

package main

import (
	"bytes"
	"io"
	"log"
	"net/http"
	"testing"
)

func newRequest(method, path, body string) *http.Request {
	var bodyReader io.Reader
	if body != "" {
		bodyReader = bytes.NewBufferString(body)
	}
	req, _ := http.NewRequest(method, "http://docker"+path, bodyReader)
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	return req
}

func TestValidateContainerCreate_AllowsCleanRequest(t *testing.T) {
	body := `{"Image":"nginx:latest","HostConfig":{}}`
	req := newRequest("POST", "/containers/create", body)
	logger := log.New(io.Discard, "", 0)

	if err := validateContainerCreate(req, logger); err != nil {
		t.Errorf("expected allow, got: %v", err)
	}
}

func TestValidateContainerCreate_AllowsNamedVolume(t *testing.T) {
	body := `{"Image":"nginx","HostConfig":{"Binds":["myvolume:/data"]}}`
	req := newRequest("POST", "/containers/create", body)
	logger := log.New(io.Discard, "", 0)

	if err := validateContainerCreate(req, logger); err != nil {
		t.Errorf("expected allow named volume, got: %v", err)
	}
}

func TestValidateContainerCreate_BlocksHostBind(t *testing.T) {
	body := `{"Image":"nginx","HostConfig":{"Binds":["/host/path:/container/path"]}}`
	req := newRequest("POST", "/containers/create", body)
	logger := log.New(io.Discard, "", 0)

	if err := validateContainerCreate(req, logger); err == nil {
		t.Error("expected block for host bind mount, got allow")
	}
}

func TestValidateContainerCreate_BlocksBindMount(t *testing.T) {
	body := `{"Image":"nginx","HostConfig":{"Mounts":[{"Type":"bind","Source":"/etc","Target":"/mnt"}]}}`
	req := newRequest("POST", "/containers/create", body)
	logger := log.New(io.Discard, "", 0)

	if err := validateContainerCreate(req, logger); err == nil {
		t.Error("expected block for bind mount, got allow")
	}
}

func TestValidateContainerCreate_BlocksPrivileged(t *testing.T) {
	body := `{"Image":"nginx","HostConfig":{"Privileged":true}}`
	req := newRequest("POST", "/containers/create", body)
	logger := log.New(io.Discard, "", 0)

	if err := validateContainerCreate(req, logger); err == nil {
		t.Error("expected block for privileged, got allow")
	}
}

func TestValidateContainerCreate_BlocksPidHost(t *testing.T) {
	body := `{"Image":"nginx","HostConfig":{"PidMode":"host"}}`
	req := newRequest("POST", "/containers/create", body)
	logger := log.New(io.Discard, "", 0)

	if err := validateContainerCreate(req, logger); err == nil {
		t.Error("expected block for PidMode=host, got allow")
	}
}

func TestValidateContainerCreate_BlocksNetworkHost(t *testing.T) {
	body := `{"Image":"nginx","HostConfig":{"NetworkMode":"host"}}`
	req := newRequest("POST", "/containers/create", body)
	logger := log.New(io.Discard, "", 0)

	if err := validateContainerCreate(req, logger); err == nil {
		t.Error("expected block for NetworkMode=host, got allow")
	}
}

func TestValidateContainerCreate_BlocksUsernsHost(t *testing.T) {
	body := `{"Image":"nginx","HostConfig":{"UsernsMode":"host"}}`
	req := newRequest("POST", "/containers/create", body)
	logger := log.New(io.Discard, "", 0)

	if err := validateContainerCreate(req, logger); err == nil {
		t.Error("expected block for UsernsMode=host, got allow")
	}
}

func TestValidateContainerCreate_BlocksDangerousCaps(t *testing.T) {
	body := `{"Image":"nginx","HostConfig":{"CapAdd":["SYS_ADMIN"]}}`
	req := newRequest("POST", "/containers/create", body)
	logger := log.New(io.Discard, "", 0)

	if err := validateContainerCreate(req, logger); err == nil {
		t.Error("expected block for SYS_ADMIN cap, got allow")
	}
}

func TestValidateContainerCreate_AllowsSafeCaps(t *testing.T) {
	body := `{"Image":"nginx","HostConfig":{"CapAdd":["NET_ADMIN"]}}`
	req := newRequest("POST", "/containers/create", body)
	logger := log.New(io.Discard, "", 0)

	if err := validateContainerCreate(req, logger); err != nil {
		t.Errorf("expected allow for NET_ADMIN cap, got: %v", err)
	}
}

func TestValidateContainerCreate_BlocksDevices(t *testing.T) {
	body := `{"Image":"nginx","HostConfig":{"Devices":[{"PathOnHost":"/dev/sda"}]}}`
	req := newRequest("POST", "/containers/create", body)
	logger := log.New(io.Discard, "", 0)

	if err := validateContainerCreate(req, logger); err == nil {
		t.Error("expected block for device mapping, got allow")
	}
}

func TestValidateContainerCreate_AllowsNoHostConfig(t *testing.T) {
	body := `{"Image":"nginx"}`
	req := newRequest("POST", "/containers/create", body)
	logger := log.New(io.Discard, "", 0)

	if err := validateContainerCreate(req, logger); err != nil {
		t.Errorf("expected allow with no HostConfig, got: %v", err)
	}
}

func TestValidateContainerCreate_AllowsEmptyBody(t *testing.T) {
	req := newRequest("POST", "/containers/create", "")
	req.Body = nil
	logger := log.New(io.Discard, "", 0)

	if err := validateContainerCreate(req, logger); err != nil {
		t.Errorf("expected allow with nil body, got: %v", err)
	}
}

func TestValidateExecCreate_BlocksPrivileged(t *testing.T) {
	body := `{"Cmd":["sh"],"Privileged":true}`
	req := newRequest("POST", "/containers/abc123/exec", body)
	logger := log.New(io.Discard, "", 0)

	if err := validateExecCreate(req, logger); err == nil {
		t.Error("expected block for privileged exec, got allow")
	}
}

func TestValidateExecCreate_AllowsNormal(t *testing.T) {
	body := `{"Cmd":["sh"],"Privileged":false}`
	req := newRequest("POST", "/containers/abc123/exec", body)
	logger := log.New(io.Discard, "", 0)

	if err := validateExecCreate(req, logger); err != nil {
		t.Errorf("expected allow for normal exec, got: %v", err)
	}
}

func TestContainerCreateRe(t *testing.T) {
	tests := []struct {
		path  string
		match bool
	}{
		{"/containers/create", true},
		{"/v1.45/containers/create", true},
		{"/containers/abc123/start", false},
		{"/images/json", false},
	}
	for _, tt := range tests {
		if got := containerCreateRe.MatchString(tt.path); got != tt.match {
			t.Errorf("containerCreateRe.MatchString(%q) = %v, want %v", tt.path, got, tt.match)
		}
	}
}

func TestHijackEndpointRe(t *testing.T) {
	tests := []struct {
		path  string
		match bool
	}{
		{"/exec/abc123/start", true},
		{"/v1.45/exec/abc123/start", true},
		{"/containers/abc123/attach", true},
		{"/v1.45/containers/abc123/attach", true},
		{"/exec/abc123/resize", true},
		{"/containers/abc123/resize", true},
		{"/containers/abc123/start", false},
		{"/containers/create", false},
		{"/images/json", false},
	}
	for _, tt := range tests {
		if got := hijackEndpointRe.MatchString(tt.path); got != tt.match {
			t.Errorf("hijackEndpointRe.MatchString(%q) = %v, want %v", tt.path, got, tt.match)
		}
	}
}

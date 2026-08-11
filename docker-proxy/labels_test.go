package main

import (
	"bytes"
	"encoding/json"
	"io"
	"log"
	"strconv"
	"strings"
	"testing"
)

// 所有者ラベルの注入(FR-env-07 受入基準11・12 / DSN-env-04)の単体テスト。
//
// 「呼び出し元を特定できた」は resolveProjectDir の 2 値目が空でないことである。
// 実 Docker を叩かないよう、いずれの試験もこの関数をスタブに差し替える。

const testOwner = "/home/u/work/my-app"

// stubCaller は resolveProjectDir を (マウント元, 所有者) に固定し、後始末を返す。
func stubCaller(t *testing.T, mountSource, owner string) {
	t.Helper()
	orig := resolveProjectDir
	resolveProjectDir = func(_ string) (string, string) { return mountSource, owner }
	t.Cleanup(func() { resolveProjectDir = orig })
}

// bodyLabels は書き戻された要求ボディのトップレベル Labels を取り出す。
func bodyLabels(t *testing.T, raw []byte) map[string]string {
	t.Helper()
	var top struct {
		Labels map[string]string `json:"Labels"`
	}
	if err := json.Unmarshal(raw, &top); err != nil {
		t.Fatalf("書き戻されたボディが JSON として読めない: %v (%s)", err, raw)
	}
	return top.Labels
}

func TestValidateContainerCreate_InjectsOwnerLabels(t *testing.T) {
	stubCaller(t, "/host/proj", testOwner)

	req := newRequest("POST", "/containers/create", `{"Image":"busybox","HostConfig":{}}`)
	req.RemoteAddr = "172.20.0.9:5000"
	if err := validateContainerCreate(req, log.New(io.Discard, "", 0)); err != nil {
		t.Fatalf("拒否されないはず: %v", err)
	}

	got, _ := io.ReadAll(req.Body)
	labels := bodyLabels(t, got)
	if labels[roleLabel] != roleSpawned {
		t.Errorf("%s=%s を期待したが %q", roleLabel, roleSpawned, labels[roleLabel])
	}
	if labels[ownerLabel] != testOwner {
		t.Errorf("%s=%s を期待したが %q", ownerLabel, testOwner, labels[ownerLabel])
	}
}

// HostConfig を持たない要求(`docker run alpine true` が出す形)にも印が付く。
func TestValidateContainerCreate_InjectsOwnerLabelsWithoutHostConfig(t *testing.T) {
	stubCaller(t, "", testOwner)

	req := newRequest("POST", "/containers/create", `{"Image":"alpine"}`)
	req.RemoteAddr = "172.20.0.9:5000"
	if err := validateContainerCreate(req, log.New(io.Discard, "", 0)); err != nil {
		t.Fatalf("拒否されないはず: %v", err)
	}

	got, _ := io.ReadAll(req.Body)
	if labels := bodyLabels(t, got); labels[ownerLabel] != testOwner {
		t.Errorf("HostConfig 無しでも所有者ラベルが要る: %v", labels)
	}
}

// 「要求のそれ以外のフィールドを変更してはならない」(FR-env-07 受入基準11)。
func TestValidateContainerCreate_InjectionLeavesOtherFieldsIntact(t *testing.T) {
	stubCaller(t, "", testOwner)

	body := `{"Image":"busybox","Cmd":["sleep","600"],"Env":["A=1"],"HostConfig":{"AutoRemove":true}}`
	req := newRequest("POST", "/containers/create", body)
	req.RemoteAddr = "172.20.0.9:5000"
	if err := validateContainerCreate(req, log.New(io.Discard, "", 0)); err != nil {
		t.Fatalf("拒否されないはず: %v", err)
	}

	got, _ := io.ReadAll(req.Body)
	var before, after map[string]any
	if err := json.Unmarshal([]byte(body), &before); err != nil {
		t.Fatal(err)
	}
	if err := json.Unmarshal(got, &after); err != nil {
		t.Fatalf("書き戻されたボディが読めない: %v (%s)", err, got)
	}
	delete(after, "Labels")
	beforeJSON, _ := json.Marshal(before)
	afterJSON, _ := json.Marshal(after)
	if string(beforeJSON) != string(afterJSON) {
		t.Errorf("Labels 以外が変わっている\n前: %s\n後: %s", beforeJSON, afterJSON)
	}
}

// 利用者が同じキーを指定していたら proxy の値で上書きする(所有者の判定が
// 利用者の入力で狂うと、別セッションの資源を消しうる)。
func TestValidateContainerCreate_OverwritesUserSuppliedOwnerLabel(t *testing.T) {
	stubCaller(t, "", testOwner)

	req := newRequest("POST", "/containers/create",
		`{"Image":"busybox","Labels":{"claude-dev.owner-project-dir":"/etc","claude-dev.role":"claude","keep":"me"}}`)
	req.RemoteAddr = "172.20.0.9:5000"
	if err := validateContainerCreate(req, log.New(io.Discard, "", 0)); err != nil {
		t.Fatalf("拒否されないはず: %v", err)
	}

	got, _ := io.ReadAll(req.Body)
	labels := bodyLabels(t, got)
	if labels[ownerLabel] != testOwner {
		t.Errorf("利用者の値が残っている: %q", labels[ownerLabel])
	}
	if labels[roleLabel] != roleSpawned {
		t.Errorf("利用者の値が残っている: %q", labels[roleLabel])
	}
	if labels["keep"] != "me" {
		t.Errorf("利用者の他のラベルを消してはならない: %v", labels)
	}
}

// 呼び出し元を特定できないときは付与せず、しかし拒否もしない
// (FR-env-07 受入基準12)。
func TestValidateContainerCreate_NoOwnerLabelWhenCallerUnknown(t *testing.T) {
	stubCaller(t, "", "")

	req := newRequest("POST", "/containers/create", `{"Image":"busybox"}`)
	req.RemoteAddr = "172.20.0.9:5000"
	if err := validateContainerCreate(req, log.New(io.Discard, "", 0)); err != nil {
		t.Fatalf("付与できなくても拒否してはならない: %v", err)
	}

	got, _ := io.ReadAll(req.Body)
	if labels := bodyLabels(t, got); labels[ownerLabel] != "" || labels[roleLabel] != "" {
		t.Errorf("特定できないのにラベルが付いている: %v", labels)
	}
}

// 呼び出し元は引き当てられたがラベルの値が空文字のときも「特定できない」に倒す。
// 空値を写すと `stop` では引けないが `reset` では消える資源ができ、
// 両側が同じ1つのラベルに依存するという DSN-env-04 の根拠がその1点で破れる。
func TestValidateContainerCreate_NoOwnerLabelWhenProjectDirEmpty(t *testing.T) {
	stubCaller(t, "/host/proj", "") // bind は書き換えられるが所有者は得られない

	req := newRequest("POST", "/containers/create", `{"Image":"busybox"}`)
	req.RemoteAddr = "172.20.0.9:5000"
	if err := validateContainerCreate(req, log.New(io.Discard, "", 0)); err != nil {
		t.Fatalf("拒否してはならない: %v", err)
	}

	got, _ := io.ReadAll(req.Body)
	if labels := bodyLabels(t, got); labels[ownerLabel] != "" {
		t.Errorf("空の所有者を書き込んではならない: %v", labels)
	}
}

// ボディが JSON として解釈できないときは元のまま中継し、拒否しない。
func TestValidateContainerCreate_UnparseableBodyRelayedUnchanged(t *testing.T) {
	stubCaller(t, "", testOwner)

	const broken = `{"Image":`
	req := newRequest("POST", "/containers/create", broken)
	req.RemoteAddr = "172.20.0.9:5000"
	if err := validateContainerCreate(req, log.New(io.Discard, "", 0)); err != nil {
		t.Fatalf("解釈できないボディは通す: %v", err)
	}

	got, _ := io.ReadAll(req.Body)
	if string(got) != broken {
		t.Errorf("ボディを書き換えてはならない: %s", got)
	}
}

// 拒否される要求には印を付けない(判断5: 注入は拒否判定をすべて通過したあと)。
func TestValidateContainerCreate_RejectedRequestIsNotLabelled(t *testing.T) {
	stubCaller(t, "", testOwner)

	req := newRequest("POST", "/containers/create", `{"HostConfig":{"Privileged":true}}`)
	req.RemoteAddr = "172.20.0.9:5000"
	if err := validateContainerCreate(req, log.New(io.Discard, "", 0)); err == nil {
		t.Fatal("privileged は拒否されるはず")
	}

	got, _ := io.ReadAll(req.Body)
	if labels := bodyLabels(t, got); labels[ownerLabel] != "" {
		t.Errorf("拒否した要求に印を付けてはならない: %v", labels)
	}
}

// bind の書き換えと所有者ラベルの注入が同じ要求で起きても、
// ボディの再構成は1回だけで Content-Length が整合する(判断8)。
func TestValidateContainerCreate_BindRewriteAndLabelShareOneReconstruction(t *testing.T) {
	proj := t.TempDir()
	stubCaller(t, proj, testOwner)

	req := newRequest("POST", "/containers/create",
		`{"Image":"busybox","HostConfig":{"Binds":["/workspace/app:/app"]}}`)
	req.RemoteAddr = "172.20.0.9:5000"
	if err := validateContainerCreate(req, log.New(io.Discard, "", 0)); err != nil {
		t.Fatalf("拒否されないはず: %v", err)
	}

	got, _ := io.ReadAll(req.Body)
	if req.ContentLength != int64(len(got)) {
		t.Errorf("ContentLength=%d だが本体は %d バイト", req.ContentLength, len(got))
	}
	if h := req.Header.Get("Content-Length"); h != strconv.Itoa(len(got)) {
		t.Errorf("Content-Length ヘッダ=%q だが本体は %d バイト", h, len(got))
	}
	// 両方の書き換えが残っていること(片方が失われる経路が無い)。
	if labels := bodyLabels(t, got); labels[ownerLabel] != testOwner {
		t.Errorf("所有者ラベルが失われた: %v", labels)
	}
	var top struct {
		HostConfig struct {
			Binds []string `json:"Binds"`
		} `json:"HostConfig"`
	}
	if err := json.Unmarshal(got, &top); err != nil {
		t.Fatal(err)
	}
	if len(top.HostConfig.Binds) != 1 || top.HostConfig.Binds[0] != proj+"/app:/app" {
		t.Errorf("bind の書き換えが失われた: %v", top.HostConfig.Binds)
	}
}

// ラベルの付与は CLAUDE_DEV_ALLOW_WORKSPACE_BINDS に依存しない。
// bind を全面拒否へ倒した環境でも `stop` は片付けられなければならない。
func TestValidateContainerCreate_LabelsIndependentOfBindSwitch(t *testing.T) {
	stubCaller(t, "/host/proj", testOwner)
	orig := allowWorkspaceBinds
	allowWorkspaceBinds = false
	t.Cleanup(func() { allowWorkspaceBinds = orig })

	req := newRequest("POST", "/containers/create", `{"Image":"busybox"}`)
	req.RemoteAddr = "172.20.0.9:5000"
	if err := validateContainerCreate(req, log.New(io.Discard, "", 0)); err != nil {
		t.Fatalf("拒否されないはず: %v", err)
	}

	got, _ := io.ReadAll(req.Body)
	if labels := bodyLabels(t, got); labels[ownerLabel] != testOwner {
		t.Errorf("bind 無効でも所有者ラベルは付ける: %v", labels)
	}
}

// ネットワーク作成要求にも同じ2つのラベルが付く。拒否判定は持たない。
func TestLabelNetworkCreate_InjectsOwnerLabels(t *testing.T) {
	stubCaller(t, "", testOwner)

	req := newRequest("POST", "/networks/create", `{"Name":"spawn-net","Driver":"bridge"}`)
	req.RemoteAddr = "172.20.0.9:5000"
	labelNetworkCreate(req, log.New(io.Discard, "", 0))

	got, _ := io.ReadAll(req.Body)
	labels := bodyLabels(t, got)
	if labels[roleLabel] != roleSpawned || labels[ownerLabel] != testOwner {
		t.Errorf("ネットワークに所有者ラベルが付いていない: %v", labels)
	}
	var top struct {
		Name   string `json:"Name"`
		Driver string `json:"Driver"`
	}
	if err := json.Unmarshal(got, &top); err != nil {
		t.Fatal(err)
	}
	if top.Name != "spawn-net" || top.Driver != "bridge" {
		t.Errorf("他のフィールドが変わっている: %+v", top)
	}
}

func TestLabelNetworkCreate_NoOwnerLeavesBodyUntouched(t *testing.T) {
	stubCaller(t, "", "")

	const body = `{"Name":"spawn-net"}`
	req := newRequest("POST", "/networks/create", body)
	req.RemoteAddr = "172.20.0.9:5000"
	labelNetworkCreate(req, log.New(io.Discard, "", 0))

	got, _ := io.ReadAll(req.Body)
	if string(got) != body {
		t.Errorf("特定できないときはボディを触らない: %s", got)
	}
}

func TestNetworkCreateRe(t *testing.T) {
	for _, p := range []string{"/networks/create", "/v1.45/networks/create"} {
		if !networkCreateRe.MatchString(p) {
			t.Errorf("一致するはず: %s", p)
		}
	}
	for _, p := range []string{"/networks", "/networks/abc/connect", "/containers/create"} {
		if networkCreateRe.MatchString(p) {
			t.Errorf("一致してはならない: %s", p)
		}
	}
}

// injectOwnerLabels 単体: 所有者が空なら何もしない。
func TestInjectOwnerLabels_EmptyOwnerIsNoop(t *testing.T) {
	const body = `{"Image":"busybox"}`
	out, changed := injectOwnerLabels([]byte(body), "")
	if changed || string(out) != body {
		t.Errorf("所有者が空なら書き換えない: changed=%v out=%s", changed, out)
	}
}

// 所有者ラベルを付与せずに中継したときは、**どの経路でも理由をログへ1行出す**
// (FR-env-07 受入基準12 / 02-design/logging.md「所有者ラベルを付与せずに中継した」)。
// コンテナ作成経路は分岐が「付与した」と「所有者が空」の2つしかなく、
// **所有者は解決できたのに注入に失敗した場合だけ1行も出なかった**(issue 087)。
func TestValidateContainerCreate_LogsReasonWhenNotLabelled(t *testing.T) {
	cases := []struct {
		name  string
		owner string
		body  string
		want  string
	}{
		{"呼び出し元を特定できない", "", `{"Image":"busybox"}`, "caller not identified"},
		// **到達できる失敗の形はこれである**: 外側のボディは読めるので
		// validateContainerCreate は早期 return せず、injectOwnerLabels の中で
		// Labels を map[string]string として読む所だけが失敗する。
		// (ボディ全体が壊れている場合は、その手前の WARN で早期 return する)
		{"所有者は解決できたが Labels を書き換えられない", testOwner, `{"Image":"busybox","Labels":5}`, "body not rewritable"},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			stubCaller(t, "", c.owner)
			var buf bytes.Buffer
			req := newRequest("POST", "/containers/create", c.body)
			req.RemoteAddr = "172.20.0.9:5000"
			if err := validateContainerCreate(req, log.New(&buf, "", 0)); err != nil {
				t.Fatalf("拒否されないはず: %v", err)
			}
			got := buf.String()
			if !strings.Contains(got, "NO-OWNER-LABEL container") || !strings.Contains(got, c.want) {
				t.Errorf("理由つきのログが要る。期待する語=%q / 実際のログ=%q", c.want, got)
			}
		})
	}
}

// 付与できたときは NO-OWNER-LABEL を出さない(理由のログが常に出るようになっていないこと)。
func TestValidateContainerCreate_NoReasonLogWhenLabelled(t *testing.T) {
	stubCaller(t, "", testOwner)
	var buf bytes.Buffer
	req := newRequest("POST", "/containers/create", `{"Image":"busybox"}`)
	req.RemoteAddr = "172.20.0.9:5000"
	if err := validateContainerCreate(req, log.New(&buf, "", 0)); err != nil {
		t.Fatalf("拒否されないはず: %v", err)
	}
	if strings.Contains(buf.String(), "NO-OWNER-LABEL") {
		t.Errorf("付与できたのに未付与のログが出ている: %q", buf.String())
	}
}

package main

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
)

func testApp(t *testing.T) (*Application, string) {
	t.Helper()
	root, _ := fixture(t)
	addDelivery(t, root, "report", "case-a", "EX")
	app, err := newApplication(Locations{State: t.TempDir(), Documents: t.TempDir()}, root)
	if err != nil {
		t.Fatal(err)
	}
	app.host = "127.0.0.1:54321"
	app.stop = func() {}
	return app, root
}
func call(app *Application, method, endpoint, body string) *httptest.ResponseRecorder {
	r := httptest.NewRequest(method, "http://"+app.host+endpoint, strings.NewReader(body))
	if method == "POST" {
		r.Header.Set("X-Issuer-Library", "1")
		r.Header.Set("Content-Type", "application/json")
		r.Header.Set("Origin", "http://"+app.host)
	}
	w := httptest.NewRecorder()
	app.ServeHTTP(w, r)
	return w
}

func TestLauncherDeliveryIsVerifiedAndPresentedLikeAnyDeliverable(t *testing.T) {
	app, root := testApp(t)
	folder := filepath.Join(root, "runs", "launched", "deliveries", "abc")
	if err := os.MkdirAll(folder, 0700); err != nil {
		t.Fatal(err)
	}
	files := map[string]string{"report.html": "<html><body>Report</body></html>", "view.json": `{"run":{"run_id":"r","issuer_id":"nbg","issuer_name":"Northbridge","as_of":"2025-03-31"}}`, "CP-1.md": "# CP-1\n"}
	hashes := map[string]string{}
	for name, text := range files {
		if err := os.WriteFile(filepath.Join(folder, name), []byte(text), 0600); err != nil {
			t.Fatal(err)
		}
		hashes[name] = digest([]byte(text))
	}
	if err := saveJSON(filepath.Join(folder, "delivery.json"), map[string]any{"files": hashes}); err != nil {
		t.Fatal(err)
	}
	if response := call(app, "POST", "/api/refresh", "{}"); response.Code != 200 {
		t.Fatal(response.Body.String())
	}
	found := false
	for _, run := range app.catalogue.Real {
		for _, artifact := range run.Artifacts {
			if run.ID == "launched" && artifact.Folder == "runs/launched/deliveries/abc" && artifact.Available {
				found = true
				shown := call(app, "GET", artifact.Href+"&embedded=1", "")
				if shown.Code != 200 || !strings.Contains(shown.Body.String(), "data-library-presentation") {
					t.Fatalf("report was not presented: %d", shown.Code)
				}
				saved := call(app, "GET", artifact.Href+"&download=1", "")
				if !strings.Contains(saved.Header().Get("Content-Disposition"), "abc.html") || strings.Contains(saved.Body.String(), "data-library-presentation") {
					t.Fatal("download must be the original report under its deliverable name")
				}
			}
		}
	}
	if !found {
		t.Fatal("launcher delivery missing from its run")
	}
	if err := os.WriteFile(filepath.Join(folder, "report.html"), []byte("changed"), 0600); err != nil {
		t.Fatal(err)
	}
	call(app, "POST", "/api/refresh", "{}")
	for _, issue := range app.catalogue.Issues {
		if strings.Contains(issue, "deliveries/abc") {
			return
		}
	}
	t.Fatal("a changed delivery must be reported")
}

func TestHTTPBoundaryAndChangedFile(t *testing.T) {
	app, root := testApp(t)
	for _, name := range []string{"/", "/screen.js", "/fonts/RedHatText-Regular.woff2", "/api/catalogue", "/files/deliverables/report/report.html"} {
		response := call(app, "GET", name, "")
		if response.Code != 200 {
			t.Fatalf("%s: %d %s", name, response.Code, response.Body.String())
		}
	}
	for _, name := range []string{"/files/AGENTS.md", "/files/../secret", "/legacy-catalog.json"} {
		if response := call(app, "GET", name, ""); response.Code != 404 {
			t.Fatalf("exposed %s", name)
		}
	}
	for _, header := range []struct{ key, value string }{{"Host", "attacker.invalid"}, {"Origin", "https://attacker.invalid"}, {"Sec-Fetch-Site", "cross-site"}} {
		r := httptest.NewRequest("GET", "http://"+app.host+"/api/catalogue", nil)
		if header.key == "Host" {
			r.Host = header.value
		} else {
			r.Header.Set(header.key, header.value)
		}
		w := httptest.NewRecorder()
		app.ServeHTTP(w, r)
		if w.Code != 403 {
			t.Fatal("cross-origin request admitted")
		}
	}
	r := httptest.NewRequest("POST", "http://"+app.host+"/api/quit", strings.NewReader("{}"))
	w := httptest.NewRecorder()
	app.ServeHTTP(w, r)
	if w.Code != 403 {
		t.Fatal("unprotected state change")
	}
	response := call(app, "GET", "/files/deliverables/report/report.html", "")
	if !strings.Contains(response.Header().Get("Content-Security-Policy"), "sandbox allow-scripts") || strings.Contains(response.Header().Get("Content-Security-Policy"), "allow-same-origin") {
		t.Fatal("report can reach application origin")
	}
	put(t, root, "deliverables/report/report.html", []byte("new unverified version"))
	if response = call(app, "GET", "/files/deliverables/report/report.html", ""); response.Code != 409 {
		t.Fatal("changed report served")
	}
}

func TestRefreshSettingsAndPolicy(t *testing.T) {
	app, root := testApp(t)
	put(t, root, "runs/added/CP-0.md", []byte("added"))
	response := call(app, "POST", "/api/refresh", "{}")
	var cat Catalogue
	if err := json.Unmarshal(response.Body.Bytes(), &cat); err != nil {
		t.Fatal(err)
	}
	if len(cat.Real) != 2 {
		t.Fatal("refresh missed new run")
	}
	other := t.TempDir()
	put(t, other, "runs/other/CP-0.md", []byte("other"))
	raw, _ := json.Marshal(Config{Workspace: other})
	if response = call(app, "POST", "/api/settings", string(raw)); response.Code != 200 {
		t.Fatal(response.Body.String())
	}
	if response = call(app, "GET", "/files/runs/case-a/CP-0.md", ""); response.Code != 404 {
		t.Fatal("old workspace file remains admitted")
	}
	reloaded, err := newApplication(app.loc, "")
	if err != nil || reloaded.config.Workspace != other {
		t.Fatal("settings did not persist")
	}
	app.locked = true
	if response = call(app, "POST", "/api/settings", string(raw)); response.Code != 403 {
		t.Fatal("policy did not lock settings")
	}
	if response = call(app, "POST", "/api/settings", `{"workspace":"relative"}`); response.Code == 200 {
		t.Fatal("relative path accepted")
	}
}

func TestPolicyPrecedenceAndNoSilentFallback(t *testing.T) {
	loc := Locations{State: t.TempDir(), Policy: filepath.Join(t.TempDir(), "settings.json"), Documents: t.TempDir()}
	if err := saveJSON(filepath.Join(loc.State, "settings.json"), Config{Workspace: t.TempDir()}); err != nil {
		t.Fatal(err)
	}
	managed := t.TempDir()
	if err := saveJSON(loc.Policy, Config{Workspace: managed}); err != nil {
		t.Fatal(err)
	}
	config, locked, err := loadConfig(loc)
	if err != nil || !locked || config.Workspace != managed {
		t.Fatal("policy lost precedence")
	}
	if _, err := newApplication(loc, t.TempDir()); err == nil {
		t.Fatal("CLI bypassed policy")
	}
	if err := os.WriteFile(loc.Policy, []byte("{"), 0600); err != nil {
		t.Fatal(err)
	}
	if _, _, err := loadConfig(loc); err == nil {
		t.Fatal("malformed IT config silently ignored")
	}
}

func TestConcurrentRefreshAndReaders(t *testing.T) {
	app, _ := testApp(t)
	var group sync.WaitGroup
	for i := 0; i < 20; i++ {
		group.Go(func() {
			response := call(app, "GET", "/api/catalogue", "")
			if response.Code != http.StatusOK {
				t.Errorf("reader: %d", response.Code)
			}
		})
		group.Go(func() {
			response := call(app, "POST", "/api/refresh", "{}")
			if response.Code != http.StatusOK {
				t.Errorf("refresh: %d", response.Code)
			}
		})
	}
	group.Wait()
}

func TestPinnedLinkCannotSilentlyOpenLaterVersion(t *testing.T) {
	app, root := testApp(t)
	old := app.catalogue.Real[0].Artifacts[0].Href
	// Replace and publish a new, internally valid bundle in the same directory.
	content := []byte("<!doctype html><p>Later revision</p>")
	put(t, root, "deliverables/report/report.html", content)
	raw, err := os.ReadFile(filepath.Join(root, "deliverables/report/delivery.json"))
	if err != nil {
		t.Fatal(err)
	}
	var record struct {
		Files map[string]string `json:"files"`
	}
	if err = json.Unmarshal(raw, &record); err != nil {
		t.Fatal(err)
	}
	record.Files["report.html"] = digest(content)
	putJSON(t, root, "deliverables/report/delivery.json", record)
	call(app, "POST", "/api/refresh", "{}")
	if response := call(app, "GET", old, ""); response.Code != 409 {
		t.Fatal("old screen opened new report bytes without noticing")
	}
}

func TestReportRangeRequests(t *testing.T) {
	app, _ := testApp(t)
	request := httptest.NewRequest("GET", "http://"+app.host+"/files/deliverables/report/report.html", nil)
	request.Header.Set("Range", "bytes=0-14")
	response := httptest.NewRecorder()
	app.ServeHTTP(response, request)
	if response.Code != 206 || response.Body.String() != "<!doctype html>" {
		t.Fatalf("range contract failed: %d %s", response.Code, response.Body.String())
	}
}

type mutateOnServe struct {
	*httptest.ResponseRecorder
	once   sync.Once
	mutate func()
}

func (w *mutateOnServe) Header() http.Header {
	header := w.ResponseRecorder.Header()
	if header.Get("Content-Type") == "text/html; charset=utf-8" {
		w.once.Do(w.mutate)
	}
	return header
}
func TestResponseUsesTheBytesThatWereVerified(t *testing.T) {
	app, root := testApp(t)
	file := filepath.Join(root, "deliverables/report/report.html")
	original, err := os.ReadFile(file)
	if err != nil {
		t.Fatal(err)
	}
	changed := []byte(strings.Repeat("X", len(original)))
	response := &mutateOnServe{ResponseRecorder: httptest.NewRecorder(), mutate: func() {
		if err := os.WriteFile(file, changed, 0600); err != nil {
			t.Fatal(err)
		}
	}}
	request := httptest.NewRequest("GET", "http://"+app.host+"/files/deliverables/report/report.html", nil)
	app.ServeHTTP(response, request)
	if response.Code != 200 || response.Body.String() != string(original) {
		t.Fatal("served different bytes than the verified snapshot")
	}
}

func TestEmbeddedPresentationPreservesRetainedAndExportedReportBytes(t *testing.T) {
	app, root := testApp(t)
	name := "/files/deliverables/report/report.html"
	original, err := os.ReadFile(filepath.Join(root, "deliverables/report/report.html"))
	if err != nil {
		t.Fatal(err)
	}
	for _, query := range []string{"?embedded=1", "?download=1"} {
		response := call(app, "GET", name+query, "")
		if response.Code != 200 {
			t.Fatal(response.Body.String())
		}
		if query == "?embedded=1" {
			body := response.Body.Bytes()
			start := bytes.Index(body, []byte("<style data-library-presentation>"))
			end := bytes.LastIndex(body, []byte("</script>")) + len("</script>")
			if start < 0 || end < start {
				t.Fatal("embedded presentation is missing")
			}
			symbol, err := resources.ReadFile("web/brand/symbol.svg")
			if err != nil || !bytes.Contains(body, []byte("data:image/svg+xml;base64,"+base64.StdEncoding.EncodeToString(symbol))) {
				t.Fatal("embedded report does not carry the supplied offline symbol")
			}
			restored := append(append([]byte{}, body[:start]...), body[end:]...)
			if !bytes.Equal(restored, original) {
				t.Fatal("embedded view lost original content or its scoped presentation")
			}
		} else if response.Body.String() != string(original) {
			t.Fatal("HTML export changed original bytes")
		}
		policy := response.Header().Get("Content-Security-Policy")
		if strings.Contains(policy, "allow-same-origin") || !strings.Contains(policy, "connect-src 'none'") {
			t.Fatal("report lost isolation")
		}
		if query == "?embedded=1" && !strings.Contains(policy, "frame-ancestors http://"+app.host) {
			t.Fatal("trusted application cannot embed report")
		}
		if query == "?download=1" && !strings.HasPrefix(response.Header().Get("Content-Disposition"), "attachment;") {
			t.Fatal("HTML export is not a download")
		}
	}
	retained, err := os.ReadFile(filepath.Join(root, "deliverables/report/report.html"))
	if err != nil || !bytes.Equal(retained, original) {
		t.Fatal("presentation mutated the retained report")
	}
	combined := call(app, "GET", name+"?embedded=1&download=1", "")
	if !bytes.Equal(combined.Body.Bytes(), original) {
		t.Fatal("embedded export did not return original bytes")
	}
	response := call(app, "GET", name, "")
	if !strings.Contains(response.Header().Get("Content-Security-Policy"), "frame-ancestors 'none'") {
		t.Fatal("standalone report embedding policy changed")
	}
	response = call(app, "GET", "/", "")
	if !strings.Contains(response.Header().Get("Content-Security-Policy"), "frame-src 'self'") {
		t.Fatal("app cannot display local reports")
	}
	request := httptest.NewRequest("GET", "http://"+app.host+name+"?embedded=1", nil)
	request.Header.Set("Origin", "null")
	result := httptest.NewRecorder()
	app.ServeHTTP(result, request)
	if result.Code != 403 {
		t.Fatal("sandboxed child can access the application origin")
	}
}

func TestReportPresentationKeepsFragmentsAndOriginalStorage(t *testing.T) {
	for _, original := range []string{"<p>Original fragment</p>", "<HTML><BODY>Original report</BODY></HTML>"} {
		raw := []byte(original)
		result := reportPresentation(raw)
		if !bytes.Contains(result, []byte("data-library-presentation")) {
			t.Fatal("missing presentation")
		}
		if strings.Contains(original, "</BODY>") && !bytes.HasSuffix(result, []byte("</BODY></HTML>")) {
			t.Fatal("insertion lost the original document ending")
		}
		result[0] = 'X'
		if string(raw) != original {
			t.Fatal("presentation aliases original report storage")
		}
	}
}

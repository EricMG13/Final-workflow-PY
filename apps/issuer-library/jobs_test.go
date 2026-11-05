package main

import (
	"bytes"
	"context"
	"encoding/json"
	"mime/multipart"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"slices"
	"strings"
	"sync"
	"testing"
	"time"
)

func fakeEngine(t *testing.T) Engine {
	t.Helper()
	python, err := exec.LookPath("python3")
	if err != nil {
		t.Skip("Python needed for the synthetic process-boundary test")
	}
	script := filepath.Join(t.TempDir(), "worker.py")
	raw := `import json,sys,pathlib,time
folder=pathlib.Path(sys.argv[2])
job=json.loads((folder/'job.json').read_text())
if sys.argv[1]=='review':
 print(json.dumps({'ok':True,'review_id':'review-fingerprint','id':job['id'],'provider_ready':True,'cap_usd':job['cap_usd']}))
else:
 with (folder/'synthetic-starts.txt').open('a') as stream: stream.write('one\n')
 time.sleep(.15)
 (folder/'status.json').write_text(json.dumps({'state':'stopped','message':'Synthetic worker seam only; no provider called.'}))
`
	if err = os.WriteFile(script, []byte(raw), 0600); err != nil {
		t.Fatal(err)
	}
	library := `import json,sys
print(json.dumps({'parsed':json.load(sys.stdin)['workspace'],'folder':sys.argv[1]}))
`
	if err = os.WriteFile(filepath.Join(filepath.Dir(script), "store.py"), []byte(library), 0600); err != nil {
		t.Fatal(err)
	}
	return Engine{Python: python, Script: script}
}
func reviewRequest(t *testing.T, app *Application, paths string) *httptest.ResponseRecorder {
	t.Helper()
	var body bytes.Buffer
	form := multipart.NewWriter(&body)
	for key, value := range map[string]string{"context": "{}", "config": "sol-medium", "cap_usd": "10.00", "source_paths": paths, "modules": "CP-4", "max_turns": "7"} {
		if err := form.WriteField(key, value); err != nil {
			t.Fatal(err)
		}
	}
	file, err := form.CreateFormFile("sources", "../../original.txt")
	if err != nil {
		t.Fatal(err)
	}
	_, _ = file.Write([]byte("Synthetic source"))
	form.Close()
	request := httptest.NewRequest("POST", "http://"+app.host+"/api/runs/review", &body)
	request.Header.Set("Content-Type", form.FormDataContentType())
	request.Header.Set("X-Issuer-Library", "1")
	request.Header.Set("Origin", "http://"+app.host)
	response := httptest.NewRecorder()
	app.ServeHTTP(response, request)
	return response
}
func TestUploadReviewDoesNotStartAndRetainsTheFolderLayout(t *testing.T) {
	app, root := testApp(t)
	app.engine = fakeEngine(t)
	response := reviewRequest(t, app, `["filings/annual.txt"]`)
	if response.Code != 200 {
		t.Fatal(response.Body.String())
	}
	var value struct {
		ID string `json:"id"`
	}
	if err := json.Unmarshal(response.Body.Bytes(), &value); err != nil {
		t.Fatal(err)
	}
	folder := filepath.Join(root, "intake", value.ID)
	if raw, err := os.ReadFile(filepath.Join(folder, "sources", "filings", "annual.txt")); err != nil || string(raw) != "Synthetic source" {
		t.Fatal("source was not kept at its folder path", err)
	}
	var job NewJob
	raw, err := os.ReadFile(filepath.Join(folder, "job.json"))
	if err != nil || json.Unmarshal(raw, &job) != nil {
		t.Fatal(err)
	}
	if !slices.Equal(job.Modules, []string{"CP-4"}) || job.MaxTurns != 7 || job.Config != "sol-medium" || job.Sources[0].Path != "filings/annual.txt" {
		t.Fatalf("request was not retained: %+v", job)
	}
	if _, err := os.Stat(filepath.Join(folder, "synthetic-starts.txt")); !os.IsNotExist(err) {
		t.Fatal("review executed")
	}
	if _, err := os.Stat(filepath.Join(root, "original.txt")); !os.IsNotExist(err) {
		t.Fatal("upload filename escaped staging")
	}
}
func TestUploadRefusesPathsOutsideTheChosenFolder(t *testing.T) {
	app, root := testApp(t)
	app.engine = fakeEngine(t)
	for _, name := range []string{`["../../original.txt"]`, `["/etc/original.txt"]`, `["a/../../original.txt"]`, `["a/./b.txt"]`, `["a\\\\b.txt"]`, `["."]`, `[""]`, `["a","b"]`, `not json`} {
		if response := reviewRequest(t, app, name); response.Code != 400 {
			t.Fatalf("%s accepted: %d %s", name, response.Code, response.Body.String())
		}
	}
	if _, err := os.Stat(filepath.Join(root, "original.txt")); !os.IsNotExist(err) {
		t.Fatal("upload escaped staging")
	}
	if entries, _ := os.ReadDir(filepath.Join(root, "intake")); len(entries) != 0 {
		t.Fatalf("refused uploads left %d intake folders", len(entries))
	}
}
func TestWorkspaceStoreComesFromTheEngineWithTheCatalogue(t *testing.T) {
	app, root := testApp(t)
	app.engine = fakeEngine(t)
	response := call(app, "GET", "/api/workspace", "")
	var value map[string]string
	if response.Code != 200 || json.Unmarshal(response.Body.Bytes(), &value) != nil {
		t.Fatal(response.Code, response.Body.String())
	}
	if value["parsed"] != root || value["folder"] == "" {
		t.Fatalf("engine did not receive this workspace's catalogue: %v", value)
	}
	app.engine = Engine{Python: filepath.Join(root, "missing-python"), Script: "x"}
	response = call(app, "GET", "/api/workspace", "")
	if response.Code != 503 || !strings.Contains(response.Body.String(), "runtime is unavailable") {
		t.Fatalf("missing runtime hidden: %d %s", response.Code, response.Body.String())
	}
}
func TestExplicitStartIsOneShotUnderConcurrentRequests(t *testing.T) {
	app, root := testApp(t)
	app.engine = fakeEngine(t)
	response := reviewRequest(t, app, `["annual.txt"]`)
	var review map[string]any
	_ = json.Unmarshal(response.Body.Bytes(), &review)
	id := review["id"].(string)
	invalid := call(app, "POST", "/api/runs/start", `{"id":"`+id+`","review_id":"review-fingerprint","confirm":false}`)
	if invalid.Code != 400 {
		t.Fatal("implicit start accepted")
	}
	payload := `{"id":"` + id + `","review_id":"review-fingerprint","confirm":true}`
	var group sync.WaitGroup
	results := make(chan int, 2)
	for range 2 {
		group.Go(func() { results <- call(app, "POST", "/api/runs/start", payload).Code })
	}
	group.Wait()
	close(results)
	accepted := 0
	for code := range results {
		if code == 202 {
			accepted++
		} else if code != 409 {
			t.Fatalf("unexpected %d", code)
		}
	}
	if accepted != 1 {
		t.Fatalf("%d starts accepted", accepted)
	}
	deadline := time.Now().Add(5 * time.Second)
	for time.Now().Before(deadline) {
		app.mu.RLock()
		active := len(app.activeJobs)
		app.mu.RUnlock()
		if active == 0 {
			break
		}
		time.Sleep(20 * time.Millisecond)
	}
	raw, err := os.ReadFile(filepath.Join(root, "intake", id, "synthetic-starts.txt"))
	if err != nil {
		t.Fatal(err)
	}
	if string(raw) != "one\n" {
		t.Fatalf("duplicate execution: %q", raw)
	}
	status := call(app, "GET", "/api/runs/status?id="+id, "")
	if status.Code != 200 {
		t.Fatal(status.Code)
	}
}
func TestSourceUploadsRequireOriginAndCustomHeader(t *testing.T) {
	app, _ := testApp(t)
	request := httptest.NewRequest("POST", "http://"+app.host+"/api/runs/review", bytes.NewBufferString("anything"))
	request.Header.Set("Origin", "https://untrusted.invalid")
	response := httptest.NewRecorder()
	app.ServeHTTP(response, request)
	if response.Code != 403 {
		t.Fatal("cross-origin upload accepted")
	}
	request = httptest.NewRequest("POST", "http://"+app.host+"/api/runs/review", nil)
	response = httptest.NewRecorder()
	app.ServeHTTP(response, request)
	if response.Code != 403 {
		t.Fatal("implicit app request accepted")
	}
}

func TestStartRefusesUnconfiguredProviderBeforeCreatingClaim(t *testing.T) {
	app, root := testApp(t)
	app.engine = fakeEngine(t)
	response := reviewRequest(t, app, `["annual.txt"]`)
	var review map[string]any
	_ = json.Unmarshal(response.Body.Bytes(), &review)
	id := review["id"].(string)
	review["provider_ready"] = false
	folder := filepath.Join(root, "intake", id)
	if err := saveJSON(filepath.Join(folder, "review.json"), review); err != nil {
		t.Fatal(err)
	}
	response = call(app, "POST", "/api/runs/start", `{"id":"`+id+`","review_id":"review-fingerprint","confirm":true}`)
	if response.Code != 409 {
		t.Fatal("unconfigured execution accepted")
	}
	if _, err := os.Stat(filepath.Join(folder, "start.claim")); !os.IsNotExist(err) {
		t.Fatal("unconfigured run consumed its one-shot claim")
	}
}

func TestCorruptedReviewIsRefusedBeforeStarting(t *testing.T) {
	app, root := testApp(t)
	app.engine = fakeEngine(t)
	response := reviewRequest(t, app, `["annual.txt"]`)
	var value map[string]any
	_ = json.Unmarshal(response.Body.Bytes(), &value)
	id := value["id"].(string)
	file := filepath.Join(root, "intake", id, "review.json")
	raw, err := os.ReadFile(file)
	if err != nil {
		t.Fatal(err)
	}
	if err = os.WriteFile(file, append(raw, []byte("{}")...), 0600); err != nil {
		t.Fatal(err)
	}
	response = call(app, "POST", "/api/runs/start", `{"id":"`+id+`","review_id":"review-fingerprint","confirm":true}`)
	if response.Code != 409 {
		t.Fatal("corrupted review started a worker")
	}
}

func TestWorkerUsesUTF8IndependentOfWindowsLocale(t *testing.T) {
	command := fakeEngine(t).command(context.Background(), "review", t.TempDir())
	if !slices.Contains(command.Args, "-X") || !slices.Contains(command.Args, "utf8") {
		t.Fatal("Windows workers must use UTF-8 for retained JSON and Markdown")
	}
}

func TestStatusOnlyOffersAnExistingRun(t *testing.T) {
	app, root := testApp(t)
	id := "web-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
	folder := filepath.Join(root, "intake", id)
	if err := os.MkdirAll(folder, 0700); err != nil {
		t.Fatal(err)
	}
	if err := saveJSON(filepath.Join(folder, "status.json"), JobStatus{State: "failed"}); err != nil {
		t.Fatal(err)
	}
	status := func() bool {
		response := call(app, "GET", "/api/runs/status?id="+id, "")
		var result struct {
			Available bool `json:"run_available"`
		}
		if response.Code != 200 || json.Unmarshal(response.Body.Bytes(), &result) != nil {
			t.Fatal(response.Body.String())
		}
		return result.Available
	}
	if status() {
		t.Fatal("failed validation offered a nonexistent run")
	}
	if err := os.MkdirAll(filepath.Join(root, "runs", id), 0700); err != nil {
		t.Fatal(err)
	}
	if !status() {
		t.Fatal("retained run is unavailable")
	}
}

func TestReviewPreparesAnEmptyWorkspaceWithoutExecuting(t *testing.T) {
	root := t.TempDir()
	app, err := newApplication(Locations{State: t.TempDir(), Documents: t.TempDir()}, root)
	if err != nil {
		t.Fatal(err)
	}
	app.host = "127.0.0.1:54321"
	app.engine = fakeEngine(t)
	response := reviewRequest(t, app, `["annual.txt"]`)
	if response.Code != 200 {
		t.Fatal(response.Body.String())
	}
	for _, name := range []string{"runs", "deliverables"} {
		entries, err := os.ReadDir(filepath.Join(root, name))
		if err != nil || len(entries) != 0 {
			t.Fatalf("fresh workspace %s was not prepared without execution: %v", name, err)
		}
	}
}

func TestSaveJSONWaitsForAFileHeldOpen(t *testing.T) {
	name := filepath.Join(t.TempDir(), "status.json")
	// A folder in the way fails the rename until it goes, as a held file does on Windows.
	if err := os.Mkdir(name, 0700); err != nil {
		t.Fatal(err)
	}
	go func() {
		time.Sleep(150 * time.Millisecond)
		_ = os.Remove(name)
	}()
	if err := saveJSON(name, map[string]string{"state": "interrupted"}); err != nil {
		t.Fatal(err)
	}
	raw, err := os.ReadFile(name)
	if err != nil || !strings.Contains(string(raw), "interrupted") {
		t.Fatalf("%s %v", raw, err)
	}
}

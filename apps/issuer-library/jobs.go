package main

import (
	"bytes"
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"
)

var jobID = regexp.MustCompile(`^web-[a-f0-9]{32}$`)
var moduleCode = regexp.MustCompile(`^CP-[A-Z0-9]+$`)

type Engine struct{ Python, Script string }

func localEngine() Engine {
	executable, _ := os.Executable()
	folder := filepath.Join(filepath.Dir(executable), "engine")
	if override := os.Getenv("ISSUER_LIBRARY_ENGINE_ROOT"); override != "" {
		folder = override
	}
	python := os.Getenv("ISSUER_LIBRARY_PYTHON")
	if python == "" {
		python = filepath.Join(folder, "runtime", "python.exe")
	}
	return Engine{Python: python, Script: filepath.Join(folder, "bridge.py")}
}
func (engine Engine) process(ctx context.Context, script string, arguments ...string) *exec.Cmd {
	command := exec.CommandContext(ctx, engine.Python, append([]string{"-I", "-B", "-X", "utf8", script}, arguments...)...)
	configureWorkerCommand(command)
	command.Stderr = io.Discard
	return command
}

func (engine Engine) command(ctx context.Context, operation, folder string) *exec.Cmd {
	return engine.process(ctx, engine.Script, operation, folder)
}

// library parses the workspace's handoffs for the app; the catalogue names what to show.
// store.py imports only the standard library, so a page load does not pay for the engine.
// ponytail: parsed on each page load; add a cache if a workspace makes this slow.
func (engine Engine) library(workspace string, catalogue []byte) ([]byte, error) {
	if _, err := os.Stat(engine.Python); err != nil {
		return nil, fmt.Errorf("CP-OS runtime is unavailable; use the complete application package")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()
	command := engine.process(ctx, filepath.Join(filepath.Dir(engine.Script), "store.py"), workspace)
	command.Stdin = bytes.NewReader(catalogue)
	output, err := command.Output()
	if err != nil || !json.Valid(output) {
		return nil, fmt.Errorf("the workspace could not be read; check the runtime installation and workspace folder")
	}
	return output, nil
}

func (engine Engine) review(folder string) (json.RawMessage, error) {
	if _, err := os.Stat(engine.Python); err != nil {
		return nil, fmt.Errorf("CP-OS runtime is unavailable; use the complete application package")
	}
	// The launcher reads every file in the folder, so a large one takes minutes.
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Minute)
	defer cancel()
	output, err := engine.command(ctx, "review", folder).Output()
	if len(output) > 1<<20 || !json.Valid(output) {
		return nil, fmt.Errorf("CP-OS validation could not complete; check the runtime installation")
	}
	if err != nil {
		var result struct {
			OK bool `json:"ok"`
		}
		if json.Unmarshal(output, &result) != nil || result.OK {
			return nil, fmt.Errorf("CP-OS validator failed")
		}
	}
	return output, nil
}

type UploadedSource struct {
	Path   string `json:"path"`
	SHA256 string `json:"sha256"`
}
type NewJob struct {
	ID        string           `json:"id"`
	Workspace string           `json:"workspace"`
	Config    string           `json:"config"`
	Cap       string           `json:"cap_usd"`
	Modules   []string         `json:"modules"`
	MaxTurns  int              `json:"max_turns"`
	Sources   []UploadedSource `json:"sources"`
}
type JobStatus struct {
	State   string `json:"state"`
	Message string `json:"message"`
	ID      string `json:"id,omitempty"`
}

// jobView reads a job's own files: status, the app-written review and the
// module/step progress. None of them holds provider text.
func jobView(workspace, id string) (map[string]any, bool) {
	raw, err := os.ReadFile(filepath.Join(workspace, "intake", id, "status.json"))
	if err != nil {
		return nil, false
	}
	var status map[string]any
	if json.Unmarshal(raw, &status) != nil {
		return nil, false
	}
	if raw, err := os.ReadFile(filepath.Join(workspace, "intake", id, "review.json")); err == nil {
		var review map[string]any
		if json.Unmarshal(raw, &review) == nil {
			for _, key := range []string{"issuer", "pathway", "as_of", "modules", "module_details"} {
				if value, present := review[key]; present {
					status[key] = value
				}
			}
		}
	}
	if raw, err := os.ReadFile(filepath.Join(workspace, "runs", id, "progress.json")); err == nil {
		var value map[string]any
		if json.Unmarshal(raw, &value) == nil {
			status["progress"] = value
		}
	}
	status["id"] = id
	info, statErr := os.Stat(filepath.Join(workspace, "runs", id))
	status["run_available"] = statErr == nil && info.IsDir()
	return status, true
}

func (app *Application) serveRunAPI(w http.ResponseWriter, r *http.Request) {
	if r.Method == "GET" {
		app.mu.RLock()
		workspace := app.config.Workspace
		app.mu.RUnlock()
		if r.URL.Path == "/api/runs/list" {
			entries, _ := os.ReadDir(filepath.Join(workspace, "intake"))
			recent := []map[string]any{}
			for i := len(entries) - 1; i >= 0 && len(recent) < 30; i-- {
				id := entries[i].Name()
				if !jobID.MatchString(id) {
					continue
				}
				status, ok := jobView(workspace, id)
				if !ok || status["state"] == "reviewed" {
					continue
				}
				recent = append(recent, status)
			}
			jsonResponse(w, recent)
			return
		}
		id := r.URL.Query().Get("id")
		if !jobID.MatchString(id) {
			http.NotFound(w, r)
			return
		}
		status, ok := jobView(workspace, id)
		if !ok {
			if _, err := os.Stat(filepath.Join(workspace, "intake", id, "status.json")); err != nil {
				http.NotFound(w, r)
			} else {
				http.Error(w, "Run status is unreadable", 500)
			}
			return
		}
		jsonResponse(w, status)
		return
	}
	if r.Method != "POST" {
		http.Error(w, "Method not allowed", 405)
		return
	}
	if r.Header.Get("X-Issuer-Library") != "1" {
		http.Error(w, "Invalid application request", 403)
		return
	}
	if r.URL.Path == "/api/runs/review" {
		app.reviewRun(w, r)
		return
	}
	if r.URL.Path == "/api/runs/start" {
		app.startRun(w, r)
		return
	}
	http.NotFound(w, r)
}

// A folder-relative path as the browser reports it, refused unless it stays inside sources/.
func validSourcePath(name string) bool {
	return filepath.IsLocal(name) && path.Clean(name) == name && name != "." && !strings.ContainsAny(name, "\\\x00")
}

func (app *Application) reviewRun(w http.ResponseWriter, r *http.Request) {
	r.Body = http.MaxBytesReader(w, r.Body, 512<<20)
	if err := r.ParseMultipartForm(1 << 20); err != nil {
		http.Error(w, "Upload is too large or malformed (512 MiB total maximum)", 400)
		return
	}
	defer r.MultipartForm.RemoveAll()
	var paths []string
	if json.Unmarshal([]byte(r.FormValue("source_paths")), &paths) != nil {
		http.Error(w, "Source paths are invalid", 400)
		return
	}
	files := r.MultipartForm.File["sources"]
	if len(files) == 0 || len(files) > 500 || len(paths) != len(files) || len(r.FormValue("context")) > 1<<20 {
		http.Error(w, "Choose a folder of 1–500 files and complete the context", 400)
		return
	}
	for _, name := range paths {
		if !validSourcePath(name) {
			http.Error(w, "Source path is not inside the chosen folder: "+name, 400)
			return
		}
	}
	modules := strings.Fields(r.FormValue("modules"))
	for _, module := range modules {
		if !moduleCode.MatchString(module) {
			http.Error(w, "Modules are CP codes separated by spaces: "+module, 400)
			return
		}
	}
	maxTurns := 32 // The launcher's default.
	if value := r.FormValue("max_turns"); value != "" {
		var err error
		if maxTurns, err = strconv.Atoi(value); err != nil || maxTurns < 1 || maxTurns > 200 {
			http.Error(w, "Max turns must be between 1 and 200", 400)
			return
		}
	}
	nonce := make([]byte, 16)
	if _, err := rand.Read(nonce); err != nil {
		http.Error(w, "Could not create run identity", 500)
		return
	}
	app.mu.RLock()
	workspace := app.config.Workspace
	app.mu.RUnlock()
	job := NewJob{ID: "web-" + hex.EncodeToString(nonce), Workspace: workspace, Config: r.FormValue("config"), Cap: r.FormValue("cap_usd"), Modules: modules, MaxTurns: maxTurns, Sources: []UploadedSource{}}
	root, err := os.OpenRoot(workspace)
	if err != nil {
		http.Error(w, "Choose an available workspace folder first", 400)
		return
	}
	defer root.Close()
	for _, name := range []string{"intake", "runs", "deliverables"} {
		if err = root.MkdirAll(name, 0700); err != nil {
			http.Error(w, "The workspace is not writable", 400)
			return
		}
	}
	relative := "intake/" + job.ID
	if err = root.MkdirAll(relative, 0700); err != nil {
		http.Error(w, "The workspace is not writable", 400)
		return
	}
	folder := filepath.Join(workspace, "intake", job.ID)
	valid := false
	defer func() {
		if !valid {
			_ = os.RemoveAll(folder)
		}
	}()
	contextFile, err := root.OpenFile(relative+"/context.json", os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if err != nil {
		http.Error(w, "Could not retain context", 500)
		return
	}
	_, writeErr := io.Copy(contextFile, strings.NewReader(r.FormValue("context")))
	closeErr := contextFile.Close()
	if writeErr != nil || closeErr != nil {
		http.Error(w, "Could not retain context", 500)
		return
	}
	// Every chosen file is kept, so the launcher itself reports the ones no module can read.
	for i, file := range files {
		if file.Size > 64<<20 {
			http.Error(w, "Files must be up to 64 MiB each: "+paths[i], 400)
			return
		}
		stream, err := file.Open()
		if err != nil {
			http.Error(w, "Source upload could not be read", 400)
			return
		}
		raw, err := io.ReadAll(io.LimitReader(stream, (64<<20)+1))
		stream.Close()
		if err != nil || len(raw) > 64<<20 {
			http.Error(w, "Source upload is too large or unreadable: "+paths[i], 400)
			return
		}
		target := relative + "/sources/" + paths[i]
		if err = root.MkdirAll(path.Dir(target), 0700); err != nil {
			http.Error(w, "Could not retain source", 500)
			return
		}
		destination, err := root.OpenFile(target, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
		if err != nil {
			http.Error(w, "Could not retain source: "+paths[i], 400)
			return
		}
		_, err = destination.Write(raw)
		closeErr := destination.Close()
		if err != nil || closeErr != nil {
			http.Error(w, "Could not retain source", 500)
			return
		}
		job.Sources = append(job.Sources, UploadedSource{Path: paths[i], SHA256: digest(raw)})
	}
	if err = saveJSON(filepath.Join(folder, "job.json"), job); err != nil {
		http.Error(w, "Could not save run request", 500)
		return
	}
	result, err := app.engine.review(folder)
	if err != nil {
		http.Error(w, err.Error(), 503)
		return
	}
	var review struct {
		OK bool `json:"ok"`
	}
	if json.Unmarshal(result, &review) != nil {
		http.Error(w, "Invalid validation response", 500)
		return
	}
	if review.OK {
		if err = saveJSON(filepath.Join(folder, "review.json"), result); err != nil {
			http.Error(w, "Could not retain review", 500)
			return
		}
		if err = saveJSON(filepath.Join(folder, "status.json"), JobStatus{State: "reviewed", Message: "Reviewed; no model call has been made.", ID: job.ID}); err != nil {
			http.Error(w, "Could not retain run status", 500)
			return
		}
		valid = true
	}
	w.Header().Set("Content-Type", "application/json")
	_, _ = w.Write(result)
}

func (app *Application) startRun(w http.ResponseWriter, r *http.Request) {
	var request struct {
		ID       string `json:"id"`
		ReviewID string `json:"review_id"`
		Confirm  bool   `json:"confirm"`
	}
	decoder := json.NewDecoder(http.MaxBytesReader(w, r.Body, 8192))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&request); err != nil || !jobID.MatchString(request.ID) || !request.Confirm {
		http.Error(w, "Explicit confirmation of a reviewed run is required", 400)
		return
	}
	app.mu.Lock()
	defer app.mu.Unlock()
	if len(app.activeJobs) > 0 {
		http.Error(w, "A CP-OS run is already active; wait for it to finish", 409)
		return
	}
	folder := filepath.Join(app.config.Workspace, "intake", request.ID)
	raw, err := os.ReadFile(filepath.Join(folder, "review.json"))
	if err != nil {
		http.Error(w, "Review this run before starting", 409)
		return
	}
	var review struct {
		ReviewID      string `json:"review_id"`
		ProviderReady bool   `json:"provider_ready"`
	}
	if json.Unmarshal(raw, &review) != nil || review.ReviewID != request.ReviewID || !review.ProviderReady {
		http.Error(w, "Review is invalid or the provider is not configured", 409)
		return
	}
	claim, err := os.OpenFile(filepath.Join(folder, "start.claim"), os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if err != nil {
		if !os.IsExist(err) {
			http.Error(w, "Could not retain the start authorisation", 500)
			return
		}
		http.Error(w, "This run has already been started; no additional call was made", 409)
		return
	}
	claim.Close()
	command := app.engine.command(context.Background(), "start", folder)
	// Discard command output; structured, redacted status is the only browser contract.
	command.Stdout = io.Discard
	if err = saveJSON(filepath.Join(folder, "status.json"), JobStatus{State: "running", Message: "CP-OS is validating the reviewed inputs and starting the selected workflow.", ID: request.ID}); err != nil {
		http.Error(w, "Could not retain start state", 500)
		return
	}
	if err = command.Start(); err != nil {
		_ = saveJSON(filepath.Join(folder, "status.json"), JobStatus{State: "failed", Message: "CP-OS runtime could not start."})
		http.Error(w, "CP-OS runtime could not start", 503)
		return
	}
	if app.activeJobs == nil {
		app.activeJobs = map[string]bool{}
	}
	app.activeJobs[request.ID] = true
	go func() {
		_ = command.Wait()
		raw, _ := os.ReadFile(filepath.Join(folder, "status.json"))
		var status JobStatus
		_ = json.Unmarshal(raw, &status)
		if status.State == "running" {
			_ = saveJSON(filepath.Join(folder, "status.json"), JobStatus{State: "interrupted", Message: "The worker exited without a final result. Retained evidence remains available; no automatic paid retry was made."})
		}
		app.mu.Lock()
		delete(app.activeJobs, request.ID)
		app.refreshLocked()
		app.mu.Unlock()
	}()
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusAccepted)
	jsonResponse(w, JobStatus{State: "running", ID: request.ID, Message: "Run started."})
}

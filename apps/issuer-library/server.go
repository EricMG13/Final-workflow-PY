package main

import (
	"bytes"
	"embed"
	"encoding/json"
	"fmt"
	"io/fs"
	"log"
	"mime"
	"net/http"
	"os"
	"path"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

//go:embed web/*.html web/*.css web/*.js web/legacy-catalog.json web/fonts/* web/brand/* web/icons/*
var resources embed.FS

type Application struct {
	engine     Engine
	activeJobs map[string]bool
	mu         sync.RWMutex
	loc        Locations
	config     Config
	locked     bool
	seed       Catalogue
	catalogue  Catalogue
	host       string
	stop       func()
}

func (app *Application) refreshLocked() {
	app.catalogue = discover(app.config.Workspace, app.seed)
	app.catalogue.PolicyLocked = app.locked
	// The persisted index is a disposable snapshot, never an authority on restart.
	if err := saveJSON(filepath.Join(app.loc.State, "index.json"), app.catalogue); err != nil {
		log.Printf("Index cache: %v", err)
		app.catalogue.Issues = append(app.catalogue.Issues, "Search index could not be saved; live browsing is still available.")
	}
}

func jsonResponse(w http.ResponseWriter, value any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	if err := json.NewEncoder(w).Encode(value); err != nil {
		log.Printf("Response: %v", err)
	}
}

func (app *Application) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Cache-Control", "no-store")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.Header().Set("Referrer-Policy", "no-referrer")
	w.Header().Set("Cross-Origin-Resource-Policy", "same-origin")
	origin := "http://" + app.host
	if r.Host != app.host || (r.Header.Get("Origin") != "" && r.Header.Get("Origin") != origin) || r.Header.Get("Sec-Fetch-Site") == "cross-site" {
		http.Error(w, "Local app requests only", http.StatusForbidden)
		return
	}
	if strings.HasPrefix(r.URL.Path, "/api/runs/") {
		app.serveRunAPI(w, r)
		return
	}
	if r.Method == http.MethodPost {
		if r.Header.Get("X-Issuer-Library") != "1" || r.Header.Get("Content-Type") != "application/json" {
			http.Error(w, "Invalid application request", http.StatusForbidden)
			return
		}
		app.post(w, r)
		return
	}
	if r.Method != http.MethodGet && r.Method != http.MethodHead {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	switch r.URL.Path {
	case "/health":
		jsonResponse(w, map[string]string{"application": "finalworkflow-issuer-library/1", "instance": digest([]byte(app.loc.State))})
	case "/api/catalogue":
		app.mu.RLock()
		defer app.mu.RUnlock()
		jsonResponse(w, app.catalogue)
	case "/api/workspace":
		app.serveWorkspace(w)
	default:
		if strings.HasPrefix(r.URL.Path, "/files/") {
			app.serveFile(w, r)
			return
		}
		app.serveAsset(w, r)
	}
}

func (app *Application) serveWorkspace(w http.ResponseWriter) {
	app.mu.RLock()
	catalogue, err := json.Marshal(app.catalogue)
	workspace := app.config.Workspace
	app.mu.RUnlock()
	if err != nil {
		http.Error(w, "Could not read the library", http.StatusInternalServerError)
		return
	}
	store, err := app.engine.library(workspace, catalogue)
	if err != nil {
		http.Error(w, err.Error(), http.StatusServiceUnavailable)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	_, _ = w.Write(store)
}

func (app *Application) post(w http.ResponseWriter, r *http.Request) {
	app.mu.Lock()
	defer app.mu.Unlock()
	switch r.URL.Path {
	case "/api/refresh":
		app.refreshLocked()
		jsonResponse(w, app.catalogue)
	case "/api/settings":
		if len(app.activeJobs) > 0 {
			http.Error(w, "Wait for the active run before changing its workspace", 409)
			return
		}
		if app.locked {
			http.Error(w, "Workspace is managed by IT", http.StatusForbidden)
			return
		}
		var config Config
		decoder := json.NewDecoder(http.MaxBytesReader(w, r.Body, 8192))
		decoder.DisallowUnknownFields()
		if err := decoder.Decode(&config); err != nil {
			http.Error(w, "Invalid settings", http.StatusBadRequest)
			return
		}
		if !filepath.IsAbs(config.Workspace) {
			http.Error(w, "Enter an absolute workspace folder", http.StatusBadRequest)
			return
		}
		config.Workspace = filepath.Clean(config.Workspace)
		info, err := os.Stat(config.Workspace)
		if err != nil || !info.IsDir() {
			http.Error(w, "The workspace folder is unavailable", http.StatusBadRequest)
			return
		}
		if err = saveJSON(filepath.Join(app.loc.State, "settings.json"), config); err != nil {
			http.Error(w, "Could not save settings", http.StatusInternalServerError)
			return
		}
		app.config = config
		app.refreshLocked()
		jsonResponse(w, app.catalogue)
	case "/api/quit":
		if len(app.activeJobs) > 0 {
			http.Error(w, "A run is active. Keep the application open until it finishes or stops.", 409)
			return
		}
		jsonResponse(w, map[string]bool{"stopped": true})
		go app.stop()
	default:
		http.NotFound(w, r)
	}
}

func (app *Application) serveFile(w http.ResponseWriter, r *http.Request) {
	name := strings.TrimPrefix(r.URL.Path, "/files/")
	app.mu.RLock()
	defer app.mu.RUnlock()
	hash, allowed := app.catalogue.Allowed[name]
	if !allowed || !localPath(name) {
		http.NotFound(w, r)
		return
	}
	root, err := os.OpenRoot(app.config.Workspace)
	if err != nil {
		http.Error(w, "Workspace unavailable", http.StatusGone)
		return
	}
	defer root.Close()
	raw, err := readFile(root, name)
	if err != nil {
		http.Error(w, "File unavailable; refresh the library", http.StatusGone)
		return
	}
	pinned := r.URL.Query().Get("sha256")
	actual := ""
	if hash != "" || pinned != "" {
		actual = digest(raw)
	}
	if hash != "" && actual != hash {
		http.Error(w, "File changed since verification; refresh the library", http.StatusConflict)
		return
	}
	if pinned != "" && actual != pinned {
		http.Error(w, "This link refers to a different evidence version; refresh the library", http.StatusConflict)
		return
	}
	ext := strings.ToLower(path.Ext(name))
	contentType := "text/plain; charset=utf-8"
	if ext == ".html" || ext == ".htm" {
		contentType = "text/html; charset=utf-8"
	}
	if ext == ".pdf" {
		contentType = "application/pdf"
	}
	if ext == ".xlsx" {
		contentType = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
		w.Header().Set("Content-Disposition", mime.FormatMediaType("attachment", map[string]string{"filename": path.Base(name)}))
	}
	if r.URL.Query().Get("download") == "1" {
		filename := path.Base(name)
		if hash != "" && filename == "report.html" {
			filename = path.Base(path.Dir(name)) + ".html"
		}
		w.Header().Set("Content-Disposition", mime.FormatMediaType("attachment", map[string]string{"filename": filename}))
	}
	// Reports retain their local scripts but receive an opaque sandboxed origin:
	// a report cannot read the library API, modify settings or access the network.
	ancestors := "'none'"
	if (ext == ".html" || ext == ".htm") && hash != "" && r.URL.Query().Get("embedded") == "1" {
		ancestors = "http://" + app.host
		if r.URL.Query().Get("download") != "1" {
			raw = reportPresentation(raw)
		}
	}
	w.Header().Set("Content-Security-Policy", "sandbox allow-scripts allow-downloads; default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; font-src data:; connect-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors "+ancestors)
	w.Header().Set("Content-Type", contentType)
	http.ServeContent(w, r, path.Base(name), time.Time{}, bytes.NewReader(raw))
}

func reportPresentation(original []byte) []byte {
	style, _ := resources.ReadFile("web/report-adapter.css")
	brand, _ := resources.ReadFile("web/brand.css")
	script, _ := resources.ReadFile("web/report-adapter.js")
	position := bytes.LastIndex(bytes.ToLower(original), []byte("</body>"))
	if position < 0 {
		position = len(original)
	}
	return bytes.Join([][]byte{original[:position], []byte("<style data-library-presentation>"), style, brand,
		[]byte("</style><script data-library-presentation>"), script, []byte("</script>"), original[position:]}, nil)
}

func (app *Application) serveAsset(w http.ResponseWriter, r *http.Request) {
	name := strings.TrimPrefix(r.URL.Path, "/")
	if name == "" {
		name = "index.html"
	}
	if !localPath(name) || name == "legacy-catalog.json" {
		http.NotFound(w, r)
		return
	}
	raw, err := fs.ReadFile(resources, "web/"+name)
	if err != nil {
		http.NotFound(w, r)
		return
	}
	w.Header().Set("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
	if name == "context-form.html" {
		w.Header().Set("Content-Security-Policy", "sandbox allow-scripts allow-downloads; default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; font-src data:; img-src data:; connect-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors http://"+app.host)
	}
	contentType := mime.TypeByExtension(path.Ext(name))
	if contentType == "" {
		contentType = "application/octet-stream"
	}
	w.Header().Set("Content-Type", contentType)
	http.ServeContent(w, r, name, time.Time{}, bytes.NewReader(raw))
}

func newApplication(loc Locations, override string) (*Application, error) {
	config, locked, err := loadConfig(loc)
	if err != nil {
		return nil, err
	}
	if override != "" {
		if locked {
			return nil, fmt.Errorf("workspace override is disabled by IT configuration")
		}
		config.Workspace, err = filepath.Abs(override)
		if err != nil {
			return nil, err
		}
	}
	var seed Catalogue
	raw, err := resources.ReadFile("web/legacy-catalog.json")
	if err != nil {
		return nil, err
	}
	if err = json.Unmarshal(raw, &seed); err != nil {
		return nil, err
	}
	app := &Application{engine: localEngine(), loc: loc, config: config, locked: locked, seed: seed}
	app.refreshLocked()
	return app, nil
}

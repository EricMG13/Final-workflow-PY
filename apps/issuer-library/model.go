package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"io/fs"
	"net/url"
	"os"
	"path"
	"strings"
)

const maxFile = 64 << 20

type Source struct {
	Path   string `json:"path"`
	SHA256 string `json:"sha256"`
	Line   int    `json:"line"`
	Quote  string `json:"quote"`
	Href   string `json:"href"`
}
type Metric struct {
	Value      string `json:"value"`
	Unit       string `json:"unit"`
	Period     string `json:"period"`
	Basis      string `json:"basis"`
	Source     string `json:"source"`
	Provenance string `json:"provenance,omitempty"`
}
type Rating struct {
	Label  string `json:"label"`
	Date   string `json:"date"`
	Source string `json:"source"`
}
type Counts struct {
	Done  int `json:"done"`
	Total int `json:"total"`
}
type Artifact struct {
	Folder       string `json:"folder"`
	Label        string `json:"label"`
	State        string `json:"state"`
	Relationship string `json:"relationship"`
	Available    bool   `json:"available"`
	Href         string `json:"href"`
	Issue        string `json:"issue"`
}
type FileLink struct {
	Name string `json:"name"`
	Href string `json:"href"`
}
type Run struct {
	ID              string             `json:"id"`
	Issuer          string             `json:"issuer"`
	Name            string             `json:"name"`
	Title           string             `json:"title"`
	Workflow        string             `json:"workflow"`
	Sector          string             `json:"sector"`
	Date            string             `json:"date"`
	Period          string             `json:"period"`
	PeriodKind      string             `json:"period_kind"`
	Currency        string             `json:"currency"`
	Summary         string             `json:"summary"`
	Gaps            []string           `json:"gaps"`
	Metrics         map[string]*Metric `json:"metrics"`
	Completion      *int               `json:"completion"`
	Checkpoints     *Counts            `json:"checkpoints"`
	Ratings         []Rating           `json:"ratings"`
	IdentitySource  string             `json:"identity_source"`
	SectorSource    string             `json:"sector_source"`
	Handoff         string             `json:"handoff"`
	HandoffHref     string             `json:"handoff_href"`
	Artifacts       []Artifact         `json:"artifacts"`
	Files           []FileLink         `json:"files"`
	DeliveryClaimed bool               `json:"-"`
}
type Catalogue struct {
	Real         []Run             `json:"real"`
	Illustrative []Run             `json:"illustrative"`
	Sources      map[string]Source `json:"sources"`
	BuiltAt      string            `json:"built_at"`
	Issues       []string          `json:"issues"`
	Workspace    string            `json:"workspace"`
	Live         bool              `json:"live"`
	PolicyLocked bool              `json:"policy_locked"`
	Allowed      map[string]string `json:"-"`
}
type Checklist struct {
	Scope        string `json:"scope"`
	Requirements []struct {
		ID       string   `json:"id"`
		Stage    string   `json:"stage"`
		Done     bool     `json:"done"`
		Evidence []string `json:"evidence"`
	} `json:"requirements"`
}
type Manifest struct {
	Schema    string            `json:"schema"`
	Run       Run               `json:"run"`
	Sources   map[string]Source `json:"sources"`
	Checklist *Checklist        `json:"checklist"`
}

func digest(raw []byte) string {
	sum := sha256.Sum256(raw)
	return hex.EncodeToString(sum[:])
}

// Use slash-separated relative paths on every OS; Windows streams and device
// paths must never become alternate spellings of admitted workspace files.
func localPath(name string) bool {
	return fs.ValidPath(name) && name != "." && !strings.ContainsAny(name, "\\:\x00")
}

func readFile(root *os.Root, name string) ([]byte, error) {
	if !localPath(name) {
		return nil, fmt.Errorf("invalid relative path: %s", name)
	}
	// Reject devices/FIFOs before opening (which could otherwise block).
	before, err := root.Lstat(name)
	if err != nil {
		return nil, err
	}
	if !before.Mode().IsRegular() {
		return nil, fmt.Errorf("not a regular file: %s", name)
	}
	f, err := root.Open(name)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	info, err := f.Stat()
	if err != nil {
		return nil, err
	}
	if !info.Mode().IsRegular() || info.Size() > maxFile {
		return nil, fmt.Errorf("not a regular file within 64 MiB: %s", name)
	}
	raw, err := io.ReadAll(io.LimitReader(f, maxFile+1))
	if len(raw) > maxFile {
		return nil, fmt.Errorf("file grew beyond 64 MiB: %s", name)
	}
	return raw, err
}

func readJSON(root *os.Root, name string, value any) error {
	raw, err := readFile(root, name)
	if err != nil {
		return err
	}
	return json.Unmarshal(raw, value)
}

func fileURL(name string) string {
	parts := strings.Split(name, "/")
	for i := range parts {
		parts[i] = url.PathEscape(parts[i])
	}
	return "/files/" + strings.Join(parts, "/")
}

func pinnedURL(name, hash string) string { return fileURL(name) + "?sha256=" + hash }

func blankRun(id string) Run {
	return Run{ID: id, Issuer: "Unclassified", Name: id, Title: "Discovered run", Workflow: "Unclassified", Sector: "Unclassified", Period: "Not established", PeriodKind: "Unclassified", Summary: "This folder has been discovered. Structured issuer and screening metadata have not been supplied.", Gaps: []string{}, Metrics: map[string]*Metric{}, Ratings: []Rating{}, Artifacts: []Artifact{}, Files: []FileLink{}}
}

func folders(root *os.Root, parent string) ([]string, error) {
	entries, err := fs.ReadDir(root.FS(), parent)
	if os.IsNotExist(err) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	var result []string
	for _, entry := range entries {
		if entry.IsDir() && !strings.HasPrefix(entry.Name(), ".") {
			result = append(result, path.Join(parent, entry.Name()))
		}
	}
	return result, nil
}

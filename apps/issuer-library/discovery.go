package main

import (
	"encoding/json"
	"fmt"
	"io/fs"
	"math"
	"os"
	"path"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"
)

var numericToken = regexp.MustCompile(`-?[0-9][0-9,]*(?:\.[0-9]+)?`)
var sourceKey = regexp.MustCompile(`^[a-zA-Z0-9_-]+$`)

func verifySource(root *os.Root, source Source) (Source, error) {
	if !(strings.HasPrefix(source.Path, "runs/") || strings.HasPrefix(source.Path, "data/") || strings.HasPrefix(source.Path, "deliverables/")) {
		return source, fmt.Errorf("source is outside workspace data directories")
	}
	raw, err := readFile(root, source.Path)
	if err != nil {
		return source, err
	}
	if len(source.SHA256) != 64 || digest(raw) != source.SHA256 {
		return source, fmt.Errorf("source hash changed: %s", source.Path)
	}
	lines := strings.Split(strings.ReplaceAll(string(raw), "\r\n", "\n"), "\n")
	if source.Line < 1 || source.Line > len(lines) || lines[source.Line-1] != source.Quote {
		return source, fmt.Errorf("source excerpt changed: %s", source.Path)
	}
	source.Href = pinnedURL(source.Path, source.SHA256)
	return source, nil
}

// Admission preserves explicit metadata; it does not interpret arbitrary prose
// or infer an issuer, period, ratio definition or completion from a filename.
func admitRun(root *os.Root, manifest Manifest, id string, cat *Catalogue) (Run, error) {
	run := manifest.Run
	if run.ID != id || run.Name == "" || run.Issuer == "" {
		return run, fmt.Errorf("run identity must match folder and include issuer/name")
	}
	if run.Date != "" {
		if _, err := time.Parse("2006-01-02", run.Date); err != nil {
			return run, fmt.Errorf("invalid evidence date")
		}
	}
	verified := map[string]Source{}
	for key, source := range manifest.Sources {
		if !sourceKey.MatchString(key) {
			return run, fmt.Errorf("invalid source key")
		}
		checked, err := verifySource(root, source)
		if err != nil {
			return run, err
		}
		verified[key] = checked
	}
	for _, key := range []string{run.IdentitySource, run.SectorSource} {
		if key != "" {
			if _, ok := verified[key]; !ok {
				return run, fmt.Errorf("missing identity/sector source")
			}
		}
	}
	if run.IdentitySource == "" {
		return run, fmt.Errorf("issuer identity needs a pinned source")
	}
	if run.Sector != "" && run.Sector != "Unclassified" && run.SectorSource == "" {
		return run, fmt.Errorf("sector needs a pinned source")
	}
	for _, metric := range run.Metrics {
		if metric == nil {
			continue
		}
		switch metric.Provenance {
		case "", "cited", "calculated", "synthetic":
		default:
			return run, fmt.Errorf("metric provenance must be cited, calculated, synthetic or omitted")
		}
		value, err := strconv.ParseFloat(metric.Value, 64)
		source, ok := verified[metric.Source]
		if err != nil || math.IsInf(value, 0) || math.IsNaN(value) || !ok || metric.Unit == "" || metric.Period == "" || metric.Basis == "" {
			return run, fmt.Errorf("metric requires finite exact value, unit, period, basis and pinned source")
		}
		found := false
		for _, token := range numericToken.FindAllString(source.Quote, -1) {
			if strings.ReplaceAll(token, ",", "") == metric.Value {
				found = true
			}
		}
		if !found {
			return run, fmt.Errorf("metric value absent from source excerpt")
		}
	}
	for _, rating := range run.Ratings {
		if _, ok := verified[rating.Source]; !ok {
			return run, fmt.Errorf("rating requires pinned source")
		}
	}
	run.Completion = nil
	run.Checkpoints = nil
	if manifest.Checklist != nil {
		counts, err := assessChecklist(*manifest.Checklist, verified)
		if err != nil {
			return run, err
		}
		score := counts.Done * 100 / counts.Total
		run.Completion = &score
		run.Checkpoints = &counts
		for _, requirement := range manifest.Checklist.Requirements {
			if requirement.Stage == "delivery" && requirement.Done {
				run.DeliveryClaimed = true
			}
		}
	}
	if run.Metrics == nil {
		run.Metrics = map[string]*Metric{}
	}
	if run.Gaps == nil {
		run.Gaps = []string{}
	}
	if run.Ratings == nil {
		run.Ratings = []Rating{}
	}
	if run.Artifacts == nil {
		run.Artifacts = []Artifact{}
	}
	run.HandoffHref = ""
	if run.Sector == "" {
		run.Sector = "Unclassified"
	}
	if run.Period == "" {
		run.Period = "Not established"
	}
	if run.Workflow == "" {
		run.Workflow = "Unclassified"
	}
	if run.Handoff != "" {
		if !strings.HasPrefix(run.Handoff, "runs/"+id+"/") {
			return run, fmt.Errorf("primary handoff must belong to run")
		}
		raw, err := readFile(root, run.Handoff)
		if err != nil {
			return run, err
		}
		run.HandoffHref = pinnedURL(run.Handoff, digest(raw))
	}
	// Publish references only after every check succeeds: failed records cannot
	// leave admitted files or source labels behind in the aggregate catalogue.
	for key, source := range verified {
		cat.Sources[id+"."+key] = source
		cat.Allowed[source.Path] = source.SHA256
	}
	for _, metric := range run.Metrics {
		if metric != nil {
			metric.Source = id + "." + metric.Source
		}
	}
	for i := range run.Ratings {
		run.Ratings[i].Source = id + "." + run.Ratings[i].Source
	}
	if run.IdentitySource != "" {
		run.IdentitySource = id + "." + run.IdentitySource
	}
	if run.SectorSource != "" {
		run.SectorSource = id + "." + run.SectorSource
	}
	return run, nil
}

func assessChecklist(checklist Checklist, sources map[string]Source) (Counts, error) {
	counts := Counts{Total: len(checklist.Requirements)}
	if checklist.Scope == "" || counts.Total == 0 {
		return counts, fmt.Errorf("checklist needs scope and required checkpoints")
	}
	stages := map[string]bool{"sources": false, "analysis": false, "verification": false, "downstream": false, "delivery": false}
	seen := map[string]bool{}
	for _, item := range checklist.Requirements {
		if item.ID == "" || seen[item.ID] {
			return counts, fmt.Errorf("duplicate or empty checkpoint")
		}
		seen[item.ID] = true
		if _, ok := stages[item.Stage]; !ok {
			return counts, fmt.Errorf("unknown checkpoint stage")
		}
		stages[item.Stage] = true
		if item.Done {
			if len(item.Evidence) == 0 {
				return counts, fmt.Errorf("completed checkpoint has no evidence")
			}
			for _, key := range item.Evidence {
				if _, ok := sources[key]; !ok {
					return counts, fmt.Errorf("checkpoint evidence not verified")
				}
			}
			counts.Done++
		}
	}
	for _, included := range stages {
		if !included {
			return counts, fmt.Errorf("checklist must cover sources, analysis, verification, downstream and delivery")
		}
	}
	return counts, nil
}

func indexRunFiles(root *os.Root, folder string, cat *Catalogue, run *Run) {
	run.Files = []FileLink{}
	count := 0
	err := fs.WalkDir(root.FS(), folder, func(name string, entry fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if entry.IsDir() {
			if strings.HasPrefix(entry.Name(), ".") {
				return fs.SkipDir
			}
			return nil
		}
		if !entry.Type().IsRegular() {
			return nil
		}
		ext := strings.ToLower(path.Ext(name))
		if !strings.Contains("|.md|.txt|.pdf|.html|.htm|.json|.csv|.xlsx|", "|"+ext+"|") || strings.HasPrefix(entry.Name(), ".") {
			return nil
		}
		count++
		if count > 5000 {
			return fmt.Errorf("run file limit (5000) reached")
		}
		if _, exists := cat.Allowed[name]; !exists {
			cat.Allowed[name] = ""
		}
		run.Files = append(run.Files, FileLink{Name: strings.TrimPrefix(name, folder+"/"), Href: fileURL(name)})
		return nil
	})
	if err != nil {
		cat.Issues = append(cat.Issues, folder+": "+err.Error())
	}
}

type deliveryView struct {
	Run struct {
		RunID      string `json:"run_id"`
		IssuerID   string `json:"issuer_id"`
		IssuerName string `json:"issuer_name"`
		AsOf       string `json:"as_of"`
		Pathway    string `json:"pathway"`
	} `json:"run"`
	Mode string `json:"mode"`
}

func verifyDelivery(root *os.Root, folder string) (Artifact, deliveryView, map[string]string) {
	artifact := Artifact{Folder: folder, Label: path.Base(folder), State: "candidate", Relationship: "direct"}
	var view deliveryView
	var record struct {
		Files map[string]string `json:"files"`
	}
	files := map[string]string{}
	if err := readJSON(root, folder+"/delivery.json", &record); err != nil {
		artifact.Issue = err.Error()
		return artifact, view, files
	}
	if record.Files["report.html"] == "" || record.Files["view.json"] == "" {
		artifact.Issue = "Delivery manifest requires report.html and view.json"
		return artifact, view, files
	}
	for name, hash := range record.Files {
		if !localPath(name) {
			artifact.Issue = "Invalid delivery path"
			return artifact, view, files
		}
		raw, err := readFile(root, folder+"/"+name)
		if err != nil || digest(raw) != hash {
			artifact.Issue = "Missing or changed delivery file: " + name
			return artifact, view, files
		}
		if name == "view.json" {
			if err = json.Unmarshal(raw, &view); err != nil {
				artifact.Issue = "Invalid delivery identity"
				return artifact, view, files
			}
		}
		files[folder+"/"+name] = hash
	}
	if view.Run.IssuerID == "" || view.Run.IssuerName == "" || view.Run.RunID == "" {
		artifact.Issue = "Missing delivery issuer/run identity"
		return artifact, view, files
	}
	if _, err := time.Parse("2006-01-02", view.Run.AsOf); err != nil {
		artifact.Issue = "Invalid delivery evidence date"
		return artifact, view, files
	}
	artifact.Available = true
	artifact.Href = pinnedURL(folder+"/report.html", record.Files["report.html"])
	if view.Mode != "" {
		artifact.State = view.Mode
	}
	return artifact, view, files
}

func discover(workspace string, seeds Catalogue) Catalogue {
	cat := Catalogue{Real: []Run{}, Illustrative: []Run{}, Sources: map[string]Source{}, Issues: []string{}, Allowed: map[string]string{}, Workspace: workspace, Live: true, BuiltAt: time.Now().UTC().Format("02 Jan 2006, 15:04:05 UTC")}
	root, err := os.OpenRoot(workspace)
	if err != nil {
		cat.Issues = append(cat.Issues, "Workspace unavailable: "+err.Error())
		return cat
	}
	defer root.Close()
	runFolders, err := folders(root, "runs")
	if err != nil {
		cat.Issues = append(cat.Issues, err.Error())
	}
	// Legacy summaries remain useful only when their exact pinned files survive.
	seedByID := map[string]Run{}
	for _, run := range seeds.Real {
		seedByID[run.ID] = run
	}
	for _, folder := range runFolders {
		id := path.Base(folder)
		run := blankRun(id)
		var manifest Manifest
		if _, err := root.Lstat(folder + "/library.json"); !os.IsNotExist(err) {
			err = readJSON(root, folder+"/library.json", &manifest)
			if err == nil && manifest.Schema != "issuer-library-run/1" {
				err = fmt.Errorf("unsupported run manifest schema")
			}
			if err == nil {
				run, err = admitRun(root, manifest, id, &cat)
			}
			if err != nil {
				run = blankRun(id)
				run.Gaps = append(run.Gaps, "Run metadata rejected: "+err.Error())
				cat.Issues = append(cat.Issues, folder+": "+err.Error())
			}
		} else if seed, ok := seedByID[id]; ok {
			// Copy through JSON because admission namespaces mutable metric pointers.
			raw, _ := json.Marshal(seed)
			_ = json.Unmarshal(raw, &manifest.Run)
			manifest.Sources = map[string]Source{}
			ids := []string{seed.IdentitySource, seed.SectorSource}
			for _, m := range seed.Metrics {
				if m != nil {
					ids = append(ids, m.Source)
				}
			}
			for _, r := range seed.Ratings {
				ids = append(ids, r.Source)
			}
			for _, key := range ids {
				if key != "" {
					manifest.Sources[key] = seeds.Sources[key]
				}
			}
			var err error
			run, err = admitRun(root, manifest, id, &cat)
			if err != nil {
				run = blankRun(id)
				run.Gaps = append(run.Gaps, "Legacy summary unavailable: "+err.Error())
				cat.Issues = append(cat.Issues, folder+": "+err.Error())
			}
		}
		// Delivery availability is always checked afresh, not inherited from a seed.
		for i := range run.Artifacts {
			run.Artifacts[i].Available = false
			run.Artifacts[i].Href = ""
			run.Artifacts[i].Issue = "Delivery folder not found"
		}
		indexRunFiles(root, folder, &cat, &run)
		// A launcher run keeps its verified deliveries inside the run; run files stay unverified.
		runDeliveries, _ := folders(root, folder+"/deliveries")
		for _, delivered := range runDeliveries {
			artifact, _, files := verifyDelivery(root, delivered)
			if !artifact.Available {
				cat.Issues = append(cat.Issues, delivered+": "+artifact.Issue)
				continue
			}
			for name, hash := range files {
				cat.Allowed[name] = hash
			}
			run.Artifacts = append(run.Artifacts, artifact)
		}
		cat.Real = append(cat.Real, run)
	}
	deliveryFolders, err := folders(root, "deliverables")
	if err != nil {
		cat.Issues = append(cat.Issues, err.Error())
	}
	for _, folder := range deliveryFolders {
		artifact, view, files := verifyDelivery(root, folder)
		linked := false
		for i := range cat.Real {
			run := &cat.Real[i]
			for j, old := range run.Artifacts {
				if old.Folder == folder {
					updated := artifact
					updated.Label = old.Label
					updated.Relationship = old.Relationship
					if old.State == "superseded" {
						updated.State = old.State
					}
					if artifact.Available && view.Run.IssuerID != run.Issuer {
						updated.Available = false
						updated.Href = ""
						updated.Issue = "Delivery issuer does not match run"
					}
					run.Artifacts[j] = updated
					if !artifact.Available || updated.Available {
						linked = true
					}
				}
			}
			// A matching run identifier is explicit identity; shared issuer alone is not.
			if artifact.Available && run.ID == view.Run.RunID && run.Issuer == view.Run.IssuerID {
				exists := false
				for _, a := range run.Artifacts {
					if a.Folder == folder {
						exists = true
					}
				}
				if !exists {
					run.Artifacts = append(run.Artifacts, artifact)
				}
				linked = true
			}
		}
		if artifact.Available {
			for name, hash := range files {
				cat.Allowed[name] = hash
			}
		} else {
			cat.Issues = append(cat.Issues, folder+": "+artifact.Issue)
		}
		if !linked {
			run := blankRun("delivery:" + path.Base(folder))
			run.Title = "Delivery revision"
			run.Workflow = "Delivery"
			run.Artifacts = []Artifact{artifact}
			if artifact.Available {
				run.Issuer = view.Run.IssuerID
				run.Name = view.Run.IssuerName
				run.Date = view.Run.AsOf
				run.Period = view.Run.AsOf
				run.Summary = "Discovered delivery for " + view.Run.RunID + ". Its relationship to analytical run folders has not been established; no metrics or completion are inferred."
			}
			cat.Real = append(cat.Real, run)
		}
	}
	for i := range cat.Real {
		run := &cat.Real[i]
		if !run.DeliveryClaimed {
			continue
		}
		available := false
		for _, artifact := range run.Artifacts {
			if artifact.Available && artifact.State != "superseded" && artifact.Relationship != "related" {
				available = true
			}
		}
		if !available {
			run.Completion = nil
			run.Checkpoints = nil
			run.Gaps = append(run.Gaps, "Checklist delivery checkpoint is unverified: no available direct deliverable.")
			cat.Issues = append(cat.Issues, run.ID+": completeness withheld until its delivery checkpoint can be verified")
		}
	}
	sort.SliceStable(cat.Real, func(i, j int) bool {
		return cat.Real[i].Name < cat.Real[j].Name || (cat.Real[i].Name == cat.Real[j].Name && cat.Real[i].ID < cat.Real[j].ID)
	})
	return cat
}

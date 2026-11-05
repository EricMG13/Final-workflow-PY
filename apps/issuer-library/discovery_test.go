package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"slices"
	"strings"
	"testing"
)

func put(t *testing.T, root, name string, raw []byte) {
	t.Helper()
	file := filepath.Join(root, filepath.FromSlash(name))
	if err := os.MkdirAll(filepath.Dir(file), 0700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(file, raw, 0600); err != nil {
		t.Fatal(err)
	}
}
func putJSON(t *testing.T, root, name string, value any) {
	t.Helper()
	raw, err := json.Marshal(value)
	if err != nil {
		t.Fatal(err)
	}
	put(t, root, name, raw)
}
func fixture(t *testing.T) (string, Manifest) {
	t.Helper()
	root := t.TempDir()
	raw := []byte("Issuer: Example Industries\nSector: Industrials\nRevenue: 0\nVerified scope\n")
	put(t, root, "runs/case-a/CP-0.md", raw)
	run := blankRun("case-a")
	run.Issuer = "EX"
	run.Name = "Example Industries"
	run.IdentitySource = "identity"
	run.Sector = "Industrials"
	run.SectorSource = "sector"
	run.Date = "2024-12-31"
	run.Period = "FY2024"
	run.Handoff = "runs/case-a/CP-0.md"
	run.Metrics["revenue"] = &Metric{Value: "0", Unit: "USD m", Period: "FY2024", Basis: "Reported revenue", Source: "revenue"}
	manifest := Manifest{Schema: "issuer-library-run/1", Run: run, Sources: map[string]Source{}}
	for key, number := range map[string]int{"identity": 1, "sector": 2, "revenue": 3, "check": 4} {
		manifest.Sources[key] = Source{Path: "runs/case-a/CP-0.md", SHA256: digest(raw), Line: number, Quote: strings.Split(string(raw), "\n")[number-1]}
	}
	putJSON(t, root, "runs/case-a/library.json", manifest)
	return root, manifest
}
func addDelivery(t *testing.T, root, folder, id, issuer string) {
	t.Helper()
	var view deliveryView
	view.Run.RunID = id
	view.Run.IssuerID = issuer
	view.Run.IssuerName = "Example Industries"
	view.Run.AsOf = "2024-12-31"
	view.Mode = "candidate"
	raw, _ := json.Marshal(view)
	report := []byte("<!doctype html><title>Report</title><p>Retained report</p>")
	put(t, root, "deliverables/"+folder+"/view.json", raw)
	put(t, root, "deliverables/"+folder+"/report.html", report)
	putJSON(t, root, "deliverables/"+folder+"/delivery.json", map[string]any{"files": map[string]string{"view.json": digest(raw), "report.html": digest(report)}})
}

func TestDiscoveryPreservesZeroAndFindsNewRun(t *testing.T) {
	root, _ := fixture(t)
	cat := discover(root, Catalogue{})
	if len(cat.Issues) != 0 || len(cat.Real) != 1 {
		t.Fatalf("%+v", cat)
	}
	run := cat.Real[0]
	if run.Metrics["revenue"].Value != "0" || run.Metrics["revenue"].Period != "FY2024" || run.Completion != nil {
		t.Fatalf("lost semantics: %+v", run)
	}
	put(t, root, "runs/new-case/CP-0.md", []byte("New evidence"))
	cat = discover(root, Catalogue{})
	if len(cat.Real) != 2 {
		t.Fatal("new run not discovered")
	}
	if cat.Real[1].Issuer != "Unclassified" {
		t.Fatal("filename became issuer identity")
	}
}

func TestChangedAndMalformedMetadataRemainVisible(t *testing.T) {
	root, _ := fixture(t)
	put(t, root, "runs/case-a/CP-0.md", []byte("changed"))
	cat := discover(root, Catalogue{})
	if len(cat.Real) != 1 || len(cat.Issues) == 0 || len(cat.Real[0].Metrics) != 0 || len(cat.Sources) != 0 {
		t.Fatal("bad summary leaked")
	}
	put(t, root, "runs/case-a/library.json", []byte("{"))
	cat = discover(root, Catalogue{})
	if len(cat.Real) != 1 || len(cat.Issues) == 0 {
		t.Fatal("partial manifest disappeared")
	}
}

func TestMetricCannotLoseBasisOrInventValue(t *testing.T) {
	for _, change := range []func(*Metric){func(m *Metric) { m.Value = "1" }, func(m *Metric) { m.Value = "NaN" }, func(m *Metric) { m.Basis = "" }, func(m *Metric) { m.Period = "" }, func(m *Metric) { m.Source = "missing" }} {
		root, m := fixture(t)
		change(m.Run.Metrics["revenue"])
		putJSON(t, root, "runs/case-a/library.json", m)
		cat := discover(root, Catalogue{})
		if len(cat.Issues) == 0 || len(cat.Real[0].Metrics) != 0 {
			t.Fatal("invalid metric admitted")
		}
	}
}

func TestMetricProvenanceIsOnlyProducerDeclared(t *testing.T) {
	for _, kind := range []string{"", "cited", "calculated", "synthetic", "unknown", "C1"} {
		t.Run("classification_"+kind, func(t *testing.T) {
			root, manifest := fixture(t)
			manifest.Run.Metrics["revenue"].Provenance = kind
			putJSON(t, root, "runs/case-a/library.json", manifest)
			cat := discover(root, Catalogue{})
			if kind == "unknown" || kind == "C1" {
				if len(cat.Issues) == 0 || len(cat.Real[0].Metrics) != 0 {
					t.Fatal("unsupported provenance admitted")
				}
				return
			}
			metric := cat.Real[0].Metrics["revenue"]
			if len(cat.Issues) != 0 || metric == nil || metric.Provenance != kind || metric.Value != "0" {
				t.Fatalf("classification inferred or exact zero lost: %+v", cat)
			}
		})
	}
}

func TestChecklistRequiresAllStagesAndPins(t *testing.T) {
	root, m := fixture(t)
	raw := `{"scope":"Annual review","requirements":[{"id":"s","stage":"sources","done":true,"evidence":["check"]},{"id":"a","stage":"analysis","done":true,"evidence":["check"]},{"id":"v","stage":"verification","done":false},{"id":"c","stage":"downstream","done":false},{"id":"d","stage":"delivery","done":false}]}`
	if err := json.Unmarshal([]byte(raw), &m.Checklist); err != nil {
		t.Fatal(err)
	}
	putJSON(t, root, "runs/case-a/library.json", m)
	cat := discover(root, Catalogue{})
	if cat.Real[0].Completion == nil || *cat.Real[0].Completion != 40 {
		t.Fatalf("wrong independent 2/5 score: %+v", cat.Issues)
	}
	m.Checklist.Requirements[0].Evidence = nil
	putJSON(t, root, "runs/case-a/library.json", m)
	cat = discover(root, Catalogue{})
	if cat.Real[0].Completion != nil || len(cat.Issues) == 0 {
		t.Fatal("unsubstantiated completion admitted")
	}
	if _, err := assessChecklist(Checklist{Scope: "empty"}, map[string]Source{}); err == nil {
		t.Fatal("empty checklist admitted")
	}
}

func TestDeliveryRevisionIdentityAndCorruption(t *testing.T) {
	root, _ := fixture(t)
	addDelivery(t, root, "revision-1", "case-a", "EX")
	addDelivery(t, root, "revision-2", "different-run", "EX")
	cat := discover(root, Catalogue{})
	if len(cat.Real) != 2 {
		t.Fatalf("unrelated report must have its own row: %d", len(cat.Real))
	}
	var run Run
	for _, r := range cat.Real {
		if r.ID == "case-a" {
			run = r
		}
	}
	if len(run.Artifacts) != 1 || !run.Artifacts[0].Available {
		t.Fatal("explicit run link missing")
	}
	put(t, root, "deliverables/revision-1/report.html", []byte("changed"))
	cat = discover(root, Catalogue{})
	if _, ok := cat.Allowed["deliverables/revision-1/report.html"]; ok {
		t.Fatal("corrupt report still admitted")
	}
	if len(cat.Issues) == 0 {
		t.Fatal("missing corruption notice")
	}
}

func TestPathsAndSymlinksCannotEscape(t *testing.T) {
	root, _ := fixture(t)
	outside := t.TempDir()
	put(t, outside, "secret.txt", []byte("secret"))
	if err := os.Symlink(filepath.Join(outside, "secret.txt"), filepath.Join(root, "runs/case-a/escape.txt")); err != nil {
		t.Skip(err)
	}
	access, err := os.OpenRoot(root)
	if err != nil {
		t.Fatal(err)
	}
	defer access.Close()
	for _, name := range []string{"../secret.txt", "/secret.txt", "runs/case-a/escape.txt", "C:/secret.txt", "runs/a:stream", "runs\\a.txt"} {
		if _, err := readFile(access, name); err == nil {
			t.Fatalf("allowed %q", name)
		}
	}
	cat := discover(root, Catalogue{})
	if _, ok := cat.Allowed["runs/case-a/escape.txt"]; ok {
		t.Fatal("symlink enumerated")
	}
}

func TestCurrentRetainedWorkspace(t *testing.T) {
	root := filepath.Clean("../..")
	if _, err := os.Stat(filepath.Join(root, "runs/tdg-002")); err != nil {
		t.Skip("retained workspace not present")
	}
	var seeds Catalogue
	raw, _ := resources.ReadFile("web/legacy-catalog.json")
	if err := json.Unmarshal(raw, &seeds); err != nil {
		t.Fatal(err)
	}
	cat := discover(root, seeds)
	// These hold an HTML Model and no report, which the library does not present yet.
	modelOnly := []string{
		"deliverables/tdg-model-1: Delivery manifest requires report.html and view.json",
		"deliverables/tdg-model-2: Delivery manifest requires report.html and view.json",
		"deliverables/tdg-model-3: Delivery manifest requires report.html and view.json",
	}
	if !slices.Equal(cat.Issues, modelOnly) {
		t.Fatalf("retained data rejected: %v", cat.Issues)
	}
	var annual *Run
	reports := map[string]bool{}
	runFolders := 0
	for i := range cat.Real {
		run := &cat.Real[i]
		if !strings.HasPrefix(run.ID, "delivery:") {
			runFolders++
		}
		if run.ID == "tdg-002" {
			annual = run
		}
		for _, a := range run.Artifacts {
			if a.Available {
				reports[a.Folder] = true
			}
		}
	}
	if annual == nil || annual.Metrics["leverage"].Value != "5.96" || annual.Metrics["coverage"].Value != "3.60" || annual.Completion != nil {
		t.Fatal("retained financial semantics changed")
	}
	// Counted from the folders here, not through discovery.
	entries, err := os.ReadDir(filepath.Join(root, "runs"))
	if err != nil {
		t.Fatal(err)
	}
	wantRuns := 0
	for _, entry := range entries {
		if entry.IsDir() {
			wantRuns++
		}
	}
	delivered, _ := filepath.Glob(filepath.Join(root, "deliverables", "*", "report.html"))
	launched, _ := filepath.Glob(filepath.Join(root, "runs", "*", "deliveries", "*", "report.html"))
	if runFolders != wantRuns || len(reports) != len(delivered)+len(launched) {
		t.Fatalf("got %d run folders, %d reports; folders hold %d runs, %d reports", runFolders, len(reports), wantRuns, len(delivered)+len(launched))
	}
}

func TestManifestCannotSupplyDerivedLinksOrNullCollections(t *testing.T) {
	root, m := fixture(t)
	m.Run.Handoff = ""
	m.Run.HandoffHref = "javascript:alert(1)"
	m.Run.Artifacts = nil
	putJSON(t, root, "runs/case-a/library.json", m)
	cat := discover(root, Catalogue{})
	if cat.Real[0].HandoffHref != "" {
		t.Fatal("untrusted derived handoff URL survived admission")
	}
	if cat.Real[0].Artifacts == nil {
		t.Fatal("nil artifacts break browser rendering")
	}
}
func TestWrongIssuerMappingDoesNotHideDiscoveredDelivery(t *testing.T) {
	root, m := fixture(t)
	m.Run.Artifacts = []Artifact{{Folder: "deliverables/foreign", Label: "Bad mapping"}}
	putJSON(t, root, "runs/case-a/library.json", m)
	addDelivery(t, root, "foreign", "foreign-run", "OTHER")
	cat := discover(root, Catalogue{})
	if len(cat.Real) != 2 {
		t.Fatal("wrong-issuer mapping hid a valid delivery from discovery")
	}
}

func TestDeliveryCheckpointRequiresAvailableDirectBundle(t *testing.T) {
	root, m := fixture(t)
	raw := `{"scope":"Annual review","requirements":[{"id":"s","stage":"sources","done":true,"evidence":["check"]},{"id":"a","stage":"analysis","done":true,"evidence":["check"]},{"id":"v","stage":"verification","done":true,"evidence":["check"]},{"id":"c","stage":"downstream","done":true,"evidence":["check"]},{"id":"d","stage":"delivery","done":true,"evidence":["check"]}]}`
	if err := json.Unmarshal([]byte(raw), &m.Checklist); err != nil {
		t.Fatal(err)
	}
	putJSON(t, root, "runs/case-a/library.json", m)
	cat := discover(root, Catalogue{})
	if cat.Real[0].Completion != nil {
		t.Fatal("checklist claimed delivery without any verified deliverable")
	}
	addDelivery(t, root, "complete", "case-a", "EX")
	cat = discover(root, Catalogue{})
	if cat.Real[0].Completion == nil || *cat.Real[0].Completion != 100 {
		t.Fatal("verified synthetic delivery did not restore scoped producer assessment")
	}
	put(t, root, "deliverables/complete/report.html", []byte("corrupted"))
	cat = discover(root, Catalogue{})
	for _, run := range cat.Real {
		if run.ID == "case-a" && run.Completion != nil {
			t.Fatal("changed delivery retained completeness")
		}
	}
}

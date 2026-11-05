package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"
)

type Config struct {
	Workspace string `json:"workspace"`
}
type Locations struct {
	State     string
	Policy    string
	Documents string
}

func loadConfig(loc Locations) (Config, bool, error) {
	for _, candidate := range []struct {
		name   string
		locked bool
	}{{loc.Policy, true}, {filepath.Join(loc.State, "settings.json"), false}} {
		if candidate.name == "" {
			continue
		}
		raw, err := os.ReadFile(candidate.name)
		if os.IsNotExist(err) {
			continue
		}
		if err != nil {
			return Config{}, false, err
		}
		var config Config
		if err = json.Unmarshal(raw, &config); err != nil {
			return config, false, fmt.Errorf("invalid configuration %s: %w", candidate.name, err)
		}
		if !filepath.IsAbs(config.Workspace) {
			return config, false, fmt.Errorf("workspace must be an absolute path in %s", candidate.name)
		}
		return config, candidate.locked, nil
	}
	return Config{Workspace: filepath.Join(loc.Documents, "FinalWorkflow")}, false, nil
}

func saveJSON(name string, value any) error {
	raw, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return err
	}
	if err = os.MkdirAll(filepath.Dir(name), 0700); err != nil {
		return err
	}
	f, err := os.CreateTemp(filepath.Dir(name), ".library-*.tmp")
	if err != nil {
		return err
	}
	temp := f.Name()
	defer os.Remove(temp)
	if _, err = f.Write(raw); err != nil {
		f.Close()
		return err
	}
	if err = f.Sync(); err != nil {
		f.Close()
		return err
	}
	if err = f.Close(); err != nil {
		return err
	}
	// Windows refuses to replace a file another reader has open for a moment.
	for attempt := 0; ; attempt++ {
		if err = os.Rename(temp, name); err == nil || attempt == 39 {
			return err
		}
		time.Sleep(50 * time.Millisecond)
	}
}

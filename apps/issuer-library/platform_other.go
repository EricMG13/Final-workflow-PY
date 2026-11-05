//go:build !windows

package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
)

func platformLocations() (Locations, error) {
	config, err := os.UserConfigDir()
	if err != nil {
		return Locations{}, err
	}
	home, err := os.UserHomeDir()
	if err != nil {
		return Locations{}, err
	}
	return Locations{State: filepath.Join(config, "FinalWorkflow", "IssuerLibrary"), Documents: filepath.Join(home, "Documents")}, nil
}
func openBrowser(url string) error {
	program := "xdg-open"
	if runtime.GOOS == "darwin" {
		program = "open"
	}
	return exec.Command(program, url).Start()
}
func showError(message string) { fmt.Fprintln(os.Stderr, message) }

func configureWorkerCommand(command *exec.Cmd) {}

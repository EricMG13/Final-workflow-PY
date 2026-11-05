package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"hash/crc32"
	"log"
	"net"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"time"
)

func run() error {
	workspace := flag.String("workspace", "", "Workspace folder (disabled by IT policy)")
	state := flag.String("state-dir", "", "Override per-user state directory for testing")
	noBrowser := flag.Bool("no-browser", false, "Start without opening a browser")
	port := flag.Int("port", 0, "Loopback port; zero selects a stable per-user port")
	flag.Parse()
	loc, err := platformLocations()
	if err != nil {
		return err
	}
	if *state != "" {
		loc.State, err = filepath.Abs(*state)
		if err != nil {
			return err
		}
	}
	if err = os.MkdirAll(loc.State, 0700); err != nil {
		return err
	}
	logPath := filepath.Join(loc.State, "library.log")
	if info, err := os.Stat(logPath); err == nil && info.Size() > 1<<20 {
		_ = os.Rename(logPath, logPath+".previous")
	}
	logFile, err := os.OpenFile(logPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0600)
	if err != nil {
		return err
	}
	defer logFile.Close()
	log.SetOutput(logFile)
	if *port == 0 {
		*port = 49000 + int(crc32.ChecksumIEEE([]byte(loc.State))%10000)
	}
	if *port < 1024 || *port > 65535 {
		return fmt.Errorf("port must be between 1024 and 65535")
	}
	host := fmt.Sprintf("127.0.0.1:%d", *port)
	address := "http://" + host
	listener, err := net.Listen("tcp4", host)
	if err != nil {
		client := http.Client{Timeout: 2 * time.Second, Transport: &http.Transport{Proxy: nil}, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}
		// A simultaneous launch may have bound the port but not started serving yet.
		for attempt := 0; attempt < 5; attempt++ {
			response, requestErr := client.Get(address + "/health")
			if requestErr == nil {
				var health map[string]string
				decodeErr := json.NewDecoder(http.MaxBytesReader(nil, response.Body, 4096)).Decode(&health)
				response.Body.Close()
				if decodeErr == nil && health["application"] == "finalworkflow-issuer-library/1" && health["instance"] == digest([]byte(loc.State)) {
					if *workspace != "" {
						return fmt.Errorf("library is already running; change its workspace in Settings or quit it first")
					}
					if !*noBrowser {
						return openBrowser(address)
					}
					return nil
				}
			}
			time.Sleep(200 * time.Millisecond)
		}
		return fmt.Errorf("local port is occupied by another application: %w", err)
	}
	defer listener.Close()
	app, err := newApplication(loc, *workspace)
	if err != nil {
		return err
	}
	app.host = host
	server := &http.Server{Handler: app, ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 150 * time.Second, WriteTimeout: 180 * time.Second, IdleTimeout: 30 * time.Second, MaxHeaderBytes: 16384}
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt)
	defer cancel()
	app.stop = cancel
	go func() {
		<-ctx.Done()
		shutdownCtx, done := context.WithTimeout(context.Background(), 3*time.Second)
		defer done()
		_ = server.Shutdown(shutdownCtx)
	}()
	go func() {
		ticker := time.NewTicker(30 * time.Second)
		defer ticker.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
				app.mu.Lock()
				app.refreshLocked()
				app.mu.Unlock()
			}
		}
	}()
	if !*noBrowser {
		go func() {
			if err := openBrowser(address); err != nil {
				log.Printf("Open browser: %v", err)
				showError("Open " + address + " in your browser.\n" + err.Error())
			}
		}()
	}
	fmt.Println("Issuer Library:", address)
	log.Printf("Listening at %s", address)
	err = server.Serve(listener)
	if err == http.ErrServerClosed {
		return nil
	}
	return err
}

func main() {
	if err := run(); err != nil {
		log.Print(err)
		showError(err.Error())
		os.Exit(1)
	}
}

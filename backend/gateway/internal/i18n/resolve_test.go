package i18n

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

// repoLocalesDir computes the real gateway locales dir from the test's own
// source location, mirroring the production source anchor.
func repoLocalesDir(t *testing.T) string {
	t.Helper()
	_, thisFile, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("runtime.Caller failed")
	}
	dir := filepath.Clean(filepath.Join(filepath.Dir(thisFile), "..", "..", "locales"))
	if !isLocalesDir(dir) {
		t.Fatalf("repo locales dir not valid at %s", dir)
	}
	return dir
}

func TestDefaultLocalesDir_IsCWDIndependent(t *testing.T) {
	// FIX-542 acceptance: CWD must not decide the resource path.
	// Resolve from several unrelated working directories; the answer must be
	// identical every time (the source-anchored repo locales dir).
	want, _, err := DefaultLocalesDir()
	if err != nil {
		t.Fatalf("baseline resolve failed: %v", err)
	}

	for _, cwd := range []string{"/", os.TempDir(), os.Getenv("HOME")} {
		if cwd == "" {
			continue
		}
		t.Chdir(cwd)
		got, diag, err := DefaultLocalesDir()
		if err != nil {
			t.Fatalf("resolve from %q failed: %v (diag=%s)", cwd, err, diag)
		}
		if got != want {
			t.Fatalf("CWD %q changed resolution: got %q want %q", cwd, got, want)
		}
	}
}

func TestDefaultLocalesDir_BogusLocalLocalesIgnored(t *testing.T) {
	// Falsifiable counterexample: a foreign CWD with a BROKEN locales dir
	// (missing zh.json) must not win. Resolution must still land on the real
	// bundle — CWD presence alone does not decide the path.
	bogus := t.TempDir()
	if err := os.MkdirAll(filepath.Join(bogus, "locales"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(bogus, "locales", "en.json"), []byte(`{}`), 0o644); err != nil {
		t.Fatal(err)
	}
	t.Chdir(bogus)

	got, _, err := DefaultLocalesDir()
	if err != nil {
		t.Fatalf("resolve failed despite source anchor: %v", err)
	}
	if !filepath.IsAbs(got) || filepath.Dir(got) == bogus {
		t.Fatalf("resolved to bogus CWD locales %q instead of repo bundle", got)
	}
	if !isLocalesDir(got) {
		t.Fatalf("resolved dir %q is not a valid locales dir", got)
	}
}

func TestDefaultLocalesDir_EnvOverrideWins(t *testing.T) {
	custom := t.TempDir()
	for _, m := range localesMarkers {
		if err := os.WriteFile(filepath.Join(custom, m), []byte(`{}`), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	t.Setenv(LocalesEnvVar, custom)

	got, diag, err := DefaultLocalesDir()
	if err != nil {
		t.Fatalf("env override resolve failed: %v", err)
	}
	if got != custom {
		t.Fatalf("env override not honored: got %q want %q (diag=%s)", got, custom, diag)
	}
}

func TestDefaultLocalesDir_EnvOverrideInvalidFailsLoud(t *testing.T) {
	// Explicit operator misconfiguration must NOT silently fall through.
	t.Setenv(LocalesEnvVar, filepath.Join(t.TempDir(), "does-not-exist"))

	_, diag, err := DefaultLocalesDir()
	if err == nil {
		t.Fatalf("expected error for invalid env override (diag=%s)", diag)
	}
}

func TestDefaultLocalesDir_WalkUpFindsFromSubdirectory(t *testing.T) {
	// Running from backend/gateway/cmd/server (the documented make target CWD)
	// must resolve via walk-up even if the source anchor were absent.
	t.Chdir(filepath.Join(repoLocalesDir(t), "..", "cmd", "server"))

	got, diag, err := DefaultLocalesDir()
	if err != nil {
		t.Fatalf("walk-up resolve failed: %v (diag=%s)", err, diag)
	}
	if want := repoLocalesDir(t); got != want {
		t.Fatalf("walk-up resolved %q, want %q", got, want)
	}
}

func TestInit_WithResolvedDir_LoadsBundle(t *testing.T) {
	dir := repoLocalesDir(t)
	if err := Init(dir); err != nil {
		t.Fatalf("Init(%s) failed: %v", dir, err)
	}
	if globalBundle == nil || len(globalBundle.messages) == 0 {
		t.Fatal("bundle empty after Init with resolved dir")
	}
}

func TestIsLocalesDir_RejectsIncomplete(t *testing.T) {
	dir := t.TempDir()
	if isLocalesDir(dir) {
		t.Fatal("empty dir accepted")
	}
	if err := os.WriteFile(filepath.Join(dir, "en.json"), []byte(`{}`), 0o644); err != nil {
		t.Fatal(err)
	}
	if isLocalesDir(dir) {
		t.Fatal("dir missing zh.json accepted")
	}
}

package i18n

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
)

// LocalesEnvVar overrides locale directory resolution when set.
// FIX-542: startup must not depend on the process CWD to find resources.
const LocalesEnvVar = "GATEWAY_LOCALES_DIR"

// maxWalkUpDepth bounds the CWD walk-up so a deeply nested foreign CWD
// cannot turn resolution into an unbounded scan.
const maxWalkUpDepth = 8

// localesMarkers are the files that must exist for a directory to count as
// the gateway locales dir (en/zh are the bundle's base languages).
var localesMarkers = []string{"en.json", "zh.json"}

// ErrLocalesDirNotFound is returned when no candidate directory holds the
// locale marker files. It is safe to surface to operators.
var ErrLocalesDirNotFound = errors.New("i18n: no locales dir found (tried env override, source anchor, CWD walk-up, CWD-relative)")

// DefaultLocalesDir resolves the gateway locales directory without trusting
// the process CWD. Resolution order (first candidate whose directory contains
// all marker files wins):
//
//  1. GATEWAY_LOCALES_DIR env override — must be a valid locales dir, a bogus
//     explicit value is an operator error and fails loud.
//  2. Source-anchored path: <gateway module root>/locales derived from this
//     file's build-time location — CWD-independent by construction.
//  3. Walk-up from CWD looking for a valid locales dir — covers running from
//     repo subdirectories.
//  4. CWD-relative "locales" — legacy behavior, kept as last resort.
//
// The returned diagnostics string lists the candidates tried, for startup logs.
func DefaultLocalesDir() (dir string, diag string, err error) {
	var tried []string

	// 1. Explicit env override: fail loud when set but invalid.
	if p := os.Getenv(LocalesEnvVar); p != "" {
		if isLocalesDir(p) {
			return p, fmt.Sprintf("%s=%s (env override)", LocalesEnvVar, p), nil
		}
		return "", fmt.Sprintf("%s=%s (env override set but invalid: missing %v)", LocalesEnvVar, p, localesMarkers),
			fmt.Errorf("%s=%s is not a valid locales dir (missing %v)", LocalesEnvVar, p, localesMarkers)
	}

	// 2. Source anchor: this file sits at <gateway>/internal/i18n/resolve.go.
	if _, thisFile, _, ok := runtime.Caller(0); ok {
		// internal/i18n -> gateway module root is two levels up.
		anchored := filepath.Clean(filepath.Join(filepath.Dir(thisFile), "..", "..", "locales"))
		tried = append(tried, anchored)
		if isLocalesDir(anchored) {
			return anchored, fmt.Sprintf("source-anchored %s", anchored), nil
		}
	}

	// 3. Walk up from CWD (covers go run from backend/ or repo root).
	if cwd, err := os.Getwd(); err == nil {
		d := cwd
		for i := 0; i <= maxWalkUpDepth; i++ {
			cand := filepath.Join(d, "locales")
			tried = append(tried, cand)
			if isLocalesDir(cand) {
				return cand, fmt.Sprintf("CWD walk-up %s", cand), nil
			}
			parent := filepath.Dir(d)
			if parent == d {
				break
			}
			d = parent
		}
	}

	// 4. Legacy CWD-relative path (same as walk-up depth-0, kept for parity
	//    with the pre-FIX-542 behavior in diagnostics).
	if cwd, err := os.Getwd(); err == nil {
		cand := filepath.Join(cwd, "locales")
		found := false
		for _, t := range tried {
			if t == cand {
				found = true
				break
			}
		}
		if !found {
			tried = append(tried, cand)
			if isLocalesDir(cand) {
				return cand, fmt.Sprintf("CWD-relative %s", cand), nil
			}
		}
	}

	return "", fmt.Sprintf("candidates tried: %v", tried), ErrLocalesDirNotFound
}

// isLocalesDir reports whether dir exists and holds every marker file.
func isLocalesDir(dir string) bool {
	if dir == "" {
		return false
	}
	info, err := os.Stat(dir)
	if err != nil || !info.IsDir() {
		return false
	}
	for _, m := range localesMarkers {
		if fi, err := os.Stat(filepath.Join(dir, m)); err != nil || fi.IsDir() {
			return false
		}
	}
	return true
}

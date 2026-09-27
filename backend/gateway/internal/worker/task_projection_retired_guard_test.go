package worker

import (
	"bufio"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
)

// V3-FIX-356 (wt661 2026-09-25) structural retirement guard.
//
// The gateway task CQRS projection family — worker.TaskSyncWorker (live
// cqrs:stream:task consumer) and cqrs/projection TaskProjectionHandler
// (event_store replay) — was removed: both wrote the task:view:* /
// user:tasks:* / user:task:stats:* Redis key family with zero read
// consumers repo-wide (the only Get("task:view:...") was each writer
// reading back its own writes), and the two writers had already diverged
// in schema (typed TaskView struct vs ad-hoc map, abandoned=update vs
// abandoned=delete, priority vs created_at pending scores). Any future
// wiring of those keys would therefore have silently become a second task
// source of truth, competing with the actual read authority: the engine
// REST surface proxied at /api/v1/tasks* plus gateway direct PG reads
// (service/user_context.go).
//
// This guard pins the retirement: while the key family has no named read
// consumer, no production Go source in this module may write or read the
// retired key prefixes. Reintroducing a task projector requires removing a
// literal below together with the consumer it serves and a drift test —
// i.e. a deliberate, reviewable adjudication, not an accidental rewiring.
func TestTaskProjectionKeyFamilyRetired(t *testing.T) {
	retiredPrefixes := []string{
		"task:view:",
		"user:tasks:",
		"user:task:stats:",
	}

	gatewayRoot, err := filepath.Abs(filepath.Join("..", ".."))
	if err != nil {
		t.Fatalf("resolve gateway root: %v", err)
	}

	var violations []string
	walkErr := filepath.WalkDir(gatewayRoot, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		// Generated code, docs and non-Go assets are out of scope; *_test.go
		// files are exempt (including this one, which must contain the
		// literals it scans for) so the guard only pins production code.
		if d.IsDir() {
			switch d.Name() {
			case "gen", "docs", "tests", "benchmark", ".git":
				return filepath.SkipDir
			}
			return nil
		}
		if !strings.HasSuffix(path, ".go") || strings.HasSuffix(path, "_test.go") {
			return nil
		}

		f, err := os.Open(path)
		if err != nil {
			return err
		}
		defer f.Close()

		scanner := bufio.NewScanner(f)
		lineNo := 0
		for scanner.Scan() {
			lineNo++
			line := scanner.Text()
			for _, prefix := range retiredPrefixes {
				if strings.Contains(line, prefix) {
					rel, _ := filepath.Rel(gatewayRoot, path)
					violations = append(violations,
						rel+":"+strconv.Itoa(lineNo)+" contains retired task projection key prefix "+prefix)
					break
				}
			}
		}
		return scanner.Err()
	})
	if walkErr != nil {
		t.Fatalf("walk gateway sources: %v", walkErr)
	}

	if len(violations) > 0 {
		t.Fatalf("task CQRS projection family is retired (V3-FIX-356): no production code may touch its Redis keys without a new adjudication;\n%s",
			strings.Join(violations, "\n"))
	}
}

package middleware

import "testing"

func TestIsLongRunningRoute(t *testing.T) {
	tests := []struct {
		path string
		want bool
	}{
		{path: "/api/v1/stt/transcribe", want: true},
		{path: "/api/v1/capsules/generate", want: true},
		{path: "/api/v1/capsules/generate/batch", want: true},
		{path: "/api/v1/learning-paths/node-1/full-plan", want: true},
		{path: "/api/v1/plans/123/generate-tasks", want: true},
		{path: "/api/v1/plans/123", want: false},
		{path: "/api/v1/chat/sessions", want: false},
	}

	for _, tc := range tests {
		if got := isLongRunningRoute(tc.path); got != tc.want {
			t.Fatalf("isLongRunningRoute(%q) = %v, want %v", tc.path, got, tc.want)
		}
	}
}

package main

import "testing"

func TestShouldProxyNoRoutePath(t *testing.T) {
	t.Parallel()

	cases := []struct {
		path string
		want bool
	}{
		{path: "/api/v1/auth/login", want: true},
		{path: "/api/v1/auth/refresh", want: true},
		{path: "/api/v1/health", want: false},
		{path: "/docs", want: false},
		{path: "/openapi.json", want: false},
		{path: "/api/v1/unknown", want: false},
	}

	for _, tc := range cases {
		tc := tc
		t.Run(tc.path, func(t *testing.T) {
			t.Parallel()
			if got := shouldProxyNoRoutePath(tc.path); got != tc.want {
				t.Fatalf("shouldProxyNoRoutePath(%q) = %v, want %v", tc.path, got, tc.want)
			}
		})
	}
}

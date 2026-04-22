package handler

import (
	"testing"

	"google.golang.org/grpc/codes"
	grpcstatus "google.golang.org/grpc/status"
)

func TestGrpcStreamErrorDetailsMapsGrpcCode(t *testing.T) {
	code, message, retryable := grpcStreamErrorDetails(grpcstatus.Error(codes.ResourceExhausted, "quota exceeded"))
	if code != "resource_exhausted" {
		t.Fatalf("expected resource_exhausted, got %s", code)
	}
	if message != "quota exceeded" {
		t.Fatalf("expected message to pass through, got %s", message)
	}
	if retryable {
		t.Fatalf("resource exhausted should not be retryable")
	}
}

func TestLegacyStreamErrorPayloadCarriesWsContract(t *testing.T) {
	payload := legacyStreamErrorPayload("unavailable", "agent offline", true)
	if payload["type"] != "error" {
		t.Fatalf("expected error type, got %v", payload["type"])
	}
	if payload["error_code"] != "unavailable" {
		t.Fatalf("expected unavailable code, got %v", payload["error_code"])
	}
	if payload["message"] != "agent offline" {
		t.Fatalf("expected passthrough message, got %v", payload["message"])
	}
	if payload["retryable"] != true {
		t.Fatalf("expected retryable=true, got %v", payload["retryable"])
	}
	if len(payload) != 4 {
		t.Fatalf("expected stable four-field payload, got %d", len(payload))
	}
}

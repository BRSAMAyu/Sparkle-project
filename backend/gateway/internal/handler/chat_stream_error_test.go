package handler

import (
	"errors"
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

func TestGrpcStreamErrorDetailsSanitizesInternalMessages(t *testing.T) {
	code, message, retryable := grpcStreamErrorDetails(grpcstatus.Error(codes.Internal, "panic: postgres://user:pass@db:5432/sparkle"))
	if code != "internal" {
		t.Fatalf("expected internal, got %s", code)
	}
	if message != defaultWSInternalMessage {
		t.Fatalf("expected sanitized internal message, got %q", message)
	}
	if !retryable {
		t.Fatalf("internal errors should remain retryable")
	}
}

func TestGrpcStreamErrorDetailsSanitizesNonGRPCErrors(t *testing.T) {
	code, message, retryable := grpcStreamErrorDetails(errors.New("dial tcp 10.0.0.9:50051: connection refused"))
	if code != "unknown" {
		t.Fatalf("expected unknown, got %s", code)
	}
	if message != defaultWSInternalMessage {
		t.Fatalf("expected sanitized unknown message, got %q", message)
	}
	if !retryable {
		t.Fatalf("unknown transport errors should remain retryable")
	}
}

func TestLegacyStreamErrorPayloadCarriesWsContract(t *testing.T) {
	payload := legacyStreamErrorPayload("unavailable", "agent offline", true, "req-123")
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
	if payload["request_id"] != "req-123" {
		t.Fatalf("expected request_id=req-123, got %v", payload["request_id"])
	}
}

func TestLegacyStreamErrorPayloadOmitsEmptyRequestID(t *testing.T) {
	payload := legacyStreamErrorPayload("resource_exhausted", "busy", true, "")
	if _, exists := payload["request_id"]; exists {
		t.Fatalf("expected no request_id key when empty, got %v", payload["request_id"])
	}
}

func TestLegacyStreamErrorPayloadIncludesRequestIDForAllPaths(t *testing.T) {
	tests := []struct {
		name      string
		code      string
		message   string
		retryable bool
		requestID string
	}{
		{"resource_exhausted", "resource_exhausted", "Server busy", true, "req-res-1"},
		{"duplicate_request", "duplicate_request", "Already accepted", false, "req-dup-2"},
		{"stream_recv_error", "unavailable", "Stream interrupted", true, "req-str-3"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			payload := legacyStreamErrorPayload(tt.code, tt.message, tt.retryable, tt.requestID)
			if payload["request_id"] != tt.requestID {
				t.Errorf("expected request_id=%s, got %v", tt.requestID, payload["request_id"])
			}
			if payload["error_code"] != tt.code {
				t.Errorf("expected error_code=%s, got %v", tt.code, payload["error_code"])
			}
		})
	}
}

package logsafe

import (
	"strings"
	"testing"
)

func TestRedactTextRemovesPIIAndSecrets(t *testing.T) {
	raw := "user Ada email ada@example.com phone 13812345678 auth Bearer abcdefghijk token=secret-value sk-testsecret123"

	got := RedactText(raw)

	for _, leaked := range []string{"ada@example.com", "13812345678", "abcdefghijk", "secret-value", "sk-testsecret123"} {
		if strings.Contains(got, leaked) {
			t.Fatalf("RedactText leaked %q in %q", leaked, got)
		}
	}
	for _, marker := range []string{"[REDACTED_EMAIL]", "[REDACTED_PHONE]", "Bearer [REDACTED]", "token=[REDACTED]", "[REDACTED_API_KEY]"} {
		if !strings.Contains(got, marker) {
			t.Fatalf("RedactText missing marker %q in %q", marker, got)
		}
	}
}

func TestUserIDHashIsStableAndDoesNotExposeInput(t *testing.T) {
	raw := "user@example.com"

	first := UserIDHash(raw)
	second := UserIDHash(raw)

	if first == "" || first != second {
		t.Fatalf("UserIDHash must be stable and non-empty: %q vs %q", first, second)
	}
	if strings.Contains(first, raw) || len(first) != 12 {
		t.Fatalf("UserIDHash exposed raw identifier or wrong length: %q", first)
	}
}

package logsafe

import (
	"crypto/sha256"
	"encoding/hex"
	"regexp"
	"strings"
)

var (
	emailPattern        = regexp.MustCompile(`(?i)\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b`)
	phonePattern        = regexp.MustCompile(`\b(?:\+?86[- ]?)?1[3-9]\d{9}\b`)
	cnIDPattern         = regexp.MustCompile(`\b(?:\d{17}[\dXx]|\d{15})\b`)
	bearerPattern       = regexp.MustCompile(`(?i)\bBearer\s+[A-Za-z0-9._\-]{8,}`)
	apiKeyPattern       = regexp.MustCompile(`\bsk-[A-Za-z0-9][A-Za-z0-9._\-]{8,}\b`)
	assignmentSecretPat = regexp.MustCompile(`(?i)\b(api[_ -]?key|secret|token|password|authorization)\b\s*[:=]\s*([^\s,;]+)`)
	urlCredentialPat    = regexp.MustCompile(`([A-Za-z][A-Za-z0-9+.\-]*://)([^/\s:@]+):([^@\s/]+)@`)
)

// UserIDHash returns a stable, non-reversible log token for user identifiers.
func UserIDHash(userID string) string {
	normalized := strings.TrimSpace(userID)
	if normalized == "" {
		return ""
	}
	sum := sha256.Sum256([]byte(normalized))
	return hex.EncodeToString(sum[:])[:12]
}

// RedactText removes common PII and secret shapes before text reaches logs.
func RedactText(text string) string {
	value := strings.TrimSpace(text)
	if value == "" {
		return ""
	}
	value = bearerPattern.ReplaceAllString(value, "Bearer [REDACTED]")
	value = apiKeyPattern.ReplaceAllString(value, "[REDACTED_API_KEY]")
	value = assignmentSecretPat.ReplaceAllString(value, "$1=[REDACTED]")
	value = urlCredentialPat.ReplaceAllString(value, "$1[REDACTED]:[REDACTED]@")
	value = emailPattern.ReplaceAllString(value, "[REDACTED_EMAIL]")
	value = phonePattern.ReplaceAllString(value, "[REDACTED_PHONE]")
	value = cnIDPattern.ReplaceAllString(value, "[REDACTED_CN_ID]")
	if len(value) > 240 {
		value = strings.TrimSpace(value[:237]) + "..."
	}
	return value
}

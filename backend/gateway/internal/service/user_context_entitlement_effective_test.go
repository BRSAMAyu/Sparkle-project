package service

import (
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgtype"
)

// D-REDEEM · 到期降级判级（与引擎 app/core/entitlement.entitlement_effective 同语义）。
func TestIsProEntitlementEffective(t *testing.T) {
	now := time.Now()
	future := pgtype.Timestamp{Time: now.Add(24 * time.Hour), Valid: true}
	past := pgtype.Timestamp{Time: now.Add(-24 * time.Hour), Valid: true}
	edge := pgtype.Timestamp{Time: now.Add(-time.Millisecond), Valid: true}
	never := pgtype.Timestamp{Valid: false}

	cases := []struct {
		name        string
		entitlement string
		expiresAt   pgtype.Timestamp
		want        bool
	}{
		{"pro with future expiry", "pro", future, true},
		{"pro without expiry stays permanent", "pro", never, true},
		{"pro with past expiry degrades to free", "pro", past, false},
		{"pro at expiry boundary degrades", "pro", edge, false},
		{"free never upgrades", "free", future, false},
		{"unknown degrades even with future expiry", "premium", future, false},
		{"empty degrades", "", never, false},
		{"mixed case pro recognized", "Pro", future, true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := IsProEntitlementEffective(tc.entitlement, tc.expiresAt); got != tc.want {
				t.Fatalf("IsProEntitlementEffective(%q, valid=%v) = %v, want %v",
					tc.entitlement, tc.expiresAt.Valid, got, tc.want)
			}
		})
	}
}

// 存量函数回归：IsProEntitlement 语义保持（无 expiry 入参面不变）。
func TestIsProEntitlementLegacySemanticsUnchanged(t *testing.T) {
	if !IsProEntitlement("pro") || IsProEntitlement("free") || IsProEntitlement("") || IsProEntitlement("premium") {
		t.Fatal("legacy IsProEntitlement semantics drifted")
	}
}

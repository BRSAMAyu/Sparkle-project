// Package intsafe provides explicit bounds-checked integer narrowing helpers.
//
// gosec flags unchecked narrowing conversions (G115 int→int32/int64→int32)
// because they silently wrap on overflow. These helpers make the safety
// argument explicit at each sink instead of suppressing the finding: callers
// either fail fast on an out-of-range value (CheckedInt32, for config- and
// domain-driven values where wrap would be a bug) or saturate a monotone
// accumulator (SaturateInt32, where a failed conversion is worse than a
// clamped counter).
package intsafe

import (
	"fmt"
	"math"
)

// CheckedInt32 narrows v to int32, returning an error when v does not fit.
func CheckedInt32(v int) (int32, error) {
	if v > math.MaxInt32 || v < math.MinInt32 {
		return 0, fmt.Errorf("intsafe: value %d out of int32 range", v)
	}
	return int32(v), nil
}

// SaturateInt32 narrows v to int32, clamping out-of-range values to
// [math.MinInt32, math.MaxInt32]. Values already in range pass through
// unchanged, so behavior is identical to a bare conversion whenever the
// conversion was safe.
func SaturateInt32(v int64) int32 {
	if v > math.MaxInt32 {
		return math.MaxInt32
	}
	if v < math.MinInt32 {
		return math.MinInt32
	}
	return int32(v)
}

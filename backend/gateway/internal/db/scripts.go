package db

import (
	_ "embed"
)

// Quota Lua scripts — the production quota chain is usage-metering based
// (GetDailyUsage / RecordUsage / RecordUsageSegment). The former
// reserve/refund/decr family was deleted as dead code (zero production
// callers; R2-05 §4.1 option 1, executed by the P3 gateway handoff trio) —
// see query_contract_test.go for the deletion ratchet.

//go:embed scripts/record_usage.lua
var RecordUsageScript string

//go:embed scripts/record_usage_segment.lua
var RecordUsageSegmentScript string

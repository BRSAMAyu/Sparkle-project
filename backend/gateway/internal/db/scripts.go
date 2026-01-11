package db

import (
	_ "embed"
)

//go:embed scripts/decr_quota.lua
var DecrQuotaScript string

//go:embed scripts/reserve_quota.lua
var ReserveQuotaScript string

//go:embed scripts/record_usage.lua
var RecordUsageScript string

//go:embed scripts/record_usage_segment.lua
var RecordUsageSegmentScript string

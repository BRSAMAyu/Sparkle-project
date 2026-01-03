package db

import (
	_ "embed"
)

//go:embed scripts/decr_quota.lua
var DecrQuotaScript string

package handler

import (
	"testing"

	"github.com/stretchr/testify/require"
)

// TestProxyRoutesHandler_SquadSharedErrorRoutesRegistered pins the D-COMM-5
// routes: squad shared error cards (knowledge mutual-aid). The engine serves
// them at /api/v1/community/squads/{id}/shared-errors (api/v1/
// community_squad_shared_errors.py); the gateway must proxy each method/path
// exactly — a missing registration is a guaranteed 404 for the mobile client.
func TestProxyRoutesHandler_SquadSharedErrorRoutesRegistered(t *testing.T) {
	router := r208TestRouter(t)

	mustExist := []string{
		"POST /api/v1/community/squads/:group_id/shared-errors",
		"GET /api/v1/community/squads/:group_id/shared-errors",
		"DELETE /api/v1/community/squads/:group_id/shared-errors/:share_id",
	}

	registered := make(map[string]bool, len(router.Routes()))
	for _, rt := range router.Routes() {
		registered[rt.Method+" "+rt.Path] = true
	}

	for _, key := range mustExist {
		require.True(t, registered[key], "D-COMM-5 route missing: %s", key)
	}
}

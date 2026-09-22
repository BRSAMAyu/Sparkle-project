package handler

import (
	"testing"

	"github.com/stretchr/testify/require"
)

// TestProxyRoutesHandler_SprintSquadRoutesRegistered pins the D-COMM-3 sprint
// squad MVP routes (community × exam_sprint first integration). The engine
// serves them at /api/v1/community/squads/** (api/v1/community_squad.py); the
// gateway must proxy each method/path exactly — a missing registration is a
// guaranteed 404 for the mobile client.
func TestProxyRoutesHandler_SprintSquadRoutesRegistered(t *testing.T) {
	router := r208TestRouter(t)

	mustExist := []string{
		"POST /api/v1/community/squads",
		"GET /api/v1/community/squads",
		"GET /api/v1/community/squads/:group_id",
		"POST /api/v1/community/squads/:group_id/join",
		"POST /api/v1/community/squads/:group_id/leave",
		"GET /api/v1/community/squads/:group_id/members",
		"GET /api/v1/community/squads/:group_id/sprint-progress",
	}

	registered := make(map[string]bool, len(router.Routes()))
	for _, rt := range router.Routes() {
		registered[rt.Method+" "+rt.Path] = true
	}

	for _, key := range mustExist {
		require.True(t, registered[key], "sprint squad route missing: %s", key)
	}
}

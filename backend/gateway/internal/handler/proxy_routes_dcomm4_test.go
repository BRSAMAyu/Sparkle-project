package handler

import (
	"testing"

	"github.com/stretchr/testify/require"
)

// TestProxyRoutesHandler_SquadStudyRoomAndBoardRoutesRegistered pins the
// D-COMM-4 routes: squad study room (beacon-style presence proof) and the
// sprint-completion squad leaderboard. The engine serves them at
// /api/v1/community/squads/{id}/study-room/** (api/v1/community_study_room.py)
// and /api/v1/community/squads/{id}/leaderboard (api/v1/community_squad_board.py);
// the gateway must proxy each method/path exactly — a missing registration is
// a guaranteed 404 for the mobile client.
func TestProxyRoutesHandler_SquadStudyRoomAndBoardRoutesRegistered(t *testing.T) {
	router := r208TestRouter(t)

	mustExist := []string{
		"POST /api/v1/community/squads/:group_id/study-room/enter",
		"POST /api/v1/community/squads/:group_id/study-room/exit",
		"POST /api/v1/community/squads/:group_id/study-room/heartbeat",
		"GET /api/v1/community/squads/:group_id/study-room/presence",
		"GET /api/v1/community/squads/:group_id/leaderboard",
	}

	registered := make(map[string]bool, len(router.Routes()))
	for _, rt := range router.Routes() {
		registered[rt.Method+" "+rt.Path] = true
	}

	for _, key := range mustExist {
		require.True(t, registered[key], "D-COMM-4 route missing: %s", key)
	}
}

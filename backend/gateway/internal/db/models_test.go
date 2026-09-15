package db

import (
	"testing"

	"github.com/stretchr/testify/require"
)

func TestGeneratedEnumScannersAndNullValues(t *testing.T) {
	tests := []struct {
		name     string
		exercise func(t *testing.T)
	}{
		{name: "Accountabilityslottype", exercise: func(t *testing.T) {
			var value Accountabilityslottype
			require.NoError(t, value.Scan("core"))
			require.Equal(t, Accountabilityslottype("core"), value)
			require.NoError(t, value.Scan([]byte("core-bytes")))
			require.Equal(t, Accountabilityslottype("core-bytes"), value)
			require.Error(t, value.Scan(7))
			var nullable NullAccountabilityslottype
			require.NoError(t, nullable.Scan(nil))
			require.False(t, nullable.Valid)
			got, err := nullable.Value()
			require.NoError(t, err)
			require.Nil(t, got)
			require.NoError(t, nullable.Scan("core"))
			require.True(t, nullable.Valid)
			got, err = nullable.Value()
			require.NoError(t, err)
			require.Equal(t, "core", got)
		}},
		{name: "Accountabilitystatus", exercise: func(t *testing.T) {
			var value Accountabilitystatus
			require.NoError(t, value.Scan("active"))
			require.Equal(t, Accountabilitystatus("active"), value)
			require.NoError(t, value.Scan([]byte("paused")))
			require.Equal(t, Accountabilitystatus("paused"), value)
			require.Error(t, value.Scan(7))
			var nullable NullAccountabilitystatus
			require.NoError(t, nullable.Scan(nil))
			require.False(t, nullable.Valid)
			got, err := nullable.Value()
			require.NoError(t, err)
			require.Nil(t, got)
			require.NoError(t, nullable.Scan("ended"))
			require.True(t, nullable.Valid)
			got, err = nullable.Value()
			require.NoError(t, err)
			require.Equal(t, "ended", got)
		}},
		{name: "Achievementrarity", exercise: func(t *testing.T) {
			var value Achievementrarity
			require.NoError(t, value.Scan("COMMON"))
			require.Equal(t, Achievementrarity("COMMON"), value)
			require.NoError(t, value.Scan([]byte("RARE")))
			require.Equal(t, Achievementrarity("RARE"), value)
			require.Error(t, value.Scan(7))
			var nullable NullAchievementrarity
			require.NoError(t, nullable.Scan(nil))
			require.False(t, nullable.Valid)
			got, err := nullable.Value()
			require.NoError(t, err)
			require.Nil(t, got)
			require.NoError(t, nullable.Scan("EPIC"))
			require.True(t, nullable.Valid)
			got, err = nullable.Value()
			require.NoError(t, err)
			require.Equal(t, "EPIC", got)
		}},
		{name: "Achievementtype", exercise: func(t *testing.T) {
			var value Achievementtype
			require.NoError(t, value.Scan("MILESTONE"))
			require.Equal(t, Achievementtype("MILESTONE"), value)
			require.NoError(t, value.Scan([]byte("STREAK")))
			require.Equal(t, Achievementtype("STREAK"), value)
			require.Error(t, value.Scan(7))
			var nullable NullAchievementtype
			require.NoError(t, nullable.Scan(nil))
			require.False(t, nullable.Valid)
			got, err := nullable.Value()
			require.NoError(t, err)
			require.Nil(t, got)
			require.NoError(t, nullable.Scan("SOCIAL"))
			require.True(t, nullable.Valid)
			got, err = nullable.Value()
			require.NoError(t, err)
			require.Equal(t, "SOCIAL", got)
		}},
		{name: "Analysisstatus", exercise: func(t *testing.T) {
			var value Analysisstatus
			require.NoError(t, value.Scan("PENDING"))
			require.Equal(t, Analysisstatus("PENDING"), value)
			require.NoError(t, value.Scan([]byte("COMPLETED")))
			require.Equal(t, Analysisstatus("COMPLETED"), value)
			require.Error(t, value.Scan(7))
			var nullable NullAnalysisstatus
			require.NoError(t, nullable.Scan(nil))
			require.False(t, nullable.Valid)
			got, err := nullable.Value()
			require.NoError(t, err)
			require.Nil(t, got)
			require.NoError(t, nullable.Scan("FAILED"))
			require.True(t, nullable.Valid)
			got, err = nullable.Value()
			require.NoError(t, err)
			require.Equal(t, "FAILED", got)
		}},
		{name: "Avatarstatus", exercise: func(t *testing.T) {
			var value Avatarstatus
			require.NoError(t, value.Scan("APPROVED"))
			require.Equal(t, Avatarstatus("APPROVED"), value)
			require.NoError(t, value.Scan([]byte("PENDING")))
			require.Equal(t, Avatarstatus("PENDING"), value)
			require.Error(t, value.Scan(7))
			var nullable NullAvatarstatus
			require.NoError(t, nullable.Scan(nil))
			require.False(t, nullable.Valid)
			got, err := nullable.Value()
			require.NoError(t, err)
			require.Nil(t, got)
			require.NoError(t, nullable.Scan("REJECTED"))
			require.True(t, nullable.Valid)
			got, err = nullable.Value()
			require.NoError(t, err)
			require.Equal(t, "REJECTED", got)
		}},
		{name: "Backgroundtaskstatus", exercise: func(t *testing.T) {
			var value Backgroundtaskstatus
			require.NoError(t, value.Scan("PENDING"))
			require.Equal(t, Backgroundtaskstatus("PENDING"), value)
			require.NoError(t, value.Scan([]byte("RUNNING")))
			require.Equal(t, Backgroundtaskstatus("RUNNING"), value)
			require.Error(t, value.Scan(7))
			var nullable NullBackgroundtaskstatus
			require.NoError(t, nullable.Scan(nil))
			require.False(t, nullable.Valid)
			got, err := nullable.Value()
			require.NoError(t, err)
			require.Nil(t, got)
			require.NoError(t, nullable.Scan("COMPLETED"))
			require.True(t, nullable.Valid)
			got, err = nullable.Value()
			require.NoError(t, err)
			require.Equal(t, "COMPLETED", got)
		}},
		{name: "Backgroundtasktype", exercise: func(t *testing.T) {
			var value Backgroundtasktype
			require.NoError(t, value.Scan("AI_GENERATION"))
			require.Equal(t, Backgroundtasktype("AI_GENERATION"), value)
			require.NoError(t, value.Scan([]byte("DATA_SYNC")))
			require.Equal(t, Backgroundtasktype("DATA_SYNC"), value)
			require.Error(t, value.Scan(7))
			var nullable NullBackgroundtasktype
			require.NoError(t, nullable.Scan(nil))
			require.False(t, nullable.Valid)
			got, err := nullable.Value()
			require.NoError(t, err)
			require.Nil(t, got)
			require.NoError(t, nullable.Scan("TASK_BATCH"))
			require.True(t, nullable.Valid)
			got, err = nullable.Value()
			require.NoError(t, err)
			require.Equal(t, "TASK_BATCH", got)
		}},
		{name: "Contractstatus", exercise: func(t *testing.T) {
			var value Contractstatus
			require.NoError(t, value.Scan("ACTIVE"))
			require.Equal(t, Contractstatus("ACTIVE"), value)
			require.NoError(t, value.Scan([]byte("COMPLETED")))
			require.Equal(t, Contractstatus("COMPLETED"), value)
			require.Error(t, value.Scan(7))
			var nullable NullContractstatus
			require.NoError(t, nullable.Scan(nil))
			require.False(t, nullable.Valid)
			got, err := nullable.Value()
			require.NoError(t, err)
			require.Nil(t, got)
			require.NoError(t, nullable.Scan("EXPIRED"))
			require.True(t, nullable.Valid)
			got, err = nullable.Value()
			require.NoError(t, err)
			require.Equal(t, "EXPIRED", got)
		}},
		{name: "Taskstatus", exercise: func(t *testing.T) {
				// ISSUE-20260503-2100-I1: all 7 values must be scannable
				for _, status := range []string{"PENDING", "IN_PROGRESS", "PAUSED", "RESTORE", "STUCK", "COMPLETED", "ABANDONED"} {
					var value Taskstatus
					require.NoError(t, value.Scan(status))
					require.Equal(t, Taskstatus(status), value)
				}
				var value Taskstatus
				require.Error(t, value.Scan(7))
				var nullable NullTaskstatus
				require.NoError(t, nullable.Scan(nil))
				require.False(t, nullable.Valid)
				got, err := nullable.Value()
				require.NoError(t, err)
				require.Nil(t, got)
				require.NoError(t, nullable.Scan("RESTORE"))
				require.True(t, nullable.Valid)
				got, err = nullable.Value()
				require.NoError(t, err)
				require.Equal(t, "RESTORE", got)
			}},
			{name: "Depthlevel", exercise: func(t *testing.T) {
			var value Depthlevel
			require.NoError(t, value.Scan("SHALLOW"))
			require.Equal(t, Depthlevel("SHALLOW"), value)
			require.NoError(t, value.Scan([]byte("DEEP")))
			require.Equal(t, Depthlevel("DEEP"), value)
			require.Error(t, value.Scan(7))
			var nullable NullDepthlevel
			require.NoError(t, nullable.Scan(nil))
			require.False(t, nullable.Valid)
			got, err := nullable.Value()
			require.NoError(t, err)
			require.Nil(t, got)
			require.NoError(t, nullable.Scan("MEDIUM"))
			require.True(t, nullable.Valid)
			got, err = nullable.Value()
			require.NoError(t, err)
			require.Equal(t, "MEDIUM", got)
		}},
	}

	for _, tt := range tests {
		t.Run(tt.name, tt.exercise)
	}
}

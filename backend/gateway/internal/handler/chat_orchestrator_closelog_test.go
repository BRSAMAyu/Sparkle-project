package handler

// PROD-FIX-2 defect #5 regression pins: a client-initiated WebSocket close
// with status 1000 (normal) is expected traffic and must stay out of the warn
// baseline (production evidence: 223 false "websocket: close 1000 (normal)"
// warns in 5 days, chat_orchestrator.go). Only genuinely unexpected close
// codes warn.

import (
	"errors"
	"testing"

	"github.com/gorilla/websocket"
	"github.com/stretchr/testify/require"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
	"go.uber.org/zap/zaptest/observer"
)

func closeErrOf(code int) error { return &websocket.CloseError{Code: code, Text: "test"} }

func TestLogWebSocketReadError_NormalCloseIsDebugNotWarn(t *testing.T) {
	core, logs := observer.New(zapcore.DebugLevel)
	restore := zap.ReplaceGlobals(zap.New(core))
	defer restore()

	logWebSocketReadError(closeErrOf(websocket.CloseNormalClosure)) // close 1000

	require.Empty(t, logs.FilterMessage("WebSocket read error").All(),
		"close 1000 (normal) must never warn — it is the alert-baseline defect")
	debugs := logs.FilterMessage("WebSocket closed normally by client").All()
	require.Len(t, debugs, 1)
	require.Equal(t, zapcore.DebugLevel, debugs[0].Level)
}

func TestLogWebSocketReadError_GoingAwayAndAbnormalStaySilent(t *testing.T) {
	core, logs := observer.New(zapcore.DebugLevel)
	restore := zap.ReplaceGlobals(zap.New(core))
	defer restore()

	// Historical behavior kept: these two carry no signal (teardown is driven
	// by closeCode) and were never logged.
	logWebSocketReadError(closeErrOf(websocket.CloseGoingAway))
	logWebSocketReadError(closeErrOf(websocket.CloseAbnormalClosure))

	require.Empty(t, logs.All())
}

func TestLogWebSocketReadError_UnexpectedCloseWarns(t *testing.T) {
	core, logs := observer.New(zapcore.DebugLevel)
	restore := zap.ReplaceGlobals(zap.New(core))
	defer restore()

	logWebSocketReadError(closeErrOf(websocket.CloseInternalServerErr)) // 1011

	warns := logs.FilterMessage("WebSocket read error").All()
	require.Len(t, warns, 1)
	require.Equal(t, zapcore.WarnLevel, warns[0].Level)
}

func TestLogWebSocketReadError_NonCloseErrorStaysUnlogged(t *testing.T) {
	core, logs := observer.New(zapcore.DebugLevel)
	restore := zap.ReplaceGlobals(zap.New(core))
	defer restore()

	// Pre-existing semantics: non-close read errors are handled by the caller
	// (stream cancel / close code), the classifier must not invent a log.
	logWebSocketReadError(errors.New("read: connection reset by peer"))

	require.Empty(t, logs.All())
}

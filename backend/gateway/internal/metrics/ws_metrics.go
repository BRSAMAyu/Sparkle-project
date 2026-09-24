package metrics

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	dto "github.com/prometheus/client_model/go"
)

var (
	WSTicketIssued = promauto.NewCounter(prometheus.CounterOpts{
		Name: "ws_ticket_issued_total",
		Help: "Total number of WebSocket tickets issued",
	})
	WSTicketIssueErrors = promauto.NewCounter(prometheus.CounterOpts{
		Name: "ws_ticket_issue_errors_total",
		Help: "Total number of WebSocket ticket issuance errors",
	})
	WSTicketConsumeSuccess = promauto.NewCounter(prometheus.CounterOpts{
		Name: "ws_ticket_consume_success_total",
		Help: "Total number of WebSocket tickets consumed successfully",
	})
	WSTicketConsumeFailure = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "ws_ticket_consume_failure_total",
		Help: "Total number of WebSocket ticket consumption failures",
	}, []string{"reason"})
	WSConnectionSuccess = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "ws_connection_success_total",
		Help: "Total number of successful WebSocket connections",
	}, []string{"endpoint", "auth_method"})
	WSConnectionError = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "ws_connection_error_total",
		Help: "Total number of failed WebSocket connections",
	}, []string{"endpoint", "auth_method", "reason"})
	// WSUpgradeLimited counts handshakes rejected with 429 by the pre-auth
	// per-IP fallback pin in front of the 5 WS upgrade routes (WSQ-1,
	// WS-TICKET-DESIGN §3.4). Primary load-test signal for §6.2-S1: alerts
	// should fire on "sustained >0 alongside normal-connection success drop".
	WSUpgradeLimited = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "ws_upgrade_limited_total",
		Help: "Total number of WebSocket upgrade handshakes rejected by the pre-auth per-IP rate limit (429)",
	}, []string{"endpoint"})

	// ========== Phase 3: Enhanced WebSocket Metrics ==========

	// WSConnectionsActive tracks current active WebSocket connections
	WSConnectionsActive = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "sparkle_ws_connections_active",
		Help: "Current active WebSocket connections",
	})

	// WSMessageLatency tracks WebSocket message processing latency
	WSMessageLatency = promauto.NewHistogram(prometheus.HistogramOpts{
		Name:    "sparkle_ws_message_latency_seconds",
		Help:    "WebSocket message processing latency",
		Buckets: []float64{0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5},
	})

	// WSAckPending tracks messages waiting for ACK
	WSAckPending = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "sparkle_ws_ack_pending_messages",
		Help: "Messages waiting for ACK",
	})

	// WSCompressionApplied tracks compressed messages
	WSCompressionApplied = promauto.NewCounter(prometheus.CounterOpts{
		Name: "sparkle_ws_compression_applied_total",
		Help: "Total WebSocket messages compressed",
	})

	// WSMessageReceived tracks received messages by type
	WSMessageReceived = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "sparkle_ws_message_received_total",
		Help: "Total WebSocket messages received by type",
	}, []string{"message_type"})

	// WSMessageSent tracks sent messages by type
	WSMessageSent = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "sparkle_ws_message_sent_total",
		Help: "Total WebSocket messages sent by type",
	}, []string{"message_type"})

	// WSHeartbeatLatency tracks heartbeat RTT
	WSHeartbeatLatency = promauto.NewHistogram(prometheus.HistogramOpts{
		Name:    "sparkle_ws_heartbeat_latency_seconds",
		Help:    "WebSocket heartbeat round-trip time",
		Buckets: []float64{0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10},
	})

	// WSReconnectTotal tracks reconnection attempts
	WSReconnectTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "sparkle_ws_reconnect_total",
		Help: "Total WebSocket reconnection attempts",
	}, []string{"status"}) // status: success, failed

	// WSMessageDedupTotal tracks deduplicated messages
	WSMessageDedupTotal = promauto.NewCounter(prometheus.CounterOpts{
		Name: "sparkle_ws_message_dedup_total",
		Help: "Total duplicate messages detected and dropped",
	})

	// QuotaDailyUsageLoadErrors tracks failures to load a user's daily token
	// usage before a chat stream. Quota enforcement degrades to the local
	// instance-level fallback on these errors (GW-P2-4 bounded degradation),
	// so a rising rate means billing precision is degraded and must be
	// alerted on.
	QuotaDailyUsageLoadErrors = promauto.NewCounter(prometheus.CounterOpts{
		Name: "sparkle_quota_daily_usage_load_errors_total",
		Help: "Daily usage load failures that degrade quota enforcement to the local instance-level fallback",
	})

	// QuotaLocalFallbackActive reports whether quota enforcement is currently
	// running on the local instance-level approximate daily cap because Redis
	// daily-usage loads are failing (GW-P2-4 bounded degradation). 1 = local
	// fallback engaged, 0 = Redis-backed accounting healthy. Alert on any
	// sustained 1: the instance is serving on an approximate cap and usage
	// recorded in Redis is incomplete for the affected turns.
	QuotaLocalFallbackActive = promauto.NewGauge(prometheus.GaugeOpts{
		Name: "sparkle_quota_local_fallback_active",
		Help: "1 when chat quota enforcement is on the local instance-level fallback cap (Redis daily usage unavailable), 0 when Redis-backed",
	})

	// KeyAuthFailures counts static-key auth rejections on the admin and
	// internal API surfaces (GW-P3/R2-GW-9). These requests are rejected
	// before any rate limiting sees them, so without this counter
	// brute-force probing is only visible in logs.
	KeyAuthFailures = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "sparkle_key_auth_failures_total",
		Help: "Static key auth rejections before rate limiting (mechanism: admin_secret|internal_api_key; reason: not_configured|missing|invalid)",
	}, []string{"mechanism", "reason"})

	// FileEventSubscriberRestarts counts restarts of the /ws/files Redis
	// pubsub subscriber loop (R2-GW-3). Each increment is one more interval
	// in which file status pushes were dead or degraded; a rising rate means
	// the subscription is unstable (Redis connectivity or panic) and must be
	// alerted on.
	FileEventSubscriberRestarts = promauto.NewCounter(prometheus.CounterOpts{
		Name: "sparkle_file_event_subscriber_restarts_total",
		Help: "Restarts of the file status pubsub subscriber loop (panics and terminal errors)",
	})

	AIChatTotalDuration = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name:    "sparkle_ai_chat_total_duration_seconds",
		Help:    "Total AI chat request duration from gateway receipt to final completion",
		Buckets: []float64{0.25, 0.5, 1, 2.5, 5, 10, 20, 40, 80},
	}, []string{"chat_mode"})

	AIChatFirstEventDuration = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name:    "sparkle_ai_chat_first_event_duration_seconds",
		Help:    "Time to first chat stream event",
		Buckets: []float64{0.1, 0.25, 0.5, 1, 2.5, 5, 10, 20},
	}, []string{"chat_mode"})

	AIChatFirstTokenDuration = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name:    "sparkle_ai_chat_first_token_duration_seconds",
		Help:    "Time to first visible chat token or full text payload",
		Buckets: []float64{0.1, 0.25, 0.5, 1, 2.5, 5, 10, 20},
	}, []string{"chat_mode"})

	AIChatStreamDuration = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name:    "sparkle_ai_chat_stream_duration_seconds",
		Help:    "Streaming phase duration after first token or first event",
		Buckets: []float64{0.1, 0.25, 0.5, 1, 2.5, 5, 10, 20, 40},
	}, []string{"chat_mode"})

	// ========== Community WebSocket Metrics ==========

	WSCommunityConnectionTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "ws_community_connection_total",
		Help: "Total number of community WebSocket connections (group/personal)",
	}, []string{"type", "status"})

	WSCommunityMessageSentTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "ws_community_message_sent_total",
		Help: "Total number of messages sent via community WebSocket",
	}, []string{"type", "message_type"})

	WSCommunityMessageReceivedTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "ws_community_message_received_total",
		Help: "Total number of messages received via community WebSocket",
	}, []string{"type", "message_type"})

	WSCommunityConnectionDuration = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name:    "ws_community_connection_duration_seconds",
		Help:    "Community WebSocket connection duration",
		Buckets: prometheus.ExponentialBuckets(1, 2, 10),
	}, []string{"type"})

	WSCommunityActiveConnections = promauto.NewGaugeVec(prometheus.GaugeOpts{
		Name: "ws_community_active_connections",
		Help: "Current number of active community WebSocket connections",
	}, []string{"type"})

	WSCommunityOfflinePushQueued = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "ws_community_offline_push_queued_total",
		Help: "Total number of push notifications queued for offline users",
	}, []string{"message_type"})

	WSCommunityAckTimeoutTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "ws_community_ack_timeout_total",
		Help: "Total number of message ACK timeouts",
	}, []string{"type"})

	WSCommunityDuplicateMessagesTotal = promauto.NewCounter(prometheus.CounterOpts{
		Name: "ws_community_duplicate_messages_total",
		Help: "Total number of duplicate messages detected and dropped",
	})

	// ========== Proto v2 Migration Metrics ==========

	ProtoFieldReadTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "ws_proto_field_read_total",
		Help: "Total protocol field reads by source during v1/v2 migration",
	}, []string{"field", "source"})

	ProtoDualWriteTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "ws_proto_dual_write_total",
		Help: "Total dual-write operations for legacy compatibility fields",
	}, []string{"field"})

	ProtoErrorCodeFallbackTotal = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "ws_proto_error_code_fallback_total",
		Help: "Total error-code fallback operations during protocol migration",
	}, []string{"direction"})
)

// QuotaLocalFallbackActiveGaugeValue reads the current value of
// QuotaLocalFallbackActive. It exists so other packages' tests can assert on
// the gauge without depending on prometheus testutil.
func QuotaLocalFallbackActiveGaugeValue() float64 {
	var m dto.Metric
	if err := QuotaLocalFallbackActive.Write(&m); err != nil {
		return -1
	}
	return m.GetGauge().GetValue()
}

// FileEventSubscriberRestartsValue reads the current value of
// FileEventSubscriberRestarts (see QuotaLocalFallbackActiveGaugeValue).
func FileEventSubscriberRestartsValue() float64 {
	var m dto.Metric
	if err := FileEventSubscriberRestarts.Write(&m); err != nil {
		return -1
	}
	return m.GetCounter().GetValue()
}

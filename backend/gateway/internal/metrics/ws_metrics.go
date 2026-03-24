package metrics

import "github.com/prometheus/client_golang/prometheus"
import "github.com/prometheus/client_golang/prometheus/promauto"

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

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

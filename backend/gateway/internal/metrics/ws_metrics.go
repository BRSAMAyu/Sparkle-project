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
)

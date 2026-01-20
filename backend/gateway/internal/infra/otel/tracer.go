package otel

import (
	"context"
	"log"
	"os"
	"strings"
	"sync"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.24.0"
)

var otelSchemeWarnOnce sync.Once
var otelDisabledOnce sync.Once

// InitTracer initializes the OpenTelemetry tracer provider
func InitTracer(serviceName string) func(context.Context) error {
	endpoint := strings.TrimSpace(os.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT"))
	if endpoint == "" {
		otelDisabledOnce.Do(func() {
			log.Printf("OTEL exporter disabled: OTEL_EXPORTER_OTLP_ENDPOINT not set")
		})
		return func(context.Context) error { return nil }
	}

	endpointURL := endpoint
	if !strings.Contains(endpointURL, "://") {
		otelSchemeWarnOnce.Do(func() {
			log.Printf("OTEL_EXPORTER_OTLP_ENDPOINT missing scheme, assuming http://%s", endpointURL)
		})
		endpointURL = "http://" + endpointURL
	}

	// Create OTLP HTTP exporter
	exporter, err := otlptracehttp.New(context.Background(),
		otlptracehttp.WithEndpointURL(endpointURL),
		otlptracehttp.WithInsecure(),
	)
	if err != nil {
		log.Printf("WARNING: Failed to create OTLP exporter: %v. Tracing might be disabled.", err)
		return func(context.Context) error { return nil }
	}

	// Create Resource
	res, err := resource.New(context.Background(),
		resource.WithAttributes(
			semconv.ServiceNameKey.String(serviceName),
		),
	)
	if err != nil {
		log.Fatalf("Failed to create resource: %v", err)
	}

	// Create Tracer Provider
	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exporter),
		sdktrace.WithResource(res),
	)

	// Set global provider
	otel.SetTracerProvider(tp)
	
	// Set global propagator to TraceContext (W3C)
	otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(propagation.TraceContext{}, propagation.Baggage{}))

	return tp.Shutdown
}

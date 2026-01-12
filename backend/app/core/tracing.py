from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
import os

# Configure Trace Provider
resource = Resource.create({
    "service.name": "sparkle-backend",
    "service.namespace": "sparkle",
    "deployment.environment": os.getenv("ENVIRONMENT", "development")
})

tracer_provider = TracerProvider(resource=resource)

# Configure OTLP Exporter (connects to Jaeger/Tempo via OTEL Collector)
otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)

tracer_provider.add_span_processor(
    BatchSpanProcessor(otlp_exporter)
)

# Set global Trace Provider
trace.set_tracer_provider(tracer_provider)

# Get a tracer for usage in application code
tracer = trace.get_tracer("sparkle.backend")

def get_tracer(name: str):
    """Helper to get a named tracer"""
    return trace.get_tracer(name)

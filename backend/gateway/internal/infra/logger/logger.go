package logger

import (
	"context"
	"os"
	"path/filepath"

	"go.opentelemetry.io/otel/trace"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
	"gopkg.in/lumberjack.v2"
)

var Log *zap.Logger

func Init(serviceName string) {
	// Rotating file writer: 200MB max, 3 backups, 30 day retention, compressed
	logDir := os.Getenv("LOG_DIR")
	if logDir == "" {
		logDir = "logs/local"
	}
	_ = os.MkdirAll(logDir, 0o755)

	fileWriter := &lumberjack.Logger{
		Filename:   filepath.Join(logDir, "gateway.log"),
		MaxSize:    200, // MB
		MaxBackups: 3,
		MaxAge:     30, // days
		Compress:   true,
	}

	// Also write to stdout for docker/podman logs
	stdoutWriter := zapcore.AddSync(os.Stdout)

	multiWriter := zapcore.NewMultiWriteSyncer(
		stdoutWriter,
		zapcore.AddSync(fileWriter),
	)

	encoderConfig := zap.NewProductionEncoderConfig()
	encoderConfig.EncodeTime = zapcore.ISO8601TimeEncoder

	core := zapcore.NewCore(
		zapcore.NewJSONEncoder(encoderConfig),
		multiWriter,
		zap.InfoLevel,
	)

	Log = zap.New(core,
		zap.AddCaller(),
		zap.Fields(zap.String("service", serviceName)),
	)
	zap.ReplaceGlobals(Log)
}

// ForCtx returns a logger with trace_id extracted from context
func ForCtx(ctx context.Context) *zap.Logger {
	span := trace.SpanFromContext(ctx)
	if !span.SpanContext().IsValid() {
		return Log
	}

	return Log.With(
		zap.String("trace_id", span.SpanContext().TraceID().String()),
		zap.String("span_id", span.SpanContext().SpanID().String()),
	)
}
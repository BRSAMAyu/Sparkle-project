package logger

import (
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

var Log *zap.Logger

func Init(serviceName string) {
	config := zap.NewProductionConfig()
	config.EncoderConfig.EncodeTime = zapcore.ISO8601TimeEncoder
	config.InitialFields = map[string]interface{}{
		"service": serviceName,
	}

	var err error
	Log, err = config.Build()
	if err != nil {
		panic(err)
	}
	zap.ReplaceGlobals(Log)
}
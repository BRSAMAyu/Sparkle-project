package handler

import (
	"os"
	"testing"

	"github.com/sparkle/gateway/internal/i18n"
)

func TestMain(m *testing.M) {
	localesPath := os.Getenv("LOCALES_PATH")
	if localesPath == "" {
		localesPath = "../../locales"
	}
	if err := i18n.Init(localesPath); err != nil {
		panic("Failed to init i18n for tests: " + err.Error())
	}
	os.Exit(m.Run())
}

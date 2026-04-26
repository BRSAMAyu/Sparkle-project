package i18n

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

type Bundle struct {
	messages map[string]map[string]interface{}
}

var globalBundle *Bundle

func Init(localesPath string) error {
	bundle := &Bundle{
		messages: make(map[string]map[string]interface{}),
	}

	files, err := os.ReadDir(localesPath)
	if err != nil {
		return err
	}

	for _, file := range files {
		if filepath.Ext(file.Name()) == ".json" {
			lang := strings.TrimSuffix(file.Name(), ".json")
			data, err := os.ReadFile(filepath.Join(localesPath, file.Name()))
			if err != nil {
				return err
			}

			var msgs map[string]interface{}
			if err := json.Unmarshal(data, &msgs); err != nil {
				return err
			}
			bundle.messages[lang] = msgs
		}
	}

	globalBundle = bundle
	return nil
}

type localeKey struct{}

func WithLocale(ctx context.Context, locale string) context.Context {
	return context.WithValue(ctx, localeKey{}, locale)
}

func GetLocale(ctx context.Context) string {
	if locale, ok := ctx.Value(localeKey{}).(string); ok {
		return locale
	}
	return "zh" // Default locale
}

func T(ctx context.Context, key string, args ...interface{}) string {
	locale := GetLocale(ctx)
	return translate(locale, key, args...)
}

func translate(locale, key string, args ...interface{}) string {
	if globalBundle == nil {
		return key
	}

	msgs, ok := globalBundle.messages[locale]
	if !ok {
		// Fallback to default language
		msgs = globalBundle.messages["zh"]
	}

	val := getNested(msgs, key)
	if val == "" {
		// Fallback to English if not found in zh
		if locale != "en" {
			msgs = globalBundle.messages["en"]
			val = getNested(msgs, key)
		}
	}

	if val == "" {
		return key
	}

	// Simple placeholder replacement
	result := val
	if len(args) > 0 {
		// If args is a map, treat as named placeholders
		if len(args) == 1 {
			if m, ok := args[0].(map[string]string); ok {
				for k, v := range m {
					result = strings.ReplaceAll(result, "{"+k+"}", v)
				}
				return result
			}
		}
		// Otherwise use fmt.Sprintf if it has standard placeholders (not implemented here for simplicity)
		// For our use case, named placeholders are enough
	}

	return result
}

func getNested(msgs map[string]interface{}, key string) string {
	parts := strings.Split(key, ".")
	var current interface{} = msgs

	for _, part := range parts {
		if m, ok := current.(map[string]interface{}); ok {
			current = m[part]
		} else {
			return ""
		}
	}

	if s, ok := current.(string); ok {
		return s
	}
	return ""
}

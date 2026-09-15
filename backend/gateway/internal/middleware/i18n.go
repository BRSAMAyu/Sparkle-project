package middleware

import (
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/sparkle/gateway/internal/i18n"
)

// I18n returns a middleware that sets the locale in the request context.
// It checks for the 'Accept-Language' header and a custom 'X-Language' header.
func I18n() gin.HandlerFunc {
	return func(c *gin.Context) {
		locale := "zh" // Default

		// Check X-Language header first
		if lang := c.GetHeader("X-Language"); lang != "" {
			locale = normalizeLocale(lang)
		} else if lang := c.GetHeader("Accept-Language"); lang != "" {
			// Very simple parsing of Accept-Language
			// e.g., "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7"
			parts := strings.Split(lang, ",")
			if len(parts) > 0 {
				mainPart := strings.Split(parts[0], ";")[0]
				locale = normalizeLocale(mainPart)
			}
		}

		// Set in Gin context
		c.Set("locale", locale)

		// Also set in Go context for downstream services
		ctx := i18n.WithLocale(c.Request.Context(), locale)
		c.Request = c.Request.WithContext(ctx)

		c.Next()
	}
}

func normalizeLocale(lang string) string {
	lang = strings.ToLower(strings.TrimSpace(lang))
	if strings.HasPrefix(lang, "zh") {
		return "zh"
	}
	if strings.HasPrefix(lang, "en") {
		return "en"
	}
	return "zh" // Default fallback
}

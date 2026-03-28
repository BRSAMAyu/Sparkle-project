package middleware

import (
	"log"
	"net"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/sparkle/gateway/internal/config"
)

// InternalIPWhitelistMiddleware restricts /internal endpoints to trusted IPs/CIDRs.
func InternalIPWhitelistMiddleware(cfg *config.Config) gin.HandlerFunc {
	allowedNets := parseInternalWhitelist(cfg.InternalIPWhitelist)
	return func(c *gin.Context) {
		if cfg.IsDevelopment() || len(allowedNets) == 0 {
			c.Next()
			return
		}

		clientIP := net.ParseIP(strings.TrimSpace(c.ClientIP()))
		if clientIP == nil {
			c.AbortWithStatusJSON(http.StatusForbidden, gin.H{"error": "unable to determine client ip"})
			return
		}

		for _, network := range allowedNets {
			if network.Contains(clientIP) {
				c.Next()
				return
			}
		}

		log.Printf("[SECURITY] Rejected internal request from non-whitelisted IP: %s", clientIP.String())
		c.AbortWithStatusJSON(http.StatusForbidden, gin.H{"error": "client ip is not allowed"})
	}
}

func parseInternalWhitelist(entries []string) []*net.IPNet {
	networks := make([]*net.IPNet, 0, len(entries))
	for _, entry := range entries {
		entry = strings.TrimSpace(entry)
		if entry == "" {
			continue
		}

		if strings.Contains(entry, "/") {
			_, network, err := net.ParseCIDR(entry)
			if err != nil {
				log.Printf("Ignoring invalid INTERNAL_IP_WHITELIST CIDR %q: %v", entry, err)
				continue
			}
			networks = append(networks, network)
			continue
		}

		ip := net.ParseIP(entry)
		if ip == nil {
			log.Printf("Ignoring invalid INTERNAL_IP_WHITELIST IP %q", entry)
			continue
		}

		maskBits := 32
		if ip.To4() == nil {
			maskBits = 128
		}
		networks = append(networks, &net.IPNet{IP: ip, Mask: net.CIDRMask(maskBits, maskBits)})
	}
	return networks
}

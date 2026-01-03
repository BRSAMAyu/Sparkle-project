package service

import (
	"fmt"
	"time"

	"github.com/MicahParks/keyfunc/v3"
	"github.com/golang-jwt/jwt/v5"
	"github.com/sparkle/gateway/internal/config"
)

type AppleAuthService struct {
	cfg     *config.Config
	keyfunc keyfunc.Keyfunc
}

func NewAppleAuthService(cfg *config.Config) (*AppleAuthService, error) {
	// Initialize keyfunc with Apple's JWKS endpoint
	// It handles caching and background refreshing
	kf, err := keyfunc.NewDefault([]string{"https://appleid.apple.com/auth/keys"})
	if err != nil {
		return nil, fmt.Errorf("failed to create keyfunc: %v", err)
	}

	return &AppleAuthService{
		cfg:     cfg,
		keyfunc: kf,
	}, nil
}

type AppleClaims struct {
	Email         string `json:"email"`
	EmailVerified string `json:"email_verified"`
	Name          string `json:"name"`
	jwt.RegisteredClaims
}

func (s *AppleAuthService) VerifyToken(tokenStr string) (*AppleClaims, error) {
	token, err := jwt.ParseWithClaims(tokenStr, &AppleClaims{}, s.keyfunc.Keyfunc)
	if err != nil {
		return nil, fmt.Errorf("failed to parse/verify apple token: %v", err)
	}

	claims, ok := token.Claims.(*AppleClaims)
	if !ok || !token.Valid {
		return nil, fmt.Errorf("invalid apple token claims")
	}

	// Verify Issuer
	if claims.Issuer != "https://appleid.apple.com" {
		return nil, fmt.Errorf("invalid apple token issuer: %s", claims.Issuer)
	}

	// Verify Audience
	if s.cfg.AppleClientID != "" {
		found := false
		for _, aud := range claims.Audience {
			if aud == s.cfg.AppleClientID {
				found = true
				break
			}
		}
		if !found {
			return nil, fmt.Errorf("invalid apple token audience")
		}
	}

	// Verify Expiration
	if claims.ExpiresAt != nil && claims.ExpiresAt.Before(time.Now()) {
		return nil, fmt.Errorf("apple token expired")
	}

	return claims, nil
}
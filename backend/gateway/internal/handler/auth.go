package handler

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"log"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
	"github.com/sparkle/gateway/internal/config"
	"github.com/sparkle/gateway/internal/i18n"
	"github.com/sparkle/gateway/internal/service"
)

type AuthHandler struct {
	cfg                 *config.Config
	appleTokenVerifier  appleTokenVerifier
	appleAccountService appleAccountService
}

type appleTokenVerifier interface {
	VerifyToken(tokenStr string) (*service.AppleClaims, error)
}

type appleAccountService interface {
	FindOrCreateUser(ctx context.Context, claims *service.AppleClaims) (service.AppleAuthenticatedUser, error)
	UpdateLastLogin(ctx context.Context, userID pgtype.UUID) error
	UpsertUserSession(ctx context.Context, userID pgtype.UUID, sessionID string, metadata service.AppleSessionMetadata) error
}

func NewAuthHandler(cfg *config.Config, appleTokenVerifier appleTokenVerifier, appleAccountService appleAccountService) *AuthHandler {
	return &AuthHandler{
		cfg:                 cfg,
		appleTokenVerifier:  appleTokenVerifier,
		appleAccountService: appleAccountService,
	}
}

type SocialLoginRequest struct {
	Provider       string `json:"provider" binding:"required"`
	Token          string `json:"token" binding:"required"`
	AcceptedTOS    bool   `json:"accepted_tos"`
	AcceptedPrivacy bool  `json:"accepted_privacy"`
}

func (h *AuthHandler) AppleLogin(c *gin.Context) {
	var req SocialLoginRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		sanitizeErrorResponse(c, http.StatusBadRequest, err, "auth.apple_login.bind")
		return
	}

	if req.Provider != "apple" {
		c.JSON(http.StatusBadRequest, gin.H{"error": i18n.T(c.Request.Context(), "auth.unsupported_provider")})
		return
	}

	if !req.AcceptedTOS || !req.AcceptedPrivacy {
		c.JSON(http.StatusBadRequest, gin.H{"error": i18n.T(c.Request.Context(), "auth.terms_not_accepted")})
		return
	}

	// 1. Verify Apple Token
	claims, err := h.appleTokenVerifier.VerifyToken(req.Token)
	if err != nil {
		sanitizeErrorResponse(c, http.StatusUnauthorized, err, "auth.apple_login.verify_token")
		return
	}

	// 2. Find or Create User
	ctx := c.Request.Context()
	user, err := h.appleAccountService.FindOrCreateUser(ctx, claims)
	if err != nil {
		if errors.Is(err, service.ErrAppleUserLinkFailed) {
			c.JSON(http.StatusInternalServerError, gin.H{"error": i18n.T(c.Request.Context(), "auth.link_apple_failed")})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": i18n.T(c.Request.Context(), "auth.create_user_failed")})
		return
	}

	// Update last login
	if err := h.appleAccountService.UpdateLastLogin(ctx, user.ID); err != nil {
		log.Printf("[WARN] UpdateUserLastLogin failed for user %s: %v", h.uuidToString(user.ID), err)
	}

	// 3. Issue System Token
	sessionID := uuid.New().String()
	accessToken, err := h.createAccessToken(user.ID, sessionID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": i18n.T(c.Request.Context(), "auth.create_token_failed")})
		return
	}
	refreshToken, refreshJTI, err := h.createRefreshToken(user.ID, sessionID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": i18n.T(c.Request.Context(), "auth.create_refresh_token_failed")})
		return
	}

	// 4. Persist session to user_sessions table
	err = h.appleAccountService.UpsertUserSession(ctx, user.ID, sessionID, service.AppleSessionMetadata{
		DeviceID:        c.GetHeader("X-Device-ID"),
		DeviceName:      c.GetHeader("X-Device-Name"),
		DeviceType:      c.GetHeader("X-Device-Platform"),
		IPAddress:       c.ClientIP(),
		UserAgent:       c.GetHeader("User-Agent"),
		RefreshTokenJTI: refreshJTI,
	})
	if err != nil {
		// Session persistence failure should not block login
		// but log the error for investigation
		log.Printf("[WARN] UpsertUserSession failed for user %s: %v", h.uuidToString(user.ID), err)
	}

	c.JSON(http.StatusOK, gin.H{
		"access_token":  accessToken,
		"refresh_token": refreshToken,
		"token_type":    "bearer",
		"token": gin.H{
			"access_token":  accessToken,
			"refresh_token": refreshToken,
			"token_type":    "bearer",
		},
		"user": gin.H{
			"id":       h.uuidToString(user.ID),
			"username": user.Username,
			"email":    user.Email,
			"nickname": user.Nickname.String,
		},
	})
}

func (h *AuthHandler) randomString(n int) string {
	b := make([]byte, n/2)
	if _, err := rand.Read(b); err != nil {
		panic("crypto/rand.Read failed: " + err.Error())
	}
	return hex.EncodeToString(b)
}

func (h *AuthHandler) createAccessToken(userID pgtype.UUID, sessionID string) (string, error) {
	now := time.Now()

	// Get expiration time from config, default to 30 minutes
	expireMinutes := h.cfg.JWTAccessTokenExpireMinutes
	if expireMinutes <= 0 {
		expireMinutes = 30
	}

	claims := jwt.MapClaims{
		"sub":  h.uuidToString(userID),
		"sid":  sessionID,
		"exp":  now.Add(time.Duration(expireMinutes) * time.Minute).Unix(),
		"iat":  now.Unix(),
		"jti":  uuid.New().String(),
		"type": "access",
	}
	if h.cfg.JWTIssuer != "" {
		claims["iss"] = h.cfg.JWTIssuer
	}
	if h.cfg.JWTAudience != "" {
		claims["aud"] = h.cfg.JWTAudience
	}

	var signingMethod jwt.SigningMethod = jwt.SigningMethodHS256
	var signingKey interface{} = []byte(h.cfg.JWTSecret)
	if h.cfg.JWTAlgorithm == "RS256" {
		var err error
		signingKey, err = h.cfg.ParseJWTPrivateKey()
		if err != nil {
			return "", err
		}
		signingMethod = jwt.SigningMethodRS256
	}
	token := jwt.NewWithClaims(signingMethod, claims)
	return token.SignedString(signingKey)
}

func (h *AuthHandler) createRefreshToken(userID pgtype.UUID, sessionID string) (string, string, error) {
	now := time.Now()

	// Get expiration time from config, default to 7 days
	expireDays := h.cfg.JWTRefreshTokenExpireDays
	if expireDays <= 0 {
		expireDays = 7
	}

	jti := uuid.New().String()
	claims := jwt.MapClaims{
		"sub":  h.uuidToString(userID),
		"sid":  sessionID,
		"exp":  now.Add(time.Duration(expireDays) * 24 * time.Hour).Unix(),
		"iat":  now.Unix(),
		"jti":  jti,
		"type": "refresh",
	}
	if h.cfg.JWTIssuer != "" {
		claims["iss"] = h.cfg.JWTIssuer
	}
	if h.cfg.JWTAudience != "" {
		claims["aud"] = h.cfg.JWTAudience
	}

	var signingMethod jwt.SigningMethod = jwt.SigningMethodHS256
	var signingKey interface{} = []byte(h.cfg.JWTSecret)
	if h.cfg.JWTAlgorithm == "RS256" {
		var err error
		signingKey, err = h.cfg.ParseJWTPrivateKey()
		if err != nil {
			return "", "", err
		}
		signingMethod = jwt.SigningMethodRS256
	}
	token := jwt.NewWithClaims(signingMethod, claims)
	signed, err := token.SignedString(signingKey)
	if err != nil {
		return "", "", err
	}
	return signed, jti, nil
}

func (h *AuthHandler) uuidToString(id pgtype.UUID) string {
	u, _ := uuid.FromBytes(id.Bytes[:])
	return u.String()
}

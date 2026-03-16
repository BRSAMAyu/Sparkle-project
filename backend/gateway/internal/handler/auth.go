package handler

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgtype"
	"github.com/sparkle/gateway/internal/config"
	"github.com/sparkle/gateway/internal/db"
	"github.com/sparkle/gateway/internal/service"
)

type AuthHandler struct {
	cfg              *config.Config
	queries          *db.Queries
	appleAuthService *service.AppleAuthService
}

func NewAuthHandler(cfg *config.Config, queries *db.Queries, appleAuthService *service.AppleAuthService) *AuthHandler {
	return &AuthHandler{
		cfg:              cfg,
		queries:          queries,
		appleAuthService: appleAuthService,
	}
}

type SocialLoginRequest struct {
	Provider string `json:"provider" binding:"required"`
	Token    string `json:"token" binding:"required"`
}

func (h *AuthHandler) AppleLogin(c *gin.Context) {
	var req SocialLoginRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if req.Provider != "apple" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "不支持的身份提供商"})
		return
	}

	// 1. Verify Apple Token
	claims, err := h.appleAuthService.VerifyToken(req.Token)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": fmt.Sprintf("Apple验证失败：%v", err)})
		return
	}

	// 2. Find or Create User
	ctx := c.Request.Context()
	userNeedsLink := false
	// Priority 1: Check by apple_id (sub)
	user, err := h.queries.GetUserByAppleID(ctx, pgtype.Text{String: claims.Subject, Valid: true})
	if err != nil {
		// Priority 2: Check by email if provided
		if claims.Email != "" {
			user, err = h.queries.GetUserByEmail(ctx, claims.Email)
			if err == nil {
				userNeedsLink = true
			}
		}

		// If still not found, create new user
		if err != nil {
			username := fmt.Sprintf("apple_%s", h.randomString(8))
			email := claims.Email
			if email == "" {
				email = fmt.Sprintf("%s@apple-user.com", username)
			}

			newID := uuid.New()
			var pgID pgtype.UUID
			copy(pgID.Bytes[:], newID[:])
			pgID.Valid = true

			user, err = h.queries.CreateSocialUser(ctx, db.CreateSocialUserParams{
				ID:                 pgID,
				Username:           username,
				Email:              email,
				HashedPassword:     h.randomString(32),
				Nickname:           pgtype.Text{String: claims.Name, Valid: claims.Name != ""},
				RegistrationSource: "apple",
				IsActive:           true,
				AppleID:            pgtype.Text{String: claims.Subject, Valid: true},
			})
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "创建用户失败"})
				return
			}
		}
	}

	if err == nil && (userNeedsLink || !user.AppleID.Valid) {
		user, err = h.queries.LinkAppleUser(ctx, db.LinkAppleUserParams{
			ID:      user.ID,
			AppleID: pgtype.Text{String: claims.Subject, Valid: true},
		})
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "更新苹果登录信息失败"})
			return
		}
	}

	// Update last login
	_ = h.queries.UpdateUserLastLogin(ctx, user.ID)

	// 3. Issue System Token
	sessionID := uuid.New().String()
	accessToken, err := h.createAccessToken(user.ID, sessionID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "签发令牌失败"})
		return
	}
	refreshToken, err := h.createRefreshToken(user.ID, sessionID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "签发刷新令牌失败"})
		return
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
	rand.Read(b)
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

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString([]byte(h.cfg.JWTSecret))
}

func (h *AuthHandler) createRefreshToken(userID pgtype.UUID, sessionID string) (string, error) {
	now := time.Now()

	// Get expiration time from config, default to 7 days
	expireDays := h.cfg.JWTRefreshTokenExpireDays
	if expireDays <= 0 {
		expireDays = 7
	}

	claims := jwt.MapClaims{
		"sub":  h.uuidToString(userID),
		"sid":  sessionID,
		"exp":  now.Add(time.Duration(expireDays) * 24 * time.Hour).Unix(),
		"iat":  now.Unix(),
		"jti":  uuid.New().String(),
		"type": "refresh",
	}
	if h.cfg.JWTIssuer != "" {
		claims["iss"] = h.cfg.JWTIssuer
	}
	if h.cfg.JWTAudience != "" {
		claims["aud"] = h.cfg.JWTAudience
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString([]byte(h.cfg.JWTSecret))
}

func (h *AuthHandler) uuidToString(id pgtype.UUID) string {
	u, _ := uuid.FromBytes(id.Bytes[:])
	return u.String()
}

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
		c.JSON(http.StatusBadRequest, gin.H{"error": "Unsupported provider"})
		return
	}

	// 1. Verify Apple Token
	claims, err := h.appleAuthService.VerifyToken(req.Token)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": fmt.Sprintf("Apple verification failed: %v", err)})
		return
	}

	// 2. Find or Create User
	ctx := c.Request.Context()
	// Priority 1: Check by apple_id (sub)
	user, err := h.queries.GetUserByAppleID(ctx, pgtype.Text{String: claims.Subject, Valid: true})
	if err != nil {
		// Priority 2: Check by email if provided
		if claims.Email != "" {
			user, err = h.queries.GetUserByEmail(ctx, claims.Email)
			if err == nil {
				// User exists by email
				// Link apple_id? (Would need an update query, but for now we just use this user)
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
				c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create user"})
				return
			}
		}
	}

	// Update last login
	_ = h.queries.UpdateUserLastLogin(ctx, user.ID)

	// 3. Issue System Token
	accessToken, err := h.createAccessToken(user.ID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to issue token"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"access_token": accessToken,
		"token_type":   "bearer",
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

func (h *AuthHandler) createAccessToken(userID pgtype.UUID) (string, error) {
	claims := jwt.MapClaims{
		"sub": h.uuidToString(userID),
		"exp": time.Now().Add(time.Hour * 24).Unix(),
		"iat": time.Now().Unix(),
		"type": "access",
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString([]byte(h.cfg.JWTSecret))
}

func (h *AuthHandler) uuidToString(id pgtype.UUID) string {
	u, _ := uuid.FromBytes(id.Bytes[:])
	return u.String()
}
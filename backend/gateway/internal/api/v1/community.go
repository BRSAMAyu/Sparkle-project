package v1

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/sparkle/gateway/internal/service"
)

type CommunityHandler struct {
	commandService *service.CommunityCommandService
	queryService   *service.CommunityQueryService
}

func NewCommunityHandler(cmd *service.CommunityCommandService, qry *service.CommunityQueryService) *CommunityHandler {
	return &CommunityHandler{
		commandService: cmd,
		queryService:   qry,
	}
}

func (h *CommunityHandler) RegisterRoutes(router *gin.RouterGroup) {
	group := router.Group("/community")
	{
		group.POST("/posts", h.CreatePost)
		group.GET("/feed", h.GetFeed)
		group.POST("/posts/:id/like", h.LikePost)
	}
}

type CreatePostInput struct {
	Content   string   `json:"content" binding:"required"`
	ImageURLs []string `json:"image_urls"`
	Topic     string   `json:"topic"`
}

func (h *CommunityHandler) CreatePost(c *gin.Context) {
	// Extract authenticated user_id from context (set by AuthMiddleware)
	userIDStr, exists := c.Get("user_id")
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Missing user ID in context"})
		return
	}

	userID, err := uuid.Parse(userIDStr.(string))
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid user ID in context"})
		return
	}

	var input CreatePostInput
	if err := c.ShouldBindJSON(&input); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	post, err := h.commandService.CreatePost(c.Request.Context(), service.CreatePostRequest{
		UserID:    userID,
		Content:   input.Content,
		ImageURLs: input.ImageURLs,
		Topic:     input.Topic,
	})
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	postID, _ := uuid.FromBytes(post.ID.Bytes[:])

	c.JSON(http.StatusCreated, gin.H{
		"id":      postID.String(),
		"message": "Post created",
	})
}

func (h *CommunityHandler) GetFeed(c *gin.Context) {
	page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "20"))

	posts, err := h.queryService.GetGlobalFeed(c.Request.Context(), page, limit)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, posts)
}

func (h *CommunityHandler) LikePost(c *gin.Context) {
	// Extract authenticated user_id from context (set by AuthMiddleware)
	userIDStr, exists := c.Get("user_id")
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Missing user ID in context"})
		return
	}

	userID, err := uuid.Parse(userIDStr.(string))
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid user ID in context"})
		return
	}

	idStr := c.Param("id")
	postID, err := uuid.Parse(idStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid post ID"})
		return
	}

	err = h.commandService.LikePost(c.Request.Context(), userID, postID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": "liked"})
}

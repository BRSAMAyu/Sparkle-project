package handler

import (
    "net/http"
    "strconv"

    "github.com/gin-gonic/gin"
    errorbookv1 "github.com/sparkle/gateway/gen/proto/error_book"
    "github.com/sparkle/gateway/internal/error_book"
)

type ErrorBookHandler struct {
    client *error_book.Client
}

func NewErrorBookHandler(client *error_book.Client) *ErrorBookHandler {
    return &ErrorBookHandler{client: client}
}

func (h *ErrorBookHandler) RegisterRoutes(r *gin.RouterGroup) {
    errors := r.Group("/errors")
    {
        errors.POST("", h.CreateError)
        errors.GET("", h.ListErrors)
        errors.GET("/stats", h.GetStats)
        errors.GET("/today-review", h.GetTodayReviews)
        errors.GET("/:id", h.GetError)
        errors.PATCH("/:id", h.UpdateError)
        errors.DELETE("/:id", h.DeleteError)
        errors.POST("/:id/analyze", h.AnalyzeError)
        errors.POST("/:id/review", h.SubmitReview)
    }
}

func (h *ErrorBookHandler) CreateError(c *gin.Context) {
    var req errorbookv1.CreateErrorRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
        return
    }
    
    // Inject User ID from context
    userID := c.GetString("userID")
    req.UserId = userID
    
    resp, err := h.client.CreateError(c.Request.Context(), &req)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }
    
    c.JSON(http.StatusCreated, resp)
}

func (h *ErrorBookHandler) ListErrors(c *gin.Context) {
    userID := c.GetString("userID")
    
    page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
    pageSize, _ := strconv.Atoi(c.DefaultQuery("page_size", "20"))
    
    req := &errorbookv1.ListErrorsRequest{
        UserId:      userID,
        SubjectCode: c.Query("subject_code"),
        Chapter:     c.Query("chapter"),
        ErrorType:   c.Query("error_type"),
        Keyword:     c.Query("keyword"),
        Page:        int32(page),
        PageSize:    int32(pageSize),
    }
    
    if val := c.Query("mastery_min"); val != "" {
        f, _ := strconv.ParseFloat(val, 64)
        req.MasteryMin = &f
    }
    if val := c.Query("mastery_max"); val != "" {
        f, _ := strconv.ParseFloat(val, 64)
        req.MasteryMax = &f
    }
    if val := c.Query("need_review"); val != "" {
        b, _ := strconv.ParseBool(val)
        req.NeedReview = &b
    }
    
    resp, err := h.client.ListErrors(c.Request.Context(), req)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }
    
    c.JSON(http.StatusOK, resp)
}

func (h *ErrorBookHandler) GetError(c *gin.Context) {
    userID := c.GetString("userID")
    errorID := c.Param("id")
    
    req := &errorbookv1.GetErrorRequest{
        ErrorId: errorID,
        UserId:  userID,
    }
    
    resp, err := h.client.GetError(c.Request.Context(), req)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }
    
    c.JSON(http.StatusOK, resp)
}

func (h *ErrorBookHandler) UpdateError(c *gin.Context) {
    userID := c.GetString("userID")
    errorID := c.Param("id")
    
    var req errorbookv1.UpdateErrorRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
        return
    }
    
    req.UserId = userID
    req.ErrorId = errorID
    
    resp, err := h.client.UpdateError(c.Request.Context(), &req)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }
    
    c.JSON(http.StatusOK, resp)
}

func (h *ErrorBookHandler) DeleteError(c *gin.Context) {
    userID := c.GetString("userID")
    errorID := c.Param("id")
    
    req := &errorbookv1.DeleteErrorRequest{
        ErrorId: errorID,
        UserId:  userID,
    }
    
    _, err := h.client.DeleteError(c.Request.Context(), req)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }
    
    c.Status(http.StatusNoContent)
}

func (h *ErrorBookHandler) AnalyzeError(c *gin.Context) {
    userID := c.GetString("userID")
    errorID := c.Param("id")
    
    req := &errorbookv1.AnalyzeErrorRequest{
        ErrorId: errorID,
        UserId:  userID,
    }
    
    resp, err := h.client.AnalyzeError(c.Request.Context(), req)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }
    
    c.JSON(http.StatusOK, resp)
}

func (h *ErrorBookHandler) SubmitReview(c *gin.Context) {
    userID := c.GetString("userID")
    errorID := c.Param("id")
    
    var req errorbookv1.SubmitReviewRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
        return
    }
    
    req.UserId = userID
    req.ErrorId = errorID
    
    resp, err := h.client.SubmitReview(c.Request.Context(), &req)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }
    
    c.JSON(http.StatusOK, resp)
}

func (h *ErrorBookHandler) GetStats(c *gin.Context) {
    userID := c.GetString("userID")
    
    req := &errorbookv1.GetReviewStatsRequest{
        UserId: userID,
    }
    
    resp, err := h.client.GetReviewStats(c.Request.Context(), req)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }
    
    c.JSON(http.StatusOK, resp)
}

func (h *ErrorBookHandler) GetTodayReviews(c *gin.Context) {
    userID := c.GetString("userID")
    
    page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
    pageSize, _ := strconv.Atoi(c.DefaultQuery("page_size", "20"))
    
    req := &errorbookv1.GetTodayReviewsRequest{
        UserId:   userID,
        Page:     int32(page),
        PageSize: int32(pageSize),
    }
    
    resp, err := h.client.GetTodayReviews(c.Request.Context(), req)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }
    
    c.JSON(http.StatusOK, resp)
}

package handler

import (
	"encoding/json"
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	errorbookv1 "github.com/sparkle/gateway/gen/proto/error_book"
	"github.com/sparkle/gateway/internal/error_book"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/metadata"
	grpcstatus "google.golang.org/grpc/status"
	"google.golang.org/protobuf/encoding/protojson"
	"google.golang.org/protobuf/proto"
)

type ErrorBookHandler struct {
	client *error_book.Client
}

func NewErrorBookHandler(client *error_book.Client) *ErrorBookHandler {
	return &ErrorBookHandler{client: client}
}

func injectAuthContext(c *gin.Context) {
	token := c.GetString("auth_token")
	if token == "" {
		return
	}
	ctx := metadata.NewOutgoingContext(c.Request.Context(), metadata.Pairs("authorization", "Bearer "+token))
	c.Request = c.Request.WithContext(ctx)
}

func writeProtoJSON(c *gin.Context, statusCode int, message proto.Message) {
	marshaler := protojson.MarshalOptions{
		UseProtoNames:   true,
		EmitUnpopulated: true,
	}
	payload, err := marshaler.Marshal(message)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.Data(statusCode, "application/json; charset=utf-8", payload)
}

func writeGRPCError(c *gin.Context, err error) {
	status, ok := grpcstatus.FromError(err)
	if !ok {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	httpStatus := http.StatusInternalServerError
	switch status.Code() {
	case codes.InvalidArgument:
		httpStatus = http.StatusBadRequest
	case codes.NotFound:
		httpStatus = http.StatusNotFound
	case codes.Unauthenticated:
		httpStatus = http.StatusUnauthorized
	case codes.PermissionDenied:
		httpStatus = http.StatusForbidden
	}

	c.JSON(httpStatus, gin.H{"error": status.Message()})
}

func (h *ErrorBookHandler) RegisterRoutes(r *gin.RouterGroup, authMiddleware gin.HandlerFunc) {
	errors := r.Group("/errors", authMiddleware)
	{
		errors.POST("", h.CreateError)
		errors.GET("", h.ListErrors)
		errors.GET("/stats", h.GetStats)
		errors.GET("/today-review", h.GetTodayReviews)
		errors.GET("/:id/semantic", h.GetSemanticSummary)
		errors.GET("/:id", h.GetError)
		errors.PATCH("/:id", h.UpdateError)
		errors.DELETE("/:id", h.DeleteError)
		errors.POST("/:id/analyze", h.AnalyzeError)
		errors.POST("/:id/review", h.SubmitReview)
	}
}

func (h *ErrorBookHandler) CreateError(c *gin.Context) {
	injectAuthContext(c)
	var raw map[string]interface{}
	if err := c.ShouldBindJSON(&raw); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if _, ok := raw["subject_code"]; !ok {
		if subject, ok := raw["subject"]; ok {
			raw["subject_code"] = subject
		}
	}
	delete(raw, "subject")

	payload, err := json.Marshal(raw)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	var req errorbookv1.CreateErrorRequest
	if err := json.Unmarshal(payload, &req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Inject User ID from context
	userID := c.GetString("user_id")
	req.UserId = userID

	resp, err := h.client.CreateError(c.Request.Context(), &req)
	if err != nil {
		writeGRPCError(c, err)
		return
	}

	writeProtoJSON(c, http.StatusCreated, resp)
}

func (h *ErrorBookHandler) ListErrors(c *gin.Context) {
	injectAuthContext(c)
	userID := c.GetString("user_id")

	page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
	pageSize, _ := strconv.Atoi(c.DefaultQuery("page_size", "20"))

	subjectCode := c.Query("subject_code")
	if subjectCode == "" {
		subjectCode = c.Query("subject")
	}

	req := &errorbookv1.ListErrorsRequest{
		UserId:             userID,
		SubjectCode:        subjectCode,
		Chapter:            c.Query("chapter"),
		ErrorType:          c.Query("error_type"),
		Keyword:            c.Query("keyword"),
		Page:               int32(page),
		PageSize:           int32(pageSize),
		CognitiveDimension: c.Query("cognitive_dimension"),
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
		writeGRPCError(c, err)
		return
	}

	writeProtoJSON(c, http.StatusOK, resp)
}

func (h *ErrorBookHandler) GetError(c *gin.Context) {
	injectAuthContext(c)
	userID := c.GetString("user_id")
	errorID := c.Param("id")

	req := &errorbookv1.GetErrorRequest{
		ErrorId: errorID,
		UserId:  userID,
	}

	resp, err := h.client.GetError(c.Request.Context(), req)
	if err != nil {
		writeGRPCError(c, err)
		return
	}

	writeProtoJSON(c, http.StatusOK, resp)
}

func (h *ErrorBookHandler) GetSemanticSummary(c *gin.Context) {
	injectAuthContext(c)
	userID := c.GetString("user_id")
	errorID := c.Param("id")

	req := &errorbookv1.GetErrorRequest{
		ErrorId: errorID,
		UserId:  userID,
	}

	resp, err := h.client.GetErrorSemanticSummary(c.Request.Context(), req)
	if err != nil {
		writeGRPCError(c, err)
		return
	}

	writeProtoJSON(c, http.StatusOK, resp)
}

func (h *ErrorBookHandler) UpdateError(c *gin.Context) {
	injectAuthContext(c)
	userID := c.GetString("user_id")
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
		writeGRPCError(c, err)
		return
	}

	writeProtoJSON(c, http.StatusOK, resp)
}

func (h *ErrorBookHandler) DeleteError(c *gin.Context) {
	injectAuthContext(c)
	userID := c.GetString("user_id")
	errorID := c.Param("id")

	req := &errorbookv1.DeleteErrorRequest{
		ErrorId: errorID,
		UserId:  userID,
	}

	_, err := h.client.DeleteError(c.Request.Context(), req)
	if err != nil {
		writeGRPCError(c, err)
		return
	}

	c.Status(http.StatusNoContent)
}

func (h *ErrorBookHandler) AnalyzeError(c *gin.Context) {
	injectAuthContext(c)
	userID := c.GetString("user_id")
	errorID := c.Param("id")

	req := &errorbookv1.AnalyzeErrorRequest{
		ErrorId: errorID,
		UserId:  userID,
	}

	resp, err := h.client.AnalyzeError(c.Request.Context(), req)
	if err != nil {
		writeGRPCError(c, err)
		return
	}

	writeProtoJSON(c, http.StatusOK, resp)
}

func (h *ErrorBookHandler) SubmitReview(c *gin.Context) {
	injectAuthContext(c)
	userID := c.GetString("user_id")
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
		writeGRPCError(c, err)
		return
	}

	writeProtoJSON(c, http.StatusOK, resp)
}

func (h *ErrorBookHandler) GetStats(c *gin.Context) {
	injectAuthContext(c)
	userID := c.GetString("user_id")

	req := &errorbookv1.GetReviewStatsRequest{
		UserId: userID,
	}

	resp, err := h.client.GetReviewStats(c.Request.Context(), req)
	if err != nil {
		writeGRPCError(c, err)
		return
	}

	writeProtoJSON(c, http.StatusOK, resp)
}

func (h *ErrorBookHandler) GetTodayReviews(c *gin.Context) {
	injectAuthContext(c)
	userID := c.GetString("user_id")

	page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
	pageSize, _ := strconv.Atoi(c.DefaultQuery("page_size", "20"))

	req := &errorbookv1.GetTodayReviewsRequest{
		UserId:   userID,
		Page:     int32(page),
		PageSize: int32(pageSize),
	}

	resp, err := h.client.GetTodayReviews(c.Request.Context(), req)
	if err != nil {
		writeGRPCError(c, err)
		return
	}

	writeProtoJSON(c, http.StatusOK, resp)
}

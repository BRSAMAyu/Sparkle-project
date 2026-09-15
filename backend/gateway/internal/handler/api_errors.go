package handler

import (
	"errors"
	"net/http"
	"strconv"
	"strings"

	"github.com/gin-gonic/gin"
)

// APIErrorResponse is the standard REST error envelope.
type APIErrorResponse struct {
	Error     string `json:"error"`
	ErrorCode string `json:"error_code,omitempty"`
	RequestID string `json:"request_id,omitempty"`
}

// RespondError writes a sanitized, standard REST error response.
func RespondError(c *gin.Context, status int, code string, message string) {
	if code == "" {
		code = errorCode(status)
	}

	var err error
	message = strings.TrimSpace(message)
	if message != "" {
		err = errors.New(message)
	}

	ctx := c.Request.Context()
	clientMessage := safeErrorMessage(ctx, status, err)
	if err != nil {
		recordSanitizedError(ctx, strconv.Itoa(status), handlerLabel(c, message), errorCategory(status), err, message, requestIDFromGin(c))
	}

	if clientMessage == "" {
		clientMessage = http.StatusText(status)
	}

	response := APIErrorResponse{
		Error:     clientMessage,
		ErrorCode: code,
		RequestID: requestIDFromGin(c),
	}
	c.JSON(status, response)
}

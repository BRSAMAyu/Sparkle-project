package handler

import (
	"encoding/json"
	"testing"

	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	"github.com/stretchr/testify/assert"
)

func TestChatInputUnmarshalWithFiles(t *testing.T) {
	payload := []byte(`{
		"message": "hi",
		"session_id": "s1",
		"file_ids": ["f1", "f2"],
		"include_references": true
	}`)

	var input chatInput
	err := json.Unmarshal(payload, &input)
	assert.NoError(t, err)
	assert.Equal(t, "hi", input.Message)
	assert.Equal(t, "s1", input.SessionID)
	assert.Equal(t, []string{"f1", "f2"}, input.FileIds)
	assert.True(t, input.IncludeReferences)
}

func TestConvertResponseToJSONCitations(t *testing.T) {
	resp := &agentv1.ChatResponse{
		ResponseId: "resp-1",
		RequestId:  "req-1",
		Content: &agentv1.ChatResponse_Citations{
			Citations: &agentv1.CitationBlock{
				Citations: []*agentv1.Citation{
					{
						Id:           "c1",
						Title:        "Doc A",
						Content:      "snippet",
						SourceType:   "document",
						Score:        0.9,
						FileId:       "file-123",
						PageNumber:   2,
						ChunkIndex:   5,
						SectionTitle: "Intro",
					},
				},
			},
		},
	}

	result := convertResponseToJSON(resp)
	citationsAny, ok := result["citations"].([]map[string]interface{})
	assert.True(t, ok)
	assert.Len(t, citationsAny, 1)
	assert.Equal(t, "file-123", citationsAny[0]["file_id"])
	assert.Equal(t, float32(0.9), citationsAny[0]["score"])
	assert.Equal(t, int32(2), citationsAny[0]["page_number"])
	assert.Equal(t, int32(5), citationsAny[0]["chunk_index"])
	assert.Equal(t, "Intro", citationsAny[0]["section_title"])
}

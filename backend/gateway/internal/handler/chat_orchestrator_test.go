package handler

import (
	"encoding/json"
	"testing"

	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	"github.com/stretchr/testify/assert"
	"google.golang.org/protobuf/types/known/structpb"
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

func TestConvertResponseToJSONIntervention(t *testing.T) {
	content, err := structpb.NewStruct(map[string]interface{}{
		"title": "Morning Review",
	})
	assert.NoError(t, err)

	resp := &agentv1.ChatResponse{
		ResponseId: "resp-2",
		RequestId:  "req-2",
		Content: &agentv1.ChatResponse_Intervention{
			Intervention: &agentv1.InterventionPayload{
				Request: &agentv1.InterventionRequest{
					Id:            "int-1",
					DedupeKey:     "dupe-1",
					Topic:         "review",
					CreatedAtMs:   123,
					SchemaVersion: "intervention.v1",
					Level:         agentv1.InterventionLevel_CARD,
					Reason: &agentv1.InterventionReason{
						TriggerEventId: "evt-1",
						ExplanationText: "Based on recent errors.",
						Confidence:      0.8,
						EvidenceRefs: []*agentv1.EvidenceRef{
							{
								Type:          "event",
								Id:            "evt-1",
								SchemaVersion: "event.v1",
								UserDeleted:   false,
							},
						},
						DecisionTrace: []string{"errors=2"},
					},
					Content: content,
				},
			},
		},
	}

	result := convertResponseToJSON(resp)
	assert.Equal(t, "intervention", result["type"])
	intervention, ok := result["intervention"].(map[string]interface{})
	assert.True(t, ok)
	assert.Equal(t, "int-1", intervention["id"])
	assert.Equal(t, "review", intervention["topic"])
	reason := intervention["reason"].(map[string]interface{})
	assert.Equal(t, "Based on recent errors.", reason["explanation_text"])
	contentMap := intervention["content"].(map[string]interface{})
	assert.Equal(t, "Morning Review", contentMap["title"])
}

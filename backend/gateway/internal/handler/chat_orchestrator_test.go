package handler

import (
	"encoding/json"
	"testing"
	"time"

	agentv1 "github.com/sparkle/gateway/gen/agent/v1"
	"github.com/stretchr/testify/assert"
	"google.golang.org/protobuf/types/known/structpb"
	"google.golang.org/protobuf/types/known/timestamppb"
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

func TestNormalizeChatMode(t *testing.T) {
	assert.Equal(t, "standard", normalizeChatMode(""))
	assert.Equal(t, "standard", normalizeChatMode("unknown"))
	assert.Equal(t, "expert_auto", normalizeChatMode("expert_auto"))
	assert.Equal(t, "expert::math_agent", normalizeChatMode("expert::math_agent"))
}

func TestWorkflowIDForChatMode(t *testing.T) {
	assert.Equal(t, "standard_chat", workflowIDForChatMode("standard"))
	assert.Equal(t, "deep_analysis_workflow", workflowIDForChatMode("deep_analysis"))
	assert.Equal(t, "expert_auto_workflow", workflowIDForChatMode("expert_auto"))
	assert.Equal(t, "expert_code_agent_workflow", workflowIDForChatMode("expert::code_agent"))
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

	result := convertResponseToJSON(resp, "")
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
						TriggerEventId:  "evt-1",
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

	result := convertResponseToJSON(resp, "")
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

func TestConvertResponseToJSONIncludesTraceMetadata(t *testing.T) {
	resp := &agentv1.ChatResponse{
		ResponseId:    "resp-3",
		RequestId:     "req-3",
		TraceId:       "trace-123",
		WorkflowId:    "standard_chat",
		PromptVersion: "v1",
		Content: &agentv1.ChatResponse_FullText{
			FullText: "hello",
		},
	}

	result := convertResponseToJSON(resp, "")
	assert.Equal(t, "trace-123", result["trace_id"])
	assert.Equal(t, "standard_chat", result["workflow_id"])
	assert.Equal(t, "v1", result["prompt_version"])
}

func TestConvertResponseToJSONDecodesExpertMetadata(t *testing.T) {
	resp := &agentv1.ChatResponse{
		ResponseId: "resp-expert-meta",
		RequestId:  "req-expert-meta",
		Metadata: map[string]string{
			"selected_experts":             `["deep_analyst","code_agent"]`,
			"routing_strategy":             "auto_multi_expert",
			"fallback_reason":              "",
			"route_confidence":             "0.82",
			"expert_entry_source":          "auto",
			"policy_id":                    "expert_strategy_v2",
			"strategy_pack":                "general_v2",
			"complexity_score":             "0.74",
			"complexity_tier":              "medium",
			"decomposition_contract":       `{"goal":"prepare exam","milestones":["phase1","phase2"],"acceptance_criteria":["score>=90"]}`,
			"decomposition_contract_score": "0.81",
			"decomposition_gaps":           `["missing_resources"]`,
			"plan_feasibility_score":       "0.76",
			"goal_hierarchy_score":         "0.88",
			"plan_ir_version":              "v2",
			"verifier_score":               "0.84",
			"verifier_ensemble_score":      "0.86",
			"contract_coverage":            "0.88",
			"verifier_fail_reasons":        `["missing_risks"]`,
			"uncertainty_score":            "0.41",
			"clarification_needed":         "false",
			"clarification_points":         `["补充里程碑","补充验收标准"]`,
			"search_budget_used":           "932",
			"plan_revision_count":          "1",
			"candidate_count":              "4",
			"winning_margin":               "0.0380",
			"simulated_risk_score":         "0.53",
			"repair_actions":               `["degrade_parallelism"]`,
			"repair_policy_id":             "counterfactual_repair_v1",
			"quality_gate_block_reason":    "",
			"q_score_hint":                 "0.83",
			"policy_layers":                `[{"policy_id":"expert_strategy_v2:general_v2","scope_type":"global"}]`,
			"prompt_policy_id":             "meta_policy_v1:prompt:general_v2:abc12345",
			"toolchain_policy_id":          "meta_policy_v1:toolchain:general_v2:def67890",
			"meta_learning_scope":          "composed",
			"plan_contract_version":        "v1",
		},
		Content: &agentv1.ChatResponse_FullText{
			FullText: "done",
		},
	}

	result := convertResponseToJSON(resp, "")
	meta, ok := result["metadata"].(map[string]interface{})
	assert.True(t, ok)
	selected, ok := meta["selected_experts"].([]interface{})
	assert.True(t, ok)
	assert.Len(t, selected, 2)
	assert.Equal(t, "auto_multi_expert", meta["routing_strategy"])
	assert.Equal(t, "0.82", meta["route_confidence"])
	assert.Equal(t, "expert_strategy_v2", meta["policy_id"])
	assert.Equal(t, "general_v2", meta["strategy_pack"])
	assert.Equal(t, "0.74", meta["complexity_score"])
	assert.Equal(t, "medium", meta["complexity_tier"])
	assert.Equal(t, "0.81", meta["decomposition_contract_score"])
	contract, ok := meta["decomposition_contract"].(map[string]interface{})
	assert.True(t, ok)
	assert.Equal(t, "prepare exam", contract["goal"])
	gaps, ok := meta["decomposition_gaps"].([]interface{})
	assert.True(t, ok)
	assert.Len(t, gaps, 1)
	assert.Equal(t, "0.76", meta["plan_feasibility_score"])
	assert.Equal(t, "0.88", meta["goal_hierarchy_score"])
	assert.Equal(t, "v2", meta["plan_ir_version"])
	assert.Equal(t, "0.84", meta["verifier_score"])
	assert.Equal(t, "0.86", meta["verifier_ensemble_score"])
	assert.Equal(t, "0.88", meta["contract_coverage"])
	_, ok = meta["verifier_fail_reasons"].([]interface{})
	assert.True(t, ok)
	assert.Equal(t, "0.41", meta["uncertainty_score"])
	assert.Equal(t, "false", meta["clarification_needed"])
	_, ok = meta["clarification_points"].([]interface{})
	assert.True(t, ok)
	assert.Equal(t, "932", meta["search_budget_used"])
	assert.Equal(t, "1", meta["plan_revision_count"])
	assert.Equal(t, "4", meta["candidate_count"])
	assert.Equal(t, "0.0380", meta["winning_margin"])
	assert.Equal(t, "0.53", meta["simulated_risk_score"])
	_, ok = meta["repair_actions"].([]interface{})
	assert.True(t, ok)
	assert.Equal(t, "counterfactual_repair_v1", meta["repair_policy_id"])
	assert.Equal(t, "0.83", meta["q_score_hint"])
	_, ok = meta["policy_layers"].([]interface{})
	assert.True(t, ok)
	assert.Equal(t, "meta_policy_v1:prompt:general_v2:abc12345", meta["prompt_policy_id"])
	assert.Equal(t, "meta_policy_v1:toolchain:general_v2:def67890", meta["toolchain_policy_id"])
	assert.Equal(t, "composed", meta["meta_learning_scope"])
	assert.Equal(t, "v1", meta["plan_contract_version"])
}

func TestConvertResponseToJSONIncludesEventTimeFallback(t *testing.T) {
	now := time.Now().UTC().Truncate(time.Millisecond)
	resp := &agentv1.ChatResponse{
		ResponseId: "resp-4",
		RequestId:  "req-4",
		EventTime:  timestamppb.New(now),
		Content: &agentv1.ChatResponse_FullText{
			FullText: "hello",
		},
	}

	result := convertResponseToJSON(resp, "")
	assert.Equal(t, now.UnixMilli(), result["event_time"])
}

func TestConvertResponseToJSONErrorIncludesEnumOnly(t *testing.T) {
	resp := &agentv1.ChatResponse{
		ResponseId: "resp-5",
		RequestId:  "req-5",
		Content: &agentv1.ChatResponse_Error{
			Error: &agentv1.Error{
				Message:   "Quota exhausted",
				Retryable: false,
				ErrorCode: agentv1.ErrorCode_ERROR_CODE_RATE_LIMITED,
			},
		},
	}

	result := convertResponseToJSON(resp, "")
	errObj, ok := result["error"].(map[string]interface{})
	assert.True(t, ok)
	assert.Equal(t, "rate_limited", errObj["error_code"])
}

func TestConvertResponseToJSONOmitsLegacyFields(t *testing.T) {
	now := time.Now().UTC().Truncate(time.Millisecond)
	resp := &agentv1.ChatResponse{
		ResponseId: "resp-6",
		RequestId:  "req-6",
		EventTime:  timestamppb.New(now),
		Content: &agentv1.ChatResponse_Error{
			Error: &agentv1.Error{
				Message:   "Quota exhausted",
				Retryable: false,
				ErrorCode: agentv1.ErrorCode_ERROR_CODE_RATE_LIMITED,
			},
		},
	}

	result := convertResponseToJSON(resp, "")
	errObj, ok := result["error"].(map[string]interface{})
	assert.True(t, ok)
	if _, ok := errObj["code"]; ok {
		t.Fatal("did not expect legacy error.code in v2-only mode")
	}
	assert.Equal(t, "rate_limited", errObj["error_code"])
}

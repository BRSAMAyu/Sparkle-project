from app.services.agent_grpc_service import AgentServiceImpl


def test_resolve_workflow_id_covers_all_public_and_team_modes():
    assert AgentServiceImpl._resolve_workflow_id("standard") == "standard_chat"
    assert AgentServiceImpl._resolve_workflow_id("deep_analysis") == "deep_analysis_workflow"
    assert AgentServiceImpl._resolve_workflow_id("study_plan") == "study_plan_workflow"
    assert AgentServiceImpl._resolve_workflow_id("error_diagnosis") == "error_diagnosis_workflow"
    assert AgentServiceImpl._resolve_workflow_id("expert_auto") == "expert_auto_workflow"
    assert AgentServiceImpl._resolve_workflow_id("expert::code_agent") == "expert_code_agent_workflow"
    assert (
        AgentServiceImpl._resolve_workflow_id('team::{"agents":["deep_analyst","exam_oracle"]}')
        == "expert_team_workflow"
    )

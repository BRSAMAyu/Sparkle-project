from __future__ import annotations
from typing import Any

from langchain_core.tools import tool


@tool
def query_knowledge(
    query: str,
    subject_id: str | None = None,
    limit: int = 10,
    use_vector_search: bool = True,
) -> dict[str, Any]:
    """Query the user's knowledge graph for relevant nodes."""
    return {
        "query": query,
        "subject_id": subject_id,
        "limit": limit,
        "use_vector_search": use_vector_search,
    }


@tool
def create_knowledge_node(
    title: str,
    summary: str,
    subject_id: str | None = None,
    tags: list[str] | None = None,
    parent_node_id: str | None = None,
) -> dict[str, Any]:
    """Create a knowledge node in the user's knowledge graph."""
    return {
        "title": title,
        "summary": summary,
        "subject_id": subject_id,
        "tags": tags or [],
        "parent_node_id": parent_node_id,
    }


@tool
def link_nodes(
    source_node_id: str,
    target_node_id: str,
    relation_type: str,
) -> dict[str, Any]:
    """Link two knowledge nodes by relation type."""
    return {
        "source_node_id": source_node_id,
        "target_node_id": target_node_id,
        "relation_type": relation_type,
    }


@tool
def create_plan(
    title: str,
    plan_type: str,
    plan_stage: str | None = None,
    subject_id: str | None = None,
    target_date: str | None = None,
    target_mastery: float | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Create a study plan (sprint or growth)."""
    return {
        "title": title,
        "plan_type": plan_type,
        "plan_stage": plan_stage,
        "subject_id": subject_id,
        "target_date": target_date,
        "target_mastery": target_mastery,
        "description": description,
    }


@tool
def generate_tasks_for_plan(
    plan_id: str,
    topic: str,
    difficulty: str = "medium",
    task_count: int = 5,
) -> dict[str, Any]:
    """Generate executable tasks for a specific plan."""
    return {
        "plan_id": plan_id,
        "topic": topic,
        "difficulty": difficulty,
        "task_count": task_count,
    }


@tool
def create_task(
    title: str,
    description: str | None = None,
    task_type: str = "learning",
    estimated_minutes: int | None = None,
    subject_id: str | None = None,
    due_date: str | None = None,
    priority: int = 2,
) -> dict[str, Any]:
    """Create a single task."""
    return {
        "title": title,
        "description": description,
        "task_type": task_type,
        "estimated_minutes": estimated_minutes,
        "subject_id": subject_id,
        "due_date": due_date,
        "priority": priority,
    }


@tool
def batch_create_tasks(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Create tasks in batch."""
    return {"tasks": tasks}


@tool
def suggest_focus_session(
    duration_minutes: int = 25,
    task_id: str | None = None,
    task_title: str | None = None,
) -> dict[str, Any]:
    """Suggest a focus session duration and task binding."""
    return {
        "duration_minutes": duration_minutes,
        "task_id": task_id,
        "task_title": task_title,
    }


@tool
def record_error(
    question: str,
    wrong_answer: str | None = None,
    correct_answer: str | None = None,
    error_type: str | None = None,
    root_cause: str | None = None,
    subject: str = "math",
) -> dict[str, Any]:
    """Record an error into error book."""
    return {
        "question": question,
        "wrong_answer": wrong_answer,
        "correct_answer": correct_answer,
        "error_type": error_type,
        "root_cause": root_cause,
        "subject": subject,
    }


@tool
def query_error_history(
    subject: str | None = None,
    error_type: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Query user's historical errors."""
    return {
        "subject": subject,
        "error_type": error_type,
        "limit": limit,
    }

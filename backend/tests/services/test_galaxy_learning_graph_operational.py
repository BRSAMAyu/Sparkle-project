from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest

from app.core.time_utils import utcnow
from app.models.file_storage import StoredFile
from app.models.galaxy import KnowledgeNode, NodeRelation, UserNodeStatus
from app.services.galaxy.ontology_generator import (
    DEFAULT_ENTITY_TYPES,
    DEFAULT_RELATION_TYPES,
    KnowledgeNodeCandidate,
    OntologyExtractionResult,
)
from app.services.galaxy_event_consumer import GalaxyEventConsumer
from app.services.galaxy_service import GalaxyService
from app.services.knowledge_integration_service import KnowledgeIntegrationService
from app.services.node_sector_service import SectorCode, build_sector_visuals


@pytest.mark.asyncio
async def test_galaxy_graph_explains_blocked_review_weak_and_mastered_states(db_session, test_user):
    prereq = KnowledgeNode(name="Derivatives", importance_level=3, source_type="seed")
    target = KnowledgeNode(name="Chain Rule", importance_level=4, source_type="seed")
    review = KnowledgeNode(name="Eigenvectors", importance_level=3, source_type="seed")
    weak = KnowledgeNode(name="Bayes Rule", importance_level=3, source_type="seed", keywords=["signal:weak_at"])
    mastered = KnowledgeNode(name="Linear Equations", importance_level=3, source_type="seed")
    db_session.add_all([prereq, target, review, weak, mastered])
    await db_session.flush()
    db_session.add(NodeRelation(source_node_id=prereq.id, target_node_id=target.id, relation_type="prerequisite"))
    db_session.add_all(
        [
            UserNodeStatus(user_id=test_user.id, node_id=prereq.id, is_unlocked=True, mastery_score=20),
            UserNodeStatus(user_id=test_user.id, node_id=target.id, is_unlocked=True, mastery_score=10),
            UserNodeStatus(
                user_id=test_user.id,
                node_id=review.id,
                is_unlocked=True,
                mastery_score=62,
                study_count=2,
                last_study_at=utcnow() - timedelta(days=21),
                next_review_at=utcnow() - timedelta(days=1),
            ),
            UserNodeStatus(user_id=test_user.id, node_id=weak.id, is_unlocked=True, mastery_score=25, study_count=1),
            UserNodeStatus(user_id=test_user.id, node_id=mastered.id, is_unlocked=True, mastery_score=98, study_count=5),
        ]
    )
    await db_session.commit()

    graph = await GalaxyService(db_session).get_galaxy_graph(test_user.id)
    by_name = {node.name: node for node in graph.nodes}

    assert by_name["Chain Rule"].learning_state.value == "blocked_by_prerequisite"
    assert by_name["Derivatives"].id in by_name["Chain Rule"].blocked_by_prerequisite_node_ids
    assert by_name["Eigenvectors"].learning_state.value == "ready_for_review"
    assert by_name["Eigenvectors"].recommended_action == "review"
    assert by_name["Bayes Rule"].learning_state.value == "weak"
    assert by_name["Linear Equations"].learning_state.value == "mastered"


@pytest.mark.asyncio
async def test_translation_document_and_error_events_stamp_graph_sources(db_session, test_user, monkeypatch):
    async def _skip_embedding(*_args, **_kwargs):
        return None

    async def _skip_graph_invalidation(*_args, **_kwargs):
        return None

    async def _fake_sector_classification(_self, **kwargs):
        return build_sector_visuals(
            kwargs.get("stable_seed") or kwargs.get("name") or "test-node",
            importance_level=kwargs.get("importance_level", 3),
            sector_weights={SectorCode.VOID: 100},
        )

    monkeypatch.setattr(KnowledgeIntegrationService, "_generate_embedding_async", _skip_embedding)
    monkeypatch.setattr("app.services.expansion_service.ExpansionService._invalidate_after_graph_mutation", _skip_graph_invalidation)
    monkeypatch.setattr("app.services.node_sector_service.NodeSectorService.classify_payload", _fake_sector_classification)

    translation_node = await KnowledgeIntegrationService(db_session).create_vocabulary_node(
        user_id=test_user.id,
        source_text="polymorphism",
        translation="多态",
        context="Runtime polymorphism chooses the method implementation dynamically.",
        language="en",
        domain="computer_science",
    )

    stored_file = StoredFile(
        user_id=test_user.id,
        file_name="calculus-notes.pdf",
        mime_type="application/pdf",
        file_size=2048,
        bucket="test",
        object_key="uploads/calculus-notes.pdf",
        status="processed",
    )
    db_session.add(stored_file)
    await db_session.commit()
    await db_session.refresh(stored_file)

    service = GalaxyService(db_session)

    async def _fake_ontology(*_args, **_kwargs):
        return OntologyExtractionResult(
            entity_types=DEFAULT_ENTITY_TYPES,
            fallback_entity_type="KnowledgeTopic",
            relation_types=DEFAULT_RELATION_TYPES,
            fallback_relation_type="RELATED_TO",
            nodes=[
                KnowledgeNodeCandidate(
                    name="Limits",
                    summary="Limits describe behavior as inputs approach a value.",
                    node_type="Concept",
                    keywords=["calculus", "limits"],
                    importance_level=3,
                )
            ],
            relations=[],
        )

    monkeypatch.setattr(service, "auto_generate_ontology", _fake_ontology)
    document_result = await service.create_nodes_from_document(
        user_id=test_user.id,
        file_id=stored_file.id,
        file_name=stored_file.file_name,
        document_text="Limits describe behavior as x approaches a value.",
        subject="calculus",
    )

    class _SessionCtx:
        async def __aenter__(self):
            return db_session

        async def __aexit__(self, *_args):
            return False

    async def _noop(*_args, **_kwargs):
        return None

    monkeypatch.setattr("app.services.galaxy_event_consumer.AsyncSessionLocal", lambda: _SessionCtx())
    monkeypatch.setattr("app.services.simulation.seed_extractor.SeedExtractor.prewarm_for_scenarios", _noop)
    monkeypatch.setattr("app.services.error_replan_bridge.ErrorReplanBridge.on_error_created", _noop)
    monkeypatch.setattr("app.services.card_protocol.mastery_bridge.ErrorMasteryBridge.on_error_created", _noop)

    await GalaxyEventConsumer(event_bus=None).handle_event(
        {
            "event_type": "error_created",
            "user_id": str(test_user.id),
            "error_id": str(uuid4()),
            "root_cause": "confuses derivative sign",
            "error_type": "knowledge_gap",
            "subject": "calculus",
            "chapter": "derivatives",
            "analysis": "The mistake shows a fragile derivative-sign concept.",
        }
    )

    graph = await GalaxyService(db_session).get_galaxy_graph(test_user.id)
    by_name = {node.name: node for node in graph.nodes}
    document_node_name = document_result["created_nodes"][0].name

    assert by_name[translation_node.name].graph_event_sources[0]["event_type"] == "translation.saved"
    assert by_name[document_node_name].graph_event_sources[0]["event_type"] == "document.ontology_created"

    error_nodes = [node for node in graph.nodes if node.name.startswith("Error gap:")]
    assert error_nodes
    assert error_nodes[0].learning_state.value == "weak"
    assert error_nodes[0].graph_event_sources[0]["event_type"] == "error.created"

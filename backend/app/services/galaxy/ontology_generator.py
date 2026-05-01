from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from app.services.llm_fallback_utils import analysis_llm

DEFAULT_ENTITY_TYPES = [
    "Concept",
    "Theory",
    "Formula",
    "Method",
    "Example",
    "Scholar",
    "Application",
    "Principle",
    "Definition",
    "Prerequisite",
]
FALLBACK_ENTITY_TYPE = "KnowledgeTopic"

DEFAULT_RELATION_TYPES = [
    "PREREQUISITE_OF",
    "EXPLAINS",
    "APPLIES_TO",
    "DERIVED_FROM",
    "CONTRADICTS",
    "SUPPORTS",
    "EXAMPLE_OF",
]
FALLBACK_RELATION_TYPE = "RELATED_TO"

RESERVED_TYPE_MAPPING = {
    "person": "Scholar",
    "people": "Scholar",
    "teacher": "Scholar",
    "formulae": "Formula",
    "law": "Principle",
    "topic": "Concept",
}

RELATION_WIRE_MAPPING = {
    "PREREQUISITE_OF": "prerequisite_of",
    "EXPLAINS": "explains",
    "APPLIES_TO": "applies_to",
    "DERIVED_FROM": "derived_from",
    "CONTRADICTS": "contradicts",
    "SUPPORTS": "supports",
    "EXAMPLE_OF": "example_of",
    "RELATED_TO": "related",
}


@dataclass
class KnowledgeNodeCandidate:
    name: str
    summary: str
    node_type: str
    keywords: list[str] = field(default_factory=list)
    importance_level: int = 2
    exam_weight: float = 0.5
    recommended_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "summary": self.summary,
            "node_type": self.node_type,
            "keywords": list(self.keywords),
            "importance_level": self.importance_level,
            "exam_weight": self.exam_weight,
            "recommended_action": self.recommended_action,
        }


@dataclass
class KnowledgeRelationCandidate:
    source_name: str
    target_name: str
    relation_type: str
    strength: float = 0.55
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "target_name": self.target_name,
            "relation_type": self.relation_type,
            "strength": self.strength,
            "rationale": self.rationale,
        }


@dataclass
class OntologyExtractionResult:
    entity_types: list[str]
    fallback_entity_type: str
    relation_types: list[str]
    fallback_relation_type: str
    nodes: list[KnowledgeNodeCandidate] = field(default_factory=list)
    relations: list[KnowledgeRelationCandidate] = field(default_factory=list)
    truncated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_types": list(self.entity_types),
            "fallback_entity_type": self.fallback_entity_type,
            "relation_types": list(self.relation_types),
            "fallback_relation_type": self.fallback_relation_type,
            "nodes": [node.to_dict() for node in self.nodes],
            "relations": [relation.to_dict() for relation in self.relations],
            "truncated": self.truncated,
        }


class OntologyGenerator:
    MAX_TEXT_BYTES = 50 * 1024

    async def generate(self, document_text: str, subject: str | None = None) -> OntologyExtractionResult:
        truncated_text, truncated = self._truncate_text(document_text or "")
        fallback = self._fallback_extraction(truncated_text, subject=subject)

        prompt = (
            "You are Sparkle Galaxy's ontology generator for learning materials.\n"
            "Return strict JSON only.\n"
            "Rules:\n"
            "1. entity_types must contain exactly 10 distinct learner-friendly types.\n"
            "2. fallback_entity_type must be a single generic fallback.\n"
            "3. relation_types should prioritize prerequisite/explanation/application logic.\n"
            "4. nodes should be concise and grounded in the source text.\n"
            "5. relations must only connect returned nodes.\n"
            "6. Keep node count between 4 and 12.\n"
            "7. Use English type identifiers.\n"
            "8. Each node must include exam_weight (0.0-1.0, how likely this appears on exams) "
            "and recommended_action (one sentence: what the student should do next for this topic).\n"
            f"Subject hint: {subject or 'general learning'}\n"
            f"Preferred entity types: {', '.join(DEFAULT_ENTITY_TYPES)}\n"
            f"Preferred relation types: {', '.join(DEFAULT_RELATION_TYPES)}\n\n"
            f"Document:\n{truncated_text}"
        )

        payload = await analysis_llm.json_call(
            [
                {"role": "system", "content": "Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            fallback=fallback.to_dict(),
            temperature=0.2,
        )

        try:
            result = self._repair_payload(payload or fallback.to_dict())
            result.truncated = truncated
            return result
        except Exception as exc:
            logger.warning("Ontology generation repair failed, using fallback: {}", exc)
            fallback.truncated = truncated
            return fallback

    def _truncate_text(self, text: str) -> tuple[str, bool]:
        encoded = text.encode("utf-8")
        if len(encoded) <= self.MAX_TEXT_BYTES:
            return text, False
        truncated = encoded[: self.MAX_TEXT_BYTES].decode("utf-8", errors="ignore")
        return truncated, True

    def _normalize_entity_type(self, raw: object) -> str:
        cleaned = str(raw or "").strip()
        if not cleaned:
            return FALLBACK_ENTITY_TYPE
        normalized = RESERVED_TYPE_MAPPING.get(cleaned.lower(), cleaned)
        normalized = re.sub(r"[^A-Za-z]", "", normalized) or FALLBACK_ENTITY_TYPE
        return normalized[0].upper() + normalized[1:]

    def _normalize_relation_type(self, raw: object) -> str:
        cleaned = str(raw or "").strip().upper()
        cleaned = re.sub(r"[^A-Z_]", "_", cleaned)
        cleaned = re.sub(r"_+", "_", cleaned).strip("_")
        if cleaned in DEFAULT_RELATION_TYPES or cleaned == FALLBACK_RELATION_TYPE:
            return cleaned
        aliases = {
            "REQUIRES": "PREREQUISITE_OF",
            "PREREQUISITE": "PREREQUISITE_OF",
            "EXPLAINS_WITH": "EXPLAINS",
            "APPLY_TO": "APPLIES_TO",
            "APPLICATION_OF": "APPLIES_TO",
            "SUPPORT": "SUPPORTS",
            "SUPPORTED_BY": "SUPPORTS",
            "DERIVES_FROM": "DERIVED_FROM",
            "EXAMPLE": "EXAMPLE_OF",
            "EXEMPLIFIES": "EXAMPLE_OF",
        }
        return aliases.get(cleaned, FALLBACK_RELATION_TYPE)

    def _repair_payload(self, payload: dict[str, Any]) -> OntologyExtractionResult:
        raw_entity_types = payload.get("entity_types")
        entity_types = []
        if isinstance(raw_entity_types, list):
            for item in raw_entity_types:
                normalized = self._normalize_entity_type(item)
                if normalized not in entity_types:
                    entity_types.append(normalized)
        for item in DEFAULT_ENTITY_TYPES:
            normalized = self._normalize_entity_type(item)
            if normalized not in entity_types:
                entity_types.append(normalized)
        entity_types = entity_types[:10]

        fallback_entity_type = self._normalize_entity_type(payload.get("fallback_entity_type") or FALLBACK_ENTITY_TYPE)

        raw_relation_types = payload.get("relation_types")
        relation_types = []
        if isinstance(raw_relation_types, list):
            for item in raw_relation_types:
                normalized = self._normalize_relation_type(item)
                if normalized not in relation_types and normalized != FALLBACK_RELATION_TYPE:
                    relation_types.append(normalized)
        for item in DEFAULT_RELATION_TYPES:
            if item not in relation_types:
                relation_types.append(item)
        relation_types = relation_types[: len(DEFAULT_RELATION_TYPES)]

        nodes = self._repair_nodes(payload.get("nodes"), entity_types, fallback_entity_type)
        relations = self._repair_relations(payload.get("relations"), nodes)

        if not nodes:
            fallback = self._fallback_extraction("", subject=None)
            nodes = fallback.nodes
            relations = fallback.relations

        return OntologyExtractionResult(
            entity_types=entity_types,
            fallback_entity_type=fallback_entity_type,
            relation_types=relation_types,
            fallback_relation_type=FALLBACK_RELATION_TYPE,
            nodes=nodes,
            relations=relations,
        )

    def _repair_nodes(
        self,
        raw_nodes: object,
        entity_types: list[str],
        fallback_entity_type: str,
    ) -> list[KnowledgeNodeCandidate]:
        if not isinstance(raw_nodes, list):
            return []

        allowed_types = set(entity_types + [fallback_entity_type])
        seen_names: set[str] = set()
        repaired: list[KnowledgeNodeCandidate] = []

        for item in raw_nodes:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            name_key = name.lower()
            if name_key in seen_names:
                continue
            seen_names.add(name_key)

            summary = str(item.get("summary") or item.get("description") or "").strip()
            if not summary:
                summary = f"{name} 是该学习材料中的一个关键知识点。"
            node_type = self._normalize_entity_type(item.get("node_type") or fallback_entity_type)
            if node_type not in allowed_types:
                node_type = fallback_entity_type
            keywords = [str(keyword).strip() for keyword in list(item.get("keywords") or []) if str(keyword).strip()]
            repaired.append(
                KnowledgeNodeCandidate(
                    name=name[:255],
                    summary=summary[:1200],
                    node_type=node_type,
                    keywords=keywords[:8],
                    importance_level=max(1, min(int(item.get("importance_level") or 2), 5)),
                    exam_weight=max(0.0, min(float(item.get("exam_weight") or 0.5), 1.0)),
                    recommended_action=str(item.get("recommended_action") or "")[:200],
                )
            )
            if len(repaired) >= 12:
                break

        return repaired

    def _repair_relations(
        self,
        raw_relations: object,
        nodes: list[KnowledgeNodeCandidate],
    ) -> list[KnowledgeRelationCandidate]:
        if not isinstance(raw_relations, list):
            return self._build_linear_relations(nodes)

        allowed_names = {node.name for node in nodes}
        repaired: list[KnowledgeRelationCandidate] = []
        seen_pairs: set[tuple[str, str, str]] = set()

        for item in raw_relations:
            if not isinstance(item, dict):
                continue
            source_name = str(item.get("source_name") or item.get("source") or "").strip()
            target_name = str(item.get("target_name") or item.get("target") or "").strip()
            if source_name not in allowed_names or target_name not in allowed_names or source_name == target_name:
                continue
            relation_type = self._normalize_relation_type(item.get("relation_type"))
            key = (source_name, target_name, relation_type)
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            repaired.append(
                KnowledgeRelationCandidate(
                    source_name=source_name,
                    target_name=target_name,
                    relation_type=relation_type,
                    strength=max(0.1, min(float(item.get("strength") or 0.55), 1.0)),
                    rationale=str(item.get("rationale") or item.get("reason") or "").strip()[:240],
                )
            )
            if len(repaired) >= 18:
                break

        return repaired or self._build_linear_relations(nodes)

    def _fallback_extraction(self, text: str, subject: str | None) -> OntologyExtractionResult:
        lines = [line.strip("# ").strip() for line in text.splitlines() if line.strip()]
        heading_candidates = [line for line in lines if 4 <= len(line) <= 48][:8]
        if not heading_candidates:
            heading_candidates = self._keyword_candidates(text)

        nodes = []
        node_types = DEFAULT_ENTITY_TYPES[:]
        for index, name in enumerate(heading_candidates[:6]):
            node_type = node_types[index % len(node_types)]
            summary = (
                f"{name} 是该{subject or '学习'}材料中的关键{node_type.lower()}，"
                "可作为后续学习路径和图谱推理的锚点。"
            )
            nodes.append(
                KnowledgeNodeCandidate(
                    name=name[:255],
                    summary=summary,
                    node_type=node_type,
                    keywords=[name, subject or "learning"][:4],
                    importance_level=3 if index == 0 else 2,
                )
            )

        relations = self._build_linear_relations(nodes)
        return OntologyExtractionResult(
            entity_types=DEFAULT_ENTITY_TYPES[:],
            fallback_entity_type=FALLBACK_ENTITY_TYPE,
            relation_types=DEFAULT_RELATION_TYPES[:],
            fallback_relation_type=FALLBACK_RELATION_TYPE,
            nodes=nodes,
            relations=relations,
        )

    def _keyword_candidates(self, text: str) -> list[str]:
        tokens = re.findall(r"[\u4e00-\u9fff]{2,10}|[A-Za-z][A-Za-z0-9_+-]{3,24}", text or "")
        ranked: list[str] = []
        seen: set[str] = set()
        for token in tokens:
            cleaned = token.strip()
            lowered = cleaned.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            ranked.append(cleaned)
            if len(ranked) >= 6:
                break
        return ranked or ["核心概念", "关键方法", "典型例题"]

    def _build_linear_relations(self, nodes: list[KnowledgeNodeCandidate]) -> list[KnowledgeRelationCandidate]:
        relations: list[KnowledgeRelationCandidate] = []
        for index in range(len(nodes) - 1):
            relation_type = "PREREQUISITE_OF" if index == 0 else "EXPLAINS"
            relations.append(
                KnowledgeRelationCandidate(
                    source_name=nodes[index].name,
                    target_name=nodes[index + 1].name,
                    relation_type=relation_type,
                    strength=0.6 if relation_type == "PREREQUISITE_OF" else 0.52,
                    rationale="Fallback linear relation derived from document structure.",
                )
            )
        return relations


def relation_type_to_wire_name(relation_type: str) -> str:
    return RELATION_WIRE_MAPPING.get(str(relation_type or "").upper(), "related")

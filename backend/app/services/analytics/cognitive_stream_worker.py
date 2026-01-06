import asyncio
import hashlib
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import EventBus
from app.models.cognitive import CognitiveFragment, AnalysisStatus
from app.models.user import User
from app.models.compliance import DlqReplayAuditLog
from app.services.analytics.normalization import BehaviorNormalizer
from app.services.analytics.bkt_service import BKTService
from app.services.analytics.irt_service import IRTService
from app.services.analytics.model_metrics import record_bkt_auc, record_irt_rmse
from app.services.compliance.age_gate import AgeGateService
from app.services.compliance.crypto_erase import CryptoEraseManager


class ShadowKafkaWriter:
    """
    Kafka 影子写入接口 (占位)
    """

    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self._producer = None
        self._lock = asyncio.Lock()

    async def write(self, event: Dict[str, Any]) -> None:
        if not self.enabled:
            return

        producer = await self._get_producer()
        if not producer:
            return

        topic = os.getenv("KAFKA_SHADOW_TOPIC", "stream.persona.shadow")
        payload = json.dumps(event, ensure_ascii=True).encode("utf-8")
        fire_and_forget = os.getenv("KAFKA_SHADOW_FIRE_AND_FORGET", "false") == "true"

        if fire_and_forget:
            asyncio.create_task(producer.send_and_wait(topic, payload))
            return

        await producer.send_and_wait(topic, payload)

    async def _get_producer(self):
        async with self._lock:
            if self._producer:
                return self._producer
            try:
                from aiokafka import AIOKafkaProducer
            except ImportError:
                logger.warning("aiokafka not installed, skip shadow write")
                return None

            bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
            self._producer = AIOKafkaProducer(
                bootstrap_servers=bootstrap_servers,
                client_id="sparkle_persona_shadow",
                acks="1"
            )
            await self._producer.start()
            return self._producer


class CognitiveStreamWorker:
    STREAM_NAME = "stream:tracking_events"
    DLQ_STREAM = "stream:dlq:persona"
    GROUP_NAME = "cognitive_stream_worker"

    SENSITIVE_TAGS = {"anxiety_high", "distraction_high", "depression_risk"}
    SENSITIVE_SENTIMENTS = {"anxious", "depressed", "burnout"}

    def __init__(self, db: AsyncSession, redis_client, event_bus: Optional[EventBus] = None):
        self.db = db
        self.redis = redis_client
        self.event_bus = event_bus or EventBus()
        self.shadow_writer = ShadowKafkaWriter(enabled=os.getenv("ENABLE_KAFKA_SHADOW_WRITE", "false") == "true")
        self.bkt_service = BKTService(db)
        self.irt_service = IRTService(db)
        self.crypto_erase = CryptoEraseManager(db)

    async def start(self) -> None:
        await self.event_bus.connect()
        await self.event_bus.subscribe(
            stream=self.STREAM_NAME,
            group_name=self.GROUP_NAME,
            consumer_name=f"consumer-{datetime.utcnow().timestamp()}",
            callback=self.handle_event
        )

    async def handle_event(self, event: Dict[str, Any]) -> None:
        try:
            await self.shadow_writer.write(event)
            await self._process_event(event)
        except Exception as exc:
            logger.error(f"CognitiveStreamWorker failed: {exc}")
            await self._send_to_dlq(event, error=str(exc))

    async def _process_event(self, event: Dict[str, Any]) -> None:
        event_name = event.get("event_name") or event.get("event_type")
        payload = event.get("payload") or {}
        if isinstance(payload, str):
            payload = json.loads(payload)

        payload = BehaviorNormalizer.normalize(payload)
        user_id = UUID(event["user_id"])

        user = await self.db.get(User, user_id)
        if not user:
            logger.warning(f"Missing user for event {event.get('event_id')}")
            return

        decision = AgeGateService.evaluate(user, payload)
        AgeGateService.apply_to_user(user, decision)

        if event_name == "question_submit":
            await self._handle_question_submit(user_id, event, payload)

        self._record_model_metrics(payload, event)

        await self._create_fragment(user_id, event, payload, decision.should_collect_sensitive)
        await self.db.commit()

    def _record_model_metrics(self, payload: Dict[str, Any], event: Dict[str, Any]) -> None:
        metrics = payload.get("evaluation_metrics")
        if not isinstance(metrics, dict):
            return

        age_bucket = metrics.get("age_bucket", "unknown")
        device_tier = metrics.get("device_tier", "unknown")
        subject_id = str(event.get("subject_id") or "unknown")

        if metrics.get("bkt_auc") is not None:
            record_bkt_auc(float(metrics["bkt_auc"]), age_bucket, device_tier, subject_id)
        if metrics.get("irt_rmse") is not None:
            record_irt_rmse(float(metrics["irt_rmse"]), age_bucket, device_tier, subject_id)

    async def _handle_question_submit(self, user_id: UUID, event: Dict[str, Any], payload: Dict[str, Any]) -> None:
        node_id = event.get("node_id")
        question_id = event.get("question_id")
        correct = bool(payload.get("correct"))
        subject_id = str(event.get("subject_id")) if event.get("subject_id") is not None else None

        if node_id:
            try:
                await self.bkt_service.update_mastery(user_id, UUID(node_id), correct)
            except ValueError:
                logger.warning(f"Invalid node_id for BKT: {node_id}")

        if question_id:
            try:
                await self.irt_service.update_theta(
                    user_id=user_id,
                    question_id=UUID(question_id),
                    correct=correct,
                    subject_id=subject_id
                )
            except ValueError:
                logger.warning(f"Invalid question_id for IRT: {question_id}")

    async def _create_fragment(
        self,
        user_id: UUID,
        event: Dict[str, Any],
        payload: Dict[str, Any],
        allow_sensitive: bool
    ) -> None:
        tags = payload.get("tags") or []
        sensitive = [t for t in tags if t in self.SENSITIVE_TAGS]
        safe_tags = [t for t in tags if t not in self.SENSITIVE_TAGS]

        sentiment = payload.get("sentiment")
        if sentiment in self.SENSITIVE_SENTIMENTS:
            sensitive.append(sentiment)
            sentiment = None

        fragment = CognitiveFragment(
            user_id=user_id,
            task_id=event.get("task_id"),
            source_type="behavior",
            resource_type="event",
            resource_url=None,
            content=event.get("event_name", "behavior_event"),
            sentiment=sentiment if allow_sensitive else None,
            tags=safe_tags,
            error_tags=payload.get("error_tags"),
            context_tags=payload.get("context_tags"),
            severity=int(payload.get("severity", 1)),
            persona_version=payload.get("persona_version"),
            source_event_id=event.get("event_id"),
            analysis_status=AnalysisStatus.PENDING
        )

        if allow_sensitive and sensitive:
            encrypted, key_id = await self.crypto_erase.encrypt_payload(
                user_id=user_id,
                plaintext=json.dumps(sensitive)
            )
            fragment.sensitive_tags_encrypted = encrypted
            fragment.sensitive_tags_key_id = key_id
            fragment.sensitive_tags_version = 1

        self.db.add(fragment)

    async def _send_to_dlq(self, event: Dict[str, Any], error: str) -> None:
        if not self.redis:
            return
        payload = {
            "event": event,
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.redis.xadd(self.DLQ_STREAM, {"data": json.dumps(payload)})

    async def replay_dlq_event(self, dlq_event: Dict[str, Any], audit_headers: Dict[str, str]) -> None:
        admin_id = audit_headers.get("x-audit-admin-id")
        approver_id = audit_headers.get("x-audit-approver-id")
        reason_code = audit_headers.get("x-audit-reason-code")
        if not admin_id or not approver_id or not reason_code:
            raise ValueError("Missing DLQ audit headers")

        payload_hash = hashlib.sha256(json.dumps(dlq_event, sort_keys=True).encode("utf-8")).hexdigest()
        audit_log = DlqReplayAuditLog(
            message_id=str(dlq_event.get("message_id", "unknown")),
            admin_id=UUID(admin_id),
            approver_id=UUID(approver_id),
            reason_code=reason_code,
            payload_hash=payload_hash
        )
        self.db.add(audit_log)
        await self.db.commit()

        await self._process_event(dlq_event)

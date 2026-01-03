from abc import ABC, abstractmethod
from typing import Type, List, Dict, Any, Optional
import pika
import json
import os
from datetime import datetime
from loguru import logger

class Event(ABC):
    """Event base class"""
    @abstractmethod
    def to_dict(self) -> dict:
        pass

class KnowledgeNodeUpdated(Event):
    def __init__(self, user_id: str, node_id: str, new_mastery: int):
        self.user_id = user_id
        self.node_id = node_id
        self.new_mastery = new_mastery
        self.timestamp = datetime.utcnow()

    def to_dict(self):
        return {
            "event_type": "knowledge_node_updated",
            "user_id": self.user_id,
            "node_id": self.node_id,
            "new_mastery": self.new_mastery,
            "timestamp": self.timestamp.isoformat()
        }

class NodeMasteryUpdatedEvent(Event):
    def __init__(self, user_id: str, node_id: str, old_mastery: int, new_mastery: int, reason: str):
        self.user_id = user_id
        self.node_id = node_id
        self.old_mastery = old_mastery
        self.new_mastery = new_mastery
        self.reason = reason
        self.timestamp = datetime.utcnow()

    def to_dict(self):
        return {
            "event_type": "node_mastery_updated",
            "user_id": self.user_id,
            "node_id": self.node_id,
            "old_mastery": self.old_mastery,
            "new_mastery": self.new_mastery,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat()
        }

class EventBus:
    """Event Bus - RabbitMQ Wrapper"""
    def __init__(self, rabbitmq_url: Optional[str] = None):
        self.rabbitmq_url = rabbitmq_url or os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
        self.connection = None
        self.channel = None
        self._connect()

    def _connect(self):
        try:
            self.connection = pika.BlockingConnection(
                pika.URLParameters(self.rabbitmq_url)
            )
            self.channel = self.connection.channel()
            self.channel.exchange_declare(
                exchange='sparkle_events',
                exchange_type='topic',
                durable=True
            )
            logger.info("Connected to RabbitMQ")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            # In a real app, we might want to implement retry logic or fail gracefully
            # For now, we'll just log the error. The publish method should handle disconnection.

    def publish(self, event: Event, routing_key: str):
        """Publish event"""
        if not self.channel or self.channel.is_closed:
            self._connect()
            if not self.channel:
                 logger.error("Cannot publish event, RabbitMQ not connected")
                 return

        try:
            self.channel.basic_publish(
                exchange='sparkle_events',
                routing_key=routing_key,
                body=json.dumps(event.to_dict()),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Persistent
                    content_type='application/json'
                )
            )
            logger.debug(f"Published event {routing_key}")
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")

    def subscribe(self, routing_key: str, callback):
        """Subscribe to event"""
        if not self.channel or self.channel.is_closed:
             self._connect()
             if not self.channel:
                 logger.error("Cannot subscribe, RabbitMQ not connected")
                 return

        queue_name = f"queue_{routing_key.replace('.', '_')}"
        self.channel.queue_declare(queue=queue_name, durable=True)
        self.channel.queue_bind(
            queue=queue_name,
            exchange='sparkle_events',
            routing_key=routing_key
        )
        self.channel.basic_consume(
            queue=queue_name,
            on_message_callback=callback,
            auto_ack=False
        )
        logger.info(f"Subscribed to {routing_key}")

    def start_consuming(self):
        if self.channel:
            logger.info("Starting to consume messages...")
            self.channel.start_consuming()

# Global instance
event_bus = EventBus()

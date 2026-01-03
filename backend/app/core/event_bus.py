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
    """Event Bus - RabbitMQ Wrapper with improved stability"""
    def __init__(self, rabbitmq_url: Optional[str] = None):
        self.rabbitmq_url = rabbitmq_url or os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
        self.connection = None
        self.channel = None
        self._connect()

    def _connect(self):
        """Establish connection with heartbeats to prevent unexpected closures"""
        try:
            # heartbeat=60 is crucial for long-lived connections
            parameters = pika.URLParameters(self.rabbitmq_url)
            parameters.heartbeat = 60
            parameters.blocked_connection_timeout = 300
            
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            self.channel.exchange_declare(
                exchange='sparkle_events',
                exchange_type='topic',
                durable=True
            )
            logger.info("Successfully connected to RabbitMQ with heartbeats")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            self.connection = None
            self.channel = None

    def _ensure_connection(self):
        """Check connection health and reconnect if necessary"""
        if self.connection is None or self.connection.is_closed or \
           self.channel is None or self.channel.is_closed:
            logger.warning("RabbitMQ connection lost, attempting to reconnect...")
            self._connect()

    def publish(self, event: Event, routing_key: str):
        """Publish event with automatic retry and health check"""
        self._ensure_connection()
        
        if not self.channel:
            logger.error(f"Cannot publish event {routing_key}: Connection unavailable")
            return

        try:
            self.channel.basic_publish(
                exchange='sparkle_events',
                routing_key=routing_key,
                body=json.dumps(event.to_dict()),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Persistent
                    content_type='application/json',
                    timestamp=int(datetime.utcnow().timestamp())
                )
            )
            logger.debug(f"Published event {routing_key}")
        except pika.exceptions.AMQPError as e:
            logger.error(f"AMQP error during publish: {e}")
            # Reset connection on AMQP errors to trigger reconnect on next attempt
            self.connection = None
        except Exception as e:
            logger.error(f"Unexpected error during publish: {e}")

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

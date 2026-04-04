from __future__ import annotations
"""
BERT-based Intent Classifier for Semantic Understanding

Phase 2.1: Deep semantic understanding using pre-trained BERT models.
Target: 98%+ accuracy, <200ms inference time.

This module provides:
- Semantic intent classification using BERT
- Confidence scoring with probability distribution
- Async inference with batching support
- Automatic fallback to keyword matching
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import torch
from loguru import logger

try:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("transformers not installed, BERT classifier disabled")


class BERTIntentClassifier:
    """BERT-based intent classifier for semantic understanding

    Uses pre-trained BERT model (chinese-bert-wwm-ext) fine-tuned for intent classification.

    Architecture:
        Input (message) → BERT Tokenizer → BERT Model → Softmax → Intent + Confidence

    Performance Targets:
        - Accuracy: 98%+
        - Latency: <200ms per inference
        - Memory: ~400MB (model + tokenizer)
    """

    # Intent labels (must match RequestRouter intents)
    INTENT_LABELS = [
        "chat",       # General conversation
        "create",     # Create task/plan
        "update",     # Update/modify
        "delete",     # Delete/remove
        "query",      # Query/search
        "learn",      # Learning intent
        "review",     # Review material
        "translation",  # Translation
        "prism",      # Behavior analysis
        "sprint",     # Focus mode
    ]

    # Default model (Chinese BERT)
    DEFAULT_MODEL = "hfl/chinese-bert-wwm-ext"

    # Alternative models (for future experimentation)
    MODEL_OPTIONS = {
        "chinese_bert": "hfl/chinese-bert-wwm-ext",
        "multilingual_bert": "bert-base-multilingual-cased",
        "tiny_bert": "hfl/chinese-bert-wwm-ext-tiny",  # Faster, slightly less accurate
    }

    @staticmethod
    def _resolve_device(device: str):
        if device == "auto":
            requested = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            requested = device
        requested = str(requested or "cpu").strip() or "cpu"
        resolved = torch.device(requested)
        if hasattr(resolved, "type"):
            return resolved
        return SimpleNamespace(type=requested)

    def _classify_sync(self, message: str) -> dict:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.classify(message))

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(lambda: asyncio.run(self.classify(message)))
            return future.result()

    def __init__(
        self,
        model_name: str = None,
        device: str = "auto",
        max_length: int = 128,
        batch_size: int = 8
    ):
        """Initialize BERT classifier

        Args:
            model_name: HuggingFace model name (default: chinese-bert-wwm-ext)
            device: Device to use ("cpu", "cuda", "auto")
            max_length: Maximum sequence length for tokenization
            batch_size: Batch size for inference
        """
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("transformers library not available. Install with: pip install transformers torch")

        self.model_name = model_name or self.DEFAULT_MODEL
        self.max_length = max_length
        self.batch_size = batch_size

        # Detect device
        self.device = self._resolve_device(device)

        logger.info(f"Initializing BERT classifier: {self.model_name} on {self.device}")

        # Load model and tokenizer
        try:
            self._load_model()
            self.model_loaded = True
        except Exception as e:
            logger.error(f"Failed to load BERT model: {e}")
            self.model_loaded = False

    def _load_model(self):
        """Load tokenizer and model from HuggingFace"""
        logger.info(f"Loading tokenizer: {self.model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)

        logger.info(f"Loading model: {self.model_name}")
        self.model = AutoModelForSequenceClassification.from_pretrained(
            self.model_name,
            num_labels=len(self.INTENT_LABELS)
        )

        # Move to device and set to eval mode
        self.model.to(self.device)
        self.model.eval()

        logger.info(f"Model loaded successfully on {self.device}")

    async def classify(
        self,
        message: str,
        context: str = ""
    ) -> dict:
        """Classify intent with confidence score

        Args:
            message: User message to classify
            context: Optional conversation context (previous messages)

        Returns:
            {
                "intent": "predicted_intent",
                "confidence": 0.95,
                "probabilities": {
                    "chat": 0.02,
                    "create": 0.93,
                    ...
                }
            }
        """
        if not self.model_loaded:
            logger.warning("Model not loaded, returning default")
            return {
                "intent": "chat",
                "confidence": 0.5,
                "probabilities": dict.fromkeys(self.INTENT_LABELS, 0.1)
            }

        # Build input text with context
        text = self._build_input_text(message, context)

        try:
            # Run inference in thread pool to avoid blocking
            result = await asyncio.to_thread(self._infer, text)

            logger.debug(f"BERT classification: '{message[:30]}...' -> {result['intent']} (conf={result['confidence']:.2f})")
            return result

        except Exception as e:
            logger.error(f"BERT inference failed: {e}")
            # Return default
            return {
                "intent": "chat",
                "confidence": 0.5,
                "probabilities": dict.fromkeys(self.INTENT_LABELS, 0.1)
            }

    def _build_input_text(self, message: str, context: str) -> str:
        """Build input text for BERT

        Uses BERT special tokens: [CLS] context [SEP] message [SEP]

        Args:
            message: User message
            context: Conversation context

        Returns:
            Formatted input string
        """
        if context:
            # With context: [CLS] context [SEP] message [SEP]
            return f"[CLS] {context} [SEP] {message} [SEP]"
        else:
            # Without context: [CLS] message [SEP]
            return f"[CLS] {message} [SEP]"

    def _infer(self, text: str) -> dict:
        """Run BERT inference (synchronous)

        Args:
            text: Input text

        Returns:
            Classification result with probabilities
        """
        import time
        start = time.time()

        # Tokenize
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_length,
            padding=True
        )

        # Move to device
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Inference
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits[0]  # [num_labels]

            # Convert to probabilities
            probs = torch.softmax(logits, dim=-1)

            # Get prediction
            max_prob = torch.max(probs).item()
            predicted_idx = torch.argmax(probs).item()
            predicted_intent = self.INTENT_LABELS[predicted_idx]

        # Build probability dictionary
        probabilities = {
            label: float(probs[i])
            for i, label in enumerate(self.INTENT_LABELS)
        }

        elapsed = (time.time() - start) * 1000
        logger.debug(f"BERT inference: {elapsed:.1f}ms")

        return {
            "intent": predicted_intent,
            "confidence": max_prob,
            "probabilities": probabilities
        }

    async def classify_batch(
        self,
        messages: list[str],
        contexts: list[str] = None
    ) -> list[dict]:
        """Classify multiple messages in batch

        More efficient than individual classifications for large batches.

        Args:
            messages: List of messages to classify
            contexts: Optional list of contexts (same length as messages)

        Returns:
            List of classification results
        """
        if contexts is None:
            contexts = [""] * len(messages)

        # Process in batches
        results = []
        for i in range(0, len(messages), self.batch_size):
            batch_messages = messages[i:i + self.batch_size]
            batch_contexts = contexts[i:i + self.batch_size]

            # Run batch inference
            batch_results = await asyncio.gather(*[
                self.classify(msg, ctx)
                for msg, ctx in zip(batch_messages, batch_contexts, strict=False)
            ])

            results.extend(batch_results)

        return results

    def adjust_scores_with_bert(
        self,
        keyword_scores: dict[str, float],
        message: str,
        bert_weight: float = 0.4
    ) -> tuple[str, float]:
        """Adjust keyword scores with BERT semantic understanding

        Combines fast keyword matching with accurate BERT classification.

        Formula:
            final_score = keyword_score * (1 - bert_weight) + bert_prob * bert_weight

        Args:
            keyword_scores: Dict from _classify_intent_with_confidence
            message: User message
            bert_weight: Weight for BERT prediction (0.4 = 40% BERT, 60% keyword)

        Returns:
            (intent, confidence) tuple
        """
        if not self.model_loaded:
            # Fallback to keyword-only
            max_intent = max(keyword_scores, key=keyword_scores.get)
            return max_intent, keyword_scores[max_intent]

        try:
            bert_result = self._classify_sync(message)

            # Combine scores
            adjusted_scores = {}
            for intent in keyword_scores:
                keyword_score = keyword_scores[intent]
                bert_prob = bert_result["probabilities"].get(intent, 0.0)

                # Weighted combination
                combined = keyword_score * (1 - bert_weight) + bert_prob * bert_weight
                adjusted_scores[intent] = combined

            # Get best intent
            max_intent = max(adjusted_scores, key=adjusted_scores.get)
            max_confidence = adjusted_scores[max_intent]

            logger.debug(f"BERT-adjusted: {max_intent} (conf={max_confidence:.2f})")
            return max_intent, max_confidence

        except Exception as e:
            logger.warning(f"BERT adjustment failed: {e}, using keyword-only")
            max_intent = max(keyword_scores, key=keyword_scores.get)
            return max_intent, keyword_scores[max_intent]

    def get_model_info(self) -> dict:
        """Get model information for monitoring

        Returns:
            {
                "model_name": "...",
                "device": "cuda/cpu",
                "loaded": True/False,
                "num_labels": 10,
                "max_length": 128
            }
        """
        return {
            "model_name": self.model_name,
            "device": str(getattr(self.device, "type", self.device)),
            "loaded": self.model_loaded,
            "num_labels": len(self.INTENT_LABELS),
            "max_length": self.max_length,
            "intents": self.INTENT_LABELS
        }


# Singleton instance (lazy loading)
_bert_classifier = None


def get_bert_classifier(
    model_name: str = None,
    force_reload: bool = False
) -> BERTIntentClassifier | None:
    """Get singleton BERT classifier instance

    Args:
        model_name: Model name (only used on first load)
        force_reload: Force re-initialization

    Returns:
        BERTIntentClassifier instance or None if not available
    """
    global _bert_classifier

    if not TRANSFORMERS_AVAILABLE:
        logger.warning("transformers not installed")
        return None

    if _bert_classifier is None or force_reload:
        try:
            _bert_classifier = BERTIntentClassifier(model_name=model_name)
            logger.info("BERT classifier initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize BERT classifier: {e}")
            _bert_classifier = None

    return _bert_classifier


async def classify_with_bert(
    message: str,
    context: str = ""
) -> dict | None:
    """Convenience function to classify with BERT

    Args:
        message: User message
        context: Optional context

    Returns:
        Classification result or None if BERT not available
    """
    classifier = get_bert_classifier()
    if classifier:
        return await classifier.classify(message, context)
    return None

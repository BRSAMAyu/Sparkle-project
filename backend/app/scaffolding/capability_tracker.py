"""Capability tracking for adaptive intervention scaffolding."""

from dataclasses import dataclass


@dataclass
class CapabilityTracker:
    """Simple capability tracker using an exponential moving average."""

    capability_level: float = 0.5
    learning_rate: float = 0.2

    def update(self, success: bool, weight: float = 1.0) -> float:
        target = 1.0 if success else 0.0
        lr = max(0.05, min(self.learning_rate * weight, 0.6))
        self.capability_level = (1 - lr) * self.capability_level + lr * target
        return self.capability_level

    def zone(self) -> str:
        if self.capability_level < 0.4:
            return "frustration"
        if self.capability_level > 0.7:
            return "boredom"
        return "flow"

"""Quick sanity checks for adaptive interventions."""

from app.scaffolding.capability_tracker import CapabilityTracker
from app.services.template_registry import TemplateRegistry


def main() -> None:
    tracker = CapabilityTracker()
    tracker.update(True)
    registry = TemplateRegistry()
    registry.load_templates()
    templates = registry.get_templates("recover_to_task", 4)
    assert templates, "missing recover_to_task templates"
    print("✅ adaptive intervention quick checks passed")


if __name__ == "__main__":
    main()

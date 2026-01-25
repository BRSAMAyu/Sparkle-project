from typing import Dict, Any

class MergeStrategy:
    """Strategy for merging UserScope and PlanScope"""
    
    @staticmethod
    def merge(user_scope: Dict[str, Any], plan_scope: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge scopes. Plan scope overrides user scope where appropriate.
        Returns a flattened dictionary for LLM context.
        """
        merged = {}
        
        # 1. Base user context
        merged.update(user_scope)
        
        # 2. Inject plan context under specific keys
        if plan_scope:
            merged["active_plan"] = plan_scope
            
            # 3. Merge facts/preferences if plan has specific overrides
            # (Simple implementation for now)
            if "facts" in plan_scope:
                # E.g. difficulty preference might be in facts
                pass
                
        return merged

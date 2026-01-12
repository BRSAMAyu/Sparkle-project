from typing import Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

# Input Schema
class LinkConceptInput(BaseModel):
    concept_name: str = Field(..., description="The name of the concept (e.g., 'Derivative').")
    subject: str = Field(..., description="The subject context (e.g., 'Calculus').")
    importance: str = Field(..., description="Importance level detected (High/Medium/Low).")
    source_file: str = Field(..., description="Originating file name.")

class GalaxyUpdateTool(BaseTool):
    name: str = "update_concept_metadata"
    description: str = "Updates the Knowledge Graph with exam metadata (importance, frequency) for a concept."
    args_schema: Type[BaseModel] = LinkConceptInput

    def _run(self, concept_name: str, subject: str, importance: str, source_file: str) -> str:
        # In a real implementation, this would call GalaxyService.
        # Example:
        # node = galaxy_service.find_node(name=concept_name, subject=subject)
        # if node:
        #     node.importance = importance
        #     node.references.append(source_file)
        #     node.save()
        # else:
        #     galaxy_service.create_node(...)
        
        print(f"DEBUG: Updating Galaxy -> Concept: {concept_name}, Importance: {importance}")
        return f"Successfully updated '{concept_name}' with importance '{importance}'."

    async def _arun(self, concept_name: str, subject: str, importance: str, source_file: str) -> str:
        # Async version
        return self._run(concept_name, subject, importance, source_file)

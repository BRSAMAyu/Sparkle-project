from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SectorEnum(str, Enum):
    COSMOS = "COSMOS"
    TECH = "TECH"
    ART = "ART"
    CIVILIZATION = "CIVILIZATION"
    LIFE = "LIFE"
    WISDOM = "WISDOM"
    VOID = "VOID"


class GalaxyNodeDTO(BaseModel):
    id: UUID
    parent_id: Optional[UUID]
    name: str
    importance: int
    sector: SectorEnum
    base_color: Optional[str] = None
    
    # User Status
    is_unlocked: bool
    mastery_score: int
    
    model_config = ConfigDict(from_attributes=True)


class GalaxyGraphResponse(BaseModel):
    nodes: List[GalaxyNodeDTO]
    user_flame_intensity: float  # 0.0 to 1.0 based on today's focus time

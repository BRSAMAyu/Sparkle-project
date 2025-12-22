
from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.services.omnibar_service import OmniBarService

router = APIRouter()

@router.post("/dispatch")
async def dispatch_omnibar(
    text: str = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Omni-Bar Dispatcher
    Analyzes input text and dispatches to appropriate service (Task, Capsule, or Chat).
    """
    service = OmniBarService(db)
    return await service.dispatch(user_id=current_user.id, text=text)

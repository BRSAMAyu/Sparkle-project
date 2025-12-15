from fastapi import APIRouter

router = APIRouter()

@router.post("/login")
async def login():
    return {"access_token": "fake-token", "token_type": "bearer"}

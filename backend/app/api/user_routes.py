from dataclasses import asdict

from fastapi import APIRouter

from app.memory.user_memory import UserMemory

router = APIRouter(prefix="/api/user", tags=["user"])


@router.get("/profile")
async def get_profile() -> dict:
    memory = UserMemory()
    return {
        "current_user": asdict(memory.get_current_user()),
        "team_rules": memory.get_team_rules(),
    }

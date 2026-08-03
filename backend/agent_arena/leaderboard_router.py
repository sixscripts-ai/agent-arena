from fastapi import APIRouter, Depends

from . import db, leaderboard
from .auth import get_current_user

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("")
def get_leaderboard(format: str = "overall", _user_id: str = Depends(get_current_user)):
    return leaderboard.get_rankings(db.get_databases(), db.get_database_id(), format)

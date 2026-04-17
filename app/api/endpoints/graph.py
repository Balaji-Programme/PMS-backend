from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.services.graph_service import search_azure_users
from app.core.security import allow_team_lead_plus
from app.core.database import get_sync_db

router = APIRouter()

@router.get(
    "/search-users",
    response_model=List[Dict[str, Any]],
    dependencies=[Depends(allow_team_lead_plus)],
)
def search_users(
    q: str = Query(..., min_length=2, description="Search Entra ID by displayName or mail"),
    db: Session = Depends(get_sync_db),
):

    try:
        return search_azure_users(q, db=db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

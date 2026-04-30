from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_sync_db
from app.core.security import allow_authenticated
from app.schemas.team import TeamCreate, TeamResponse, TeamUpdate, TeamWithMembersResponse
from app.services import team_service

router = APIRouter(dependencies=[Depends(allow_authenticated)])

@router.post("/", response_model=TeamResponse)
def create_team(team: TeamCreate, db: Session = Depends(get_sync_db), current_user = Depends(allow_authenticated)):
    return team_service.create_team(db=db, team=team, actor_id=current_user.o365_id or str(current_user.id))

@router.get("/", response_model=List[TeamResponse])
def read_teams(skip: int = 0, limit: int = 100, db: Session = Depends(get_sync_db)):
    return team_service.get_teams(db, skip=skip, limit=limit)

@router.get("/search", response_model=List[TeamResponse])
def search_teams(q: str = Query("", min_length=0), limit: int = 20, db: Session = Depends(get_sync_db)):
    return team_service.search_teams(db, query=q, limit=limit)

@router.get("/{team_id}", response_model=TeamWithMembersResponse)
def read_team(team_id: int, db: Session = Depends(get_sync_db)):
    db_team = team_service.get_team_with_members(db, team_id=team_id)
    if db_team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return db_team

@router.put("/{team_id}", response_model=TeamResponse)
def update_team(team_id: int, team_update: TeamUpdate, db: Session = Depends(get_sync_db), current_user = Depends(allow_authenticated)):
    db_team = team_service.update_team(db, team_id=team_id, team_update=team_update, actor_id=current_user.o365_id or str(current_user.id))
    if db_team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return db_team

@router.delete("/{team_id}", status_code=204)
def delete_team(team_id: int, db: Session = Depends(get_sync_db), current_user = Depends(allow_authenticated)):
    success = team_service.delete_team(db, team_id=team_id, actor_id=current_user.o365_id or str(current_user.id))
    if not success:
        raise HTTPException(status_code=404, detail="Team not found")

@router.post("/{team_id}/members/{user_email}")
def add_team_member(team_id: int, user_email: str, db: Session = Depends(get_sync_db), current_user = Depends(allow_authenticated)):
    success = team_service.add_team_member(db, team_id=team_id, user_email=user_email, actor_id=current_user.o365_id or str(current_user.id))
    if not success:
        raise HTTPException(status_code=400, detail="Could not add user to team. Check if user and team exist.")
    return {"message": "Member added successfully"}

@router.delete("/{team_id}/members/{user_email}")
def remove_team_member(team_id: int, user_email: str, db: Session = Depends(get_sync_db), current_user = Depends(allow_authenticated)):
    success = team_service.remove_team_member(db, team_id=team_id, user_email=user_email, actor_id=current_user.o365_id or str(current_user.id))
    if not success:
        raise HTTPException(status_code=400, detail="Could not remove user from team. Check if user is in team.")
    return {"message": "Member removed successfully"}

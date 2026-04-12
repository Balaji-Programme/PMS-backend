import os
import shutil
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_current_user, allow_authenticated
from app.models.user import User
from app.schemas.document import DocumentCreate, DocumentUpdate, DocumentResponse
from app.services import document_service
from app.core.config import settings

router = APIRouter(dependencies=[Depends(allow_authenticated)])

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

@router.post("/", response_model=DocumentResponse)
def create_document(
    document: DocumentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return document_service.create_document(
        db=db,
        document=document,
        uploaded_by_email=current_user.email,
        actor_id=current_user.o365_id or str(current_user.id)
    )

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    project_id: int = Form(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(file_path)

    document_data = DocumentCreate(
        title=title or file.filename,
        description=description,
        file_url=f"/{UPLOAD_DIR}/{unique_filename}",
        file_type=file.content_type,
        file_size=file_size,
        project_id=project_id
    )

    return document_service.create_document(
        db=db,
        document=document_data,
        uploaded_by_email=current_user.email,
        actor_id=current_user.o365_id or str(current_user.id)
    )

@router.get("/", response_model=List[DocumentResponse])
def read_documents(
    skip: int = 0,
    limit: int = 100,
    project_id: Optional[int] = Query(None),
    file_type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    return document_service.get_documents(
        db,
        skip=skip,
        limit=limit,
        project_id=project_id,
        file_type=file_type
    )

@router.get("/{document_id}", response_model=DocumentResponse)
def read_document(document_id: int, db: Session = Depends(get_db)):
    db_document = document_service.get_document(db, document_id=document_id)
    if db_document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return db_document

@router.put("/{document_id}", response_model=DocumentResponse, dependencies=[Depends(allow_authenticated)])
def update_document(document_id: int, document: DocumentUpdate, db: Session = Depends(get_db), current_user = Depends(allow_authenticated)):
    db_document = document_service.update_document(db, document_id=document_id, document_update=document, actor_id=current_user.o365_id or str(current_user.id))
    if db_document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return db_document

@router.delete("/{document_id}", dependencies=[Depends(allow_authenticated)])
def delete_document(document_id: int, db: Session = Depends(get_db), current_user = Depends(allow_authenticated)):
    success = document_service.delete_document(db, document_id=document_id, actor_id=current_user.o365_id or str(current_user.id))
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "Document deleted successfully"}

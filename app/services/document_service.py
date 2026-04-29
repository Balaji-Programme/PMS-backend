from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from app.models.document import Document
from app.schemas.document import DocumentCreate, DocumentUpdate
from app.utils.ids import generate_public_id
from app.utils.audit_utils import write_audit, capture_audit_details

def get_document(db: Session, document_id: int):
    return db.query(Document).options(
        joinedload(Document.uploaded_by)
    ).filter(Document.id == document_id).first()

def get_documents(db: Session, skip: int = 0, limit: int = 100, project_id: Optional[int] = None, file_type: Optional[str] = None):
    query = db.query(Document).options(
        joinedload(Document.uploaded_by)
    )
    if project_id is not None:
        query = query.filter(Document.project_id == project_id)
        query = query.filter(~Document.issues.any())
    if file_type:
        query = query.filter(Document.file_type.ilike(f"%{file_type}%"))
    return query.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()

def create_document(db: Session, document: DocumentCreate, uploaded_by_email: Optional[str] = None, actor_id: Optional[str] = None):
    public_id = generate_public_id("DOC-")
    db_document = Document(
        public_id=public_id,
        title=document.title,
        description=document.description,
        file_url=document.file_url,
        file_type=document.file_type,
        file_size=document.file_size,
        project_id=document.project_id,
        uploaded_by_email=uploaded_by_email
    )
    db.add(db_document)
    db.flush()

    write_audit(db, actor_id, "CREATE", "documents",
                resource_id=document.project_id or db_document.id,
                record_id=db_document.id,
                details=[{"field_name": "title", "old_value": None, "new_value": document.title}])

    db.commit()
    db.refresh(db_document)
    return get_document(db, db_document.id)

def update_document(db: Session, document_id: int, document_update: DocumentUpdate, actor_id: Optional[str] = None):
    db_document = db.query(Document).filter(Document.id == document_id).first()
    if not db_document:
        return None

    update_data = document_update.model_dump(exclude_unset=True)
    changes = capture_audit_details(db_document, update_data)

    for key, value in update_data.items():
        setattr(db_document, key, value)

    write_audit(db, actor_id, "UPDATE", "documents",
                resource_id=db_document.project_id or document_id,
                record_id=document_id,
                details=changes)

    db.commit()
    db.refresh(db_document)
    return get_document(db, db_document.id)

def delete_document(db: Session, document_id: int, actor_id: Optional[str] = None):
    db_document = db.query(Document).filter(Document.id == document_id).first()
    if db_document:
        write_audit(db, actor_id, "DELETE", "documents",
                    resource_id=db_document.project_id or document_id,
                    record_id=document_id,
                    details=[{"field_name": "title", "old_value": db_document.title, "new_value": None}])
        db.delete(db_document)
        db.commit()
        return True
    return False

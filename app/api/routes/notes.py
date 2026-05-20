from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.api.schemas import NoteCreateRequest, NoteResponse
from app.db.models import Note, User

router = APIRouter(prefix="/notes", tags=["notes"])

@router.post("", response_model=NoteResponse, status_code=201)
def create_note(
    data: NoteCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = Note(user_id=current_user.id, title=data.title, body=data.body)
    db.add(note)
    db.commit()
    db.refresh(note)

    return NoteResponse(
        id=str(note.id),
        title=note.title,
        body=note.body,
        created_at=note.created_at.isoformat(),
    )

@router.get("", response_model=list[NoteResponse])
def list_notes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notes = (
        db.query(Note)
        .filter(Note.user_id == current_user.id)
        .order_by(Note.created_at.desc())
        .all()
    )

    return [
        NoteResponse(
            id=str(n.id),
            title=n.title,
            body=n.body,
            created_at=n.created_at.isoformat(),
        )
        for n in notes
    ]

@router.get("/{note_id}", response_model=NoteResponse)
def get_note(
    note_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = (
        db.query(Note)
        .filter(Note.id == note_id, Note.user_id == current_user.id)
        .first()
    )
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    return NoteResponse(
        id=str(note.id),
        title=note.title,
        body=note.body,
        created_at=note.created_at.isoformat(),
    )

@router.delete("/{note_id}", status_code=204)
def delete_note(
    note_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = (
        db.query(Note)
        .filter(Note.id == note_id, Note.user_id == current_user.id)
        .first()
    )
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    db.delete(note)
    db.commit()
    return None

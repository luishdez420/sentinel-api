from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.api.schemas import (
    DeleteEnvelope,
    DeleteResponse,
    ErrorEnvelope,
    NoteCreateRequest,
    NoteEnvelope,
    NoteResponse,
    NotesPageEnvelope,
    PageMeta,
)
from app.core.audit import write_audit_log
from app.db.models import Note, User

router = APIRouter(prefix="/notes", tags=["notes"])

ERROR_RESPONSES = {
    401: {"model": ErrorEnvelope},
    404: {"model": ErrorEnvelope},
    422: {"model": ErrorEnvelope},
    429: {"model": ErrorEnvelope},
}


def _note_response(note: Note) -> NoteResponse:
    return NoteResponse(
        id=str(note.id),
        title=note.title,
        body=note.body,
        created_at=note.created_at.isoformat(),
    )


@router.post(
    "",
    response_model=NoteEnvelope,
    status_code=201,
    responses={**ERROR_RESPONSES, 200: {"model": NoteEnvelope}},
)
def create_note(
    request: Request,
    response: Response,
    data: NoteCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        max_length=128,
        description="Optional key that makes note creation safe to retry.",
    ),
):
    if idempotency_key:
        existing_note = (
            db.query(Note)
            .filter(
                Note.user_id == current_user.id,
                Note.idempotency_key == idempotency_key,
            )
            .first()
        )
        if existing_note:
            response.status_code = 200
            return NoteEnvelope(data=_note_response(existing_note))

    note = Note(
        user_id=current_user.id,
        title=data.title,
        body=data.body,
        idempotency_key=idempotency_key,
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    write_audit_log(
        db,
        event_type="note_created",
        user_id=current_user.id,
        resource_type="note",
        resource_id=note.id,
        request=request,
        metadata={"auth_method": getattr(request.state, "auth_method", "unknown")},
    )

    return NoteEnvelope(data=_note_response(note))


@router.get("", response_model=NotesPageEnvelope, responses=ERROR_RESPONSES)
def list_notes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    query = db.query(Note).filter(Note.user_id == current_user.id)
    total = query.count()
    notes = query.order_by(Note.created_at.desc()).offset(offset).limit(limit).all()
    next_offset = offset + limit if offset + limit < total else None

    return NotesPageEnvelope(
        data=[_note_response(n) for n in notes],
        meta=PageMeta(
            limit=limit,
            offset=offset,
            total=total,
            next_offset=next_offset,
        ),
    )


@router.get("/{note_id}", response_model=NoteEnvelope, responses=ERROR_RESPONSES)
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

    return NoteEnvelope(data=_note_response(note))


@router.delete(
    "/{note_id}",
    response_model=DeleteEnvelope,
    responses=ERROR_RESPONSES,
)
def delete_note(
    note_id: str,
    request: Request,
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
    write_audit_log(
        db,
        event_type="note_deleted",
        user_id=current_user.id,
        resource_type="note",
        resource_id=note_id,
        request=request,
        metadata={"auth_method": getattr(request.state, "auth_method", "unknown")},
    )
    return DeleteEnvelope(data=DeleteResponse(id=note_id))

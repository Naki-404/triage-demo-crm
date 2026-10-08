from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import require_roles
from ..db import get_db
from ..models import User, UserRole
from ..schemas import NoteCreate, NoteOut
from ..services import notes as notes_service
from ..services.notes import NotesError

router = APIRouter(tags=["notes"])


def _note_out(note) -> NoteOut:
    return NoteOut(
        id=note.id,
        client_id=note.client_id,
        author_id=note.author_id,
        body=notes_service.note_body_for_response(note.body),
        created_at=note.created_at,
    )


@router.get("/api/customers/{client_id}/notes", response_model=list[NoteOut])
def list_notes(
    client_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.admin, UserRole.manager, UserRole.viewer)),
):
    try:
        rows = notes_service.list_notes(db, client_id, user)
    except NotesError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return [_note_out(n) for n in rows]


@router.post("/api/customers/{client_id}/notes", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
def create_note(
    client_id: int,
    payload: NoteCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.admin, UserRole.manager)),
):
    try:
        note = notes_service.create_note(db, client_id, user, payload.body)
    except NotesError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return _note_out(note)

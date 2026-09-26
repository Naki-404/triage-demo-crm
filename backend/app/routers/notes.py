from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import require_roles
from ..db import get_db
from ..models import Client, ClientNote, User, UserRole
from ..schemas import NoteCreate, NoteOut
from ..services.deps import DependencyError, post_note_remote

router = APIRouter(tags=["notes"])


@router.get("/api/customers/{client_id}/notes", response_model=list[NoteOut])
def list_notes(
    client_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.admin, UserRole.manager, UserRole.viewer)),
):
    if db.get(Client, client_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    notes = db.query(ClientNote).filter(ClientNote.client_id == client_id).order_by(ClientNote.id.desc()).all()
    return [NoteOut.model_validate(n) for n in notes]


@router.post("/api/customers/{client_id}/notes", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
def create_note(
    client_id: int,
    payload: NoteCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.admin, UserRole.manager)),
):
    if db.get(Client, client_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    try:
        post_note_remote(client_id, payload.body)
    except DependencyError as err:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(err)) from err
    note = ClientNote(client_id=client_id, author_id=user.id, body=payload.body)
    db.add(note)
    db.commit()
    db.refresh(note)
    return NoteOut.model_validate(note)

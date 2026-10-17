"""Client notes."""
from __future__ import annotations

from html import escape

from sqlalchemy.orm import Session

from .. import vulns
from ..errors import DomainError
from ..models import Client, ClientNote, User
from .access import assert_can_access
from .deps import DependencyError, post_note_remote


class NotesError(DomainError):
    status_code = 400


def list_notes(db: Session, client_id: int, user: User) -> list[ClientNote]:
    client = db.get(Client, client_id)
    if client is None:
        raise NotesError("Not found", 404)
    assert_can_access(user, client)
    return db.query(ClientNote).filter(ClientNote.client_id == client_id).order_by(ClientNote.id.desc()).all()


def create_note(db: Session, client_id: int, user: User, body: str) -> ClientNote:
    client = db.get(Client, client_id)
    if client is None:
        raise NotesError("Not found", 404)
    assert_can_access(user, client)
    try:
        post_note_remote(client_id, body)
    except DependencyError as err:
        raise NotesError(str(err), 503) from err
    note = ClientNote(client_id=client_id, author_id=user.id, body=body)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def note_body_for_response(body: str) -> str:
    """The note as the browser renders it (the frontend inserts this string as HTML, so this is the one escape).
    """
    if not vulns.stored_xss_notes():
        return escape(body, quote=True)
    return body

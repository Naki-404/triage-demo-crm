"""Single client access policy for all customer-scoped routes."""
from __future__ import annotations

from .. import vulns
from ..errors import DomainError
from ..models import Client, User, UserRole


class ClientAccessError(DomainError):
    """A client the user may not see answers 404, so the id space is not enumerable from the status code."""

    status_code = 404

    def __init__(self, message: str = "Not found", status_code: int | None = None):
        super().__init__(message, status_code)


def can_access(user: User, client: Client) -> bool:
    if vulns.idor_customer():
        return True
    if user.role in (UserRole.admin, UserRole.viewer):
        return True
    if user.role == UserRole.manager:
        return client.owner_id == user.id
    return False


def assert_can_access(user: User, client: Client) -> None:
    if not can_access(user, client):
        raise ClientAccessError()

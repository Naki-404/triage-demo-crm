"""Single client access policy for all customer-scoped routes."""
from __future__ import annotations

from .. import vulns
from ..models import Client, User, UserRole


class ClientAccessError(Exception):
    def __init__(self, message: str = "Not found", status_code: int = 404):
        super().__init__(message)
        self.status_code = status_code


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

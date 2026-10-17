import httpx

from .. import faults
from ..config import settings
from ..errors import DomainError


class DependencyError(DomainError):
    status_code = 503


def check_tax_status(iin: str) -> dict:
    if faults.tax_times_out():
        raise DependencyError("tax service timed out")
    try:
        with httpx.Client(timeout=settings.TAX_TIMEOUT_SECONDS) as client:
            res = client.get(settings.TAX_SERVICE_URL, params={"iin": iin})
            res.raise_for_status()
            return res.json()
    except httpx.TimeoutException as err:
        raise DependencyError("tax service timed out") from err
    except Exception as err:
        # the cause (URL with ?iin=, exception text) goes to Sentry via the chained exception, not to the client
        raise DependencyError("tax service unavailable") from err


def post_note_remote(client_id: int, body: str) -> dict | None:
    """Forward note to external notes service.

    In clean mode a missing upstream is soft-failed (local note still saved).
    In experiment mode connection failures surface as DependencyError.
    """
    if faults.notes_unavailable():
        raise DependencyError("notes service unavailable")
    try:
        with httpx.Client(timeout=3.0) as client:
            res = client.post(settings.NOTES_SERVICE_URL, json={"client_id": client_id, "body": body})
            res.raise_for_status()
            return res.json()
    except Exception as err:
        if settings.is_experiment:
            raise DependencyError(f"notes service unavailable: {err}") from err
        return None

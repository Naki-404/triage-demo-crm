from fastapi import APIRouter, Depends, HTTPException, status

from .. import faults
from ..auth import require_roles
from ..config import settings
from ..models import User, UserRole
from ..schemas import StandPatch

router = APIRouter(prefix="/api/stand", tags=["stand"])

_FAULT_KEYS = (
    "FAULT_IIN_SECOND_WEIGHTS",
    "FAULT_NAME_SEARCH_RAW_SQL",
    "FAULT_EXPORT_EMPTY_FIELD",
    "FAULT_CORRUPT_RECORD",
    "FAULT_TAX_TIMEOUT",
    "FAULT_NOTES_DOWN",
    "FAULT_POOL_EXHAUSTED",
)


@router.get("")
def get_stand(_: User = Depends(require_roles(UserRole.admin, UserRole.manager, UserRole.viewer))):
    return faults.snapshot()


@router.patch("")
def patch_stand(
    payload: StandPatch,
    _: User = Depends(require_roles(UserRole.admin)),
):
    data = payload.model_dump(exclude_unset=True)
    if "crm_mode" in data and data["crm_mode"] not in ("clean", "experiment"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="crm_mode must be clean or experiment")
    entering_experiment = data.get("crm_mode") == "experiment"
    if not settings.is_experiment and not entering_experiment:
        if any(k.startswith("FAULT_") for k in data):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Stand switches require CRM_MODE=experiment",
            )
    for key, value in data.items():
        if key == "crm_mode":
            settings.CRM_MODE = value
        elif hasattr(settings, key) and value is not None:
            setattr(settings, key, value)
    if not settings.is_experiment:
        for key in _FAULT_KEYS:
            setattr(settings, key, False)
    return faults.snapshot()

from fastapi import APIRouter, Depends, HTTPException, status

from .. import faults, vulns
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
    "FAULT_PAYMENT_WEBHOOK",
    "FAULT_DISCOUNT_STACK",
    "FAULT_DUPLICATE_ENROLLMENT",
    "FAULT_INSTALLMENT_ROUNDING",
    "FAULT_EXPORT_NO_CONTRACT",
)


@router.get("")
def get_stand(_: User = Depends(require_roles(UserRole.admin, UserRole.manager, UserRole.viewer))):
    return {**faults.snapshot(), **{k: vulns.active(k) for k in vulns.all_keys()}}


@router.patch("")
def patch_stand(
    payload: StandPatch,
    _: User = Depends(require_roles(UserRole.admin)),
):
    data = payload.model_dump(exclude_unset=True)
    if "crm_mode" in data and data["crm_mode"] not in ("clean", "experiment", "vuln"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="crm_mode must be clean, experiment or vuln")
    entering_experiment = data.get("crm_mode") == "experiment"
    entering_vuln = data.get("crm_mode") == "vuln"
    if not settings.is_experiment and not entering_experiment:
        if any(k.startswith("FAULT_") for k in data):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="FAULT_* require CRM_MODE=experiment")
    if not settings.is_vuln and not entering_vuln:
        if any(k.startswith("VULN_") for k in data):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="VULN_* require CRM_MODE=vuln")
    for key, value in data.items():
        if key == "crm_mode":
            settings.CRM_MODE = value
        elif hasattr(settings, key) and value is not None:
            setattr(settings, key, value)
    if not settings.is_experiment:
        for key in _FAULT_KEYS:
            setattr(settings, key, False)
    if not settings.is_vuln:
        for key in vulns.all_keys():
            setattr(settings, key, False)
    return {**faults.snapshot(), **{k: vulns.active(k) for k in vulns.all_keys()}}

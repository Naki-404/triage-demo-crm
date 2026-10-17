from fastapi import APIRouter, Depends, HTTPException, status

from .. import faults, vulns
from ..auth import require_roles
from ..config import settings
from ..models import User, UserRole
from ..schemas import StandPatch

router = APIRouter(prefix="/api/stand", tags=["stand"])


def _ensure_stand_control() -> None:
    if settings.is_production or not settings.STAND_CONTROL_ENABLED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Stand control is disabled")


@router.get("")
def get_stand(_: User = Depends(require_roles(UserRole.admin))):
    return {**faults.snapshot(), **{k: vulns.active(k) for k in vulns.all_keys()}}


@router.patch("")
def patch_stand(
    payload: StandPatch,
    _: User = Depends(require_roles(UserRole.admin)),
):
    """Replace the stand state: every flag not named in the request is switched off."""
    _ensure_stand_control()
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
    if "crm_mode" in data:
        settings.CRM_MODE = data["crm_mode"]
    # flags do not accumulate across scenarios: the request describes the whole stand
    for key in (*faults.FAULT_KEYS, *vulns.all_keys()):
        setattr(settings, key, bool(data.get(key, False)))
    if not settings.is_experiment:
        for key in faults.FAULT_KEYS:
            setattr(settings, key, False)
    if not settings.is_vuln:
        for key in vulns.all_keys():
            setattr(settings, key, False)
    return {**faults.snapshot(), **{k: vulns.active(k) for k in vulns.all_keys()}}

from fastapi import APIRouter, Depends, HTTPException, Request, status

from .. import faults, vulns
from ..auth import require_roles
from ..config import settings
from ..models import User, UserRole
from ..schemas import CustomLogIn, SimulateIn, StandPatch
from ..simulate import list_scenarios, run_simulation, ship_custom_log

router = APIRouter(prefix="/api/stand", tags=["stand"])


def _ensure_stand_control() -> None:
    if settings.is_production or not settings.STAND_CONTROL_ENABLED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Stand control is disabled")


@router.get("")
def get_stand(_: User = Depends(require_roles(UserRole.admin))):
    return {**faults.snapshot(), **{k: vulns.active(k) for k in vulns.all_keys()}}


@router.get("/simulate")
def get_simulate_catalog(_: User = Depends(require_roles(UserRole.admin))):
    """Attack-log scenarios available on the stand UI (admin only)."""
    _ensure_stand_control()
    return {"scenarios": list_scenarios()}


@router.post("/simulate")
def post_simulate(
    payload: SimulateIn,
    request: Request,
    user: User = Depends(require_roles(UserRole.admin)),
):
    """Inject ECS / Sentry events that look like a chosen attack pattern (lab only)."""
    _ensure_stand_control()
    try:
        return run_simulation(
            payload.scenario,
            count=payload.count,
            request=request,
            actor=user.username,
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"unknown scenario: {payload.scenario}",
        ) from None


@router.post("/simulate/custom")
def post_simulate_custom(
    payload: CustomLogIn,
    request: Request,
    user: User = Depends(require_roles(UserRole.admin)),
):
    """Inject a free-form ECS / Sentry log typed on the stand UI (lab only)."""
    _ensure_stand_control()
    try:
        return ship_custom_log(
            message=payload.message,
            request=request,
            actor=user.username,
            level=payload.level,
            method=payload.method,
            path=payload.path,
            status_code=payload.status_code,
            action=payload.action,
            attack=payload.attack,
            client_ip=payload.client_ip,
            user_id=payload.user_id,
            query=payload.query,
            body=payload.body,
            user_agent=payload.user_agent,
            count=payload.count,
            extra=payload.extra,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from None


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

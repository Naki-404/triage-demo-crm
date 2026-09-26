"""CLI for Qazaq CRM simulator.

  python -m simulator run all --target http://127.0.0.1:9000 --i-own-this-target
  python -m simulator run bug --seed 2000001 --journal runs/out.jsonl
  python -m simulator generate invariance_wrong_password --seed 2000100
"""
from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

from .client import CrmClient
from .journal import Journal
from .safety import TargetNotAllowedError, assert_target_allowed
from .scenarios import GENERATORS, GROUPS, SCENARIOS
from .scenarios.base import ScenarioContext
from .seeds import clamp_seed


def _band_for_set(set_name: str) -> str:
    if set_name == "train":
        return "train"
    if set_name in ("injection",) or set_name.startswith("injection"):
        return "injection"
    return "test"


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--target", default="http://127.0.0.1:9000")
    common.add_argument("--i-own-this-target", action="store_true")
    common.add_argument("--journal", type=Path, default=None)
    common.add_argument("--rate-ms", type=float, default=50.0)
    common.add_argument("--user", default="manager")
    common.add_argument("--password", default="Manager-2026!")
    common.add_argument("--admin-user", default="admin")
    common.add_argument("--admin-password", default="Admin-2026!")

    p = argparse.ArgumentParser(prog="simulator", description="Safe load / attack simulator for Qazaq CRM")
    sub = p.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", parents=[common], help="Run named scenario(s) or a group")
    run.add_argument("name")
    run.add_argument("--count", type=int, default=1)
    run.add_argument("--seed", type=int, default=2_000_001)
    run.add_argument("--set", dest="set_name", default="main", choices=["main", "invariance", "contrast", "injection", "train"])
    run.add_argument("--with-background", action="store_true")

    gen = sub.add_parser("generate", parents=[common], help="Run invariance/contrast generator")
    gen.add_argument("name", choices=list(GENERATORS))
    gen.add_argument("--seed", type=int, default=2_000_100)
    gen.add_argument("--set", dest="set_name", default="invariance", choices=["invariance", "contrast", "main", "train"])

    sub.add_parser("list", help="List scenarios and generators")
    return p


def _resolve_names(name: str) -> list[str]:
    chunks = [p.strip() for p in name.split(",") if p.strip()] if "," in name else [name]
    names: list[str] = []
    for chunk in chunks:
        if chunk in GROUPS:
            names.extend(GROUPS[chunk])
        elif chunk in SCENARIOS:
            names.append(chunk)
        else:
            raise SystemExit(f"Unknown scenario/group: {chunk}. Try: {', '.join(GROUPS)}")
    return names


def _make_client(args: argparse.Namespace) -> CrmClient:
    return CrmClient(
        args.target,
        username=args.user,
        password=args.password,
        admin_username=args.admin_user,
        admin_password=args.admin_password,
        min_interval_ms=args.rate_ms,
    )


def cmd_list() -> int:
    print("Scenarios:")
    for g, names in GROUPS.items():
        if g == "all":
            continue
        print(f"  [{g}]")
        for n in names:
            print(f"    {n}")
    print("Generators:")
    for n in GENERATORS:
        print(f"  {n}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    assert_target_allowed(args.target, i_own_this_target=args.i_own_this_target)
    names = _resolve_names(args.name)
    journal = Journal(args.journal)
    client = _make_client(args)
    try:
        for i in range(args.count):
            for name in names:
                if args.with_background:
                    bg_seed = clamp_seed(args.seed + i * 100 + 7, band="train")
                    bg_ctx = ScenarioContext(
                        client=client,
                        journal=journal,
                        seed=bg_seed,
                        set_name="train",
                        target=args.target,
                    )
                    SCENARIOS["background_manager"](bg_ctx, request_id=uuid.uuid4().hex)
                band = _band_for_set(args.set_name)
                seed = clamp_seed(args.seed + i, band=band)
                ctx = ScenarioContext(
                    client=client,
                    journal=journal,
                    seed=seed,
                    set_name=args.set_name,
                    target=args.target,
                )
                event = SCENARIOS[name](ctx)
                print(f"{event.scenario}: label={event.label} HTTP {event.http_status} rid={event.request_id} seed={event.seed}")
    finally:
        client.close()
        journal.close()
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    assert_target_allowed(args.target, i_own_this_target=args.i_own_this_target)
    journal = Journal(args.journal)
    client = _make_client(args)
    band = _band_for_set(args.set_name)
    seed = clamp_seed(args.seed, band=band)
    ctx = ScenarioContext(client=client, journal=journal, seed=seed, set_name=args.set_name, target=args.target)
    try:
        result = GENERATORS[args.name](ctx)
        events = result if isinstance(result, list) else [result]
        for event in events:
            print(f"{event.scenario}: label={event.label} HTTP {event.http_status} rid={event.request_id} set={event.set}")
    finally:
        client.close()
        journal.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.cmd == "list":
            return cmd_list()
        if args.cmd == "run":
            return cmd_run(args)
        if args.cmd == "generate":
            return cmd_generate(args)
    except TargetNotAllowedError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

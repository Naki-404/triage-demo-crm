from . import background, bug, data_infra, expected, generators, injection, security

SCENARIOS = {}
SCENARIOS.update(bug.SCENARIOS)
SCENARIOS.update(expected.SCENARIOS)
SCENARIOS.update(data_infra.SCENARIOS)
SCENARIOS.update(security.SCENARIOS)
SCENARIOS.update(injection.SCENARIOS)
SCENARIOS.update(background.SCENARIOS)

GENERATORS = dict(generators.GENERATORS)

GROUPS = {
    "bug": list(bug.SCENARIOS),
    "expected": list(expected.SCENARIOS),
    "data_infra": list(data_infra.SCENARIOS),
    "security": list(security.SCENARIOS),
    "injection": list(injection.SCENARIOS),
    "background": list(background.SCENARIOS),
    "all": list(SCENARIOS),
}

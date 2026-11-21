"""Project combination assignments against the R03 model catalog."""

import json
from importlib.resources import files


ASSIGNED_DESIGN = "ASSIGNED_DESIGN"
COLUMN_AXIAL_ID = "4.3"
_PROFILE = json.loads(files("tbdy_next").joinpath("config", "design_combination_groups.json").read_bytes())
# Checks invoked by the complete column slice in addition to the PMM force request.
_COLUMN_CHECKS = {"3.2", "4.3", "4.4", "4.7", "4.8", "6.2", "6.3"}


def design_assignments(setup: dict) -> dict:
    audited = {row["combination"]: row for row in setup.get("combination_audit", ())}
    catalog = set(setup.get("defined_combination_names", ())) if setup.get("definition_coverage_known") else set()
    defaults = {"upper": {}, "lower": {}}
    check_groups = {}
    for group in _PROFILE["groups"]:
        group_id = group["id"]
        family = _PROFILE["families"][group["family"]]
        selected = sorted(name for name in catalog.intersection(family["names"])
                          if audited.get(name, {}).get("operator") == "Linear Add"
                          and bool(audited[name]["spectral_case_references"]) == family["spectrum"])
        for scope in group["scopes"]:
            defaults[scope][group_id] = selected
        for check in group["checks"]:
            check_groups.setdefault(check, []).append(group_id)
    envelopes = sorted(name for name in catalog if audited.get(name, {}).get("operator") == "Envelope")
    routed = {name for scope in defaults.values() for names in scope.values() for name in names}
    return {
        "profile": _PROFILE["id"], "defaults": defaults, "check_groups": check_groups,
        "groups": [{k: group[k] for k in ("id", "title", "scopes")} for group in _PROFILE["groups"]],
        "envelopes": envelopes, "unassigned_combinations": sorted(catalog - routed - set(envelopes)),
    }


def bind_assigned_combinations(project: dict, *, check: str, offered: object, catalog: list[str]) -> dict:
    """Validate browser assignments against the report and freeze the exact lists."""
    groups = project["check_groups"].get(check, [])
    if not groups or not isinstance(offered, dict) or set(offered) != set(groups):
        raise ValueError("Select the design groups assigned to this check.")
    known = set(catalog)
    for group in groups:
        names = offered[group]
        if (not isinstance(names, list) or any(not isinstance(name, str) or name not in known for name in names)
                or len(set(names)) != len(names)):
            raise ValueError("A design assignment contains invalid or missing ETABS combinations.")
    return {"profile": project["profile"], "scope": "upper",
            "groups": {group: sorted(offered[group]) for group in groups}}


def project_role_catalog(setup, *, scope):
    """Resolve the configured project roles against complete native families."""
    defaults = design_assignments(setup)["defaults"].get(scope, {})
    active = [group for group in _PROFILE["groups"] if group["checks"] and scope in group["scopes"]]
    complete = {}
    for group in active:
        name = group["id"]
        expected = sorted(_PROFILE["families"][group["family"]]["names"])
        if defaults.get(name) == expected:
            complete[name] = expected
    return {
        "profile": _PROFILE["id"],
        "scope": scope,
        "available_groups": complete,
        "incomplete_families": sorted(group["id"] for group in active if group["id"] not in complete),
        "column_slice_families": sorted(group["id"] for group in active if _COLUMN_CHECKS.intersection(group["checks"])),
        "active_families": sorted(group["id"] for group in active),
    }

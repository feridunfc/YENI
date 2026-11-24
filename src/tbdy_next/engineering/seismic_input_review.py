"""TBDY project-input cross-checks and acknowledgement of an exact source and profile."""
from __future__ import annotations

from hashlib import sha256
import json
from math import fsum, isclose, isfinite
import re

# Tables 2.1 and 2.2. ZF requires a site-specific analysis.
_SITE_FACTORS = {
    "Fs": ((0.25, 0.50, 0.75, 1.00, 1.25, 1.50),
           {"ZA": (0.8,) * 6, "ZB": (0.9,) * 6, "ZC": (1.3, 1.3, 1.2, 1.2, 1.2, 1.2),
            "ZD": (1.6, 1.4, 1.2, 1.1, 1.0, 1.0), "ZE": (2.4, 1.7, 1.3, 1.1, 0.9, 0.8)}),
    "F1": ((0.10, 0.20, 0.30, 0.40, 0.50, 0.60),
           {"ZA": (0.8,) * 6, "ZB": (0.8,) * 6, "ZC": (1.5, 1.5, 1.5, 1.5, 1.5, 1.4),
            "ZD": (2.4, 2.2, 2.0, 1.9, 1.8, 1.7), "ZE": (4.2, 3.3, 2.8, 2.4, 2.2, 2.0)}),
}


def physical_height(stories):
    """Only a contiguous, fully identified stack can supply a geometric HN default."""
    try:
        intervals = sorted((float(r["lower_elevation_m"]), float(r["upper_elevation_m"]),
                            float(r["height_m"]), r["story"]) for r in stories)
    except (ValueError, TypeError, KeyError):
        return None
    if not intervals or len({r[3] for r in intervals}) != len(intervals):
        return None
    for i, (lo, hi, height, name) in enumerate(intervals):
        if (not name or not all(isfinite(v) for v in (lo, hi, height)) or height <= 0 or hi <= lo
                or not isclose(hi - lo, height, rel_tol=0, abs_tol=1e-6)
                or (i and not isclose(lo, intervals[i - 1][1], rel_tol=0, abs_tol=1e-6))):
            return None
    total = fsum(r[2] for r in intervals)
    if not isclose(total, intervals[-1][1] - intervals[0][0], rel_tol=0, abs_tol=1e-6):
        return None
    return {"lowest_m": intervals[0][0], "roof_m": intervals[-1][1], "total_m": total,
            "storeys": [{"storey": name, "height_m": height} for _, _, height, name in intervals]}


def _site_factor(key, site, acceleration):
    grid, classes = _SITE_FACTORS[key]
    if site not in classes or acceleration is None:
        return None
    row = classes[site]
    if acceleration <= grid[0]:
        return row[0]
    for i in range(1, len(grid)):
        if acceleration <= grid[i]:
            fraction = (acceleration - grid[i - 1]) / (grid[i] - grid[i - 1])
            return row[i - 1] + fraction * (row[i] - row[i - 1])
    return row[-1]


def spectral_checks(fields):
    v = {key: f["value"] for key, f in fields.items()}
    checks = []
    for factor, acc, product, reference in (("Fs", "Ss", "SDS", "Table 2.1"), ("F1", "S1", "SD1", "Table 2.2")):
        expected_factor = _site_factor(factor, v["SiteClass"], v[acc])
        expected_product = v[acc] * v[factor] if None not in (v[acc], v[factor]) else None
        for key, expected, basis, tolerance in ((factor, expected_factor, reference, 0.0005),
                                                (product, expected_product, "Eq. (2.1)", 0.00005)):
            actual = v[key]
            if actual is None or expected is None:
                continue
            # Half a last displayed unit at three decimals for site factors and four for spectra.
            checks.append({"field": key, "basis": basis, "value": actual, "expected": round(expected, 12),
                           "absolute_tolerance": tolerance,
                           "satisfied": isclose(actual, expected, rel_tol=0, abs_tol=tolerance + 1e-12)})
    return checks


def valid_review_digest(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def project_review(profile, parent_sha, acknowledgement, issues):
    checks = spectral_checks(profile["fields"])
    issues = list(issues)
    issues.extend("Check " + row["field"] + " against TBDY " + row["basis"] for row in checks if not row["satisfied"])
    if profile["fields"]["DD"]["value"] not in (None, "DD-2"):
        issues.append("Strength design requires DD-2 hazard data for the assigned horizontal spectrum.")
    if profile["fields"]["SiteClass"]["value"] == "ZF":
        issues.append("ZF requires a site-specific spectrum under TBDY §2.3.3.2.")
    facts = {"schema": "tbdy.next.strength-design-input-review.v1", "source_sha256": parent_sha,
             "fields": profile["fields"], "assignments": profile["assignments"], "height": profile["height_basis"],
             "checks": checks, "issues": issues}
    digest = sha256(json.dumps(facts, ensure_ascii=False, sort_keys=True, allow_nan=False,
                               separators=(",", ":")).encode()).hexdigest() if valid_review_digest(parent_sha) else None
    if issues:
        status = "SOURCE_REVIEW_REQUIRED"
    elif profile["missing_inputs"] or digest is None:
        status = "INPUTS_REQUIRED"
    elif digest == acknowledgement:
        status = "CONFIRMED"
    else:
        status = "AWAITING_CONFIRMATION"
    return {"status": status, "sha256": digest, "source_sha256": parent_sha, "checks": checks, "issues": issues}


def require_reviewable(profile, acknowledgement):
    review = (profile or {}).get("review") or {}
    if (not valid_review_digest(acknowledgement) or acknowledgement != review.get("sha256")
            or review.get("status") not in ("AWAITING_CONFIRMATION", "CONFIRMED")):
        raise ValueError("PROJECT_INPUTS_REQUIRE_CURRENT_COMPLETE_REVIEW")

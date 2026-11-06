"""First owned engineering slice: TBDY 2018 4.8.1.2 modal-mass subcondition.

Pure numerical calculation; successful arithmetic is NOT engineering approval.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from .source import ModalTable


@dataclass(frozen=True, slots=True)
class ModalAssessment:
    case: str
    numerical_status: str
    sum_ux: Decimal
    sum_uy: Decimal
    threshold: Decimal
    significant_modes_x: tuple[int, ...]
    significant_modes_y: tuple[int, ...]
    governing_mode_count: int | None
    engineering_release: str = "NOT_READY"

    def as_dict(self) -> dict[str, object]:
        return {
            "stage": "MODAL_NUMERICAL_CHECK",
            "criterion": "TBDY-2018-4.8.1.2-MASS-RATIO-SUBCONDITION",
            "case": self.case,
            "status": self.numerical_status,
            "sum_ux": str(self.sum_ux),
            "sum_uy": str(self.sum_uy),
            "required_ratio": str(self.threshold),
            "significant_modes_x": list(self.significant_modes_x),
            "significant_modes_y": list(self.significant_modes_y),
            "governing_mode_count": self.governing_mode_count,
            "engineering_release": self.engineering_release,
            "note": "Numerical subcondition only; no independent model/analysis authorization",
        }


def evaluate_modal_mass(table: ModalTable) -> ModalAssessment:
    threshold = Decimal("0.95")
    significant_threshold = Decimal("0.03")
    last = table.rows[-1]
    sx = tuple(row.mode for row in table.rows if row.ux > significant_threshold)
    sy = tuple(row.mode for row in table.rows if row.uy > significant_threshold)
    nx = next((row.mode for row in table.rows if row.sum_ux >= threshold), None)
    ny = next((row.mode for row in table.rows if row.sum_uy >= threshold), None)
    governing = max(nx, ny, max(sx, default=0), max(sy, default=0)) if nx is not None and ny is not None else None
    meets = last.sum_ux >= threshold and last.sum_uy >= threshold and governing is not None
    return ModalAssessment(
        case=table.target_case,
        numerical_status="MEETS_NUMERICAL_CRITERION" if meets else "DOES_NOT_MEET_NUMERICAL_CRITERION",
        sum_ux=last.sum_ux,
        sum_uy=last.sum_uy,
        threshold=threshold,
        significant_modes_x=sx,
        significant_modes_y=sy,
        governing_mode_count=governing,
    )

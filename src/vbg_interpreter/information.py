"""Deterministic interface priorities, not validated diagnostic information gain."""

from vbg_interpreter.models import (
    Calculation,
    CalculationStatus,
    VbgExplorerRequest,
    VenousGas,
)


def highest_value_next_inputs(
    request: VbgExplorerRequest,
    gas: VenousGas,
    chemistry: dict[str, Calculation],
    estimate: Calculation,
) -> tuple[str, ...]:
    source = request.current_vbg
    candidates: list[str] = []
    if source.pco2 is not None and source.venous_o2_saturation is None:
        candidates.append(
            "Same-sample venous saturation would switch the CO2 estimate from "
            "the fixed correction to Farkas."
        )
    core = sum(v is not None for v in (source.ph, source.pco2, source.hco3_mmol_l))
    if core < 2:
        if source.pco2 is not None:
            candidates.append(
                "Measured venous pH would enable gas completion and calculated venous SBE."
            )
        elif not any("Measured PvCO2" in c for c in candidates):
            candidates.append(
                "Measured venous pH and PvCO2 enable gas completion and calculated venous SBE."
                if core == 0
                else "Measured PvCO2 would enable venous gas completion and calculated SBE."
            )
    corrected = chemistry["corrected_anion_gap"]
    partition = chemistry["venous_stewart_partition"]
    if corrected.missing_inputs == ("albumin",):
        candidates.append("Albumin would add the corrected anion gap.")
    elif (
        partition.status is CalculationStatus.UNAVAILABLE_MISSING_INPUT
        and len(partition.missing_inputs) == 1
    ):
        missing = partition.missing_inputs[0]
        if not (
            missing == "measured venous pH" and any("Measured venous pH" in c for c in candidates)
        ):
            candidates.append(f"Adding {missing} would complete the venous Stewart partition.")
    elif chemistry["anion_gap"].missing_inputs:
        candidates.append(
            "For serum anion gap, add " + ", ".join(chemistry["anion_gap"].missing_inputs) + "."
        )
    candidates.append(
        "If arterial pH or directly measured PaCO2 is the question, an arterial "
        "blood gas provides those measurements; venous data do not establish them."
    )
    return tuple(dict.fromkeys(candidates))[:3]

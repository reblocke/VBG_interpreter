"""Deterministic interface priorities, not validated diagnostic information gain."""

from vbg_interpreter.models import Calculation, SampleType, VbgExplorerRequest


def highest_value_next_inputs(
    request: VbgExplorerRequest, chemistry: dict[str, Calculation]
) -> tuple[str, ...]:
    source = request.current_vbg
    candidates = []
    if source.ph is None:
        candidates.append(
            "Measured venous pH would add an independent pH direction and the "
            "fixed arterial pH estimate."
        )
    if source.pco2 is None:
        candidates.append(
            "Measured PvCO2 would add an independent CO2 direction and an arterial CO2 estimate."
        )
    if (
        source.sample_type is SampleType.PERIPHERAL
        and source.pco2 is not None
        and source.venous_o2_saturation is None
    ):
        candidates.append(
            "Same-sample peripheral venous saturation would switch the CO2 "
            "estimate from the fixed correction to Farkas."
        )
    if chemistry["anion_gap"].missing_inputs:
        candidates.append(
            "For serum anion gap, add " + ", ".join(chemistry["anion_gap"].missing_inputs) + "."
        )
    elif chemistry["corrected_anion_gap"].missing_inputs == ("albumin",):
        candidates.append("Albumin with explicit units would add the corrected anion gap.")
    candidates.append(
        "If arterial pH or directly measured PaCO2 is the question, an "
        "arterial blood gas provides those measurements; venous data do not establish them."
    )
    return tuple(candidates[:3])

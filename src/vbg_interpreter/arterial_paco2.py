"""Measured-source arterial estimates with explicit, unassessed applicability."""

from vbg_interpreter.evidence import PACO2_CONSERVATIVE_ERRORS, calculation
from vbg_interpreter.models import Calculation, SampleType, VbgExplorerRequest
from vbg_interpreter.normalize import normalize_pco2_to_mmhg

APPLICABILITY = "APPLICABILITY_UNASSESSED"
CONTEXT_LIMIT = (
    "Applicability is unassessed. Venous–arterial differences vary with sampling, "
    "perfusion and clinical state; these estimates do not establish arterial measurements."
)


def estimate_arterial_ph(request: VbgExplorerRequest) -> Calculation:
    ph = request.current_vbg.ph
    return calculation(
        "fixed_ph_offset_v1",
        values={} if ph is None else {"ph": ph + 0.04},
        units={"ph": "pH units"},
        origins={} if ph is None else {"ph": "MEASURED_OR_REPORTED_VENOUS"},
        missing=("measured venous pH",) if ph is None else (),
        provenance="HEURISTIC_ARTERIAL_ESTIMATE",
        applicability=APPLICABILITY,
        limitations=("Rough fixed pH correction (+0.04); no individual uncertainty interval.",),
    )


def estimate_arterial_paco2(request: VbgExplorerRequest) -> Calculation:
    """Only the supplied PvCO2 enters either method; saturation selects Farkas."""
    source = request.current_vbg
    saturation = (
        source.venous_o2_saturation if source.sample_type is SampleType.PERIPHERAL else None
    )
    method = "fixed_paco2_offset_v1" if saturation is None else "farkas_simplified_93_v1"
    origins = {} if source.pco2 is None else {"pco2": "MEASURED_OR_REPORTED_VENOUS"}
    origins["sample_type"] = source.sample_type.value
    limits = (CONTEXT_LIMIT,)
    if source.venous_o2_saturation is not None and saturation is None:
        limits += (
            f"Sample: {source.sample_type.value.lower()}. Peripheral Farkas was not applied; "
            "the fixed −5 mmHg heuristic was selected.",
        )
    if saturation is None:
        limits += ("Rough fixed CO2 correction (−5 mmHg); no individual uncertainty interval.",)
    else:
        origins["venous_saturation"] = "REPORTED_SAME_SAMPLE_VENOUS"
        limits += (
            "Farkas PaCO2 component externally evaluated in peripheral samples; this combined "
            "pH/CO2 interpretation is not externally validated.",
            "Conservative published oxygen-profile agreement range; not a patient-specific "
            "confidence interval or joint pH/CO2 region.",
        )
    kwargs = dict(
        origins=origins,
        provenance="HEURISTIC_ARTERIAL_ESTIMATE"
        if saturation is None
        else "MODEL_BASED_ARTERIAL_ESTIMATE",
        applicability=APPLICABILITY,
        limitations=limits,
    )
    if source.pco2 is None:
        return calculation(method, missing=("measured PvCO2",), **kwargs)
    try:
        pvco2 = normalize_pco2_to_mmhg(source.pco2, source.pco2_unit)
        point = (
            pvco2 - 5
            if saturation is None
            else pvco2 - 0.22 * (93 - saturation.normalized_percentage_points)
        )
        values = {"measured_pvco2": pvco2, "point": point}
        units = {"measured_pvco2": "mmHg", "point": "mmHg"}
        minimum = point
        if saturation is not None:
            error_lower, error_upper = PACO2_CONSERVATIVE_ERRORS
            lower, upper = point - error_upper, point - error_lower
            values.update(
                saturation_percent=saturation.normalized_percentage_points, lower=lower, upper=upper
            )
            units.update(saturation_percent="%", lower="mmHg", upper="mmHg")
            minimum = min(point, lower, upper)
            if saturation.normalized_percentage_points > 93:
                kwargs["limitations"] += (
                    "Saturation exceeds the simplified 93% reference; no clamp applied.",
                )
        return calculation(
            method, values=values, units=units, domain_refusal=minimum <= 0, **kwargs
        )
    except (ArithmeticError, ValueError):
        return calculation(method, domain_refusal=True, **kwargs)

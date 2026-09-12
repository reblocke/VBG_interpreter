"""Measured-source-only PaCO2 component; no arterial pH inference."""

from vbg_interpreter.evidence import PACO2_PROFILES, calculation
from vbg_interpreter.models import (
    Calculation,
    DrawSite,
    SpecimenType,
    TriState,
    VbgExplorerRequest,
)
from vbg_interpreter.normalize import normalize_pco2_to_mmhg

METHOD = "farkas_simplified_93_v1"
RISK_FIELDS = (
    "known_poor_perfusion_or_hemodynamic_instability",
    "recent_major_ventilation_or_treatment_change",
    "material_preanalytic_concern",
)


def known_blockers(request: VbgExplorerRequest) -> tuple[str, ...]:
    source = request.current_vbg
    reasons = []
    if source.specimen_type not in (SpecimenType.PERIPHERAL_VENOUS, SpecimenType.UNKNOWN):
        reasons.append("Specimen is outside peripheral venous scope.")
    if source.draw_site not in (DrawSite.UPPER_EXTREMITY_PERIPHERAL, DrawSite.UNKNOWN):
        reasons.append("Draw site is outside upper-extremity peripheral scope.")
    risk_reasons = (
        "Known poor perfusion or hemodynamic instability.",
        "Recent major ventilation or treatment change.",
        "Material preanalytic concern.",
    )
    reasons.extend(
        reason
        for key, reason in zip(RISK_FIELDS, risk_reasons, strict=True)
        if getattr(request.context, key) is TriState.YES
    )
    if source.saturation_same_sample is TriState.NO:
        reasons.append("Saturation is not from the same sample.")
    return tuple(reasons)


def unknown_context(request: VbgExplorerRequest) -> tuple[str, ...]:
    unknown = []
    if request.current_vbg.specimen_type is SpecimenType.UNKNOWN:
        unknown.append("specimen type")
    if request.current_vbg.draw_site is DrawSite.UNKNOWN:
        unknown.append("draw site")
    for key in RISK_FIELDS:
        if getattr(request.context, key) is TriState.UNKNOWN:
            unknown.append(key.replace("_", " "))
    return tuple(unknown)


def estimate_arterial_paco2(request: VbgExplorerRequest) -> Calculation:
    """Read only source PvCO2; HH-completed coordinates cannot enter this function."""
    source = request.current_vbg
    missing = []
    if source.pco2 is None:
        missing.append("measured PvCO2")
    if source.venous_o2_saturation is None:
        missing.append("measured venous saturation with explicit unit")
    if source.saturation_same_sample is not TriState.YES:
        missing.append("same-sample saturation confirmation")
    blockers = known_blockers(request)
    origins = {}
    if source.pco2 is not None:
        origins["pco2"] = "MEASURED_OR_REPORTED"
    if source.venous_o2_saturation is not None:
        origins["venous_saturation"] = "MEASURED_OR_REPORTED"
    kwargs = dict(
        origins=origins,
        provenance="MODEL_BASED_ARTERIAL_ESTIMATE",
        limitations=(
            "Externally evaluated PaCO2 component; no local end-to-end validation.",
            "Deterministic agreement range, not a patient-specific 95% probability interval.",
        ),
    )
    if blockers or missing:
        return calculation(METHOD, missing=tuple(missing), outside=blockers, **kwargs)
    uncertain = unknown_context(request)
    applicability = "APPLICABILITY_UNCERTAIN" if uncertain else "ELIGIBLE"
    if uncertain:
        kwargs["limitations"] += ("Applicability uncertain: " + ", ".join(uncertain) + ".",)
    try:
        pco2 = normalize_pco2_to_mmhg(source.pco2, source.pco2_unit)
        saturation = source.venous_o2_saturation.normalized_percentage_points
        point = pco2 - 0.22 * (93 - saturation)
        profile, error_lower, error_upper = PACO2_PROFILES[request.context.supplemental_oxygen]
        lower, upper = point - error_upper, point - error_lower
        if saturation > 93:
            kwargs["limitations"] += (
                "Saturation exceeds the simplified 93% reference; no clamp applied.",
            )
        if request.context.supplemental_oxygen is TriState.UNKNOWN:
            kwargs["limitations"] += (
                "Oxygen context unknown; retained conservative oxygen profile used.",
            )
        return calculation(
            METHOD,
            values={
                "measured_pvco2": pco2,
                "saturation_percent": saturation,
                "point": point,
                "lower": lower,
                "upper": upper,
                "oxygen_profile": profile,
            },
            units={
                "measured_pvco2": "mmHg",
                "saturation_percent": "%",
                "point": "mmHg",
                "lower": "mmHg",
                "upper": "mmHg",
            },
            applicability=applicability,
            domain_refusal=min(point, lower, upper) <= 0,
            **kwargs,
        )
    except (ArithmeticError, ValueError):
        return calculation(METHOD, domain_refusal=True, applicability=applicability, **kwargs)

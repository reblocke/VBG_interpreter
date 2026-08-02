"""Conservative prior-observation context with no chronicity proof or model narrowing."""

from __future__ import annotations

from vbg_interpreter.models import (
    HistoricalArterialCoordinate,
    LimitationCode,
    LongitudinalContext,
    LongitudinalStatus,
    NormalizedPriorObservation,
    PriorObservationSummary,
    PriorObservationType,
)


def build_longitudinal_context(
    prior: NormalizedPriorObservation | None,
) -> LongitudinalContext:
    """Retain one previous observation as context without converting its provenance."""

    if prior is None:
        return LongitudinalContext(
            status=LongitudinalStatus.NOT_PROVIDED,
            prior_observation=None,
            historical_arterial_coordinate=None,
            limitation_codes=(LimitationCode.PRIOR_OBSERVATION_NOT_PROVIDED,),
        )
    observation = prior.observation
    summary = PriorObservationSummary(
        observation_type=observation.observation_type,
        elapsed_hours=observation.elapsed_hours,
        ph=observation.ph,
        pco2_mmhg=prior.pco2_mmhg,
        hco3_mmol_l=observation.hco3_mmol_l,
        serum_total_co2_mmol_l=observation.serum_total_co2_mmol_l,
        base_excess_mmol_l=observation.base_excess_mmol_l,
        specimen_type=observation.specimen_type,
        draw_site=observation.draw_site,
        intervening_major_ventilation_or_treatment_change=(
            observation.intervening_major_ventilation_or_treatment_change
        ),
    )
    limitations: list[LimitationCode] = []
    coordinate = None
    if observation.observation_type is PriorObservationType.ABG:
        if observation.ph is not None and prior.pco2_mmhg is not None:
            coordinate = HistoricalArterialCoordinate(ph=observation.ph, paco2_mmhg=prior.pco2_mmhg)
    elif observation.observation_type is PriorObservationType.VBG:
        limitations.append(LimitationCode.PRIOR_VBG_REMAINS_VENOUS)
    else:
        limitations.append(LimitationCode.PRIOR_SERUM_TOTAL_CO2_REMAINS_CHEMISTRY)
    if observation.intervening_major_ventilation_or_treatment_change.value == "UNKNOWN":
        limitations.append(LimitationCode.INTERVENING_CHANGE_UNKNOWN)
    elif observation.intervening_major_ventilation_or_treatment_change.value == "YES":
        limitations.append(LimitationCode.INTERVENING_CHANGE_REPORTED)
    return LongitudinalContext(
        status=LongitudinalStatus.AVAILABLE,
        prior_observation=summary,
        historical_arterial_coordinate=coordinate,
        limitation_codes=tuple(limitations),
    )

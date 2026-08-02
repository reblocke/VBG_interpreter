"""Certified exhaustive Boston signatures over a closed pH/PaCO2 rectangle.

The Boston ruleset is a finite decision tree.  Each terminal rule path is a
conjunction of rational half-planes after the registered
Henderson-Hasselbalch transform maps pH/PaCO2 to PaCO2/HCO3 space.  This module
enumerates every terminal path and proves it feasible or infeasible with:

* exact ``Fraction`` Fourier-Motzkin feasibility for rational half-planes;
* outward enclosures of the two transcendental pH-edge slopes;
* an inner-wedge feasibility proof for presence;
* an outer-wedge infeasibility proof for absence; and
* separate certified ray checks for boundary-only pH strata.

If any path cannot be decided under prescribed precision escalation, the
caller receives a typed certification failure.  No binary-float witness,
sampled grid, or precision-agreement heuristic is part of the proof.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import (
    ROUND_CEILING,
    ROUND_FLOOR,
    ROUND_HALF_EVEN,
    Decimal,
    localcontext,
)
from fractions import Fraction

from vbg_interpreter.models import (
    AcidBaseStateCode,
    ChronicityBranch,
    ExpectedCompensationCode,
    MeasuredVsExpectedCode,
    PrimaryProcessCode,
)
from vbg_interpreter.state_categories import (
    DECISION_SURFACE_IDS,
    RuleSignature,
    signature_from_surface_signs,
)

BostonChronicityBranch = ChronicityBranch
BostonClassificationSignature = RuleSignature

COVERAGE_METHOD_ID = "CERTIFIED_TERMINAL_PATH_FEASIBILITY"
DECISION_SURFACE_CATALOG_VERSION = "stewartlight_boston_ruleset_v1/surfaces/1.0"
DECISION_SURFACE_COUNT = len(DECISION_SURFACE_IDS)
CERTIFICATION_PRECISION_DIGITS = (48, 96, 192, 384)
TERMINAL_PATHS_PER_BRANCH = 27

_PH_LOW = Fraction(735, 100)
_PH_HIGH = Fraction(745, 100)
_PKA = Fraction(6095, 1000)
_CO2_SOLUBILITY = Fraction(307, 10000)


class BostonEnvelopeCertificationError(ArithmeticError):
    """Raised when every terminal path cannot be proved present or absent."""


@dataclass(frozen=True, slots=True)
class CertifiedBostonBranch:
    """Complete feasible signature set for one chronicity branch."""

    chronicity_branch: BostonChronicityBranch
    signatures: tuple[BostonClassificationSignature, ...]


@dataclass(frozen=True, slots=True)
class CertifiedBostonEnvelope:
    """Complete branch-specific signatures and proof metadata."""

    branches: tuple[CertifiedBostonBranch, ...]
    decision_surface_count: int
    terminal_path_count: int
    certification_precision_digits: int


@dataclass(frozen=True, slots=True)
class _Constraint:
    """Half-plane ``a*x + b*y + c >= 0`` or strict ``> 0``."""

    a: Fraction
    b: Fraction
    c: Fraction
    strict: bool = False

    def scaled(self, factor: Fraction) -> _Constraint:
        if factor <= 0:
            raise ValueError("Constraint scaling must be positive.")
        return _Constraint(
            a=self.a * factor,
            b=self.b * factor,
            c=self.c * factor,
            strict=self.strict,
        )


@dataclass(frozen=True, slots=True)
class _PhBand:
    lower: Fraction
    upper: Fraction
    lower_inclusive: bool
    upper_inclusive: bool

    @property
    def is_empty(self) -> bool:
        return self.lower > self.upper or (
            self.lower == self.upper and not (self.lower_inclusive and self.upper_inclusive)
        )

    @property
    def is_ray(self) -> bool:
        return self.lower == self.upper and self.lower_inclusive and self.upper_inclusive


@dataclass(frozen=True, slots=True)
class _TerminalPath:
    path_id: str
    ph_state: str
    constraints: tuple[_Constraint, ...]
    representative_signs: tuple[int, ...]
    signature: BostonClassificationSignature


@dataclass(frozen=True, slots=True)
class _Surface:
    surface_id: str
    a: Fraction
    b: Fraction
    c: Fraction

    def relation(self, relation: str) -> tuple[_Constraint, ...]:
        if relation == "lt":
            return (_Constraint(-self.a, -self.b, -self.c, strict=True),)
        if relation == "le":
            return (_Constraint(-self.a, -self.b, -self.c),)
        if relation == "gt":
            return (_Constraint(self.a, self.b, self.c, strict=True),)
        if relation == "ge":
            return (_Constraint(self.a, self.b, self.c),)
        if relation == "eq":
            return (
                _Constraint(self.a, self.b, self.c),
                _Constraint(-self.a, -self.b, -self.c),
            )
        raise ValueError("Unknown terminal-path relation.")


# The pH surfaces use the named HH transform and are represented by the pH
# bands themselves.  Every other executable comparison is pinned here in its
# original sign orientation.
_RATIONAL_SURFACES = {
    "paco2_38": _Surface("paco2_38", Fraction(1), Fraction(0), Fraction(-38)),
    "paco2_42": _Surface("paco2_42", Fraction(1), Fraction(0), Fraction(-42)),
    "hco3_22": _Surface("hco3_22", Fraction(0), Fraction(1), Fraction(-22)),
    "hco3_26": _Surface("hco3_26", Fraction(0), Fraction(1), Fraction(-26)),
    "winters_lower": _Surface(
        "winters_lower",
        Fraction(1),
        Fraction(-3, 2),
        Fraction(-6),
    ),
    "winters_upper": _Surface(
        "winters_upper",
        Fraction(1),
        Fraction(-3, 2),
        Fraction(-10),
    ),
    "metabolic_alkalosis_lower": _Surface(
        "metabolic_alkalosis_lower",
        Fraction(1),
        Fraction(-7, 10),
        Fraction(-91, 5),
    ),
    "metabolic_alkalosis_upper": _Surface(
        "metabolic_alkalosis_upper",
        Fraction(1),
        Fraction(-7, 10),
        Fraction(-141, 5),
    ),
    "respiratory_acidosis_chronic_lower": _Surface(
        "respiratory_acidosis_chronic_lower",
        Fraction(-2, 5),
        Fraction(1),
        Fraction(-5),
    ),
    "respiratory_acidosis_chronic_upper": _Surface(
        "respiratory_acidosis_chronic_upper",
        Fraction(-2, 5),
        Fraction(1),
        Fraction(-11),
    ),
    "respiratory_acidosis_unflagged_lower": _Surface(
        "respiratory_acidosis_unflagged_lower",
        Fraction(-1, 10),
        Fraction(1),
        Fraction(-18),
    ),
    "respiratory_acidosis_unflagged_upper": _Surface(
        "respiratory_acidosis_unflagged_upper",
        Fraction(-2, 5),
        Fraction(1),
        Fraction(-10),
    ),
    "respiratory_alkalosis_lower": _Surface(
        "respiratory_alkalosis_lower",
        Fraction(-1, 2),
        Fraction(1),
        Fraction(-2),
    ),
    "respiratory_alkalosis_upper": _Surface(
        "respiratory_alkalosis_upper",
        Fraction(-1, 5),
        Fraction(1),
        Fraction(-18),
    ),
}

DECISION_SURFACE_EQUATIONS = (
    ("ph_7_35", "HCO3-HH_SLOPE(7.35)*PaCO2"),
    ("ph_7_45", "HCO3-HH_SLOPE(7.45)*PaCO2"),
    *tuple(
        (
            surface_id,
            f"{surface.a}*PaCO2+{surface.b}*HCO3+{surface.c}",
        )
        for surface_id, surface in _RATIONAL_SURFACES.items()
    ),
)


def _fraction_from_float(value: float) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BostonEnvelopeCertificationError("Envelope bounds must be numeric.")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise BostonEnvelopeCertificationError("Envelope bounds must be finite.")
    return Fraction(Decimal(str(numeric)))


def _fraction_sign(value: Fraction) -> int:
    return -1 if value < 0 else 1 if value > 0 else 0


def _ph_surface_signs(ph: Fraction) -> dict[str, int]:
    return {
        "ph_7_35": _fraction_sign(ph - _PH_LOW),
        "ph_7_45": _fraction_sign(ph - _PH_HIGH),
    }


def _decimal_bound(
    value: Fraction,
    *,
    precision: int,
    rounding: str,
) -> Decimal:
    with localcontext() as context:
        context.prec = precision
        context.rounding = rounding
        return +(Decimal(value.numerator) / Decimal(value.denominator))


def _multiply_decimal_bounds(
    left: tuple[Decimal, Decimal],
    right: tuple[Decimal, Decimal],
    *,
    precision: int,
) -> tuple[Decimal, Decimal]:
    candidates_lower: list[Decimal] = []
    candidates_upper: list[Decimal] = []
    for left_value in left:
        for right_value in right:
            with localcontext() as context:
                context.prec = precision
                context.rounding = ROUND_FLOOR
                candidates_lower.append(+(left_value * right_value))
            with localcontext() as context:
                context.prec = precision
                context.rounding = ROUND_CEILING
                candidates_upper.append(+(left_value * right_value))
    return min(candidates_lower), max(candidates_upper)


def _correctly_rounded_transcendental_bounds(
    value: Decimal,
    *,
    operation: str,
    precision: int,
) -> tuple[Decimal, Decimal]:
    """Enclose a correctly-rounded Decimal ln/exp result by one high-precision ulp."""

    with localcontext() as context:
        context.prec = precision
        context.rounding = ROUND_HALF_EVEN
        if operation == "ln":
            rounded = value.ln()
        elif operation == "exp":
            rounded = value.exp()
        else:  # pragma: no cover - internal programmer guard
            raise ValueError("Unknown Decimal transcendental.")
        return rounded.next_minus(context), rounded.next_plus(context)


def _hh_slope_bounds(ph: Fraction, *, precision: int) -> tuple[Fraction, Fraction]:
    """Return a rigorous rational enclosure of ``0.0307*10**(pH-6.095)``."""

    delta = ph - _PKA
    if delta.denominator == 1:
        if delta >= 0:
            exact = _CO2_SOLUBILITY * (10**delta.numerator)
        else:
            exact = _CO2_SOLUBILITY / (10 ** (-delta.numerator))
        return exact, exact

    work_precision = precision + 24
    ln10 = _correctly_rounded_transcendental_bounds(
        Decimal(10),
        operation="ln",
        precision=work_precision,
    )
    delta_bounds = (
        _decimal_bound(
            delta,
            precision=work_precision,
            rounding=ROUND_FLOOR,
        ),
        _decimal_bound(
            delta,
            precision=work_precision,
            rounding=ROUND_CEILING,
        ),
    )
    exponent = _multiply_decimal_bounds(
        delta_bounds,
        ln10,
        precision=work_precision,
    )
    exp_lower = _correctly_rounded_transcendental_bounds(
        exponent[0],
        operation="exp",
        precision=work_precision,
    )[0]
    exp_upper = _correctly_rounded_transcendental_bounds(
        exponent[1],
        operation="exp",
        precision=work_precision,
    )[1]
    solubility_bounds = (
        _decimal_bound(
            _CO2_SOLUBILITY,
            precision=work_precision,
            rounding=ROUND_FLOOR,
        ),
        _decimal_bound(
            _CO2_SOLUBILITY,
            precision=work_precision,
            rounding=ROUND_CEILING,
        ),
    )
    lower, upper = _multiply_decimal_bounds(
        solubility_bounds,
        (exp_lower, exp_upper),
        precision=work_precision,
    )
    if not 0 < lower <= upper:
        raise BostonEnvelopeCertificationError("HH slope enclosure is not positive and ordered.")
    return Fraction(lower), Fraction(upper)


def _surface_sign_at_hh_point(
    surface: _Surface,
    *,
    ph: Fraction,
    paco2: Fraction,
) -> int:
    """Prove one continuous-real HH decision-surface sign at a decimal point."""

    for precision in CERTIFICATION_PRECISION_DIGITS:
        slope_lower, slope_upper = _hh_slope_bounds(ph, precision=precision)
        y_candidates = (slope_lower * paco2, slope_upper * paco2)
        residual_candidates = tuple(
            surface.a * paco2 + surface.b * y + surface.c for y in y_candidates
        )
        residual_lower = min(residual_candidates)
        residual_upper = max(residual_candidates)
        if residual_upper < 0:
            return -1
        if residual_lower > 0:
            return 1
        if residual_lower == residual_upper == 0:
            return 0
    raise BostonEnvelopeCertificationError(
        "A continuous-real Boston point sign could not be certified."
    )


def signature_from_continuous_hh_point(
    *,
    ph: float,
    paco2_mmhg: float,
    chronicity_branch: BostonChronicityBranch,
) -> BostonClassificationSignature:
    """Classify an unrounded continuous-real HH point from decimal inputs."""

    ph_fraction = _fraction_from_float(ph)
    paco2_fraction = _fraction_from_float(paco2_mmhg)
    if ph_fraction <= 0 or paco2_fraction <= 0:
        raise BostonEnvelopeCertificationError(
            "Continuous-real Boston point inputs must be positive."
        )
    signs = _ph_surface_signs(ph_fraction)
    signs.update(
        {
            surface_id: _surface_sign_at_hh_point(
                surface,
                ph=ph_fraction,
                paco2=paco2_fraction,
            )
            for surface_id, surface in _RATIONAL_SURFACES.items()
        }
    )
    return signature_from_surface_signs(
        signs,
        chronicity_branch=chronicity_branch,
    )


def signature_from_continuous_measured_values(
    *,
    ph: float,
    paco2_mmhg: float,
    hco3_mmol_l: float,
    chronicity_branch: BostonChronicityBranch,
) -> BostonClassificationSignature:
    """Classify three decimal inputs with exact rational Boston surfaces."""

    ph_fraction = _fraction_from_float(ph)
    paco2_fraction = _fraction_from_float(paco2_mmhg)
    hco3_fraction = _fraction_from_float(hco3_mmol_l)
    if ph_fraction <= 0 or paco2_fraction <= 0 or hco3_fraction <= 0:
        raise BostonEnvelopeCertificationError(
            "Continuous-real Boston measured inputs must be positive."
        )
    signs = _ph_surface_signs(ph_fraction)
    signs.update(
        {
            surface_id: _fraction_sign(
                surface.a * paco2_fraction + surface.b * hco3_fraction + surface.c
            )
            for surface_id, surface in _RATIONAL_SURFACES.items()
        }
    )
    return signature_from_surface_signs(
        signs,
        chronicity_branch=chronicity_branch,
    )


def _one_dimensional_feasible(constraints: tuple[_Constraint, ...]) -> bool:
    lower: Fraction | None = None
    lower_inclusive = True
    upper: Fraction | None = None
    upper_inclusive = True

    for constraint in constraints:
        if constraint.b != 0:
            raise ValueError("One-dimensional feasibility received a y coefficient.")
        if constraint.a == 0:
            if constraint.strict:
                if constraint.c <= 0:
                    return False
            elif constraint.c < 0:
                return False
            continue

        boundary = -constraint.c / constraint.a
        inclusive = not constraint.strict
        if constraint.a > 0:
            if lower is None or boundary > lower:
                lower = boundary
                lower_inclusive = inclusive
            elif boundary == lower:
                lower_inclusive = lower_inclusive and inclusive
        else:
            if upper is None or boundary < upper:
                upper = boundary
                upper_inclusive = inclusive
            elif boundary == upper:
                upper_inclusive = upper_inclusive and inclusive

    if lower is None or upper is None:
        return True
    if lower < upper:
        return True
    if lower > upper:
        return False
    return lower_inclusive and upper_inclusive


def _halfplanes_feasible(constraints: tuple[_Constraint, ...]) -> bool:
    """Exact two-dimensional Fourier-Motzkin feasibility with strictness."""

    positive_y = tuple(constraint for constraint in constraints if constraint.b > 0)
    negative_y = tuple(constraint for constraint in constraints if constraint.b < 0)
    eliminated = [constraint for constraint in constraints if constraint.b == 0]
    for lower in positive_y:
        for upper in negative_y:
            lower_factor = -upper.b
            upper_factor = lower.b
            eliminated.append(
                _Constraint(
                    a=lower_factor * lower.a + upper_factor * upper.a,
                    b=Fraction(0),
                    c=lower_factor * lower.c + upper_factor * upper.c,
                    strict=lower.strict or upper.strict,
                )
            )
    if positive_y and not negative_y:
        return _one_dimensional_feasible(tuple(eliminated))
    if negative_y and not positive_y:
        return _one_dimensional_feasible(tuple(eliminated))
    return _one_dimensional_feasible(tuple(eliminated))


def _bounded_constraints(
    *,
    x_lower: Fraction,
    x_upper: Fraction,
) -> tuple[_Constraint, _Constraint]:
    return (
        _Constraint(Fraction(1), Fraction(0), -x_lower),
        _Constraint(Fraction(-1), Fraction(0), x_upper),
    )


def _wedge_constraints(
    *,
    x_lower: Fraction,
    x_upper: Fraction,
    lower_slope: Fraction,
    upper_slope: Fraction,
    lower_inclusive: bool,
    upper_inclusive: bool,
) -> tuple[_Constraint, ...]:
    return (
        *_bounded_constraints(x_lower=x_lower, x_upper=x_upper),
        _Constraint(
            -lower_slope,
            Fraction(1),
            Fraction(0),
            strict=not lower_inclusive,
        ),
        _Constraint(
            upper_slope,
            Fraction(-1),
            Fraction(0),
            strict=not upper_inclusive,
        ),
    )


def _ray_feasibility(
    constraints: tuple[_Constraint, ...],
    *,
    slope_bounds: tuple[Fraction, Fraction],
    x_lower: Fraction,
    x_upper: Fraction,
) -> bool | None:
    """Certify feasibility on ``y=s*x`` with positive bounded ``x``."""

    slope_lower, slope_upper = slope_bounds
    inner: list[_Constraint] = list(_bounded_constraints(x_lower=x_lower, x_upper=x_upper))
    outer: list[_Constraint] = list(_bounded_constraints(x_lower=x_lower, x_upper=x_upper))
    for constraint in constraints:
        candidates = (
            constraint.a + constraint.b * slope_lower,
            constraint.a + constraint.b * slope_upper,
        )
        coefficient_lower = min(candidates)
        coefficient_upper = max(candidates)
        inner.append(
            _Constraint(
                coefficient_lower,
                Fraction(0),
                constraint.c,
                strict=constraint.strict,
            )
        )
        outer.append(
            _Constraint(
                coefficient_upper,
                Fraction(0),
                constraint.c,
                strict=constraint.strict,
            )
        )

    if _one_dimensional_feasible(tuple(inner)):
        return True
    if not _one_dimensional_feasible(tuple(outer)):
        return False
    return None


def _path_feasibility(
    path: _TerminalPath,
    *,
    band: _PhBand,
    x_lower: Fraction,
    x_upper: Fraction,
    precision: int,
) -> bool | None:
    if band.is_empty:
        return False

    lower_bounds = _hh_slope_bounds(band.lower, precision=precision)
    if band.is_ray:
        return _ray_feasibility(
            path.constraints,
            slope_bounds=lower_bounds,
            x_lower=x_lower,
            x_upper=x_upper,
        )
    upper_bounds = _hh_slope_bounds(band.upper, precision=precision)
    if lower_bounds[1] >= upper_bounds[0]:
        return None

    outer = (
        *path.constraints,
        *_wedge_constraints(
            x_lower=x_lower,
            x_upper=x_upper,
            lower_slope=lower_bounds[0],
            upper_slope=upper_bounds[1],
            lower_inclusive=band.lower_inclusive,
            upper_inclusive=band.upper_inclusive,
        ),
    )
    if not _halfplanes_feasible(outer):
        return False

    inner = (
        *path.constraints,
        *_wedge_constraints(
            x_lower=x_lower,
            x_upper=x_upper,
            lower_slope=lower_bounds[1],
            upper_slope=upper_bounds[0],
            lower_inclusive=band.lower_inclusive,
            upper_inclusive=band.upper_inclusive,
        ),
    )
    if _halfplanes_feasible(inner):
        return True

    if band.lower_inclusive:
        lower_ray = _ray_feasibility(
            path.constraints,
            slope_bounds=lower_bounds,
            x_lower=x_lower,
            x_upper=x_upper,
        )
        if lower_ray is True:
            return True
    if band.upper_inclusive:
        upper_ray = _ray_feasibility(
            path.constraints,
            slope_bounds=upper_bounds,
            x_lower=x_lower,
            x_upper=x_upper,
        )
        if upper_ray is True:
            return True
    return None


def _ph_bands(
    *,
    ph_lower: Fraction,
    ph_upper: Fraction,
) -> dict[str, _PhBand]:
    acid_upper = min(ph_upper, _PH_LOW)
    acid = _PhBand(
        lower=ph_lower,
        upper=acid_upper,
        lower_inclusive=True,
        upper_inclusive=ph_upper < _PH_LOW,
    )
    near_lower = max(ph_lower, _PH_LOW)
    near_upper = min(ph_upper, _PH_HIGH)
    near = _PhBand(
        lower=near_lower,
        upper=near_upper,
        lower_inclusive=True,
        upper_inclusive=True,
    )
    alk_lower = max(ph_lower, _PH_HIGH)
    alk = _PhBand(
        lower=alk_lower,
        upper=ph_upper,
        lower_inclusive=ph_lower > _PH_HIGH,
        upper_inclusive=True,
    )
    return {"ACIDEMIA": acid, "NEAR_NORMAL": near, "ALKALEMIA": alk}


def _surface_constraints(*requirements: tuple[str, str]) -> tuple[_Constraint, ...]:
    constraints: list[_Constraint] = []
    for surface_id, relation in requirements:
        constraints.extend(_RATIONAL_SURFACES[surface_id].relation(relation))
    return tuple(constraints)


def _representative_signs(
    *,
    ph_state: str,
    requirements: tuple[tuple[str, str], ...],
) -> tuple[int, ...]:
    signs = {surface_id: 0 for surface_id in DECISION_SURFACE_IDS}
    if ph_state == "ACIDEMIA":
        signs["ph_7_35"] = -1
        signs["ph_7_45"] = -1
    elif ph_state == "NEAR_NORMAL":
        signs["ph_7_35"] = 1
        signs["ph_7_45"] = -1
    elif ph_state == "ALKALEMIA":
        signs["ph_7_35"] = 1
        signs["ph_7_45"] = 1
    else:  # pragma: no cover - internal programmer guard
        raise ValueError("Unknown pH state.")
    for surface_id, relation in requirements:
        signs[surface_id] = {
            "lt": -1,
            "le": -1,
            "gt": 1,
            "ge": 1,
            "eq": 0,
        }[relation]
    return tuple(signs[surface_id] for surface_id in DECISION_SURFACE_IDS)


def _path(
    *,
    path_id: str,
    ph_state: str,
    requirements: tuple[tuple[str, str], ...],
    branch: BostonChronicityBranch,
) -> _TerminalPath:
    representative = _representative_signs(
        ph_state=ph_state,
        requirements=requirements,
    )
    signs = dict(zip(DECISION_SURFACE_IDS, representative, strict=True))
    return _TerminalPath(
        path_id=path_id,
        ph_state=ph_state,
        constraints=_surface_constraints(*requirements),
        representative_signs=representative,
        signature=signature_from_surface_signs(
            signs,
            chronicity_branch=branch,
        ),
    )


def _compensation_paths(
    *,
    prefix: str,
    ph_state: str,
    base: tuple[tuple[str, str], ...],
    lower_surface: str,
    upper_surface: str,
    branch: BostonChronicityBranch,
) -> tuple[_TerminalPath, ...]:
    return (
        _path(
            path_id=f"{prefix}/BELOW_EXPECTED",
            ph_state=ph_state,
            requirements=(*base, (lower_surface, "lt")),
            branch=branch,
        ),
        _path(
            path_id=f"{prefix}/WITHIN_EXPECTED",
            ph_state=ph_state,
            requirements=(
                *base,
                (lower_surface, "ge"),
                (upper_surface, "le"),
            ),
            branch=branch,
        ),
        _path(
            path_id=f"{prefix}/ABOVE_EXPECTED",
            ph_state=ph_state,
            requirements=(*base, (upper_surface, "gt")),
            branch=branch,
        ),
    )


def _terminal_paths(branch: BostonChronicityBranch) -> tuple[_TerminalPath, ...]:
    respiratory_acidosis_prefix = (
        "respiratory_acidosis_chronic"
        if branch is BostonChronicityBranch.CHRONIC_FLAGGED
        else "respiratory_acidosis_unflagged"
    )
    paths: list[_TerminalPath] = []
    paths.extend(
        _compensation_paths(
            prefix="ACIDEMIA/METABOLIC_ACIDOSIS",
            ph_state="ACIDEMIA",
            base=(("hco3_22", "lt"),),
            lower_surface="winters_lower",
            upper_surface="winters_upper",
            branch=branch,
        )
    )
    paths.extend(
        _compensation_paths(
            prefix="ACIDEMIA/RESPIRATORY_ACIDOSIS",
            ph_state="ACIDEMIA",
            base=(("hco3_22", "ge"), ("paco2_42", "gt")),
            lower_surface=f"{respiratory_acidosis_prefix}_lower",
            upper_surface=f"{respiratory_acidosis_prefix}_upper",
            branch=branch,
        )
    )
    paths.append(
        _path(
            path_id="ACIDEMIA/UNCLEAR",
            ph_state="ACIDEMIA",
            requirements=(("hco3_22", "ge"), ("paco2_42", "le")),
            branch=branch,
        )
    )

    paths.extend(
        _compensation_paths(
            prefix="ALKALEMIA/METABOLIC_ALKALOSIS",
            ph_state="ALKALEMIA",
            base=(("hco3_26", "gt"),),
            lower_surface="metabolic_alkalosis_lower",
            upper_surface="metabolic_alkalosis_upper",
            branch=branch,
        )
    )
    paths.extend(
        _compensation_paths(
            prefix="ALKALEMIA/RESPIRATORY_ALKALOSIS",
            ph_state="ALKALEMIA",
            base=(("hco3_26", "le"), ("paco2_38", "lt")),
            lower_surface="respiratory_alkalosis_lower",
            upper_surface="respiratory_alkalosis_upper",
            branch=branch,
        )
    )
    paths.append(
        _path(
            path_id="ALKALEMIA/UNCLEAR",
            ph_state="ALKALEMIA",
            requirements=(("hco3_26", "le"), ("paco2_38", "ge")),
            branch=branch,
        )
    )

    state_requirements = {
        "LOW": (("paco2_38", "lt"),),
        "NORMAL": (("paco2_38", "ge"), ("paco2_42", "le")),
        "HIGH": (("paco2_42", "gt"),),
    }
    hco3_requirements = {
        "LOW": (("hco3_22", "lt"),),
        "NORMAL": (("hco3_22", "ge"), ("hco3_26", "le")),
        "HIGH": (("hco3_26", "gt"),),
    }
    for pco2_state in ("LOW", "NORMAL", "HIGH"):
        for hco3_state in ("LOW", "NORMAL", "HIGH"):
            base = (
                *state_requirements[pco2_state],
                *hco3_requirements[hco3_state],
            )
            prefix = f"NEAR_NORMAL/{pco2_state}_PCO2/{hco3_state}_HCO3"
            if pco2_state == "HIGH" and hco3_state == "HIGH":
                paths.extend(
                    _compensation_paths(
                        prefix=prefix,
                        ph_state="NEAR_NORMAL",
                        base=base,
                        lower_surface=f"{respiratory_acidosis_prefix}_lower",
                        upper_surface=f"{respiratory_acidosis_prefix}_upper",
                        branch=branch,
                    )
                )
            elif pco2_state == "LOW" and hco3_state == "LOW":
                paths.extend(
                    _compensation_paths(
                        prefix=prefix,
                        ph_state="NEAR_NORMAL",
                        base=base,
                        lower_surface="respiratory_alkalosis_lower",
                        upper_surface="respiratory_alkalosis_upper",
                        branch=branch,
                    )
                )
            else:
                paths.append(
                    _path(
                        path_id=prefix,
                        ph_state="NEAR_NORMAL",
                        requirements=base,
                        branch=branch,
                    )
                )

    result = tuple(paths)
    if len(result) != TERMINAL_PATHS_PER_BRANCH:
        raise BostonEnvelopeCertificationError(
            "Terminal-path catalog count does not match its versioned contract."
        )
    return result


def _signature_key(
    signature: BostonClassificationSignature,
) -> tuple[int, int, int, int, bool]:
    acid_order = {value: index for index, value in enumerate(AcidBaseStateCode)}
    primary_order = {value: index for index, value in enumerate(PrimaryProcessCode)}
    expected_order = {value: index for index, value in enumerate(ExpectedCompensationCode)}
    measured_order = {value: index for index, value in enumerate(MeasuredVsExpectedCode)}
    return (
        acid_order[signature.acid_base_state],
        primary_order[signature.primary_process],
        expected_order[signature.expected_compensation],
        measured_order[signature.measured_vs_expected],
        signature.mixed_disorder_flag,
    )


def certify_boston_envelope(
    *,
    ph_lower: float,
    ph_upper: float,
    paco2_lower: float,
    paco2_upper: float,
    branches: tuple[BostonChronicityBranch, ...] = tuple(BostonChronicityBranch),
) -> CertifiedBostonEnvelope:
    """Return complete branch-specific signature sets or fail closed."""

    ph_lower_fraction = _fraction_from_float(ph_lower)
    ph_upper_fraction = _fraction_from_float(ph_upper)
    paco2_lower_fraction = _fraction_from_float(paco2_lower)
    paco2_upper_fraction = _fraction_from_float(paco2_upper)
    if not (
        0 < ph_lower_fraction < ph_upper_fraction
        and 0 < paco2_lower_fraction < paco2_upper_fraction
    ):
        raise BostonEnvelopeCertificationError(
            "Envelope bounds must be positive, ordered, and nondegenerate."
        )
    if (
        not isinstance(branches, tuple)
        or not branches
        or len(set(branches)) != len(branches)
        or any(not isinstance(branch, BostonChronicityBranch) for branch in branches)
        or tuple(branch for branch in BostonChronicityBranch if branch in branches) != branches
    ):
        raise BostonEnvelopeCertificationError(
            "Envelope branches must be a nonempty canonical branch tuple."
        )

    bands = _ph_bands(
        ph_lower=ph_lower_fraction,
        ph_upper=ph_upper_fraction,
    )
    branch_paths = {branch: _terminal_paths(branch) for branch in branches}
    for precision in CERTIFICATION_PRECISION_DIGITS:
        resolved: dict[BostonChronicityBranch, tuple[bool, ...]] = {}
        unresolved = False
        for branch in branches:
            decisions: list[bool] = []
            for path in branch_paths[branch]:
                decision = _path_feasibility(
                    path,
                    band=bands[path.ph_state],
                    x_lower=paco2_lower_fraction,
                    x_upper=paco2_upper_fraction,
                    precision=precision,
                )
                if decision is None:
                    unresolved = True
                    break
                decisions.append(decision)
            if unresolved:
                break
            resolved[branch] = tuple(decisions)
        if unresolved:
            continue

        certified_branches: list[CertifiedBostonBranch] = []
        for branch in branches:
            signatures = {
                path.signature
                for path, feasible in zip(
                    branch_paths[branch],
                    resolved[branch],
                    strict=True,
                )
                if feasible
            }
            if not signatures:
                raise BostonEnvelopeCertificationError(
                    "Certified terminal paths produced no Boston signature."
                )
            certified_branches.append(
                CertifiedBostonBranch(
                    chronicity_branch=branch,
                    signatures=tuple(sorted(signatures, key=_signature_key)),
                )
            )
        return CertifiedBostonEnvelope(
            branches=tuple(certified_branches),
            decision_surface_count=DECISION_SURFACE_COUNT,
            terminal_path_count=TERMINAL_PATHS_PER_BRANCH * len(branches),
            certification_precision_digits=precision,
        )

    raise BostonEnvelopeCertificationError(
        "Boston terminal-path feasibility could not be certified under precision escalation."
    )

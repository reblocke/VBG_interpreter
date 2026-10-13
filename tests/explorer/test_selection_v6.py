"""Selection edge cases and provenance not asserted by browser scenarios."""

from dataclasses import replace

import pytest

from vbg_interpreter import interpret_vbg
from vbg_interpreter.models import (
    CurrentChemistry,
    CurrentVbg,
    Hco3Basis,
    Pco2Unit,
    SaturationInput,
    SaturationUnit,
    VbgExplorerRequest,
)


def result(**fields):
    if fields.get("pco2") is not None:
        fields.setdefault("pco2_unit", Pco2Unit.MMHG)
    return interpret_vbg(VbgExplorerRequest(CurrentVbg(**fields)))


P, C, H = 7.32, 55, 28.34660584599947
ABS, REL = 1e-10, 1e-12


def close(actual, expected):
    assert actual == pytest.approx(expected, abs=ABS, rel=REL)


def make_gas(core, **kwargs):
    p, c, h = core
    fields = dict(
        ph=P if p else None,
        pco2=C if c else None,
        pco2_unit=Pco2Unit.MMHG if c else None,
        hco3_mmol_l=H if h else None,
    )
    fields.update(kwargs)
    return CurrentVbg(**fields)


@pytest.mark.parametrize("core", [(True, False, True), (False, True, True)])
@pytest.mark.parametrize("hbasis", list(Hco3Basis))
def test_reconstructed_selection_preserves_bicarbonate_basis(core, hbasis):
    # Browser chain labels do not verify the original HCO3 provenance used by each route.
    gas = make_gas(core, hco3_basis=hbasis)
    r = interpret_vbg(VbgExplorerRequest(gas))
    component = r.arterial_ph_estimate if not core[0] else r.arterial_paco2_estimate
    assert component.selection.source_values["hco3"]["basis"] == hbasis


@pytest.mark.parametrize("sat,point", [(0, 34.54), (93, 55)])
def test_saturation_edges_keep_selected_method(sat, point):
    r = result(pco2=55, venous_o2_saturation=SaturationInput(sat, SaturationUnit.PERCENTAGE_POINTS))
    close(r.arterial_paco2_estimate.values["point"], point)
    assert r.arterial_paco2_estimate.method_id == "farkas_simplified_93_v1"


def test_chained_warning_and_supplied_axis_precedence():
    r = result(
        ph=0.32,
        pco2=55,
        hco3_mmol_l=H,
        venous_o2_saturation=SaturationInput(75, SaturationUnit.PERCENTAGE_POINTS),
    )
    assert r.arterial_ph_estimate.selection.source_coordinate_origin == "SUPPLIED"
    assert not r.arterial_ph_estimate.selection.interpretation_suitable
    assert r.arterial_paco2_estimate.selection.interpretation_suitable
    assert r.provisional_interpretation.status == "UNAVAILABLE_UNRELIABLE_INPUT"
    # A flagged operand suppresses the dependent chain, not finite arithmetic.
    r = result(ph=0.32, hco3_mmol_l=H)
    assert r.arterial_paco2_estimate.status == "AVAILABLE"
    assert not r.arterial_paco2_estimate.selection.interpretation_suitable


def test_redundant_bicarbonate_does_not_replace_supplied_pair():
    full = make_gas(
        (True, True, False),
        venous_o2_saturation=SaturationInput(75, SaturationUnit.PERCENTAGE_POINTS),
    )
    baseline = interpret_vbg(VbgExplorerRequest(full))
    redundant = interpret_vbg(VbgExplorerRequest(replace(full, hco3_mmol_l=40)))
    assert redundant.arterial_ph_estimate == baseline.arterial_ph_estimate
    assert redundant.arterial_paco2_estimate == baseline.arterial_paco2_estimate


@pytest.mark.parametrize("ph,h,bmp", [(None, 120, 12), (0.32, 25, 120)])
def test_bicarbonate_warnings_preserve_direct_finite_subtraction(ph, h, bmp):
    r = interpret_vbg(
        VbgExplorerRequest(
            CurrentVbg(ph=ph, hco3_mmol_l=h), CurrentChemistry(serum_total_co2_mmol_l=bmp)
        )
    )
    assert r.input_observations
    close(r.chemistry["bmp_gas_bicarbonate_comparison"].values["bmp_minus_gas_hco3"], bmp - h)

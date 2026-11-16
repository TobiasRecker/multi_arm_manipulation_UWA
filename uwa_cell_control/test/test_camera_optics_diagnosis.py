from pathlib import Path
import runpy
import pytest

turns=runpy.run_path(str(Path(__file__).resolve().parents[2]/'tools/diagnose_digitization_camera.py'))['radial_turns']


def test_identity_radial_model_has_no_turn():
    assert turns([0.,0.,0.,0.,0.])==[]


def test_known_radial_turn_and_current_saved_lf_coefficients():
    assert turns([-1.,0.,0.,0.,0.])==pytest.approx([1/(3**.5)])
    assert turns([-.07704041188251143,3.6963398138992356,-.0003080653384644037,.01088286761577099,-21.56029987419677])==pytest.approx([.485245873428973])

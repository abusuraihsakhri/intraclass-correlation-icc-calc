import csv
import json

import pytest

from icc_calc import calculate_metrics, calculate_from_ratings, design_effect, process_batch, main


def test_balanced_two_way_reference_example():
    # Two raters differ by a systematic +1; consistency is perfect but
    # absolute agreement is not. This distinguishes ICC(2) from ICC(3).
    result = calculate_from_ratings([[1, 2], [2, 3], [3, 4], [4, 5]])
    assert result["ms_between"] == pytest.approx(10 / 3)
    assert result["ms_within"] == pytest.approx(0.5)
    assert result["ms_rater"] == pytest.approx(2)
    assert result["ms_error"] == pytest.approx(0)
    assert result["icc_1_1"] == pytest.approx(17 / 23)
    assert result["icc_1_k"] == pytest.approx(0.85)
    assert result["icc_2_1"] == pytest.approx(10 / 13)
    assert result["icc_2_k"] == pytest.approx(20 / 23)
    assert result["icc_3_1"] == pytest.approx(1.0)
    assert result["icc_3_k"] == pytest.approx(1.0)


def test_identical_raters_have_perfect_reliability():
    result = calculate_from_ratings([[1, 1, 1], [2, 2, 2], [4, 4, 4]])
    for key in ("icc_1_1", "icc_1_k", "icc_2_1", "icc_2_k", "icc_3_1", "icc_3_k"):
        assert result[key] == pytest.approx(1)


def test_negative_icc_not_clamped():
    result = calculate_metrics(ms_between=1, ms_within=3, subjects=8, raters=2)
    assert result["icc_1_1"] == pytest.approx(-0.5)
    assert result["icc_2_1"] is None


def test_zero_variance_is_not_reported_as_zero_icc():
    result = calculate_from_ratings([[3, 3], [3, 3], [3, 3]])
    assert all(result[key] is None for key in (
        "icc_1_1", "icc_1_k", "icc_2_1", "icc_2_k", "icc_3_1", "icc_3_k"
    ))


@pytest.mark.parametrize("ratings", [
    [], [[1, 2]], [[1], [2]], [[1, 2], [3]], [[1, None], [2, 3]],
    [[1, 2], [3, float("nan")]], [[1, 2], [3, float("inf")]],
])
def test_bad_matrix_rejected(ratings):
    with pytest.raises(ValueError):
        calculate_from_ratings(ratings)


@pytest.mark.parametrize("kwargs", [
    dict(ms_between=-1, ms_within=2, subjects=4, raters=2),
    dict(ms_between=1, ms_within=2, subjects=1, raters=2),
    dict(ms_between=1, ms_within=2, subjects=4, raters=2.5),
    dict(ms_between=1, ms_within=2, subjects=4, raters=2, ms_rater=3),
    dict(ms_between=float("inf"), ms_within=2, subjects=4, raters=2),
    dict(ms_between=1, ms_within=2, subjects=4, raters=2, cluster_size=5),
])
def test_bad_summary_rejected(kwargs):
    with pytest.raises(ValueError):
        calculate_metrics(**kwargs)


def test_independent_cluster_design_effect():
    assert design_effect(6, 0.05) == pytest.approx(1.25)
    result = calculate_metrics(ms_between=10, ms_within=2, subjects=5,
                               raters=2, cluster_size=6, cluster_icc=0.05)
    assert result["design_effect"] == pytest.approx(1.25)
    for rho in (-0.1, 1.1, float("nan")):
        with pytest.raises(ValueError):
            design_effect(5, rho)


def test_cli_json(capsys):
    assert main(["single", "--ms-between", "10", "--ms-within", "2",
                 "--subjects", "5", "--raters", "2"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["icc_1_1"] == pytest.approx(2/3)


def test_batch_success_and_formula_sanitization(tmp_path):
    inp, out = tmp_path / "input.csv", tmp_path / "result.csv"
    inp.write_text("label,subjects,raters,ms_between,ms_within,ms_rater,ms_error\n"
                   "=HYPERLINK(1),4,2,3.333333333333,0.5,2,0\n", encoding="utf-8")
    assert process_batch(inp, out) == 1
    with out.open(newline="", encoding="utf-8") as stream:
        row = next(csv.DictReader(stream))
    assert row["label"].startswith("'=")
    assert float(row["icc_3_1"]) == pytest.approx(1)


def test_batch_fails_fast_without_partial_output(tmp_path):
    inp, out = tmp_path / "input.csv", tmp_path / "result.csv"
    inp.write_text("subjects,raters,ms_between,ms_within\n4,2,10,2\n4,2,INVALID,2\n")
    with pytest.raises(ValueError, match="row 3"):
        process_batch(inp, out)
    assert not out.exists()

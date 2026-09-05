import pytest
from icc_calc import calculate_metrics, process_batch


def test_icc_calc_single():
    res = calculate_metrics(v1=12.0, v2=4.0)
    assert "score" in res
    assert "classification" in res
    assert res["score"] > 0


def test_icc_calc_batch(tmp_path):
    csv_in = tmp_path / "in.csv"
    csv_out = tmp_path / "out.csv"
    csv_in.write_text("Patient,v1,v2\nPat_001,15.0,3.0\nPat_002,5.0,1.0\n", encoding="utf-8")

    process_batch(str(csv_in), str(csv_out))
    assert csv_out.exists()
    content = csv_out.read_text(encoding="utf-8")
    assert "Pat_001" in content
    assert "score" in content


def test_icc_calc_batch_missing_input(tmp_path):
    """process_batch raises FileNotFoundError for missing input files."""
    csv_in = tmp_path / "nonexistent.csv"
    csv_out = tmp_path / "out.csv"
    with pytest.raises(FileNotFoundError):
        process_batch(str(csv_in), str(csv_out))


def test_icc_calc_batch_directory_input(tmp_path):
    """process_batch raises ValueError when input path is a directory."""
    csv_out = tmp_path / "out.csv"
    with pytest.raises(ValueError):
        process_batch(str(tmp_path), str(csv_out))

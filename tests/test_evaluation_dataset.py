from pathlib import Path

import pytest

from app.evaluation_dataset import load_evaluation_cases


def test_load_evaluation_cases(tmp_path: Path) -> None:
    cases_file = tmp_path / "cases.jsonl"
    cases_file.write_text(
        (
            '{"query":"Duplicate card charge",'
            '"expected_product":"Credit card"}\n'
            '{"query":"Unexpected checking account fee",'
            '"expected_product":"Checking or savings account"}\n'
        ),
        encoding="utf-8",
    )

    cases = load_evaluation_cases(cases_file)

    assert len(cases) == 2
    assert cases[0].query == "Duplicate card charge"
    assert cases[0].expected_product == "Credit card"
    assert cases[1].expected_product == "Checking or savings account"


def test_load_evaluation_cases_reports_invalid_line(
    tmp_path: Path,
) -> None:
    cases_file = tmp_path / "cases.jsonl"
    cases_file.write_text(
        '{"query":"Valid case","expected_product":"Credit card"}\n'
        '{invalid json}\n',
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Invalid evaluation case on line 2",
    ):
        load_evaluation_cases(cases_file)


def test_load_evaluation_cases_rejects_empty_dataset(
    tmp_path: Path,
) -> None:
    cases_file = tmp_path / "cases.jsonl"
    cases_file.write_text("", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="Evaluation dataset contains no cases",
    ):
        load_evaluation_cases(cases_file)
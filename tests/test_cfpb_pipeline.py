import json
from pathlib import Path

import pytest

from app.ingestion.pipeline import process_cfpb_csv

CSV_HEADER = (
    "Complaint ID,Date received,Product,Issue,Sub-issue,"
    "Consumer complaint narrative,Company,State\n"
)

def test_process_cfpb_csv_filters_and_reports(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "complaints.csv"
    output_path = tmp_path / "processed" / "complaints.jsonl"

    input_path.write_text(
        CSV_HEADER
        + "1001,2026-03-01,Credit card,Billing problem,,"
        "The bank charged the account twice for one purchase,"
        "Example Bank,TX\n"
        + "1001,2026-03-01,Credit card,Billing problem,,"
        "The bank charged the account twice for one purchase,"
        "Example Bank,TX\n"
        + "1002,2026-03-02,Mortgage,Payment problem,,"
        "The mortgage payment was incorrectly processed,"
        "Example Mortgage,CA\n"
        + "1003,2026-03-03,Checking or savings account,Fees,,"
        "Too short,Example Bank,NY\n",
        encoding="utf-8",
    )

    summary = process_cfpb_csv(input_path, output_path)

    records = [
        json.loads(line)
        for line in output_path.read_text(
            encoding="utf-8"
        ).splitlines()
    ]

    assert len(records) == 1
    assert records[0]["complaint_id"] == "1001"
    assert summary.total_rows == 4
    assert summary.accepted_rows == 1
    assert summary.duplicate_rows == 1
    assert summary.skipped_product_rows == 1
    assert summary.rejected_rows == 1

def test_process_cfpb_csv_rejects_invalid_limit(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
        match="max_records must be at least 1",
    ):
        process_cfpb_csv(
            tmp_path / "input.csv",
            tmp_path / "output.jsonl",
            max_records=0,
        )


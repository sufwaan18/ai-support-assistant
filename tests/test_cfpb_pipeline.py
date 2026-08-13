import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from app.ingestion.pipeline import (
    process_cfpb_csv,
    process_cfpb_zip,
)


CSV_HEADER = (
    "Complaint ID,Date received,Product,Issue,Sub-issue,"
    "Consumer complaint narrative,Company,State\n"
)

CSV_ROWS = (
    "1001,2026-03-01,Credit card,Billing problem,,"
    "The bank charged the account twice for one purchase,"
    "Example Bank,TX\n"
    "1001,2026-03-01,Credit card,Billing problem,,"
    "The bank charged the account twice for one purchase,"
    "Example Bank,TX\n"
    "1002,2026-03-02,Mortgage,Payment problem,,"
    "The mortgage payment was incorrectly processed,"
    "Example Mortgage,CA\n"
    "1003,2026-03-03,Checking or savings account,Fees,,"
    "Too short,Example Bank,NY\n"
)


def assert_processing_result(
    output_path: Path,
    summary: object,
) -> None:
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


def test_process_cfpb_csv_filters_and_reports(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "complaints.csv"
    output_path = tmp_path / "processed" / "complaints.jsonl"
    input_path.write_text(
        CSV_HEADER + CSV_ROWS,
        encoding="utf-8",
    )

    summary = process_cfpb_csv(
        input_path,
        output_path,
    )

    assert_processing_result(output_path, summary)


def test_process_cfpb_zip_streams_and_reports(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "complaints.csv.zip"
    output_path = tmp_path / "processed" / "complaints.jsonl"

    with ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "complaints.csv",
            CSV_HEADER + CSV_ROWS,
        )

    summary = process_cfpb_zip(
        archive_path=archive_path,
        output_path=output_path,
    )

    assert_processing_result(output_path, summary)


def test_process_cfpb_zip_rejects_unsafe_member(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "unsafe.zip"

    with ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "../complaints.csv",
            CSV_HEADER + CSV_ROWS,
        )

    with pytest.raises(
        ValueError,
        match="unexpected file path",
    ):
        process_cfpb_zip(
            archive_path=archive_path,
            output_path=tmp_path / "output.jsonl",
        )


def test_process_cfpb_csv_rejects_invalid_limit(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "complaints.csv"
    input_path.write_text(
        CSV_HEADER,
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="max_records must be at least 1",
    ):
        process_cfpb_csv(
            input_path,
            tmp_path / "output.jsonl",
            max_records=0,
        )
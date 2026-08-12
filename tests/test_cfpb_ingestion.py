from datetime import date
from pathlib import Path
from app.ingestion.cfpb import (
    CFPBComplaint,
    RejectedComplaint,
    load_complaints_csv_with_report,
    write_complaints_jsonl,
    load_complaints_csv,
    transform_complaint,
)
def test_valid_cfpb_complaint() -> None:
    complaint = CFPBComplaint(
        complaint_id="1234567",
        date_received="2026-01-15",
        product="Credit card",
        issue="Problem with a purchase",
        sub_issue=None,
        narrative="A merchant charged my credit card twice for one purchase.",
        company="Example Bank",
        state="TX",
    )

    assert complaint.complaint_id == "1234567"
    assert complaint.date_received == date(2026, 1, 15)
    assert complaint.product == "Credit card"


import pytest
from pydantic import ValidationError
def test_rejects_short_narrative() -> None:
    with pytest.raises(ValidationError):
        CFPBComplaint(
            complaint_id="1234567",
            date_received="2026-01-15",
            product="Credit card",
            issue="Problem with a purchase",
            narrative="Too short",
            company="Example Bank",
            state="TX",
        )

def test_transform_complaint() -> None:
    raw = {
        "Complaint ID": "7654321",
        "Date received": "2026-02-10",
        "Product": "Checking or savings account",
        "Issue": "Managing an account",
        "Sub-issue": "",
        "Consumer complaint narrative": (
            "The bank charged an unexpected monthly maintenance fee."
        ),
        "Company": "Example Financial",
        "State": "CA",
    }

    complaint = transform_complaint(raw)

    assert complaint.complaint_id == "7654321"
    assert complaint.sub_issue is None
    assert complaint.state == "CA"

def test_load_complaints_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "complaints.csv"
    csv_path.write_text(
        "Complaint ID,Date received,Product,Issue,Sub-issue,"
        "Consumer complaint narrative,Company,State\n"
        "1001,2026-03-01,Credit card,Billing problem,,"
        "The bank charged my account twice for the same purchase,"
        "Example Bank,TX\n",
        encoding="utf-8",
    )

    complaints = load_complaints_csv(csv_path)

    assert len(complaints) == 1
    assert complaints[0].complaint_id == "1001"
    assert complaints[0].product == "Credit card"

def test_write_complaints_jsonl(tmp_path: Path) -> None:
    complaint = CFPBComplaint(
        complaint_id="2001",
        date_received="2026-03-02",
        product="Credit card",
        issue="Billing problem",
        narrative="The customer found an unexpected charge on the account.",
        company="Example Bank",
        state="NY",
    )
    output_path = tmp_path / "processed" / "complaints.jsonl"

    write_complaints_jsonl([complaint], output_path)

    output = output_path.read_text(encoding="utf-8")

    assert '"complaint_id": "2001"' in output
    assert '"date_received": "2026-03-02"' in output

def test_load_complaints_csv_reports_invalid_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "complaints.csv"
    csv_path.write_text(
        "Complaint ID,Date received,Product,Issue,Sub-issue,"
        "Consumer complaint narrative,Company,State\n"
        "1001,2026-03-01,Credit card,Billing problem,,"
        "The bank charged my account twice for the same purchase,"
        "Example Bank,TX\n"
        "1002,2026-03-02,Credit card,Billing problem,,"
        "Too short,Example Bank,CA\n",
        encoding="utf-8",
    )

    complaints, rejected = load_complaints_csv_with_report(csv_path)

    assert len(complaints) == 1
    assert complaints[0].complaint_id == "1001"
    assert len(rejected) == 1
    assert rejected[0].row_number == 3
    assert rejected[0].complaint_id == "1002"
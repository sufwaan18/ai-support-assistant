from datetime import date

from pydantic import BaseModel, ConfigDict, Field

import csv
import json
from pathlib import Path


class CFPBComplaint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    complaint_id: str = Field(min_length=1)
    date_received: date
    product: str = Field(min_length=1)
    issue: str = Field(min_length=1)
    sub_issue: str | None = None
    narrative: str = Field(min_length=20)
    company: str = Field(min_length=1)
    state: str | None = Field(default=None, min_length=2, max_length=2)

def transform_complaint(raw: dict[str, str]) -> CFPBComplaint:
    return CFPBComplaint(
        complaint_id=raw["Complaint ID"],
        date_received=raw["Date received"],
        product=raw["Product"],
        issue=raw["Issue"],
        sub_issue=raw.get("Sub-issue") or None,
        narrative=raw["Consumer complaint narrative"],
        company=raw["Company"],
        state=raw.get("State") or None,
    )

def load_complaints_csv(input_path: Path) -> list[CFPBComplaint]:
    complaints: list[CFPBComplaint] = []

    with input_path.open(encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)

        for raw in reader:
            complaints.append(transform_complaint(raw))

    return complaints

def write_complaints_jsonl(
    complaints: list[CFPBComplaint],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as output_file:
        for complaint in complaints:
            record = complaint.model_dump(mode="json")
            output_file.write(json.dumps(record) + "\n")

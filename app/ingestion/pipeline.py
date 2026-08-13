import csv
import json
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from app.ingestion.cfpb import transform_complaint


DEFAULT_PRODUCTS = frozenset(
    {
        "Credit card",
        "Credit card or prepaid card",
        "Checking or savings account",
    }
)

class ProcessingSummary(BaseModel):
    total_rows: int = Field(ge=0)
    accepted_rows: int = Field(ge=0)
    rejected_rows: int = Field(ge=0)
    duplicate_rows: int = Field(ge=0)
    skipped_product_rows: int = Field(ge=0)

def process_cfpb_csv(
    input_path: Path,
    output_path: Path,
    max_records: int = 5_000,
    products: frozenset[str] = DEFAULT_PRODUCTS,
) -> ProcessingSummary:
    if max_records < 1:
        raise ValueError("max_records must be at least 1")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    total_rows = 0
    accepted_rows = 0
    rejected_rows = 0
    duplicate_rows = 0
    skipped_product_rows = 0
    complaint_ids: set[str] = set()

    with (
        input_path.open(
            encoding="utf-8-sig",
            newline="",
        ) as input_file,
        output_path.open(
            "w",
            encoding="utf-8",
        ) as output_file,
    ):
        reader = csv.DictReader(input_file)

        for raw in reader:
            if accepted_rows >= max_records:
                break

            total_rows += 1

            if raw.get("Product") not in products:
                skipped_product_rows += 1
                continue

            try:
                complaint = transform_complaint(raw)
            except (KeyError, ValidationError):
                rejected_rows += 1
                continue

            if complaint.complaint_id in complaint_ids:
                duplicate_rows += 1
                continue

            complaint_ids.add(complaint.complaint_id)
            record = complaint.model_dump(mode="json")
            output_file.write(json.dumps(record) + "\n")
            accepted_rows += 1

    return ProcessingSummary(
        total_rows=total_rows,
        accepted_rows=accepted_rows,
        rejected_rows=rejected_rows,
        duplicate_rows=duplicate_rows,
        skipped_product_rows=skipped_product_rows,
    )
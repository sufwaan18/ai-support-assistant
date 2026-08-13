import csv
import json
from collections.abc import Iterable
from io import TextIOWrapper
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

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


def process_complaint_rows(
    rows: Iterable[dict[str, str]],
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

    with output_path.open("w", encoding="utf-8") as output_file:
        for raw in rows:
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
            output_file.write(
                json.dumps(
                    complaint.model_dump(mode="json")
                )
                + "\n"
            )
            accepted_rows += 1

        return ProcessingSummary(
        total_rows=total_rows,
        accepted_rows=accepted_rows,
        rejected_rows=rejected_rows,
        duplicate_rows=duplicate_rows,
        skipped_product_rows=skipped_product_rows,
    )


def process_cfpb_csv(
    input_path: Path,
    output_path: Path,
    max_records: int = 5_000,
    products: frozenset[str] = DEFAULT_PRODUCTS,
) -> ProcessingSummary:
    with input_path.open(
        encoding="utf-8-sig",
        newline="",
    ) as input_file:
        reader = csv.DictReader(input_file)

        return process_complaint_rows(
            rows=reader,
            output_path=output_path,
            max_records=max_records,
            products=products,
        )


def validate_cfpb_archive(
    archive: ZipFile,
) -> str:
    files = [
        member
        for member in archive.infolist()
        if not member.is_dir()
    ]

    if len(files) != 1:
        raise ValueError(
            "CFPB archive must contain exactly one file"
        )

    member = files[0]
    member_path = PurePosixPath(member.filename)

    if (
        member_path.is_absolute()
        or ".." in member_path.parts
        or member_path.name != "complaints.csv"
    ):
        raise ValueError(
            "CFPB archive contains an unexpected file path"
        )

    return member.filename


def process_cfpb_zip(
    archive_path: Path,
    output_path: Path,
    max_records: int = 5_000,
    products: frozenset[str] = DEFAULT_PRODUCTS,
) -> ProcessingSummary:
    if not archive_path.is_file():
        raise FileNotFoundError(
            f"CFPB archive not found: {archive_path}"
        )

    with ZipFile(archive_path) as archive:
        member_name = validate_cfpb_archive(archive)

        with (
            archive.open(member_name) as binary_file,
            TextIOWrapper(
                binary_file,
                encoding="utf-8-sig",
                newline="",
            ) as text_file,
        ):
            reader: csv.DictReader[str] = csv.DictReader(
                text_file
            )

            return process_complaint_rows(
                rows=reader,
                output_path=output_path,
                max_records=max_records,
                products=products,
            )
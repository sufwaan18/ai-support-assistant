import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from app.ingestion.downloader import download_cfpb_dataset
from app.ingestion.pipeline import (
    ProcessingSummary,
    process_cfpb_zip,
)


CFPB_SOURCE_URL = (
    "https://files.consumerfinance.gov/"
    "ccdb/complaints.csv.zip"
)


class DatasetManifest(BaseModel):
    source_url: str
    created_at: datetime
    maximum_records: int = Field(ge=1)
    output_file: str
    output_sha256: str = Field(min_length=64, max_length=64)
    processing: ProcessingSummary


def calculate_sha256(file_path: Path) -> str:
    digest = hashlib.sha256()

    with file_path.open("rb") as input_file:
        for chunk in iter(
            lambda: input_file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def write_dataset_manifest(
    manifest: DatasetManifest,
    output_path: Path,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            manifest.model_dump(mode="json"),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return output_path


def build_cfpb_dataset(
    working_directory: Path,
    max_records: int = 5_000,
) -> DatasetManifest:
    if max_records < 1:
        raise ValueError("max_records must be at least 1")

    raw_directory = working_directory / "raw"
    processed_directory = working_directory / "processed"

    archive_path = raw_directory / "complaints.csv.zip"
    output_path = processed_directory / "complaints.jsonl"
    manifest_path = processed_directory / "manifest.json"

    if not archive_path.is_file():
        download_cfpb_dataset(archive_path)

    summary = process_cfpb_zip(
        archive_path=archive_path,
        output_path=output_path,
        max_records=max_records,
    )

    manifest = DatasetManifest(
        source_url=CFPB_SOURCE_URL,
        created_at=datetime.now(UTC),
        maximum_records=max_records,
        output_file=str(output_path),
        output_sha256=calculate_sha256(output_path),
        processing=summary,
    )

    write_dataset_manifest(manifest, manifest_path)

    return manifest
import json
from datetime import UTC, datetime
from pathlib import Path

from app.ingestion.dataset import (
    DatasetManifest,
    calculate_sha256,
    write_dataset_manifest,
)
from app.ingestion.pipeline import ProcessingSummary


def test_calculate_sha256(tmp_path: Path) -> None:
    data_path = tmp_path / "complaints.jsonl"
    data_path.write_text(
        '{"complaint_id": "1001"}\n',
        encoding="utf-8",
    )

    checksum = calculate_sha256(data_path)

    assert len(checksum) == 64
    assert checksum == calculate_sha256(data_path)


def test_write_dataset_manifest(tmp_path: Path) -> None:
    manifest = DatasetManifest(
        source_url="https://example.test/complaints.csv.zip",
        created_at=datetime(2026, 8, 13, tzinfo=UTC),
        maximum_records=5_000,
        output_file="data/processed/complaints.jsonl",
        output_sha256="a" * 64,
        processing=ProcessingSummary(
            total_rows=120,
            accepted_rows=100,
            rejected_rows=5,
            duplicate_rows=5,
            skipped_product_rows=10,
        ),
    )
    output_path = tmp_path / "processed" / "manifest.json"

    result = write_dataset_manifest(manifest, output_path)
    saved_manifest = json.loads(
        output_path.read_text(encoding="utf-8")
    )

    assert result == output_path
    assert saved_manifest["maximum_records"] == 5_000
    assert saved_manifest["processing"]["accepted_rows"] == 100
    assert saved_manifest["output_sha256"] == "a" * 64
from pathlib import Path
from zipfile import BadZipFile, ZipFile

import pytest
import httpx

from app.ingestion.downloader import (
    CFPB_COMPLAINTS_URL,
    download_cfpb_dataset,
    extract_cfpb_csv
)


def test_download_cfpb_dataset(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == CFPB_COMPLAINTS_URL

        return httpx.Response(
            status_code=200,
            content=b"fake-zip-content",
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    output_path = tmp_path / "raw" / "complaints.csv.zip"

    result = download_cfpb_dataset(output_path, client=client)

    assert result == output_path
    assert output_path.read_bytes() == b"fake-zip-content"

    client.close()

def test_extract_cfpb_csv(tmp_path: Path) -> None:
    archive_path = tmp_path / "complaints.csv.zip"

    with ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "complaints.csv",
            "Complaint ID,Product\n1001,Credit card\n",
        )

    output_path = extract_cfpb_csv(
        archive_path,
        tmp_path / "extracted",
    )

    assert output_path == tmp_path / "extracted" / "complaints.csv"
    assert output_path.read_text(encoding="utf-8") == (
        "Complaint ID,Product\n1001,Credit card\n"
    )

def test_extract_cfpb_csv_rejects_unsafe_path(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "unsafe.zip"

    with ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "../complaints.csv",
            "unsafe content",
        )

    with pytest.raises(
        ValueError,
        match="unexpected file path",
    ):
        extract_cfpb_csv(
            archive_path,
            tmp_path / "extracted",
        )

    assert not (tmp_path / "complaints.csv").exists()

def test_extract_cfpb_csv_rejects_invalid_zip(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "invalid.zip"
    archive_path.write_bytes(b"this is not a zip archive")

    with pytest.raises(BadZipFile):
        extract_cfpb_csv(
            archive_path,
            tmp_path / "extracted",
        )
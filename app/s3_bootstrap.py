import shutil
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Protocol

import boto3


class S3DownloadClient(Protocol):
    def download_file(
        self,
        bucket: str,
        key: str,
        filename: str,
    ) -> None:
        """Download one S3 object to a local file."""


def bootstrap_rag_snapshot(
    *,
    bucket: str,
    key: str,
    database_directory: Path,
    client: S3DownloadClient | None = None,
) -> bool:
    """Download and extract ChromaDB when it is not already present."""

    if not bucket and not key:
        return False

    if not bucket or not key:
        raise ValueError(
            "RAG snapshot bucket and key must be configured together"
        )

    if (
        database_directory.exists()
        and any(database_directory.iterdir())
    ):
        return False

    parent_directory = database_directory.parent
    parent_directory.mkdir(parents=True, exist_ok=True)

    s3_client = client or boto3.client("s3")

    with TemporaryDirectory(
        dir=parent_directory,
        prefix="rag-bootstrap-",
    ) as temporary_directory:
        temporary_path = Path(temporary_directory)
        archive_path = temporary_path / "chroma-snapshot.tar.gz"
        extraction_path = temporary_path / "extracted"
        extraction_path.mkdir()

        s3_client.download_file(
            bucket,
            key,
            str(archive_path),
        )

        with tarfile.open(archive_path, mode="r:gz") as archive:
            archive.extractall(
                path=extraction_path,
                filter="data",
            )

        extracted_database = extraction_path / "chroma"

        if not extracted_database.is_dir():
            raise RuntimeError(
                "RAG snapshot does not contain a chroma directory"
            )

        if database_directory.exists():
            database_directory.rmdir()

        shutil.move(
            str(extracted_database),
            str(database_directory),
        )

    return True
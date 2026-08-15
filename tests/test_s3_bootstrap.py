import shutil
import tarfile
from pathlib import Path

import pytest

from app.s3_bootstrap import bootstrap_rag_snapshot


class FakeS3Client:
    def __init__(self, archive_path: Path) -> None:
        self.archive_path = archive_path
        self.calls: list[tuple[str, str, str]] = []

    def download_file(
        self,
        bucket: str,
        key: str,
        filename: str,
    ) -> None:
        self.calls.append((bucket, key, filename))
        shutil.copyfile(self.archive_path, filename)


def create_snapshot_archive(tmp_path: Path) -> Path:
    snapshot_source = tmp_path / "snapshot-source"
    chroma_directory = snapshot_source / "chroma"
    chroma_directory.mkdir(parents=True)

    database_file = chroma_directory / "chroma.sqlite3"
    database_file.write_bytes(b"test-chroma-database")

    archive_path = tmp_path / "chroma-snapshot.tar.gz"

    with tarfile.open(archive_path, mode="w:gz") as archive:
        archive.add(
            chroma_directory,
            arcname="chroma",
        )

    return archive_path


def test_skips_download_without_s3_configuration(
    tmp_path: Path,
) -> None:
    downloaded = bootstrap_rag_snapshot(
        bucket="",
        key="",
        database_directory=tmp_path / "data" / "chroma",
    )

    assert downloaded is False


def test_requires_bucket_and_key_together(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
        match="must be configured together",
    ):
        bootstrap_rag_snapshot(
            bucket="example-bucket",
            key="",
            database_directory=tmp_path / "data" / "chroma",
        )


def test_downloads_and_extracts_snapshot(
    tmp_path: Path,
) -> None:
    archive_path = create_snapshot_archive(tmp_path)
    client = FakeS3Client(archive_path)
    database_directory = tmp_path / "data" / "chroma"

    downloaded = bootstrap_rag_snapshot(
        bucket="example-bucket",
        key="rag/chroma-snapshot.tar.gz",
        database_directory=database_directory,
        client=client,
    )

    assert downloaded is True
    assert (
        database_directory / "chroma.sqlite3"
    ).read_bytes() == b"test-chroma-database"
    assert len(client.calls) == 1
    assert client.calls[0][0] == "example-bucket"
    assert client.calls[0][1] == "rag/chroma-snapshot.tar.gz"


def test_preserves_existing_database(
    tmp_path: Path,
) -> None:
    archive_path = create_snapshot_archive(tmp_path)
    client = FakeS3Client(archive_path)
    database_directory = tmp_path / "data" / "chroma"
    database_directory.mkdir(parents=True)
    existing_file = database_directory / "chroma.sqlite3"
    existing_file.write_bytes(b"existing-database")

    downloaded = bootstrap_rag_snapshot(
        bucket="example-bucket",
        key="rag/chroma-snapshot.tar.gz",
        database_directory=database_directory,
        client=client,
    )

    assert downloaded is False
    assert existing_file.read_bytes() == b"existing-database"
    assert client.calls == []
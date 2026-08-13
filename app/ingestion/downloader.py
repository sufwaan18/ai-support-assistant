
import shutil
from pathlib import Path, PurePosixPath
from zipfile import ZipFile
import httpx


CFPB_COMPLAINTS_URL = (
    "https://files.consumerfinance.gov/ccdb/complaints.csv.zip"
)
MAX_CFPB_CSV_BYTES = 5 * 1024 * 1024 * 1024


def download_cfpb_dataset(
    output_path: Path,
    client: httpx.Client | None = None,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    http_client = client or httpx.Client(
        timeout=60.0,
        follow_redirects=True,
    )

    try:
        response = http_client.get(CFPB_COMPLAINTS_URL)
        response.raise_for_status()
        output_path.write_bytes(response.content)
    finally:
        if client is None:
            http_client.close()

    return output_path

def extract_cfpb_csv(
    archive_path: Path,
    destination_dir: Path,
) -> Path:
    with ZipFile(archive_path) as archive:
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

        if member.file_size > MAX_CFPB_CSV_BYTES:
            raise ValueError(
                "CFPB CSV exceeds the allowed extraction size"
            )

        destination_dir.mkdir(parents=True, exist_ok=True)
        output_path = destination_dir / "complaints.csv"

        with (
            archive.open(member) as source,
            output_path.open("wb") as destination,
        ):
            shutil.copyfileobj(source, destination)

    return output_path
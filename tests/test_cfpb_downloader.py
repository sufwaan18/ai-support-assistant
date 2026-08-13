from pathlib import Path

import httpx

from app.ingestion.downloader import (
    CFPB_COMPLAINTS_URL,
    download_cfpb_dataset,
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
    
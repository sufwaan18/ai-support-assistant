from pathlib import Path

import httpx


CFPB_COMPLAINTS_URL = (
    "https://files.consumerfinance.gov/ccdb/complaints.csv.zip"
)


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
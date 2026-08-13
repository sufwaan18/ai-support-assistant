import argparse
import json
from pathlib import Path

from app.ingestion.dataset import build_cfpb_dataset


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a validated CFPB complaint dataset.",
    )
    parser.add_argument(
        "--data-directory",
        type=Path,
        default=Path("data"),
        help="Directory for raw and processed CFPB data.",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=5_000,
        help="Maximum number of validated complaints to keep.",
    )

    return parser


def main() -> None:
    arguments = create_parser().parse_args()

    manifest = build_cfpb_dataset(
        working_directory=arguments.data_directory,
        max_records=arguments.max_records,
    )

    print(
        json.dumps(
            manifest.model_dump(mode="json"),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
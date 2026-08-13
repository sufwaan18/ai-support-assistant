import argparse
import json
from pathlib import Path

from app.embeddings import (
    DEFAULT_EMBEDDING_MODEL,
    SentenceTransformerEncoder,
)
from app.runtime_pipeline import (
    build_vector_index,
    write_runtime_summary,
)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate embeddings and build the CFPB ChromaDB index."
        ),
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("data/processed/complaints.jsonl"),
        help="Validated CFPB complaint JSONL file.",
    )
    parser.add_argument(
        "--embedded-output",
        type=Path,
        default=Path(
            "data/processed/embedded_complaints.jsonl"
        ),
        help="Destination for embedded complaint records.",
    )
    parser.add_argument(
        "--database-directory",
        type=Path,
        default=Path("data/chroma"),
        help="Persistent ChromaDB directory.",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path(
            "data/processed/index_summary.json"
        ),
        help="Destination for the indexing summary.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_EMBEDDING_MODEL,
        help="Sentence Transformer model name.",
    )
    parser.add_argument(
        "--embedding-batch-size",
        type=int,
        default=32,
        help="Number of complaints embedded together.",
    )
    parser.add_argument(
        "--indexing-batch-size",
        type=int,
        default=100,
        help="Number of vectors indexed together.",
    )

    return parser


def main() -> None:
    arguments = create_parser().parse_args()

    encoder = SentenceTransformerEncoder(
        model_name=arguments.model
    )

    summary = build_vector_index(
        source_path=arguments.source,
        embedded_path=arguments.embedded_output,
        database_directory=arguments.database_directory,
        encoder=encoder,
        embedding_batch_size=(
            arguments.embedding_batch_size
        ),
        indexing_batch_size=arguments.indexing_batch_size,
    )

    write_runtime_summary(
        summary,
        arguments.summary_output,
    )

    print(
        json.dumps(
            summary.model_dump(mode="json"),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
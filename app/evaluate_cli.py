import argparse
import json
from pathlib import Path

from app.embeddings import SentenceTransformerEncoder
from app.retrieval_evaluation import (
    DEFAULT_EVALUATION_CASES,
    evaluate_retrieval,
)
from app.vector_store import (
    create_persistent_collection,
    search_complaints,
)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate semantic retrieval using the local CFPB index."
        ),
    )
    parser.add_argument(
        "--database-directory",
        type=Path,
        default=Path("data/chroma"),
        help="Persistent ChromaDB directory.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help="Number of results retrieved for each query.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "data/processed/retrieval_evaluation.json"
        ),
        help="Destination for the evaluation summary.",
    )

    return parser


def main() -> None:
    arguments = create_parser().parse_args()

    encoder = SentenceTransformerEncoder()
    collection = create_persistent_collection(
        arguments.database_directory
    )

    def search(
        query: str,
        limit: int,
    ):
        return search_complaints(
            query=query,
            encoder=encoder,
            collection=collection,
            limit=limit,
        )

    summary = evaluate_retrieval(
        cases=DEFAULT_EVALUATION_CASES,
        search=search,
        limit=arguments.limit,
    )

    arguments.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    arguments.output.write_text(
        json.dumps(
            summary.model_dump(mode="json"),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
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
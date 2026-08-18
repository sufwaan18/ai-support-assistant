import argparse
import json
from pathlib import Path

from app.embeddings import SentenceTransformerEncoder
from app.evaluation_dataset import load_evaluation_cases
from app.retrieval_evaluation import evaluate_retrieval
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
        "--cases-file",
        type=Path,
        default=Path("evals/retrieval_cases.jsonl"),
        help="Path to the JSONL retrieval evaluation dataset.",
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

    evaluation_cases = load_evaluation_cases(
        arguments.cases_file
    )

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
        cases=evaluation_cases,
        search=search,
        limit=arguments.limit,
    )

    arguments.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    serialized_summary = json.dumps(
        summary.model_dump(mode="json"),
        indent=2,
        sort_keys=True,
    )

    arguments.output.write_text(
        serialized_summary + "\n",
        encoding="utf-8",
    )

    print(serialized_summary)


if __name__ == "__main__":
    main()
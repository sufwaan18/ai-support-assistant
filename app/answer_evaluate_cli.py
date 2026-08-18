import argparse
import json
from pathlib import Path

from app.answer_evaluation import (
    evaluate_answers,
    load_answer_evaluation_cases,
)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate grounded financial-support answer quality."
        ),
    )
    parser.add_argument(
        "--cases-file",
        type=Path,
        default=Path("evals/answer_quality_cases.jsonl"),
        help="Path to the JSONL answer evaluation dataset.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "data/processed/answer_quality_evaluation.json"
        ),
        help="Destination for the evaluation report.",
    )
    return parser


def main() -> None:
    arguments = create_parser().parse_args()
    cases = load_answer_evaluation_cases(
        arguments.cases_file
    )
    summary = evaluate_answers(cases)
    serialized_summary = json.dumps(
        summary.model_dump(mode="json"),
        indent=2,
        sort_keys=True,
    )

    arguments.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    arguments.output.write_text(
        serialized_summary + "\n",
        encoding="utf-8",
    )
    print(serialized_summary)


if __name__ == "__main__":
    main()

import json
from pathlib import Path

from pydantic import ValidationError

from app.retrieval_evaluation import EvaluationCase


def load_evaluation_cases(path: Path) -> list[EvaluationCase]:
    if not path.is_file():
        raise FileNotFoundError(f"Evaluation dataset not found: {path}")

    cases: list[EvaluationCase] = []

    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue

        try:
            payload = json.loads(line)
            evaluation_case = EvaluationCase.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as error:
            raise ValueError(
                f"Invalid evaluation case on line {line_number}"
            ) from error

        cases.append(evaluation_case)

    if not cases:
        raise ValueError("Evaluation dataset contains no cases")

    return cases
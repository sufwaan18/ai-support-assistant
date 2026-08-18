import json
import re
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError


CITATION_PATTERN = re.compile(
    r"\[CFPB complaint ID:\s*([^\]]+)\]"
)
INSUFFICIENT_CONTEXT_MARKERS = (
    "insufficient context",
    "not enough context",
    "available context does not",
    "context does not provide",
)


class AnswerEvaluationCase(BaseModel):
    case_id: str = Field(min_length=1)
    subject: str = Field(min_length=3)
    message: str = Field(min_length=10)
    candidate_reply: str = Field(min_length=1)
    source_ids: list[str]
    expected_terms: list[str] = Field(min_length=1)
    forbidden_terms: list[str] = Field(default_factory=list)
    minimum_term_matches: int = Field(default=1, ge=1)


class AnswerEvaluationResult(BaseModel):
    case_id: str
    passed: bool
    groundedness_passed: bool
    citation_integrity_passed: bool
    citation_presence_passed: bool
    relevance_passed: bool
    safety_passed: bool
    cited_source_ids: list[str]
    unsupported_source_ids: list[str]
    matched_expected_terms: list[str]
    matched_forbidden_terms: list[str]


class AnswerEvaluationSummary(BaseModel):
    total_cases: int
    passed_cases: int
    pass_rate: float
    groundedness_rate: float
    citation_integrity_rate: float
    relevance_rate: float
    safety_rate: float
    results: list[AnswerEvaluationResult]


def extract_citation_ids(reply: str) -> set[str]:
    return {
        complaint_id.strip()
        for complaint_id in CITATION_PATTERN.findall(reply)
    }


def load_answer_evaluation_cases(
    path: Path,
) -> list[AnswerEvaluationCase]:
    if not path.is_file():
        raise FileNotFoundError(
            f"Answer evaluation dataset not found: {path}"
        )

    cases: list[AnswerEvaluationCase] = []

    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue

        try:
            payload = json.loads(line)
            case = AnswerEvaluationCase.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as error:
            raise ValueError(
                "Invalid answer evaluation case "
                f"on line {line_number}"
            ) from error

        cases.append(case)

    if not cases:
        raise ValueError(
            "Answer evaluation dataset contains no cases"
        )

    return cases


def evaluate_answer_case(
    case: AnswerEvaluationCase,
) -> AnswerEvaluationResult:
    reply_lower = case.candidate_reply.casefold()
    cited_ids = extract_citation_ids(case.candidate_reply)
    source_ids = set(case.source_ids)
    unsupported_ids = cited_ids - source_ids

    citation_integrity_passed = not unsupported_ids
    if source_ids:
        citation_presence_passed = bool(cited_ids)
    else:
        citation_presence_passed = (
            not cited_ids
            and any(
                marker in reply_lower
                for marker in INSUFFICIENT_CONTEXT_MARKERS
            )
        )

    groundedness_passed = (
        citation_integrity_passed
        and citation_presence_passed
    )

    matched_expected_terms = [
        term
        for term in case.expected_terms
        if term.casefold() in reply_lower
    ]
    relevance_passed = (
        len(matched_expected_terms)
        >= case.minimum_term_matches
    )

    matched_forbidden_terms = [
        term
        for term in case.forbidden_terms
        if term.casefold() in reply_lower
    ]
    safety_passed = not matched_forbidden_terms

    passed = (
        groundedness_passed
        and relevance_passed
        and safety_passed
    )

    return AnswerEvaluationResult(
        case_id=case.case_id,
        passed=passed,
        groundedness_passed=groundedness_passed,
        citation_integrity_passed=(
            citation_integrity_passed
        ),
        citation_presence_passed=citation_presence_passed,
        relevance_passed=relevance_passed,
        safety_passed=safety_passed,
        cited_source_ids=sorted(cited_ids),
        unsupported_source_ids=sorted(unsupported_ids),
        matched_expected_terms=matched_expected_terms,
        matched_forbidden_terms=matched_forbidden_terms,
    )


def evaluate_answers(
    cases: list[AnswerEvaluationCase],
) -> AnswerEvaluationSummary:
    results = [
        evaluate_answer_case(case)
        for case in cases
    ]
    total_cases = len(results)
    passed_cases = sum(result.passed for result in results)

    def rate(attribute: str) -> float:
        if total_cases == 0:
            return 0.0

        passing_results = sum(
            bool(getattr(result, attribute))
            for result in results
        )
        return passing_results / total_cases

    return AnswerEvaluationSummary(
        total_cases=total_cases,
        passed_cases=passed_cases,
        pass_rate=(
            passed_cases / total_cases
            if total_cases
            else 0.0
        ),
        groundedness_rate=rate("groundedness_passed"),
        citation_integrity_rate=rate(
            "citation_integrity_passed"
        ),
        relevance_rate=rate("relevance_passed"),
        safety_rate=rate("safety_passed"),
        results=results,
    )

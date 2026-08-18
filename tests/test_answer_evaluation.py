from pathlib import Path

import pytest

from app.answer_evaluation import (
    AnswerEvaluationCase,
    evaluate_answer_case,
    evaluate_answers,
    extract_citation_ids,
    load_answer_evaluation_cases,
)


def create_case(**overrides: object) -> AnswerEvaluationCase:
    values: dict[str, object] = {
        "case_id": "duplicate-charge",
        "subject": "Duplicate charge",
        "message": "The same charge appears twice on my statement.",
        "candidate_reply": (
            "Contact the card issuer about the duplicate charge "
            "[CFPB complaint ID: 1001]."
        ),
        "source_ids": ["1001"],
        "expected_terms": ["card issuer", "duplicate"],
        "forbidden_terms": ["guaranteed refund"],
        "minimum_term_matches": 2,
    }
    values.update(overrides)
    return AnswerEvaluationCase.model_validate(values)


def test_extract_citation_ids() -> None:
    reply = (
        "See [CFPB complaint ID: 1001] and "
        "[CFPB complaint ID: 1002]."
    )

    assert extract_citation_ids(reply) == {"1001", "1002"}


def test_evaluate_answer_case_passes_grounded_reply() -> None:
    result = evaluate_answer_case(create_case())

    assert result.passed is True
    assert result.groundedness_passed is True
    assert result.relevance_passed is True
    assert result.safety_passed is True


def test_evaluate_answer_case_rejects_unsupported_citation() -> None:
    case = create_case(
        candidate_reply=(
            "Contact the card issuer about the duplicate charge "
            "[CFPB complaint ID: invented-9]."
        )
    )

    result = evaluate_answer_case(case)

    assert result.passed is False
    assert result.citation_integrity_passed is False
    assert result.unsupported_source_ids == ["invented-9"]


def test_evaluate_answer_case_rejects_unsafe_claim() -> None:
    case = create_case(
        candidate_reply=(
            "The card issuer will provide a guaranteed refund "
            "for the duplicate charge "
            "[CFPB complaint ID: 1001]."
        )
    )

    result = evaluate_answer_case(case)

    assert result.passed is False
    assert result.safety_passed is False
    assert result.matched_forbidden_terms == [
        "guaranteed refund"
    ]


def test_evaluate_answer_case_handles_missing_context() -> None:
    case = create_case(
        candidate_reply=(
            "The available context does not provide enough "
            "information about this duplicate transaction."
        ),
        source_ids=[],
        expected_terms=["duplicate", "context"],
        minimum_term_matches=2,
    )

    result = evaluate_answer_case(case)

    assert result.passed is True
    assert result.citation_presence_passed is True


def test_evaluate_answers_calculates_rates() -> None:
    cases = [
        create_case(),
        create_case(
            case_id="unsafe",
            candidate_reply=(
                "The card issuer will provide a guaranteed refund for the duplicate "
                "charge [CFPB complaint ID: 1001]."
            ),
        ),
    ]

    summary = evaluate_answers(cases)

    assert summary.total_cases == 2
    assert summary.passed_cases == 1
    assert summary.pass_rate == pytest.approx(0.5)
    assert summary.groundedness_rate == pytest.approx(1.0)
    assert summary.relevance_rate == pytest.approx(1.0)
    assert summary.safety_rate == pytest.approx(0.5)


def test_load_answer_evaluation_cases(tmp_path: Path) -> None:
    cases_file = tmp_path / "answer-cases.jsonl"
    cases_file.write_text(
        (
            '{"case_id":"one","subject":"Card issue",'
            '"message":"A duplicate charge appeared today.",'
            '"candidate_reply":"Insufficient context.",'
            '"source_ids":[],"expected_terms":["context"]}\n'
        ),
        encoding="utf-8",
    )

    cases = load_answer_evaluation_cases(cases_file)

    assert len(cases) == 1
    assert cases[0].case_id == "one"


def test_load_answer_evaluation_cases_reports_line(
    tmp_path: Path,
) -> None:
    cases_file = tmp_path / "answer-cases.jsonl"
    cases_file.write_text("{invalid json}\n", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="Invalid answer evaluation case on line 1",
    ):
        load_answer_evaluation_cases(cases_file)

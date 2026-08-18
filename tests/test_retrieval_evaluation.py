import pytest

from app.retrieval_evaluation import (
    EvaluationCase,
    evaluate_retrieval,
)
from app.vector_store import RetrievedComplaint


def create_result(product: str) -> RetrievedComplaint:
    return RetrievedComplaint(
        complaint_id="1001",
        document="Example complaint document",
        distance=0.2,
        metadata={
            "product": product,
            "issue": "Example issue",
        },
    )


def test_evaluate_retrieval_calculates_recall() -> None:
    cases = [
        EvaluationCase(
            query="duplicate credit card charge",
            expected_product="Credit card",
        ),
        EvaluationCase(
            query="unexpected checking account fee",
            expected_product="Checking or savings account",
        ),
    ]

    def fake_search(
        query: str,
        limit: int,
    ) -> list[RetrievedComplaint]:
        assert limit == 3

        if "credit card" in query:
            return [create_result("Credit card")]

        return [create_result("Mortgage")]

    summary = evaluate_retrieval(
        cases=cases,
        search=fake_search,
        limit=3,
    )

    assert summary.total_cases == 2
    assert summary.matched_cases == 1
    assert summary.recall_at_k == pytest.approx(0.5)
    assert summary.mean_reciprocal_rank == pytest.approx(0.5)

    assert summary.results[0].matched is True
    assert summary.results[0].first_relevant_rank == 1
    assert summary.results[0].reciprocal_rank == pytest.approx(1.0)

    assert summary.results[1].matched is False
    assert summary.results[1].first_relevant_rank is None
    assert summary.results[1].reciprocal_rank == 0.0


def test_evaluate_retrieval_handles_empty_cases() -> None:
    summary = evaluate_retrieval(
        cases=[],
        search=lambda query, limit: [],
        limit=3,
    )

    assert summary.total_cases == 0
    assert summary.matched_cases == 0
    assert summary.recall_at_k == 0.0
    assert summary.mean_reciprocal_rank == 0.0
    assert summary.results == []


def test_evaluate_retrieval_rejects_invalid_limit() -> None:
    with pytest.raises(
        ValueError,
        match="limit must be at least 1",
    ):
        evaluate_retrieval(
            cases=[],
            search=lambda query, limit: [],
            limit=0,
        )


def test_evaluate_retrieval_calculates_rank_metrics() -> None:
    cases = [
        EvaluationCase(
            query="duplicate credit card transaction",
            expected_product="Credit card",
        ),
    ]

    def fake_search(
        query: str,
        limit: int,
    ) -> list[RetrievedComplaint]:
        assert query == "duplicate credit card transaction"
        assert limit == 3

        return [
            create_result("Mortgage"),
            create_result("Credit card"),
        ]

    summary = evaluate_retrieval(
        cases=cases,
        search=fake_search,
        limit=3,
    )

    result = summary.results[0]

    assert result.matched is True
    assert result.first_relevant_rank == 2
    assert result.reciprocal_rank == pytest.approx(0.5)
    assert summary.mean_reciprocal_rank == pytest.approx(0.5)
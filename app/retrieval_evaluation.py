from collections.abc import Callable

from pydantic import BaseModel, Field

from app.vector_store import RetrievedComplaint


class EvaluationCase(BaseModel):
    query: str = Field(min_length=1)
    expected_product: str = Field(min_length=1)


class EvaluationCaseResult(BaseModel):
    query: str
    expected_product: str
    retrieved_products: list[str]
    matched: bool
    first_relevant_rank: int | None
    reciprocal_rank: float = Field(ge=0, le=1)


class RetrievalEvaluationSummary(BaseModel):
    total_cases: int = Field(ge=0)
    matched_cases: int = Field(ge=0)
    recall_at_k: float = Field(ge=0, le=1)
    mean_reciprocal_rank: float = Field(ge=0, le=1)
    results: list[EvaluationCaseResult]


SearchFunction = Callable[
    [str, int],
    list[RetrievedComplaint],
]


DEFAULT_EVALUATION_CASES = [
    EvaluationCase(
        query=(
            "The same credit card purchase was charged "
            "twice on my statement"
        ),
        expected_product="Credit card",
    ),
    EvaluationCase(
        query=(
            "My checking account was charged an unexpected "
            "monthly maintenance fee"
        ),
        expected_product="Checking or savings account",
    ),
    EvaluationCase(
        query=(
            "The bank froze my checking account and I cannot "
            "access my money"
        ),
        expected_product="Checking or savings account",
    ),
    EvaluationCase(
        query=(
            "My credit card company will not resolve a dispute "
            "for a purchase I did not make"
        ),
        expected_product="Credit card",
    ),
]


def find_first_relevant_rank(
    retrieved_products: list[str],
    expected_product: str,
) -> int | None:
    for rank, product in enumerate(
        retrieved_products,
        start=1,
    ):
        if product == expected_product:
            return rank

    return None


def evaluate_retrieval(
    cases: list[EvaluationCase],
    search: SearchFunction,
    limit: int = 3,
) -> RetrievalEvaluationSummary:
    if limit < 1:
        raise ValueError("limit must be at least 1")

    results: list[EvaluationCaseResult] = []

    for case in cases:
        retrieved = search(case.query, limit)

        retrieved_products = [
            complaint.metadata.get("product", "Unknown")
            for complaint in retrieved
        ]

        first_relevant_rank = find_first_relevant_rank(
            retrieved_products=retrieved_products,
            expected_product=case.expected_product,
        )

        reciprocal_rank = (
            1 / first_relevant_rank
            if first_relevant_rank is not None
            else 0.0
        )

        results.append(
            EvaluationCaseResult(
                query=case.query,
                expected_product=case.expected_product,
                retrieved_products=retrieved_products,
                matched=first_relevant_rank is not None,
                first_relevant_rank=first_relevant_rank,
                reciprocal_rank=reciprocal_rank,
            )
        )

    total_cases = len(results)
    matched_cases = sum(
        result.matched
        for result in results
    )

    recall_at_k = (
        matched_cases / total_cases
        if total_cases
        else 0.0
    )

    mean_reciprocal_rank = (
        sum(
            result.reciprocal_rank
            for result in results
        )
        / total_cases
        if total_cases
        else 0.0
    )

    return RetrievalEvaluationSummary(
        total_cases=total_cases,
        matched_cases=matched_cases,
        recall_at_k=recall_at_k,
        mean_reciprocal_rank=mean_reciprocal_rank,
        results=results,
    )
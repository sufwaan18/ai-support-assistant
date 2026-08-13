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


class RetrievalEvaluationSummary(BaseModel):
    total_cases: int = Field(ge=0)
    matched_cases: int = Field(ge=0)
    recall_at_k: float = Field(ge=0, le=1)
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
        matched = case.expected_product in retrieved_products

        results.append(
            EvaluationCaseResult(
                query=case.query,
                expected_product=case.expected_product,
                retrieved_products=retrieved_products,
                matched=matched,
            )
        )

    matched_cases = sum(
        result.matched
        for result in results
    )
    total_cases = len(results)
    recall_at_k = (
        matched_cases / total_cases
        if total_cases
        else 0.0
    )

    return RetrievalEvaluationSummary(
        total_cases=total_cases,
        matched_cases=matched_cases,
        recall_at_k=recall_at_k,
        results=results,
    )
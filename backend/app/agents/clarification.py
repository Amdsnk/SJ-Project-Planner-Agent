"""Clarification Agent.

Generates targeted questions when extracted items have missing/ambiguous fields
or are flagged as a conflict by the Reconciliation Agent.
"""
from __future__ import annotations

from dataclasses import dataclass

from .reconciliation import ReconciledItem


@dataclass
class ClarificationQuestion:
    draft_item_index: int
    question: str
    context: str


class ClarificationAgent:
    name = "clarification_agent"

    async def run(self, items: list[ReconciledItem]) -> list[ClarificationQuestion]:
        questions: list[ClarificationQuestion] = []
        for idx, it in enumerate(items):
            ctx = f"{it.action.upper()} {it.task_code}: {it.title}"
            if it.action == "conflict":
                questions.append(ClarificationQuestion(
                    draft_item_index=idx,
                    question=(f"Is '{it.title}' the same as existing task {it.task_code}, "
                              f"or should it be tracked as a new task?"),
                    context=ctx + f"\nEvidence: {it.evidence}",
                ))
                continue
            if not it.owner:
                questions.append(ClarificationQuestion(
                    draft_item_index=idx,
                    question=f"Who should own '{it.title}'?",
                    context=ctx,
                ))
            if not it.due_date:
                questions.append(ClarificationQuestion(
                    draft_item_index=idx,
                    question=f"What is the due date for '{it.title}'? Is it confirmed?",
                    context=ctx,
                ))
            if it.confidence < 0.5:
                questions.append(ClarificationQuestion(
                    draft_item_index=idx,
                    question=(f"Confidence is low ({it.confidence:.2f}) on '{it.title}'. "
                              "Please confirm scope and wording."),
                    context=ctx + f"\nEvidence: {it.evidence}",
                ))
        return questions

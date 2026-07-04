"""Deep Research REST endpoint."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.deep_research import run_deep_research

router = APIRouter()


class ResearchRequest(BaseModel):
    question: str = Field(min_length=5)


class ResearchResult(BaseModel):
    report: str
    sources: list[str]
    sub_questions: list[str]


@router.post("/run", response_model=ResearchResult)
async def research_run(
    body: ResearchRequest,
    _current_user: User = Depends(get_current_user),
) -> ResearchResult:
    """
    Deep research — searches the web across multiple sub-questions,
    reads source pages, and synthesizes a cited Markdown report.
    Takes 30–90 seconds depending on topic breadth.
    """
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="question must not be empty")

    result = await run_deep_research(question)
    return ResearchResult(**result)

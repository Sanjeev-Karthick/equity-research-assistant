import uuid

from fastapi import FastAPI, HTTPException

from src.api.schemas import ResearchRequest, ResearchResponse

app = FastAPI(
    title="Financial Research Assistant",
    description=(
        "HTTP API for the multi-agent financial research supervisor. "
        "Results should not be taken as financial advice."
    ),
    version="1.0.0",
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/research", response_model=ResearchResponse)
def research(body: ResearchRequest) -> ResearchResponse:
    from src.financial_research.assistant import get_assistant

    session_id = body.session_id or str(uuid.uuid4())
    try:
        assistant = get_assistant()
        result = assistant.invoke(
            body.query,
            session_id=session_id,
            enable_trace=body.enable_trace,
            trace_level=body.trace_level,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return ResearchResponse(
        query=body.query,
        result=result,
        session_id=session_id,
    )

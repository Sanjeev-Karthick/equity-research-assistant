import uuid

from fastapi import FastAPI, HTTPException, status

from src.api.schemas import (
    ErrorResponse,
    HealthResponse,
    ResearchRequest,
    ResearchResponse,
)

TAGS_METADATA = [
    {
        "name": "Health",
        "description": "Process liveness. These routes do not call Amazon Bedrock.",
    },
    {
        "name": "Research",
        "description": (
            "Run a financial research query through the Bedrock supervisor agent. "
            "The first call in a process may create or reuse AWS agents, a knowledge "
            "base, and an S3 bucket; later calls only invoke."
        ),
    },
]

app = FastAPI(
    title="Financial Research Assistant API",
    summary="Multi-agent equity research over HTTP",
    version="1.0.0",
    contact={"name": "Equity Research Assistant"},
    license_info={"name": "Apache 2.0"},
    openapi_tags=TAGS_METADATA,
    description="""
HTTP API for the Amazon Bedrock **supervisor** that coordinates news research,
quantitative stock tools, and insight summarization.

**Not financial advice.** Responses are generated analysis of public market data
and documents. Do not treat allocations, price commentary, or news summaries as
recommendations to buy or sell.

### Typical flow

1. `GET /health` — confirm the process is up (no AWS required).
2. `POST /research` — send a `query`. Save `session_id` from the response.
3. Optional follow-ups — send the same `session_id` to continue the conversation.

Interactive OpenAPI UI: [`/docs`](/docs) (Swagger) and [`/redoc`](/redoc).
""",
)


@app.get(
    "/health",
    tags=["Health"],
    response_model=HealthResponse,
    summary="Liveness check",
    description=(
        "Returns `{ \"status\": \"ok\" }` when the FastAPI process can serve HTTP. "
        "Does not initialize Bedrock agents or validate AWS credentials."
    ),
)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post(
    "/research",
    tags=["Research"],
    response_model=ResearchResponse,
    summary="Run a research query",
    description=(
        "Invokes `financial_research_assistant` with the given query. "
        "Latency is typically tens of seconds because the supervisor may call "
        "sub-agents, Lambda tools (stock data, web search), and a knowledge base.\n\n"
        "If `session_id` is omitted, the API generates one and returns it."
    ),
    responses={
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": "Invalid JSON body (empty query, bad types).",
            "model": ErrorResponse,
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Bedrock, IAM, Lambda, or agent setup failed.",
            "model": ErrorResponse,
        },
    },
)
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e

    return ResearchResponse(
        query=body.query,
        result=result,
        session_id=session_id,
    )

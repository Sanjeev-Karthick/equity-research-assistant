from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Liveness probe. Does not initialize Bedrock agents."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"status": "ok"}]}
    )

    status: Literal["ok"] = Field(
        ..., description="Always `ok` when the HTTP process is running."
    )


class ResearchRequest(BaseModel):
    """Body for `POST /research`."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "query": (
                        "What's AAPL stock price doing over the last week "
                        "and relate that to recent news?"
                    ),
                    "session_id": None,
                    "enable_trace": False,
                    "trace_level": "core",
                },
                {
                    "query": (
                        "Optimize my portfolio with AAPL, MSFT, and GOOGL. "
                        "Show me the recommended allocations."
                    ),
                    "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "enable_trace": False,
                    "trace_level": "core",
                },
            ]
        }
    )

    query: str = Field(
        ...,
        min_length=1,
        max_length=8000,
        description=(
            "Natural-language research question. The supervisor routes this to "
            "news, quantitative, and/or summarizer sub-agents as needed."
        ),
        examples=[
            "What's AAPL stock price doing over the last week and relate that to recent news?"
        ],
    )
    session_id: Optional[str] = Field(
        default=None,
        description=(
            "Bedrock agent session ID. Omit on the first turn; reuse the value "
            "from the previous response to continue the same conversation."
        ),
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
    enable_trace: bool = Field(
        default=False,
        description=(
            "When true, Bedrock orchestration traces are written to server logs. "
            "They are never returned in the HTTP response."
        ),
    )
    trace_level: Literal["outline", "core", "all"] = Field(
        default="core",
        description="Trace verbosity when `enable_trace` is true: `outline`, `core`, or `all`.",
    )


class ResearchResponse(BaseModel):
    """Successful research result from the supervisor agent."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "query": "What's AAPL stock price doing over the last week and relate that to recent news?",
                    "result": (
                        "## Price action\n"
                        "AAPL traded in a narrow range over the last week...\n\n"
                        "## Related news\n"
                        "- ...\n\n"
                        "This analysis is informational and is not financial advice."
                    ),
                    "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                }
            ]
        }
    )

    query: str = Field(..., description="Echo of the request query.")
    result: str = Field(
        ...,
        description=(
            "Supervisor agent answer. Structure and length vary by query. "
            "Not financial advice."
        ),
    )
    session_id: str = Field(
        ...,
        description="Session ID to send on follow-up requests for conversation continuity.",
    )


class ErrorResponse(BaseModel):
    """FastAPI error payload."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"detail": "Failed to invoke the financial research assistant."}
            ]
        }
    )

    detail: str = Field(..., description="Human-readable error message.")

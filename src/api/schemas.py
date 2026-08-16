from typing import Literal, Optional

from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Financial research question")
    session_id: Optional[str] = Field(
        default=None, description="Optional session ID for conversation continuity"
    )
    enable_trace: bool = False
    trace_level: Literal["outline", "core", "all"] = "core"


class ResearchResponse(BaseModel):
    query: str
    result: str
    session_id: Optional[str] = None

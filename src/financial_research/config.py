"""Configuration for the financial research assistant and API."""

import os

from src.utils.bedrock_agent import account_id, region

LLM = os.getenv("BEDROCK_LLM", "us.anthropic.claude-3-5-sonnet-20241022-v2:0")
EMBEDDING_MODEL = os.getenv(
    "BEDROCK_EMBEDDING_MODEL", "amazon.titan-embed-text-v2:0"
)

KB_NAME = os.getenv("KB_NAME", "financial-research-kb")
KB_DESCRIPTION = (
    "Knowledge base for financial analysis containing 10-K reports, "
    "earnings calls, and SEC filings."
)
KB_BUCKET_NAME = os.getenv(
    "KB_BUCKET_NAME", f"financial-research-data-{region}-{account_id}"
)

STOCK_DATA_LAMBDA_ARN = os.getenv(
    "STOCK_DATA_LAMBDA_ARN",
    f"arn:aws:lambda:{region}:{account_id}:function:stock_data_tools",
)
WEB_SEARCH_LAMBDA_ARN = os.getenv(
    "WEB_SEARCH_LAMBDA_ARN",
    f"arn:aws:lambda:{region}:{account_id}:function:web_search",
)

FORCE_RECREATE_AGENTS = os.getenv("FORCE_RECREATE_AGENTS", "false").lower() in (
    "1",
    "true",
    "yes",
)
ENABLE_CRYPTO_GUARDRAIL = os.getenv("ENABLE_CRYPTO_GUARDRAIL", "false").lower() in (
    "1",
    "true",
    "yes",
)

AGENT_NAMES = [
    "financial_research_assistant",
    "news_agent",
    "quantitative_analysis_agent",
    "smart_summarizer_agent",
]
GUARDRAIL_NAME = "no_crypto_guardrail"

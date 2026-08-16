"""Financial research assistant: Bedrock multi-agent setup and invoke."""

from __future__ import annotations

import logging
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from src.financial_research import config
from src.utils.bedrock_agent import (
    Agent,
    Guardrail,
    SupervisorAgent,
    account_id,
    agents_helper,
    region,
)
from src.utils.knowledge_base_helper import KnowledgeBasesForAmazonBedrock

logger = logging.getLogger(__name__)

bedrock_client = boto3.client("bedrock")
bedrock_agent_client = boto3.client("bedrock-agent")
s3_client = boto3.client("s3", region_name=region)
kb_helper = KnowledgeBasesForAmazonBedrock()


def create_bucket_if_not_exists(bucket_name: str) -> None:
    """Create an S3 bucket if it doesn't already exist."""
    try:
        if region == "us-east-1":
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": region},
            )
        logger.info("Created bucket: %s", bucket_name)
    except ClientError as e:
        if e.response["Error"]["Code"] in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            logger.info("Bucket already exists: %s", bucket_name)
        else:
            raise


def clean_up_agents() -> None:
    """Delete agents and the optional crypto guardrail created by this module."""
    logger.info("Cleaning up agents...")
    for name in config.AGENT_NAMES:
        try:
            agents_helper.delete_agent(
                agent_name=name, delete_role_flag=True, verbose=True
            )
        except Exception as e:
            logger.warning("Could not delete %s: %s", name, e)

    logger.info("Cleaning up guardrails...")
    try:
        response = bedrock_client.list_guardrails()
        for guardrail in response.get("guardrails", []):
            if guardrail["name"] == config.GUARDRAIL_NAME:
                logger.info("Deleting guardrail: %s", guardrail["id"])
                bedrock_client.delete_guardrail(guardrailIdentifier=guardrail["id"])
    except Exception as e:
        logger.warning("Could not clean up guardrails: %s", e)


def create_guardrail() -> Guardrail:
    """Create a guardrail that filters cryptocurrency discussions."""
    return Guardrail(
        name=config.GUARDRAIL_NAME,
        topic_name="cryptocurrency_topic",
        description="Prevents discussion of cryptocurrency and blockchain investments.",
        denied_topics=["bitcoin", "crypto", "cryptocurrency", "ethereum", "blockchain"],
        blocked_input_response=(
            "I apologize, but I cannot provide analysis on cryptocurrency investments."
        ),
        verbose=True,
    )


def _find_agent(name: str) -> Optional[dict]:
    response = bedrock_agent_client.list_agents()
    for agent in response.get("agentSummaries", []):
        if agent["agentName"] == name:
            return agent
    return None


def _live_alias(agent_id: str) -> Optional[dict]:
    response = bedrock_agent_client.list_agent_aliases(agentId=agent_id)
    aliases = response.get("agentAliasSummaries", [])
    for alias in aliases:
        if alias.get("agentAliasName") == "live":
            return alias
    return aliases[0] if aliases else None


def _hydrate_existing(agent: Agent) -> bool:
    """Attach IDs from an already-deployed Bedrock agent. Returns True if found."""
    summary = _find_agent(agent.name)
    if not summary:
        return False
    alias = _live_alias(summary["agentId"])
    if not alias:
        return False
    agent.agent_id = summary["agentId"]
    agent.agent_arn = summary.get("agentArn") or (
        f"arn:aws:bedrock:{region}:{account_id}:agent/{agent.agent_id}"
    )
    agent.agent_alias_id = alias["agentAliasId"]
    agent.agent_alias_arn = alias.get("agentAliasArn") or (
        f"arn:aws:bedrock:{region}:{account_id}:agent-alias/"
        f"{agent.agent_id}/{agent.agent_alias_id}"
    )
    logger.info("Reusing existing agent %s (ID: %s)", agent.name, agent.agent_id)
    return True


def _create_or_reuse_agent(**kwargs) -> Agent:
    agent = Agent(**kwargs)
    if not config.FORCE_RECREATE_AGENTS and _hydrate_existing(agent):
        return agent
    return Agent.create(**kwargs)


def _create_or_reuse_supervisor(**kwargs) -> SupervisorAgent:
    supervisor = SupervisorAgent(**kwargs)
    if not config.FORCE_RECREATE_AGENTS and _hydrate_existing(supervisor):
        return supervisor
    return SupervisorAgent.create(**kwargs)


class FinancialResearchAssistant:
    """Supervisor-backed assistant equivalent to the former notebook workflow."""

    def __init__(self) -> None:
        logger.info("AWS Account: %s | Region: %s | LLM: %s", account_id, region, config.LLM)
        Agent.set_force_recreate_default(config.FORCE_RECREATE_AGENTS)

        if config.FORCE_RECREATE_AGENTS:
            clean_up_agents()

        create_bucket_if_not_exists(config.KB_BUCKET_NAME)

        guardrail = create_guardrail() if config.ENABLE_CRYPTO_GUARDRAIL else None

        smart_summarizer_agent = _create_or_reuse_agent(
            name="smart_summarizer_agent",
            role="Financial Analyst specializing in investment insight synthesis",
            goal="Analyze stock trends and market news to generate structured investment insights.",
            instructions="""You are a Financial Analyst responsible for synthesizing stock trends 
and financial news into structured insights.

Your responsibilities:
- Combine stock price trends with financial news to identify key patterns
- Analyze macroeconomic indicators, company earnings, and market sentiment
- Ensure responses are fact-driven, clearly structured, and cite sources when possible
- Keep analyses concise and focused on major trends and anomalies

Important guidelines:
- Do NOT provide financial advice - analyze and summarize data objectively
- If given portfolio optimization percentages, note they are mathematical results, not advice
- Maintain a professional tone without using emojis
- Structure your output with clear sections and bullet points""",
            llm=config.LLM,
        )

        quantitative_analysis_agent = _create_or_reuse_agent(
            name="quantitative_analysis_agent",
            role="Stock Data and Portfolio Optimization Specialist",
            goal="Retrieve real-time and historical stock prices, and optimize investment portfolios.",
            instructions="""You are a Stock Data and Portfolio Optimization Specialist.

Your capabilities:
1. Retrieve stock price data using the stock_data_lookup tool
2. Perform portfolio optimization with at least 3 stock tickers
3. Analyze historical price movements and volatility

Core behaviors:
- Always retrieve stock data first before running portfolio optimization
- If fewer than 3 tickers are provided for optimization, inform the user
- Focus on data retrieval and mathematical analysis - do not interpret trends
- Return data in a clear, structured format""",
            tools=[
                {
                    "code": config.STOCK_DATA_LAMBDA_ARN,
                    "definition": {
                        "name": "stock_data_lookup",
                        "description": (
                            "Gets the 1-month stock price history for a given ticker, formatted as JSON."
                        ),
                        "parameters": {
                            "ticker": {
                                "description": (
                                    "The stock ticker symbol to retrieve price history for (e.g., AAPL)"
                                ),
                                "type": "string",
                                "required": True,
                            }
                        },
                    },
                },
                {
                    "code": config.STOCK_DATA_LAMBDA_ARN,
                    "definition": {
                        "name": "portfolio_optimization",
                        "description": (
                            "Optimizes a stock portfolio given a list of tickers. Requires at least 3 tickers."
                        ),
                        "parameters": {
                            "tickers": {
                                "description": "A comma-separated list of stock tickers (minimum 3)",
                                "type": "string",
                                "required": True,
                            },
                            "prices": {
                                "description": "JSON object with historical prices from stock_data_lookup",
                                "type": "string",
                                "required": True,
                            },
                        },
                    },
                },
            ],
            llm=config.LLM,
        )

        kb_id, _ds_id = kb_helper.create_or_retrieve_knowledge_base(
            kb_name=config.KB_NAME,
            kb_description=config.KB_DESCRIPTION,
            data_bucket_name=config.KB_BUCKET_NAME,
            embedding_model=config.EMBEDDING_MODEL,
        )
        self.kb_id = kb_id

        news_agent = _create_or_reuse_agent(
            name="news_agent",
            role="Market News Researcher and Financial Document Analyst",
            goal="Retrieve insights from the knowledge base and fetch latest financial news when needed.",
            instructions=f"""You are a Financial Document & News Analyst responsible for extracting 
insights from official financial reports and real-time news.

Your capabilities:
1. Extract insights from earnings calls, SEC filings, and press releases in the knowledge base (ID: {kb_id})
2. Summarize financial reports with focus on factual accuracy
3. Retrieve latest financial news when the knowledge base lacks relevant information

Core behaviors:
- ALWAYS check the knowledge base (ID: {kb_id}) FIRST before fetching external news
- Avoid unnecessary web searches - use external sources only when KB is insufficient
- Ensure all findings are fact-based, neutral, and structured for investment research
- Cite sources clearly in your responses""",
            tools=[
                {
                    "code": config.WEB_SEARCH_LAMBDA_ARN,
                    "definition": {
                        "name": "web_search",
                        "description": (
                            "Searches the web for financial news, earnings reports, and market updates."
                        ),
                        "parameters": {
                            "search_query": {
                                "description": "The query to search the web with",
                                "type": "string",
                                "required": True,
                            },
                            "target_website": {
                                "description": "Specific website to search (e.g., reuters.com)",
                                "type": "string",
                                "required": False,
                            },
                            "topic": {
                                "description": "Topic category (e.g., 'news', 'finance')",
                                "type": "string",
                                "required": False,
                            },
                            "days": {
                                "description": "Number of days of history to search",
                                "type": "string",
                                "required": False,
                            },
                        },
                    },
                },
            ],
            kb_id=kb_id,
            llm=config.LLM,
        )

        self.supervisor = _create_or_reuse_supervisor(
            name="financial_research_assistant",
            role="Investment Research Assistant and Multi-Agent Coordinator",
            goal=(
                "Orchestrate specialized agents to conduct comprehensive stock analysis "
                "and produce structured investment reports."
            ),
            instructions=f"""You are an Investment Research Assistant responsible for coordinating 
financial research from specialized agents and producing structured insights.

Your capabilities:
1. Manage collaboration between sub-agents to retrieve and analyze financial data
2. Synthesize stock trends, financial reports, and market news into structured analysis
3. Deliver well-organized, fact-based investment insights with clear source attribution

Available sub-agents:
- **news_agent**: Retrieves and summarizes financial news and documents
  - Always instruct it to check the knowledge base (ID: {kb_id}) first
- **quantitative_analysis_agent**: Provides stock prices and portfolio optimization
  - For optimization, requires at least 3 tickers
- **smart_summarizer_agent**: Synthesizes data into structured investment insights

Core behaviors:
- Only invoke a sub-agent when necessary for the user's request
- Ensure responses are well-structured and relevant to investment decisions
- Clearly distinguish between news analysis, technical data, and synthesized insights
- Never provide specific investment recommendations - present analysis objectively""",
            collaboration_type="SUPERVISOR",
            collaborator_agents=[
                {
                    "agent": "news_agent",
                    "instructions": (
                        f"Always check the knowledge base (ID: {kb_id}) first. "
                        "Use for financial news and document analysis."
                    ),
                },
                {
                    "agent": "quantitative_analysis_agent",
                    "instructions": (
                        "Use for retrieving stock price history and performing portfolio optimization."
                    ),
                },
                {
                    "agent": "smart_summarizer_agent",
                    "instructions": (
                        "Use for synthesizing data and generating structured investment insights."
                    ),
                },
            ],
            collaborator_objects=[
                news_agent,
                quantitative_analysis_agent,
                smart_summarizer_agent,
            ],
            guardrail=guardrail,
            llm=config.LLM,
        )

        logger.info(
            "Financial research assistant ready (ID: %s)",
            self.supervisor.agent_id,
        )

    def invoke(
        self,
        request: str,
        session_id: Optional[str] = None,
        enable_trace: bool = False,
        trace_level: str = "core",
    ) -> str:
        """Run a research query through the supervisor agent."""
        return self.supervisor.invoke(
            request,
            session_id=session_id,
            enable_trace=enable_trace,
            trace_level=trace_level,
        )


_assistant: Optional[FinancialResearchAssistant] = None


def get_assistant() -> FinancialResearchAssistant:
    """Return a process-wide assistant, creating Bedrock resources on first use."""
    global _assistant
    if _assistant is None:
        _assistant = FinancialResearchAssistant()
    return _assistant

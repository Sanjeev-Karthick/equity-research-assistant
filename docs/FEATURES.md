# Features

The product is a **supervisor multi-agent** system for equity research, now served as a FastAPI app instead of a Jupyter notebook.

> **Not financial advice.** Outputs are informational analysis of market data, news, and documents.

## What it does

| Capability | How it works |
| --- | --- |
| Orchestrated research | A supervisor agent (`financial_research_assistant`) decides which sub-agents to call for a user query |
| News and filings | `news_agent` searches a Bedrock knowledge base first, then the web search Lambda if needed |
| Prices and portfolios | `quantitative_analysis_agent` calls the stock-data Lambda for history and optional optimization (≥ 3 tickers) |
| Structured write-up | `smart_summarizer_agent` combines numbers and news into a sourced, non-advisory summary |
| HTTP access | `POST /research` wraps `supervisor.invoke(...)`; `GET /health` is a process ping |
| Session continuity | Returned `session_id` maps to a Bedrock agent session |
| Optional guardrail | Cryptocurrency topics can be blocked via `ENABLE_CRYPTO_GUARDRAIL` |
| Agent reuse | On later process starts, existing Bedrock agents named in config are reused unless `FORCE_RECREATE_AGENTS` is set |

## Architecture

```
Client
  │  POST /research { query, session_id? }
  ▼
FastAPI (src/api)
  │  get_assistant().invoke(query)
  ▼
Supervisor: financial_research_assistant
  ├── news_agent ──► Knowledge Base (S3 + OpenSearch Serverless)
  │              └──► Lambda: web_search (Tavily)
  ├── quantitative_analysis_agent
  │              └──► Lambda: stock_data_tools (lookup + optimize)
  └── smart_summarizer_agent
```

Helpers live in `src/utils/` (Bedrock agent CRUD/invoke, knowledge base). Lambda sources live in `src/shared/`.

## Agents

### Supervisor — `financial_research_assistant`

- Coordinates sub-agents; does not fetch prices or search the web itself.
- Instructed to invoke collaborators only when needed and not to give buy/sell recommendations.

### News — `news_agent`

- Knowledge base: 10-Ks, earnings materials, SEC-style documents you upload to the research bucket.
- Tool: `web_search` (query, optional site, topic, lookback days).
- Instructed to check the KB before the web.

### Quantitative — `quantitative_analysis_agent`

- Tool: `stock_data_lookup` — about one month of prices for a ticker.
- Tool: `portfolio_optimization` — needs **at least three** tickers plus price JSON from lookup.
- Instructed to fetch data before optimizing and not to interpret trends (summarizer does that).

### Summarizer — `smart_summarizer_agent`

- No tools. Synthesizes collaborator output into structured, cited, emoji-free analysis.

## Knowledge base and storage

On first assistant init the service will:

1. Ensure S3 bucket `KB_BUCKET_NAME` (default `financial-research-data-{region}-{account}`).
2. Create or retrieve knowledge base `KB_NAME` (default `financial-research-kb`) with Titan embeddings.

Uploading PDFs into that bucket and syncing the data source is still a separate ops step (see knowledge-base helper). The API does not expose document upload.

## Configuration

See [API.md](./API.md) for the full environment-variable table. Defaults assume:

- Claude 3.5 Sonnet v2 (`us.anthropic.claude-3-5-sonnet-20241022-v2:0`)
- Lambdas named `stock_data_tools` and `web_search` in the same account/region

## Example queries the system is built for

- “What's AAPL stock price doing over the last week and relate that to recent news?”
- “Optimize my portfolio with AAPL, MSFT, and GOOGL”
- “Analyze Amazon's financial health based on the 2024 10K report” (works well only if that filing is in the KB)

## What this release does not include

- Authentication or rate limiting
- Invoke-only mode with pre-provisioned agent IDs (first `/research` may still create AWS resources)
- Request timeouts, concurrency caps, or streaming
- Document-upload or admin/cleanup HTTP routes (`clean_up_agents()` exists in Python only)

Those are follow-ups for a small production deployment; this branch is the notebook → module → HTTP cutover.

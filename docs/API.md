# API documentation

Base URL (local): `http://localhost:8000`

Interactive specs after the server is running:

| UI | URL |
| --- | --- |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| OpenAPI JSON | http://localhost:8000/openapi.json |

Start the server from the repository root:

```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

> **Not financial advice.** Every research response is generated analysis, not a recommendation to buy, sell, or hold securities.

There is no authentication in this version. Anyone who can reach the host can invoke Bedrock (and incur cost).

---

## `GET /health`

Liveness probe for the HTTP process.

| | |
| --- | --- |
| AWS / Bedrock | Not used |
| Success body | `{ "status": "ok" }` |
| Status codes | `200` |

```bash
curl -s http://localhost:8000/health
```

```json
{ "status": "ok" }
```

---

## `POST /research`

Runs a natural-language query through the Bedrock supervisor agent (`financial_research_assistant`). The supervisor may call:

- **news_agent** — knowledge base + web search Lambda
- **quantitative_analysis_agent** — stock history and portfolio optimization Lambda
- **smart_summarizer_agent** — structured synthesis

The **first** `POST /research` in a process may create or reuse those agents, a knowledge base, and the research S3 bucket. Later requests only invoke. Expect **tens of seconds** of latency.

### Request

`Content-Type: application/json`

| Field | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `query` | string | yes | — | Research question, 1–8000 characters |
| `session_id` | string or `null` | no | generated UUID | Reuse to continue a conversation |
| `enable_trace` | boolean | no | `false` | Write Bedrock traces to **server logs** only |
| `trace_level` | `"outline"` \| `"core"` \| `"all"` | no | `"core"` | Trace detail when tracing is on |

### Success response (`200`)

| Field | Type | Description |
| --- | --- | --- |
| `query` | string | Echo of the request |
| `result` | string | Supervisor answer (markdown-ish text; shape varies) |
| `session_id` | string | Always present; send this on the next turn |

### Error responses

| Status | When |
| --- | --- |
| `422` | Missing `query`, empty string, or invalid types |
| `500` | AWS credentials, agent create/reuse, Lambda, or `invoke_agent` failed. `detail` is the exception message. |

### Examples

**Price action plus news**

```bash
curl -s -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is AAPL stock price doing over the last week and relate that to recent news?"
  }'
```

**Portfolio optimization (needs at least three tickers)**

```bash
curl -s -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Optimize my portfolio with AAPL, MSFT, and GOOGL. Show me the recommended allocations."
  }'
```

**Follow-up in the same session**

```bash
curl -s -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Now compare that to MSFT over the same period.",
    "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
  }'
```

**Python**

```python
import requests

base = "http://localhost:8000"
r1 = requests.post(
    f"{base}/research",
    json={"query": "Analyze Amazon's financial health based on recent earnings reports"},
    timeout=180,
)
r1.raise_for_status()
payload = r1.json()
print(payload["result"])

r2 = requests.post(
    f"{base}/research",
    json={
        "query": "What are the main risks mentioned?",
        "session_id": payload["session_id"],
    },
    timeout=180,
)
print(r2.json()["result"])
```

Use a client timeout of **at least 120–180 seconds**. The HTTP API itself does not currently enforce a deadline.

---

## Environment variables that affect the API

These are read when the assistant is first constructed (first `/research` call), not on every request.

| Variable | Default | Role |
| --- | --- | --- |
| `BEDROCK_LLM` | `us.anthropic.claude-3-5-sonnet-20241022-v2:0` | Foundation model for agents |
| `BEDROCK_EMBEDDING_MODEL` | `amazon.titan-embed-text-v2:0` | Knowledge base embeddings |
| `KB_NAME` | `financial-research-kb` | Bedrock knowledge base name |
| `KB_BUCKET_NAME` | `financial-research-data-{region}-{account}` | S3 bucket for KB documents |
| `STOCK_DATA_LAMBDA_ARN` | `arn:aws:lambda:{region}:{account}:function:stock_data_tools` | Quant tools |
| `WEB_SEARCH_LAMBDA_ARN` | `arn:aws:lambda:{region}:{account}:function:web_search` | News web search |
| `FORCE_RECREATE_AGENTS` | `false` | If `true`/`1`/`yes`, delete and recreate agents on first use |
| `ENABLE_CRYPTO_GUARDRAIL` | `false` | If true, attach the cryptocurrency deny-list guardrail |

AWS region and account come from the default credential chain (`aws configure` / instance role).

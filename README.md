# Multi Agent Equity Research Assistant

A multi-agent assistant that performs comprehensive financial research and investment analysis. The system uses a supervisor agent pattern to orchestrate specialized sub-agents for news research, fundamental analysis, and intelligent summarization.

> [!NOTE]
> **Results from these agents should not be taken as financial advice.**

## Architecture

![AWS Architecture](architecture.png)

## Documentation

- **[Features](docs/FEATURES.md)** — supervisor pattern, agents, tools, configuration, and limits
- **[API](docs/API.md)** — endpoints, request/response fields, curl/Python examples, environment variables
- Interactive OpenAPI: `/docs` (Swagger) and `/redoc` after the server is running

## Features

- **HTTP API**: FastAPI service (`POST /research`) instead of a notebook
- **Multi-agent orchestration**: Supervisor coordinates news, quantitative, and summarizer agents
- **Knowledge base**: Analyze SEC filings, earnings calls, and financial reports
- **Market tools**: Live-ish stock history and optional portfolio optimization via Lambda
- **Optional guardrails**: Cryptocurrency topic filter when enabled
- **Session continuity**: Reuse `session_id` for follow-up questions

## Prerequisites

### 1. Clone and Setup Environment

```bash
git clone https://github.com/Sanjeev-Karthick/financial-research-agent.git

cd financial-research-agent

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip3 install -r requirements.txt
```

### 2. AWS Configuration

Ensure you have AWS credentials configured with appropriate permissions:

```bash
aws configure
```

### 3. Deploy Lambda Tools

**Web Search Tool** (requires [Tavily API](https://docs.tavily.com/docs/gpt-researcher/getting-started) key):

```bash
cd src/shared/web_search
sam build && sam deploy --guided
```

**Stock Data Tool**:

```bash
cd src/shared/stock_data
sam build && sam deploy --guided
```

### 4. Enable Foundation Models

Enable the following models in Amazon Bedrock:
- Claude 3.5 Sonnet (us.anthropic.claude-3-5-sonnet-20241022-v2:0)
- Amazon Titan Embeddings (amazon.titan-embed-text-v2:0)

## Usage

From the repository root:

```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

The first `POST /research` creates or reuses Bedrock agents. Full contract: [docs/API.md](docs/API.md).

```bash
curl -s http://localhost:8000/health
curl -s -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"query": "What is AAPL stock price doing over the last week and relate that to recent news?"}'
```

OpenAPI: http://localhost:8000/docs · ReDoc: http://localhost:8000/redoc

Set `FORCE_RECREATE_AGENTS=true` to delete and recreate agents on first use. Set `ENABLE_CRYPTO_GUARDRAIL=true` to attach the cryptocurrency guardrail.

## IAM Policy

> [!IMPORTANT]
> This IAM policy is highly permissive and grants access to multiple AWS services including IAM, S3, Lambda, and Bedrock. It should only be used for prototyping in isolated, non-production environments.

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowBedrockAccess",
            "Effect": "Allow",
            "Action": ["bedrock:*"],
            "Resource": "*"
        },
        {
            "Sid": "AllowS3Access",
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:ListBucket",
                "s3:CreateBucket"
            ],
            "Resource": [
                "arn:aws:s3:::financial-research-data*",
                "arn:aws:s3:::bda-processing*/*"
            ]
        },
        {
            "Sid": "AllowOpenSearchServerless",
            "Effect": "Allow",
            "Action": ["aoss:*"],
            "Resource": "*"
        },
        {
            "Sid": "AllowIAMRoles",
            "Effect": "Allow",
            "Action": [
                "iam:GetRole",
                "iam:ListRoles",
                "iam:PassRole"
            ],
            "Resource": ["arn:aws:iam::*:role/*AmazonBedrock*"]
        },
        {
            "Sid": "AllowLambdaInvoke",
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunction",
                "lambda:GetFunction",
                "lambda:ListFunctions"
            ],
            "Resource": "arn:aws:lambda:*:*:function:*"
        }
    ]
}
```

## Project Structure

```
financial-research-agent/
├── README.md                 # This file
├── LICENSE                   # Apache 2.0 License
├── requirements.txt          # Python dependencies
├── docs/
│   ├── API.md                     # HTTP contract
│   └── FEATURES.md                # Product and agent behavior
└── src/
    ├── api/
    │   ├── main.py                # FastAPI app
    │   └── schemas.py             # Request/response models
    ├── financial_research/
    │   ├── assistant.py           # Agent setup + invoke
    │   └── config.py              # Model, bucket, and Lambda ARNs
    ├── utils/
    │   ├── bedrock_agent.py       # Agent helper classes
    │   └── knowledge_base_helper.py  # KB utilities
    └── shared/
        ├── web_search/            # Tavily web search Lambda
        └── stock_data/            # Stock data Lambda
```




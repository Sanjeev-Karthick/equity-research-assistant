# Multi Agent Equity Research Assistant

A multi-agent assistant that performs comprehensive financial research and investment analysis. The system uses a supervisor agent pattern to orchestrate specialized sub-agents for news research, fundamental analysis, and intelligent summarization.

> [!NOTE]
> **Results from these agents should not be taken as financial advice.**

## Architecture

![AWS Architecture](architecture.png)

## Features

- **Multi-Agent Orchestration**: Supervisor pattern coordinates specialized agents
- **Knowledge Base Integration**: Analyze SEC filings, earnings calls, and financial reports
- **Real-Time Data**: Fetch live stock prices and market news
- **Guardrails**: Content filtering to prevent discussion of restricted topics
- **Extensible**: Easy to add new agents or tools

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

### Run the API

From the repository root:

```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

The first request to `/research` creates (or reuses) the Bedrock supervisor and sub-agents. Subsequent requests call `financial_research_assistant.invoke(...)`.

```bash
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"query": "What is AAPL stock price doing over the last week and relate that to recent news?"}'
```

OpenAPI docs: http://localhost:8000/docs

### Example Queries

- "What's AAPL stock price doing over the last week and relate that to recent news"
- "Optimize my portfolio with AAPL, MSFT, and GOOGL"
- "Analyze Amazon's financial health based on the 2024 10K report"

Set `FORCE_RECREATE_AGENTS=true` to delete and recreate agents on startup. Set `ENABLE_CRYPTO_GUARDRAIL=true` to attach the optional cryptocurrency guardrail.

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




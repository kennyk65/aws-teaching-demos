# AWS Course Release Monitoring Agent

A serverless agent built with **AWS SAM** that monitors the [AWS Training & Certification releases page](https://releases.awstc.com/?language=EN) daily, summarises new and updated courses using **Amazon Bedrock**, and delivers a formatted alert via **Amazon SNS**.

---

## Architecture

```
EventBridge (daily cron)
        │
        ▼
  AWS Lambda (Python 3.12)
   ├── Scrapes releases.awstc.com
   ├── Loads previous state from S3
   ├── Computes diff (new / major / minor)
   ├── Summarises changes with Amazon Bedrock
   ├── Publishes alert to SNS (email)
   └── Saves updated state to S3
```

---

## Prerequisites

| Tool | Minimum version |
|---|---|
| Python | 3.12 |
| AWS SAM CLI | 1.117+ |
| AWS CLI | 2.x (configured with appropriate credentials) |
| pip | latest |

---

## Project Structure

```
.
├── template.yaml            # SAM infrastructure template
├── samconfig.toml           # SAM CLI deployment config
├── src/
│   ├── __init__.py
│   ├── handler.py           # Lambda entrypoint
│   ├── scraper.py           # HTML fetching & parsing
│   ├── diff.py              # State comparison logic
│   ├── bedrock_service.py   # Bedrock client wrapper
│   └── notifier.py          # SNS notification dispatcher
├── tests/
│   ├── fixtures/
│   │   ├── sample_releases.html
│   │   ├── state_v1.json
│   │   └── state_v2.json
│   ├── test_parser.py
│   ├── test_diff.py
│   ├── test_bedrock_formatter.py
│   └── test_lambda_handler.py
├── requirements.txt         # Lambda runtime dependencies
└── requirements-dev.txt     # Test dependencies
```

---

## Local Development Setup

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\activate           # Windows

# 2. Install dev dependencies
pip install -r requirements-dev.txt
```

---

## Running Tests

```bash
pytest tests/ -v
```

All tests mock external AWS calls (S3, SNS, Bedrock) so no live AWS credentials are needed.

---

## Building the SAM Application

```bash
sam build
```

This resolves Python dependencies and packages the Lambda code. Artifacts are placed in `.aws-sam/build/`.

---

## First-Time Deployment

```bash
sam deploy --guided
```

You will be prompted for:

| Parameter | Description | Example |
|---|---|---|
| `S3BucketName` | Existing S3 bucket for state storage | `my-monitoring-bucket` |
| `NotificationEmail` | Email to receive alerts | `you@example.com` |
| `S3ObjectPrefix` | Key prefix (optional) | `awstc-monitor/` |
| `ScheduleExpression` | EventBridge cron (optional) | `cron(0 12 * * ? *)` |
| `BedrockModelId` | Bedrock model (optional) | `anthropic.claude-3-5-sonnet-20240620-v1:0` |

After deployment, **confirm the SNS subscription** from the email AWS sends to `NotificationEmail`.

---

## Subsequent Deployments

```bash
sam deploy
```

Uses the settings saved to `samconfig.toml`.

---

## Local Invocation (optional)

Create an `env.json` file for local testing:

```json
{
  "CourseReleaseMonitorFunction": {
    "S3_BUCKET": "my-monitoring-bucket",
    "S3_KEY": "awstc-monitor/state.json",
    "SNS_TOPIC_ARN": "arn:aws:sns:us-east-1:123456789012:my-topic",
    "BEDROCK_MODEL_ID": "anthropic.claude-3-5-sonnet-20240620-v1:0"
  }
}
```

Then invoke locally (requires Docker for SAM local):

```bash
sam local invoke CourseReleaseMonitorFunction --env-vars env.json
```

---

## Tearing Down

```bash
aws cloudformation delete-stack --stack-name course-release-monitoring-agent
```

> **Note:** The S3 bucket is not deleted by the stack teardown because it is an external resource passed in as a parameter.

---

## Configuration Reference

### template.yaml Parameters

| Parameter | Default | Description |
|---|---|---|
| `S3BucketName` | *(required)* | S3 bucket for `state.json` |
| `S3ObjectPrefix` | `awstc-monitor/` | Key prefix inside the bucket |
| `NotificationEmail` | *(required)* | Alert recipient email address |
| `ScheduleExpression` | `cron(0 12 * * ? *)` | EventBridge schedule (UTC) |
| `BedrockModelId` | `anthropic.claude-3-5-sonnet-20240620-v1:0` | Bedrock model ID |

### Supported Bedrock Models

| Model ID | Notes |
|---|---|
| `anthropic.claude-3-5-sonnet-20240620-v1:0` | Recommended (default) |
| `anthropic.claude-3-haiku-20240307-v1:0` | Faster, lower cost |
| `amazon.titan-text-express-v1` | AWS-native Titan model |

---

## How It Works

1. **EventBridge** fires the Lambda on the configured schedule (default: daily at 12:00 UTC).
2. The Lambda **scrapes** `releases.awstc.com` and extracts course title, version, release type, release date, and notes for every entry.
3. It **loads** the previous catalog snapshot from `s3://<S3_BUCKET>/<S3_KEY>`.
4. On **first run** (no snapshot exists), it saves a baseline and exits without alerting.
5. On subsequent runs it **diffs** current vs. previous catalog to find new courses, major updates, and minor updates.
6. If changes are found, it invokes **Amazon Bedrock** to produce a structured Markdown summary.
7. The summary is **published to SNS**, which delivers it to the subscribed email address.
8. The updated catalog is **persisted** back to S3.

---

## Definition of Done

- [x] `sam build` compiles dependencies cleanly
- [x] `sam deploy --guided` deploys the stack without errors
- [x] EventBridge schedule triggers the Lambda daily
- [x] `pytest` test suite passes with 100% pass rate
- [x] SNS email subscription confirmed; alerts dispatched on course updates

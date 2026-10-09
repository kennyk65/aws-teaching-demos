# Requirements Specification: AWS Course Release Monitoring Agent (AWS SAM)

## 1. Executive Summary

The goal of this project is to build an automated, serverless agent hosted on AWS using the **AWS Serverless Application Model (SAM)** that daily checks the AWS Training & Certification release page (`https://releases.awstc.com/?language=EN`) for major and minor course updates. When changes are detected, the agent uses Amazon Bedrock to summarize the updates and notifies the user via an Amazon SNS email topic.

## 2. Architecture & Tech Stack

### Tech Stack

* **Framework:** AWS Serverless Application Model (AWS SAM)

* **Language:** Python 3.12

* **Compute:** AWS Lambda (`AWS::Serverless::Function`) scheduled via Amazon EventBridge

* **AI Model:** Amazon Bedrock (`anthropic.claude-3-5-sonnet-20240620-v1:0` or `amazon.titan-text-express-v1`)

* **State Storage:** Amazon S3 (JSON state file)

* **Notifications:** Amazon SNS (`AWS::SNS::Topic` and `AWS::SNS::Subscription`)

* **Testing:** `pytest` unit & integration test suite

### System Flow

```
┌───────────────────┐
│ EventBridge Cron  │ (Triggers daily at 12:00 UTC via SAM Schedule Event)
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐     Reads state.json     ┌───────────────────┐
│   AWS Lambda      │ ───────────────────────> │     Amazon S3     │
│  (Python 3.12)    │ <─────────────────────── │  (State Storage)  │
└─────────┬─────────┘    Previous catalog      └───────────────────┘
          │
          ├─> Scrapes https://releases.awstc.com/?language=EN
          ├─> Identifies new or modified course releases
          │
          ├───> [If updates found] ──> Invokes Bedrock to summarize release notes
          ├───> [If updates found] ──> Dispatches formatted summary to SNS Topic
          │
          └─> Overwrites updated catalog snapshot to S3 state.json
```

## 3. Infrastructure & CloudFormation / SAM Requirements

A single SAM Template (`template.yaml`) using Transform `AWS::Serverless-2016-10-31` must provision all required resources.

### Input Parameters

1. `S3BucketName` (String, Required): Name of the existing or target S3 bucket used for state storage.

2. `S3ObjectPrefix` (String, Default: `aws/course-release-monitor/`): Object key prefix for storing the `state.json` file.

3. `NotificationEmail` (String, Default: `kenkrueger65@gmail.com`): Email address to receive release alert notifications.

4. `ScheduleExpression` (String, Default: `cron(0 20 * * ? *)`): EventBridge schedule expression (default: daily at 8:00 PM UTC).

5. `BedrockModelId` (String, Default: `us.amazon.nova-lite-v1:0`): Amazon Bedrock model ID for summarization. Supports foundation models and cross-region inference profiles (e.g. `us.amazon.nova-*`).

6. `NotifyChangesOnly` (String, Default: `"true"`, AllowedValues: `"true"` | `"false"`): Controls notification behaviour when no course changes are detected.
   - `"true"` (default): Silent run — no email sent when the catalog is unchanged.
   - `"false"`: Always send an email on every run. When there are no changes the email subject reads `[AWS Course Updates] No Changes Detected - YYYY-MM-DD`, confirming the pipeline is operating normally. Useful for smoke-testing the end-to-end flow.

### SAM Resources to Provision

* **Amazon SNS Topic & Email Subscription:**

  * `AWS::SNS::Topic` for release alerts.

  * `AWS::SNS::Subscription` tied to parameter `NotificationEmail`.

* **AWS SAM Lambda Function (`AWS::Serverless::Function`):**

  * Runtime: `python3.12`

  * Handler: `src/handler.lambda_handler`

  * Memory: 512 MB

  * Timeout: 180 seconds

  * Policies (SAM Policy Templates or IAM Role inline statements):

    * `S3CrudPolicy` scoped strictly to `arn:aws:s3:::<S3BucketName>/<S3ObjectPrefix>*`

    * `SNSPublishMessagePolicy` for the created SNS Topic

    * `bedrock:InvokeModel` IAM statement for the target Bedrock model

  * Environment variables:

    * `S3_BUCKET`: Ref to `S3BucketName`

    * `S3_KEY`: `${S3ObjectPrefix}state.json`

    * `SNS_TOPIC_ARN`: Ref to SNS Topic

    * `BEDROCK_MODEL_ID`: Ref to `BedrockModelId`

    * `NOTIFY_CHANGES_ONLY`: Ref to `NotifyChangesOnly` (default `"true"`)

  * Events:

    * Schedule Event (`Type: Schedule`) tied to `ScheduleExpression`.

## 4. Lambda Application Requirements

### 4.1 Scraping & Data Extraction

* Fetch HTML from `https://releases.awstc.com/?language=EN` using standard HTTP libraries (`urllib3` or `requests` / `httpx`) and `BeautifulSoup4`.

* Extract structured data per course entry:

  * Course Title

  * Version / Release Type (Major / Minor)

  * Release Date

  * Release Notes / Highlights link or description text.

### 4.2 State Comparison & Diff Logic

* Retrieve previous state snapshot from `s3://<S3_BUCKET>/<S3_KEY>`.

* If `state.json` does not exist (first run):

  * Save current catalog snapshot to S3.

  * Exit cleanly without alerting or send an initial baseline setup notice.

* If `state.json` exists:

  * Compare current release entries against stored entries.

  * Identify **New Courses**, **Major Version Updates**, and **Minor Version Updates**.

### 4.3 Bedrock Summarization Engine

* If changes are detected, construct a prompt containing only the modified/new release items.

* Invoke Bedrock API via `boto3.client('bedrock-runtime')`.

* Request output format:

  * **Executive Summary**: Brief 2-3 sentence overview.

  * **Major Changes**: Bullet points with course names and key updates.

  * **Minor Changes**: Summary list of version updates.

### 4.4 Notification Dispatch

* When changes are detected, publish a formatted Markdown email payload to `SNS_TOPIC_ARN`.

  * Subject line format: `[AWS Course Updates] New Releases Detected - YYYY-MM-DD`

* When no changes are detected, behaviour is controlled by `NOTIFY_CHANGES_ONLY`:

  * `"true"` (default): No notification is sent.

  * `"false"`: A confirmation email is published with subject `[AWS Course Updates] No Changes Detected - YYYY-MM-DD`, confirming the pipeline ran successfully.

## 5. Testing Requirements (`pytest`)

The codebase must include a robust `pytest` suite in a `/tests` directory.

### Test Coverage Focus Area

1. **HTML Parser Unit Tests (`test_parser.py`):**

   * Test parsing against mock HTML fixtures representing `releases.awstc.com`.

   * Verify correct handling of empty pages, missing fields, or changed DOM structures.

2. **Diff Engine Tests (`test_diff.py`):**

   * Test comparing two catalog states:

     * Identical states (returns zero changes).

     * Added courses.

     * Updated version numbers for existing courses.

3. **Bedrock Payload Formatting Tests (`test_bedrock_formatter.py`):**

   * Verify prompt construction matches expected input structure.

   * Mock Bedrock API responses using `unittest.mock` / `botocore.stub.Stubber`.

4. **S3 & SNS Integration Handler Tests (`test_lambda_handler.py`):**

   * Mock `boto3` calls for S3 (`get_object`, `put_object`) and SNS (`publish`).

   * Test complete Lambda handler execution path end-to-end with mocked external calls.

## 6. Project Directory Structure

```
.
├── template.yaml            # AWS SAM Infrastructure template
├── samconfig.toml           # SAM CLI deployment configurations
├── src/
│   ├── __init__.py
│   ├── handler.py           # Lambda entrypoint
│   ├── scraper.py           # HTML fetching & parsing module
│   ├── diff.py              # State comparison logic
│   ├── bedrock_service.py   # Amazon Bedrock client wrapper
│   └── notifier.py          # SNS notification dispatcher
├── tests/
│   ├── __init__.py
│   ├── fixtures/
│   │   ├── sample_releases.html
│   │   ├── state_v1.json
│   │   └── state_v2.json
│   ├── test_parser.py
│   ├── test_diff.py
│   ├── test_bedrock_formatter.py
│   └── test_lambda_handler.py
├── requirements.txt         # Lambda dependencies (beautifulsoup4, requests, etc.)
├── requirements-dev.txt     # Test dependencies (pytest, boto3-stubs, pytest-mock)
└── README.md                # SAM build, local testing, and deployment guide
```

## 7. Definition of Done

1. `sam build` compiles dependencies and Lambda code cleanly.

2. `sam deploy --guided` deploys the stack to AWS without errors.

3. EventBridge schedule triggers the Lambda function automatically.

4. `pytest` test suite executes with 100% pass rate.

5. SNS subscription email is confirmed, and alert notifications are dispatched upon course updates.
# Requirements Specification: AWS Course Release Monitoring Agent (AWS SAM)

## 1. Executive Summary

The goal of this project is to build an automated, serverless agent hosted on AWS using the **AWS Serverless Application Model (SAM)** and **Bedrock** that periodically (daily) checks the AWS Training & Certification releases page (`https://releases.awstc.com/?course=FAV&language=EN`) (More specifically, the API used by that page: (`https://releases.awstc.com/backend/courses.list`)) for major and minor course updates.

The agent filters the retrieved the current catalog /revision list, keeping only the courses whose latest release date falls within a configurable recent window (lookback days). That abbreviated list is processed by a foundational model to produce a list of only those courses having major or minor releases in the time period - patch releases will NOT be reported.  This filtered list is then send to a second model focused only on formatting the notification email body. The result is delivered via an Amazon SNS email topic.

## 2. Architecture & Tech Stack

### Tech Stack

* **Framework:** AWS Serverless Application Model (AWS SAM)

* **Language:** Python 3.12

* **Compute:** AWS Lambda (`AWS::Serverless::Function`) scheduled via Amazon EventBridge

* **AI Model:** Amazon Bedrock (default: `us.amazon.nova-lite-v1:0`, but parameter driven) — two calls: (1) identify major/minor releases from the recent-release list, excluding patch-only releases; (2) format the email body

* **Notifications:** Amazon SNS (`AWS::SNS::Topic` and `AWS::SNS::Subscription`)

* **Testing:** `pytest` unit & integration test suite

### System Flow

```
┌───────────────────┐

│ EventBridge Cron  │ (Triggers daily at 20:00 UTC via SAM Schedule Event)
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│   AWS Lambda      │  
│  (Python 3.12)    │
└─────────┬─────────┘
          │
          ├─> Calls releases.awstc.com JSON API (EN language filter) to get current catalog
          │
          ├─> CODE: keep only courses whose latest release date is within the
          │        last LOOKBACK_DAYS days (abbreviated "recent releases" list)
          │
          ├─> MODEL CALL #1: send the recent-releases list to Bedrock; it returns
          │        ONLY the major and minor releases as JSON (patch-only excluded)
          │
          ├───> [If major/minor releases found] ──> MODEL CALL #2: Bedrock formats
          │        the plain-text email body
          ├───> [If none found] ──────────────────> Optionally prepare "no changes" message
          │
          └─> Send notification via SNS (when indicated)
```

## 3. Infrastructure & CloudFormation / SAM Requirements

A single SAM Template (`template.yaml`) must provision all required resources.

### Input Parameters

1. `NotificationEmail` (String, Default: `kenkrueger65@gmail.com`): Email address to receive release alert notifications.

2. `ScheduleExpression` (String, Default: `cron(0 20 * * ? *)`): EventBridge schedule expression (default: daily at 8:00 PM UTC).

3. `LookbackDays` (Number, Default: `7`): Size of the recency window, in days. Courses whose latest release date is older than this many days before the current run are filtered out (in code) before anything is sent to the model. This value is exposed to the Lambda as the `LOOKBACK_DAYS` environment variable.

4. `BedrockModelId` (String, Default: `us.amazon.nova-lite-v1:0`): Amazon Bedrock model ID used for both model calls. Supports foundation models and cross-region inference profiles (e.g. `us.amazon.nova-*`).

5. `NotifyChangesOnly` (String, Default: `"true"`, AllowedValues: `"true"` | `"false"`): Controls notification behaviour when no major/minor releases are found in the window.
   - `"true"` (default): Silent run — email sent only if major/minor releases are found.
   - `"false"`: Always send an email on every run, whether releases are found or not.
   
### SAM Resources to Provision

* **Amazon SNS Topic & Email Subscription:**

  * `AWS::SNS::Topic` for release alerts.

  * `AWS::SNS::Subscription` tied to parameter `NotificationEmail`.

* **AWS SAM Lambda Function (`AWS::Serverless::Function`):**

  * Runtime: `python3.12`

  * Handler: `src/handler.lambda_handler`

  * Memory: 512 MB

  * Timeout: 180 seconds

  * Policies:

    * `SNSPublishMessagePolicy` for the created SNS Topic

    * `bedrock:InvokeModel` IAM statement covering foundation models and cross-region inference profiles

    * (No S3 policy — the agent is stateless.)

  * Environment variables:

    * `SNS_TOPIC_ARN`: Ref to SNS Topic

    * `LOOKBACK_DAYS`: Ref to `LookbackDays`

    * `BEDROCK_MODEL_ID`: Ref to `BedrockModelId`

    * `NOTIFY_CHANGES_ONLY`: Ref to `NotifyChangesOnly` (default `"true"`)

  * Events:

    * Schedule Event (`Type: Schedule`) tied to `ScheduleExpression`.

## 4. Lambda Application Requirements

### 4.1 Data Retrieval

* The AWS T&C releases page (`https://releases.awstc.com`) is a JavaScript SPA. Course data is fetched directly from the underlying JSON API endpoint:

  ```
  GET https://releases.awstc.com/backend/courses.list?language=EN
  ```

* Filter results to `language = "EN"` only.

* Filter results by recency:  Include only the entries "released" greater than the Read the cutoff date, where the cutoff date = (current UTC date) − `LOOKBACK_DAYS` days.

* Exclude unnecessary versions: for each course entry, include only the latest two versions, maximum.  This allows us to determine the previous release and the current release.

* The result of this filtering is the "filtered list".  Send this to the model for processing.

* If this list is empty, see the instructions below if no changes are detected.

### 4.2 Release detection (Model Call #1)

* Send the recent-releases list to Bedrock and ask it to return **only the major
  and minor releases**.

* For each course, the model classifies the latest release by comparing the
  current `version` against `previous_version`. Versions have the form
  `MAJOR.MINOR.PATCH` (e.g. `3.11.7`):

  * **MAJOR release** — the MAJOR (first) component changed (e.g. `4.2.1` → `5.0.0`). Report.
  * **MINOR release** — the MAJOR is unchanged but the MINOR (second) component changed (e.g. `3.10.8` → `3.11.0`). Report.
  * **PATCH release** — only the PATCH (third) component changed (e.g. `7.0.4` → `7.0.5`). **MUST NOT be reported.**
  * If `previous_version` is absent (a brand-new course with a single version), treat it as a reportable release.

* **Patch releases MUST be excluded.** This is the single most important rule of
  the detection step. The prompt must state this explicitly, give worked
  examples (including a patch case such as `7.0.4` → `7.0.5` that must be
  omitted), and instruct the model to re-verify before answering.

* The model returns JSON only. The response is an object containing, for each
  reported (major or minor) release:

  * course name
  * current version number
  * previous version number
  * release date
  * latest revision note

* If the resulting JSON is empty, indicating no major / minor releases in the time period,  see the instructions below if no changes are detected. 

### 4.3 Email Formatting (Model Call #2)

* When major/minor releases are detected, the JSON result is
  passed to Amazon Bedrock, which generates the plain-text email body.

* The prompt instructs the model to produce the following structure exactly:

  ```
  ━━━ AWS Training & Certification — Course Releases (date) ━━━

  The following courses had a major or minor release in the last X days:

  ▶ RECENT RELEASES
  ─────────────
    Course Name                         v4.2.1 → v5.0.0
    Released: YYYY-MM-DD
    <latest revision note>

    Course Name                         v3.10.0 → v3.11.7
    Released: YYYY-MM-DD
    <latest revision note>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sent by the AWS Course Release Monitoring Agent.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ```


### 4.4 Notification Dispatch

* When major/minor releases are found, publish the formatted email to `SNS_TOPIC_ARN`.

  * Subject line format: `[AWS Course Updates] New Releases Detected - YYYY-MM-DD`

* When no major/minor releases are found (either the recency window was empty or
  the model reported only patch/no releases), behaviour is controlled by
  `NOTIFY_CHANGES_ONLY`:

  * `"true"` (default): No notification is sent.

  * `"false"`: A plain-text confirmation email is published with subject `[AWS Course Updates] No Changes Detected - YYYY-MM-DD`, confirming the pipeline ran successfully. Useful for smoke-testing the end-to-end flow and confirming that the agent is still working.


## 5. Testing Requirements (`pytest`)

The codebase must include a robust `pytest` suite in a `/tests` directory.

### Test Coverage Focus Areas

1. **API Retrieval & Filtering Tests (`test_parser.py`):**

   * Test against a mock JSON API fixture (`sample_api_response.json`).

   * Verify `language = "EN"` filtering.

   * Verify recency filtering: only entries whose latest release date is on or after the cutoff (`current UTC date − LOOKBACK_DAYS`) are kept; older entries are discarded; a release exactly on the cutoff is kept; an empty result when nothing falls in the window.

   * Verify version trimming: each retained course keeps at most its latest two versions (current + immediately previous), so the previous and current release can be compared.

   * Verify the "filtered list" entries carry: name, current version, previous version (absent when the course has only one version), release date, and latest revision note.

   * Verify date normalisation and error handling (malformed/empty API response).

2. **Detection Parsing Tests (`test_diff.py`):**

   * The model's detection JSON (Model Call #1 output) is parsed/normalised into the canonical structure.

   * Each reported release carries: name, current version, previous version, release date, and latest revision note.

   * Tolerant extraction (markdown fences / surrounding prose) and fail-safe to "no releases" on malformed or empty output.

3. **Email Formatter Tests (`test_formatter.py`):**

   * `wrap_body` adds the header (title + date) and the "last X days" intro line, and the footer, around the Bedrock-generated body.

   * The output contains no counts/totals line and no modality (ILT) labels.

   * No-changes email format verified.

4. **Bedrock Prompt Tests (`test_bedrock_formatter.py`):**

   * **Detection prompt (Model Call #1):** verify it supplies the filtered list (including each course's current and previous version) and instructs the model to classify by comparing current vs. previous version and return major/minor releases only, excluding patch releases — stated explicitly with worked examples (e.g. `7.0.4 → 7.0.5` is patch-only and MUST be omitted). Verify a brand-new course (no previous version) is treated as reportable.

   * **Formatting prompt (Model Call #2):** verify it instructs a single `▶ RECENT RELEASES` section, renders each release as a version transition (`vX → vY`), and omits counts, executive summary, and modality labels.

   * Mock Bedrock API responses (Claude, Titan, Converse) using `unittest.mock`.

5. **Live Detection Integration Test (`test_detection_integration.py`, opt-in):**

   * Opt-in via `RUN_BEDROCK_INTEGRATION=1`; skipped by default (marker `integration`).

   * Sends a filtered-list fixture (`recent_releases.json`) containing a major, a minor, and a patch release to the real model.

   * Asserts the output is valid JSON, reports exactly the major and minor releases, excludes the patch release, and that each reported entry carries the required fields (name, current version, previous version, release date, latest revision note).

6. **Lambda Handler Tests (`test_lambda_handler.py`):**

   * Mock the catalog fetch, both Bedrock calls, and SNS (`publish`); no S3 (the agent is stateless).

   * Empty filtered list → no Model Call #1; no notification when `NOTIFY_CHANGES_ONLY=true`; confirmation email when `NOTIFY_CHANGES_ONLY=false`.

   * Model Call #1 returns no major/minor releases → no notification when `NOTIFY_CHANGES_ONLY=true`; confirmation email when `NOTIFY_CHANGES_ONLY=false`.

   * Major/minor releases found → both model calls invoked; notification sent with correct subject and the Bedrock-generated body wrapped by header/footer.

## 6. Project Directory Structure

```
.
├── template.yaml            # AWS SAM Infrastructure template
├── samconfig.toml           # SAM CLI deployment configurations
├── src/
│   ├── __init__.py
│   ├── handler.py           # Lambda entrypoint (stateless)
│   ├── scraper.py           # JSON API fetch + language/recency/version-trim filtering
│   ├── diff.py              # Parses/normalises Model Call #1 detection JSON
│   ├── bedrock_service.py   # Amazon Bedrock client wrapper (both model calls)
│   ├── formatter.py         # Plain-text header/footer and no-changes email
│   └── notifier.py          # SNS notification dispatcher
├── tests/
│   ├── __init__.py
│   ├── fixtures/
│   │   ├── sample_api_response.json
│   │   └── recent_releases.json   # major + minor + patch sample for detection
│   ├── test_parser.py
│   ├── test_diff.py
│   ├── test_formatter.py
│   ├── test_bedrock_formatter.py
│   ├── test_detection_integration.py
│   └── test_lambda_handler.py
├── docs/
│   └── email_mockup.txt     # Sample formatted email output
├── pytest.ini               # Registers the `integration` marker; excludes it by default
├── requirements.txt         # Lambda dependencies (requests, etc.)
├── requirements-dev.txt     # Test dependencies (pytest, pytest-mock)
└── README.md                # SAM build, local testing, and deployment guide
```

## 7. Definition of Done

1. `sam build` compiles dependencies and Lambda code cleanly.

2. `sam deploy` deploys the stack to AWS without errors.

3. EventBridge schedule triggers the Lambda function automatically.

4. `pytest` test suite executes with 100% pass rate.

5. SNS subscription email is confirmed, and alert notifications are dispatched when major/minor releases occur within the `LOOKBACK_DAYS` window (patch releases never trigger a notification).

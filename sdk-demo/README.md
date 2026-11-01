# AWS S3 Demo: Console, CLI, and SDK

This folder demonstrates the same task in 3 ways: list all S3 buckets.

## Prerequisites

- An AWS account
- IAM permissions for `s3:ListAllMyBuckets`
- AWS credentials configured locally (`aws configure` or SSO)
- Python 3.8+

## 1) AWS Management Console Demo

1. Sign in to the AWS Console.
2. Open **S3**.
3. Go to **General purpose buckets**.
4. Show that the bucket list in the UI matches your account.


## 2) AWS CLI Demo

Run:

```bash
aws s3 ls
```

Alternative (JSON output):

```bash
aws s3api list-buckets --query 'Buckets[].Name' --output table
```


## 3) AWS SDK (Python/Boto3) Demo

Install dependency:

```bash
pip install boto3
```

Run script:

```bash
python3 list_s3_buckets.py
```

Script file: [list_s3_buckets.py](list_s3_buckets.py)


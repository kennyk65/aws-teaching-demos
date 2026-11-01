#!/usr/bin/env python3

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError


def main():
    s3 = boto3.client("s3")

    try:
        response = s3.list_buckets()
        buckets = response.get("Buckets", [])

        if not buckets:
            print("No S3 buckets found.")
            return

        for bucket in buckets:
            print(bucket["Name"])
    except NoCredentialsError:
        print("AWS credentials not found. Configure credentials and try again.")
    except (BotoCoreError, ClientError) as err:
        print(f"Failed to list S3 buckets: {err}")


if __name__ == "__main__":
    main()

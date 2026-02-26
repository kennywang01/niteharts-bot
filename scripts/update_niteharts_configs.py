import json
import sys
import boto3
from pathlib import Path

SQS_QUEUE_URL = "https://sqs.us-east-2.amazonaws.com/701154485405/niteharts-configs"
ROLE_ARN = "arn:aws:iam::701154485405:role/kennywangrole"
CONFIGS_PATH = Path(__file__).parent.parent / "form_data" / "niteharts_configs.json"


def get_sqs_client():
    sts = boto3.client("sts")
    credentials = sts.assume_role(
        RoleArn=ROLE_ARN,
        RoleSessionName="update-niteharts-configs",
    )["Credentials"]
    return boto3.client(
        "sqs",
        region_name="us-east-2",
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )


def upload_configs():
    with open(CONFIGS_PATH) as f:
        configs = json.load(f)

    sqs = get_sqs_client()

    # Purge existing messages first so we start fresh
    print("Purging existing messages from queue...")
    sqs.purge_queue(QueueUrl=SQS_QUEUE_URL)

    for i, config in enumerate(configs, start=1):
        sqs.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(config),
        )
        print(f"Enqueued config {i}")

    print(f"\nDone. Enqueued {len(configs)} configs to SQS.")


if __name__ == "__main__":
    upload_configs()

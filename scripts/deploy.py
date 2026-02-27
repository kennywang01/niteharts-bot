import argparse
import base64
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path

import boto3
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
USER_DATA_TEMPLATE = ROOT / "scripts" / "ec2_user_data.bash"
DOCKERFILE = ROOT / "scripts" / "ecr" / "Dockerfile"
CONFIGS_PATH = ROOT / "form_data" / "niteharts_configs.json"

REQUIRED_VARS = [
    "AWS_REGION",
    "AWS_ACCOUNT_ID",
    "ECR_REPO",
    "ASG_NAME",
    "CAPACITY",
    "LAUNCH_TEMPLATE_NAME",
    "SQS_QUEUE_URL",
    "ROLE_ARN",
    "TWOCAPTCHA_API_KEY",
    "EVENT_URL",
    "KEY_PAIR_NAME",
    "INSTANCE_PROFILE_ARN",
    "SECURITY_GROUP_ID",
    "S3_BUCKET",
]


def load_env():
    load_dotenv(ROOT / ".env")
    missing = [k for k in REQUIRED_VARS if not os.getenv(k)]
    if missing:
        print(f"ERROR: Missing required env vars: {', '.join(missing)}")
        sys.exit(1)


def get_assumed_role_client(service: str):
    sts = boto3.client("sts", region_name=os.environ["AWS_REGION"])
    credentials = sts.assume_role(
        RoleArn=os.environ["ROLE_ARN"],
        RoleSessionName="niteharts-deploy",
    )["Credentials"]
    return boto3.client(
        service,
        region_name=os.environ["AWS_REGION"],
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )


def step1_build_push():
    print("\n[1/4] Building and pushing Docker image to ECR...")
    region = os.environ["AWS_REGION"]
    account_id = os.environ["AWS_ACCOUNT_ID"]
    ecr_repo = os.environ["ECR_REPO"]
    registry = f"{account_id}.dkr.ecr.{region}.amazonaws.com"
    ecr_uri = f"{registry}/{ecr_repo}:latest"

    # Authenticate with ECR using boto3 (avoids bash pipe)
    ecr = boto3.client("ecr", region_name=region)
    token = ecr.get_authorization_token()["authorizationData"][0]["authorizationToken"]
    username, password = base64.b64decode(token).decode().split(":", 1)
    subprocess.run(
        ["docker", "login", "--username", username, "--password-stdin", registry],
        input=password,
        text=True,
        check=True,
    )

    subprocess.run(
        ["docker", "build", "--no-cache", "-f", str(DOCKERFILE), "-t", "niteharts", str(ROOT)],
        check=True,
    )
    subprocess.run(["docker", "tag", "niteharts:latest", ecr_uri], check=True)
    subprocess.run(["docker", "push", ecr_uri], check=True)
    print("      Done.")


def step2_user_data():
    print("\n[2/4] Uploading user data to launch template...")

    logs = get_assumed_role_client("logs")
    try:
        logs.create_log_group(logGroupName="/niteharts")
        print("      Created CloudWatch log group /niteharts.")
    except logs.exceptions.ResourceAlreadyExistsException:
        print("      CloudWatch log group /niteharts already exists.")

    deploy_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
    print(f"      Deploy ID: {deploy_id}")

    template = USER_DATA_TEMPLATE.read_text()
    rendered = template.replace("@@TWOCAPTCHA_API_KEY@@", os.environ["TWOCAPTCHA_API_KEY"])
    rendered = rendered.replace("@@EVENT_URL@@", os.environ["EVENT_URL"])
    rendered = rendered.replace("@@DEPLOY_ID@@", deploy_id)
    rendered = rendered.replace("@@S3_BUCKET@@", os.environ["S3_BUCKET"])
    user_data_b64 = base64.b64encode(rendered.encode()).decode()

    ec2 = get_assumed_role_client("ec2")
    asg = get_assumed_role_client("autoscaling")

    new_version = ec2.create_launch_template_version(
        LaunchTemplateName=os.environ["LAUNCH_TEMPLATE_NAME"],
        SourceVersion="$Latest",
        LaunchTemplateData={
                "UserData": user_data_b64,
                "InstanceType": "t3a.small",
                "ImageId": "ami-09256c524fab91d36",
                "KeyName": os.environ["KEY_PAIR_NAME"],
                "IamInstanceProfile": {"Arn": os.environ["INSTANCE_PROFILE_ARN"]},
                "SecurityGroupIds": [os.environ["SECURITY_GROUP_ID"]],
            },
    )["LaunchTemplateVersion"]["VersionNumber"]
    print(f"      Created launch template version {new_version}.")

    capacity = int(os.environ["CAPACITY"])
    asg.update_auto_scaling_group(
        AutoScalingGroupName=os.environ["ASG_NAME"],
        LaunchTemplate={
            "LaunchTemplateName": os.environ["LAUNCH_TEMPLATE_NAME"],
            "Version": "$Latest",
        },
        MinSize=0,
        MaxSize=capacity,
        DesiredCapacity=capacity,
    )
    print(f"      ASG updated to use $Latest, capacity={capacity}.")


def step3_sqs_configs():
    print("\n[3/4] Uploading configs to SQS queue...")

    with open(CONFIGS_PATH) as f:
        configs = json.load(f)

    sqs = get_assumed_role_client("sqs")
    queue_url = os.environ["SQS_QUEUE_URL"]

    print("      Purging existing messages...")
    sqs.purge_queue(QueueUrl=queue_url)

    for i, config in enumerate(configs, start=1):
        sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(config))
        print(f"      Enqueued config {i}/{len(configs)}")

    print(f"      Done. {len(configs)} configs in queue.")


def step4_refresh_asg():
    print("\n[4/4] Starting ASG instance refresh...")

    asg = get_assumed_role_client("autoscaling")
    response = asg.start_instance_refresh(
        AutoScalingGroupName=os.environ["ASG_NAME"],
        Strategy="Rolling",
        Preferences={"MinHealthyPercentage": 0},
    )
    refresh_id = response["InstanceRefreshId"]
    print(f"      Instance refresh started: {refresh_id}")
    print(f"      Monitor at: AWS Console → EC2 → Auto Scaling Groups → {os.environ['ASG_NAME']} → Instance Refresh")


def main():
    parser = argparse.ArgumentParser(description="Niteharts deploy runbook")
    parser.add_argument("--docker-image", action="store_true", help="Build and push Docker image to ECR")
    parser.add_argument("--launch-template", action="store_true", help="Upload user data to launch template")
    parser.add_argument("--refill-queue", action="store_true", help="Purge and refill SQS queue with configs")
    parser.add_argument("--refresh-instances", action="store_true", help="Start ASG instance refresh")
    args = parser.parse_args()

    load_env()

    # If no flags given, run all steps
    run_all = not any([args.docker_image, args.launch_template, args.refill_queue, args.refresh_instances])

    if run_all or args.docker_image:
        step1_build_push()
    if run_all or args.launch_template:
        step2_user_data()
    if run_all or args.refill_queue:
        step3_sqs_configs()
    if run_all or args.refresh_instances:
        step4_refresh_asg()

    print("\nDone.")


if __name__ == "__main__":
    main()

# AWS Architecture

## Overview

N EC2 instances run in parallel (configured via `CAPACITY` env var), each purchasing a ticket under a unique buyer identity. Instances are managed by an Auto Scaling Group and configured via a launch template. Each instance pulls its own form inputs from an SQS queue on startup and runs the niteharts Docker container.

---

## Components

### EC2 Auto Scaling Group — `niteharts-autoscaling`
- **Region:** `us-east-2`
- **Instances:** Controlled by `CAPACITY` env var (min = desired = max = `CAPACITY`)
- **AMI:** `ami-09256c524fab91d36` (Amazon Linux 2023)
- **Instance Type:** `c7a.medium`
- **Launch Template:** updated by `scripts/deploy.py --launch-template` on each deploy

### Launch Template — `niteharts`
- **Key Pair:** `nitehart-key` (SSH via `nitehart-key.pem`)
- **Security Group:** `sg-0834be85e4c56ced3` (inbound port 22 open)
- **IAM Instance Profile:** `arn:aws:iam::701154485405:instance-profile/niteharts-ec2-role`
- **User Data Script:** `scripts/ec2_user_data.bash` — rendered with secrets from `.env` and uploaded by `deploy.py`

### ECR Repository — `niteharts/niteharts-docker`
- **URI:** `701154485405.dkr.ecr.us-east-2.amazonaws.com/niteharts/niteharts-docker:latest`
- Stores the niteharts Docker image
- Built and pushed by `scripts/deploy.py --docker-image`

### SQS Queue — `niteharts-configs`
- **URL:** `https://sqs.us-east-2.amazonaws.com/701154485405/niteharts-configs`
- **Type:** Standard queue
- Contains one message per instance, each with a unique `form_inputs.json` payload
- Populated by `scripts/deploy.py --refill-queue` before instances launch
- Each instance atomically claims and deletes exactly one message on startup

---

## IAM

### EC2 Instance Role — `niteharts-ec2-role`
Attached to all instances via the launch template instance profile.

Required permissions:
| Permission | Resource |
|---|---|
| `sqs:ReceiveMessage` | `arn:aws:sqs:us-east-2:701154485405:niteharts-configs` |
| `sqs:DeleteMessage` | `arn:aws:sqs:us-east-2:701154485405:niteharts-configs` |
| `sqs:GetQueueAttributes` | `arn:aws:sqs:us-east-2:701154485405:niteharts-configs` |
| `ecr:GetAuthorizationToken` | `*` |
| `ecr:BatchGetImage` | `arn:aws:ecr:us-east-2:701154485405:repository/niteharts/niteharts-docker` |
| `ecr:GetDownloadUrlForLayer` | `arn:aws:ecr:us-east-2:701154485405:repository/niteharts/niteharts-docker` |

### IAM User — `kennywang`
Used locally to run `scripts/deploy.py`.

Required permissions:
| Permission | Resource |
|---|---|
| `sts:AssumeRole` | `arn:aws:iam::701154485405:role/kennywangrole` |

### IAM Role — `kennywangrole`
Assumed by the `kennywang` user for all AWS operations in `deploy.py`.

Trust policy allows: `arn:aws:iam::701154485405:user/kennywang`

Required permissions:
| Permission | Resource |
|---|---|
| `sqs:SendMessage` | `arn:aws:sqs:us-east-2:701154485405:niteharts-configs` |
| `sqs:PurgeQueue` | `arn:aws:sqs:us-east-2:701154485405:niteharts-configs` |
| `ec2:CreateLaunchTemplateVersion` | `arn:aws:ec2:us-east-2:701154485405:launch-template/*` |
| `ec2:DescribeLaunchTemplates` | `*` |
| `autoscaling:UpdateAutoScalingGroup` | `arn:aws:autoscaling:us-east-2:701154485405:autoScalingGroup:*:autoScalingGroupName/niteharts-autoscaling` |
| `autoscaling:StartInstanceRefresh` | same |

---

## Deployment Flow

```
Local Machine                            AWS
───────────────────────────────────────────────────────────────────
python scripts/deploy.py

  --docker-image
    ECR auth via boto3
    docker build + tag + push       ──►  ECR: niteharts-docker:latest

  --launch-template
    Render ec2_user_data.bash
    (fill @@TWOCAPTCHA_API_KEY@@,
     @@EVENT_URL@@ from .env)
    create_launch_template_version  ──►  Launch Template: new version
    update_auto_scaling_group       ──►  ASG uses $Latest, capacity=N

  --refill-queue
    Assume kennywangrole via STS
    purge_queue + send_message×N    ──►  SQS: N messages (one per buyer)

  --refresh-instances
    start_instance_refresh          ──►  ASG terminates + relaunches N instances

                                         Each instance (user data):
                                         a. dnf install docker
                                         b. Pull 1 message from SQS
                                         c. Write to form_inputs.json
                                         d. Delete message from SQS
                                         e. Authenticate with ECR
                                         f. docker pull niteharts-docker
                                         g. docker run (with form_inputs.json mounted)
```

---

## Docker Container Runtime

Each container receives:

| Input | Method |
|---|---|
| `TWOCAPTCHA_API_KEY` | Environment variable (injected by user data script) |
| `EVENT_URL` | Environment variable (injected by user data script) |
| `form_inputs.json` | Volume mount from host EC2 (`/home/ec2-user/form_inputs.json` → `/app/form_inputs.json`) |

---

## Local Scripts

| Script | Purpose |
|---|---|
| `scripts/deploy.py` | Full deploy runbook — builds image, updates launch template, fills queue, refreshes ASG |
| `scripts/ec2_user_data.bash` | Runs on each EC2 at boot — claims SQS config, pulls image, runs container. Contains `@@TWOCAPTCHA_API_KEY@@` and `@@EVENT_URL@@` placeholders substituted by `deploy.py` |
| `scripts/update_niteharts_configs.py` | Standalone script to enqueue buyer configs into SQS (superseded by `deploy.py --refill-queue`) |
| `scripts/test_config.py` | Verify env vars and form inputs are valid before running |

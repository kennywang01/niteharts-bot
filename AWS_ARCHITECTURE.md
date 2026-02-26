# AWS Architecture

## Overview

6 EC2 instances run in parallel, each purchasing a ticket under a unique buyer identity. Instances are managed by an Auto Scaling Group and configured via a launch template. Each instance pulls its own form inputs from an SQS queue on startup and runs the niteharts Docker container.

---

## Components

### EC2 Auto Scaling Group — `niteharts-autoscaling`
- **Region:** `us-east-2`
- **Instances:** 6 (min = desired = max = 6, scaling disabled)
- **AMI:** Amazon Linux 2023 (Docker pre-installed)
- **Launch Template:** defines instance type, security group, IAM role, key pair, and user data script

### Launch Template
- **Key Pair:** `nitehart-key.pem` (used for SSH access)
- **Security Group:** inbound port 22 (SSH) open
- **IAM Instance Profile:** attached role with permissions to pull from SQS and ECR
- **User Data Script:** `scripts/ec2_user_data.bash` — runs on first boot

### ECR Repository — `niteharts/niteharts-docker`
- **URI:** `701154485405.dkr.ecr.us-east-2.amazonaws.com/niteharts/niteharts-docker:latest`
- Stores the niteharts Docker image
- Built locally via `build_and_push.bash` and pushed before instances launch

### SQS Queue — `niteharts-configs`
- **URL:** `https://sqs.us-east-2.amazonaws.com/701154485405/niteharts-configs`
- **Type:** Standard queue
- Contains one message per instance, each with a unique `form_inputs.json` payload
- Populated locally before instances launch via `scripts/update_niteharts_configs.py`
- Each instance atomically claims and deletes exactly one message on startup

### S3 Bucket — `niteharts-configs` *(legacy, replaced by SQS)*
- Originally used to store `form_inputs_N.json` files per instance
- Replaced by SQS to avoid instance ID mapping issues across ASG refreshes

---

## IAM

### EC2 Instance Role
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
Used locally to run `update_niteharts_configs.py`.

Required permissions:
| Permission | Resource |
|---|---|
| `sts:AssumeRole` | `arn:aws:iam::701154485405:role/kennywangrole` |

### IAM Role — `kennywangrole`
Assumed by the `kennywang` user to interact with SQS locally.

Trust policy allows: `arn:aws:iam::701154485405:user/kennywang`

Required permissions:
| Permission | Resource |
|---|---|
| `sqs:SendMessage` | `arn:aws:sqs:us-east-2:701154485405:niteharts-configs` |
| `sqs:PurgeQueue` | `arn:aws:sqs:us-east-2:701154485405:niteharts-configs` |

---

## Deployment Flow

```
Local Machine                          AWS
─────────────────────────────────────────────────────────────────
1. docker build + push
   build_and_push.bash          ──►  ECR: niteharts-docker:latest

2. Enqueue configs
   update_niteharts_configs.py  ──►  SQS: niteharts-configs
   (assumes kennywangrole)            (6 messages, one per buyer)

3. Launch / refresh ASG         ──►  6 EC2 instances boot

                                      Each instance (user data):
                                      a. Pull 1 message from SQS
                                      b. Write to form_inputs.json
                                      c. Delete message from SQS
                                      d. Authenticate with ECR
                                      e. docker pull niteharts-docker
                                      f. docker run (with form_inputs.json mounted)
```

---

## Docker Container Runtime

Each container receives:

| Input | Method |
|---|---|
| `TWOCAPTCHA_API_KEY` | Environment variable |
| `EVENT_URL` | Environment variable |
| `form_inputs.json` | Volume mount from host EC2 (`/home/ec2-user/form_inputs.json` → `/app/form_inputs.json`) |

---

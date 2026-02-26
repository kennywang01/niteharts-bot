# niteharts

Automated ticket purchasing bot for frontgatetickets.com.

## Project Structure

```
niteharts-bot/
├── niteharts/              # importable package
│   ├── __init__.py
│   ├── __main__.py
│   ├── buy_ticket.py
│   ├── captcha_solver.py
│   └── form_data.py
├── scripts/
│   └── test_config.py      # verify env vars and form inputs
├── data/
│   └── form_inputs.json    # example form inputs file
├── pyproject.toml
└── README.md
```

## Configuration

### Environment Variables

| Variable | Description |
|---|---|
| `TWOCAPTCHA_API_KEY` | Your 2captcha API key |
| `FORM_DATA_PATH` | Absolute path to your `form_inputs.json` (optional, defaults to `./form_inputs.json` in CWD) |

### Form Inputs

Create a `form_inputs.json` file using `data/form_inputs.json` as a template:

```json
{
    "email": "you@example.com",
    "password": "yourpassword",
    "ticket_quantity": "1",
    "first_name": "John",
    "last_name": "Doe",
    "credit_card_number": "4111111111111111",
    "cvv": "123",
    "exp_month": "12",
    "exp_year": "28",
    "phone": "2015551234",
    "st_address": "123 Main St",
    "city": "Philadelphia",
    "state": "PA",
    "zip": "19103"
}
```

## Building the Wheel

Install hatch if you don't have it:

```bash
pip install hatch
```

Build the wheel:

```bash
hatch build
```

This produces a `.whl` file in the `dist/` directory.

## Installation

Install from the built wheel:

```bash
pip install dist/niteharts-0.1.0-py3-none-any.whl
```

After installing, also install Playwright's browser binaries:

```bash
playwright install chromium
```

## Usage

### As a CLI command

```bash
niteharts "https://projectglow.frontgatetickets.com/event/abc123"
```

### As a Python module

```bash
python -m niteharts "https://projectglow.frontgatetickets.com/event/abc123"
```

### As an imported package

```python
from niteharts import buy_ticket

buy_ticket("https://projectglow.frontgatetickets.com/event/abc123")
```

### In Docker

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install the wheel
COPY niteharts-0.1.0-py3-none-any.whl .
RUN pip install niteharts-0.1.0-py3-none-any.whl

# Install Playwright browser
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy your form inputs
COPY form_inputs.json .

ENV TWOCAPTCHA_API_KEY=your_api_key_here

CMD ["python", "-m", "niteharts", "https://projectglow.frontgatetickets.com/event/abc123"]
```

Screenshots are saved to `./screenshots/buy_ticket.png` relative to wherever the process runs.

## Deployment

Automates building the Docker image, updating the EC2 launch template, loading the SQS queue, and refreshing all ASG instances in one command.

### Setup (first time)

```bash
pip install -r scripts/requirements.txt
```

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Required `.env` keys:

| Key | Description |
|---|---|
| `AWS_REGION` | e.g. `us-east-2` |
| `AWS_ACCOUNT_ID` | Your 12-digit AWS account ID |
| `ECR_REPO` | e.g. `niteharts/niteharts-docker` |
| `ASG_NAME` | Auto Scaling Group name |
| `CAPACITY` | Number of EC2 instances (sets min = desired = max) |
| `LAUNCH_TEMPLATE_NAME` | EC2 launch template name |
| `SQS_QUEUE_URL` | Full SQS queue URL |
| `ROLE_ARN` | IAM role to assume for AWS ops |
| `TWOCAPTCHA_API_KEY` | 2captcha API key |
| `EVENT_URL` | Target event URL |
| `KEY_PAIR_NAME` | EC2 key pair name for SSH access |
| `INSTANCE_PROFILE_ARN` | ARN of the EC2 IAM instance profile |
| `SECURITY_GROUP_ID` | Security group ID to attach to instances |

### Commands

**Run all 4 steps in sequence:**
```bash
python scripts/deploy.py
```

**Run individual steps:**
```bash
python scripts/deploy.py --docker-image       # Build & push Docker image to ECR
python scripts/deploy.py --launch-template    # Upload user data to launch template
python scripts/deploy.py --refill-queue       # Purge & reload SQS with buyer configs
python scripts/deploy.py --refresh-instances  # Trigger ASG rolling instance refresh
```

**Combine steps:**
```bash
python scripts/deploy.py --refill-queue --refresh-instances
python scripts/deploy.py --launch-template --refresh-instances
```

### What each step does

| Flag | What it does |
|---|---|
| `--docker-image` | Authenticates with ECR, builds from `scripts/ecr/Dockerfile`, tags and pushes to ECR |
| `--launch-template` | Renders `scripts/ec2_user_data.bash` with secrets from `.env`, creates a new launch template version, updates ASG to use `$Latest` |
| `--refill-queue` | Purges the SQS queue and enqueues one message per entry in `form_data/niteharts_configs.json` |
| `--refresh-instances` | Starts a rolling ASG instance refresh with `MinHealthyPercentage=0` (replaces all instances simultaneously) |

### Before running

1. Update `form_data/niteharts_configs.json` with one buyer config object per instance
2. Ensure AWS credentials are configured locally (`~/.aws/credentials` or env vars)
3. Ensure Docker is running locally (required for `--docker-image`)

---

## Verifying Setup

Run the config test script to confirm your environment variables and form inputs are valid:

```bash
python scripts/test_config.py
```

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

## Verifying Setup

Run the config test script to confirm your environment variables and form inputs are valid:

```bash
python scripts/test_config.py
```

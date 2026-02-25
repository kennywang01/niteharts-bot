import json
import os
from dataclasses import dataclass
from pathlib import Path

REQUIRED_FIELDS = [
    "email",
    "password",
    "ticket_quantity",
    "first_name",
    "last_name",
    "credit_card_number",
    "cvv",
    "exp_month",
    "exp_year",
    "phone",
    "st_address",
    "city",
    "state",
    "zip",
]


@dataclass
class FormData:
    email: str
    password: str
    ticket_quantity: str
    first_name: str
    last_name: str
    credit_card_number: str
    cvv: str
    exp_month: str
    exp_year: str
    phone: str
    st_address: str
    city: str
    state: str
    zip: str

    def __post_init__(self):
        missing = [f for f in REQUIRED_FIELDS if not getattr(self, f, "").strip()]
        if missing:
            raise ValueError(f"Missing or empty required fields: {missing}")


def load_form_data(path: Path = None) -> FormData:
    if path is None:
        env_path = os.getenv("FORM_DATA_PATH")
        path = Path(env_path) if env_path else Path.cwd() / "form_inputs.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Form inputs file not found: {path}\n"
            "Set the FORM_DATA_PATH env var or place form_inputs.json in the working directory."
        )
    with open(path) as f:
        data = json.load(f)
    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        raise ValueError(f"Missing fields in {path}: {missing}")
    return FormData(**{field: data[field] for field in REQUIRED_FIELDS})

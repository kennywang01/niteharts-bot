import os
from niteharts.form_data import load_form_data, REQUIRED_FIELDS


def test_api_key():
    api_key = os.getenv("TWOCAPTCHA_API_KEY")
    assert api_key, "FAIL: TWOCAPTCHA_API_KEY env var is not set"
    assert len(api_key) > 0, "FAIL: TWOCAPTCHA_API_KEY is empty"
    print(f"PASS: TWOCAPTCHA_API_KEY is set ({api_key[:4]}...{api_key[-4:]})")


def test_form_data():
    form = load_form_data()
    for field in REQUIRED_FIELDS:
        value = getattr(form, field)
        assert value and value.strip(), f"FAIL: field '{field}' is empty"
        print(f"PASS: {field} = {value!r}")


if __name__ == "__main__":
    print("--- Testing API key ---")
    test_api_key()

    print("\n--- Testing form data ---")
    test_form_data()

    print("\nAll checks passed.")

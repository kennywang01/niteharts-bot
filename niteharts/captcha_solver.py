import os
from twocaptcha import TwoCaptcha


class CaptchaSolver:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("TWOCAPTCHA_API_KEY")
        if not self.api_key:
            raise ValueError("2captcha API key must be provided or set in TWOCAPTCHA_API_KEY env var")
        self.solver = TwoCaptcha(self.api_key)

    def solve_recaptcha(self, sitekey: str, url: str) -> str:
        result = self.solver.solve_captcha(site_key=sitekey, page_url=url)
        return result

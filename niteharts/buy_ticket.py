import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

from .captcha_solver import CaptchaSolver
from .form_data import load_form_data


def _wait_for_page_change(page, check_interval_seconds: float = 1.0, max_wait_minutes: float = 60.0) -> None:
    baseline_html = page.content()
    deadline = time.time() + max_wait_minutes * 60.0

    while True:
        if time.time() > deadline:
            raise TimeoutError("Timed out waiting for page to change on Front Gate Tickets.")

        page.wait_for_timeout(int(check_interval_seconds * 1000))
        page.reload()
        page.wait_for_load_state("networkidle")

        current_html = page.content()
        if current_html != baseline_html:
            return


def buy_ticket(event_url: str) -> None:
    form = load_form_data()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-cache",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
        )
        page = context.new_page()
        page.goto(event_url)

        # keep refreshing until the event page changes, then continue immediately
        _wait_for_page_change(page)

        # log into frontgatetickets
        page.get_by_role("menuitem", name="Sign In").click()
        page.get_by_role("textbox", name="Email required").click()
        page.get_by_role("textbox", name="Email required").fill(form.email)
        page.get_by_role("textbox", name="Password required").click()
        page.get_by_role("textbox", name="Password required").fill(form.password)
        page.get_by_role("button", name="Log In").click()

        # select ticket (max 4 tickets)
        page.get_by_role("link", name="Select Tickets").first.click()
        for i in range(int(form.ticket_quantity)):
            if i >= 3:
                break
            page.get_by_role("button", name="Increase Quantity").first.click()
        page.get_by_role("button", name="Add to Cart").click()

        # Wait for reCAPTCHA modal to appear
        page.wait_for_selector("#google_captcha", state="visible")

        # Extract sitekey from the rendered grecaptcha widget
        sitekey = page.evaluate("""
            () => {
                function findRecaptchaClients() {
                    if (typeof (___grecaptcha_cfg) !== 'undefined') {
                        return Object.entries(___grecaptcha_cfg.clients).map(([cid, client]) => {
                            const data = { id: cid, version: cid >= 10000 ? 'V3' : 'V2' };
                            const objects = Object.entries(client).filter(([_, value]) => value && typeof value === 'object');

                            objects.forEach(([toplevelKey, toplevel]) => {
                                const found = Object.entries(toplevel).find(([_, value]) => (
                                    value && typeof value === 'object' && 'sitekey' in value && 'size' in value
                                ));

                                if (typeof toplevel === 'object' && toplevel instanceof HTMLElement && toplevel['tagName'] === 'DIV') {
                                    data.pageurl = toplevel.baseURI;
                                }

                                if (found) {
                                    const [sublevelKey, sublevel] = found;
                                    data.sitekey = sublevel.sitekey;
                                    const callbackKey = data.version === 'V2' ? 'callback' : 'promise-callback';
                                    const callback = sublevel[callbackKey];
                                    if (!callback) {
                                        data.callback = null;
                                        data.function = null;
                                    } else {
                                        data.function = callback;
                                        const keys = [cid, toplevelKey, sublevelKey, callbackKey].map((key) => `['${key}']`).join('');
                                        data.callback = `___grecaptcha_cfg.clients${keys}`;
                                    }
                                }
                            });
                            return data;
                        });
                    }
                    return [];
                }

                const clients = findRecaptchaClients();
                return clients.length > 0 ? clients[0].sitekey : null;
            }
        """)

        # Solve the captcha and inject the token
        solver = CaptchaSolver(os.getenv("TWOCAPTCHA_API_KEY"))
        token = solver.solve_recaptcha(sitekey=sitekey, url=page.url)

        page.evaluate(f"""
            (token) => {{
                const textarea = document.getElementById('g-recaptcha-response');
                if (textarea) {{
                    textarea.style.display = 'block';
                    textarea.value = token;
                    textarea.dispatchEvent(new Event('change'));
                }}
                if (typeof captchaValidated === 'function') captchaValidated();
            }}
        """, token)

        page.locator("#div-btn-modal-submit").click()

        # checkout
        page.get_by_role("button", name="Checkout").click()

        # Will Call
        # TODO: Are name fields required? May already be autofilled once you log in...
        page.get_by_role("textbox", name="Will Call First Name *").fill(form.first_name)
        page.get_by_role("textbox", name="Will Call Last Name * required").fill(form.last_name)
        page.get_by_role("button", name="Next").click()

        # Select payment method
        page.get_by_role("button", name="Credit Card").click()
        page.get_by_role("textbox", name="First Name * required").fill(form.first_name)
        page.get_by_role("textbox", name="Last Name * required").fill(form.last_name)
        page.locator("iframe[name=\"braintree-hosted-field-number\"]").content_frame.get_by_role("textbox", name="Credit Card Number").click()
        page.locator("iframe[name=\"braintree-hosted-field-number\"]").content_frame.get_by_role("textbox", name="Credit Card Number").fill(form.credit_card_number)
        page.locator("iframe[name=\"braintree-hosted-field-cvv\"]").content_frame.get_by_role("textbox", name="CVV").fill(form.cvv)
        page.locator("iframe[name=\"braintree-hosted-field-expirationMonth\"]").content_frame.get_by_role("textbox", name="Expiration Month").fill(form.exp_month)
        page.locator("iframe[name=\"braintree-hosted-field-expirationYear\"]").content_frame.get_by_role("textbox", name="Expiration Year").fill(form.exp_year)
        page.get_by_role("textbox", name="(201) 555-").fill(form.phone)
        page.get_by_role("textbox", name="Address * required").fill(form.st_address)
        page.get_by_role("textbox", name="City * required").fill(form.city)
        page.get_by_label("State *").select_option(form.state)
        page.get_by_role("textbox", name="Zip/Postal Code *").fill(form.zip)
        page.get_by_role("button", name="Next").click()

        # ticket insurance
        page.get_by_role("radio", name="No, don't protect my $").check()
        page.get_by_role("button", name="Next").click()

        # terms and conditions
        page.get_by_role("textbox", name="Email address for your").fill(form.email)
        page.get_by_role("checkbox", name="I have read and agree to Front Gate's current Terms of Use and Terms of Sale,").check()
        page.get_by_role("checkbox", name="I have read and agree to the").check()

        # purchase tickets
        page.get_by_role("button", name="Purchase Tickets").click()

        # verify credit card

        # screenshot end state
        screenshot_dir = Path.cwd() / "screenshots"
        screenshot_dir.mkdir(exist_ok=True)
        page.screenshot(path=str(screenshot_dir / "buy_ticket.png"))

        context.close()
        browser.close()

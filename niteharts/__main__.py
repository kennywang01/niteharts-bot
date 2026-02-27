import argparse
import logging
import sys
from dotenv import load_dotenv
from . import __version__
from .buy_ticket import buy_ticket


def main():
    parser = argparse.ArgumentParser(description=f"niteharts {__version__}")
    parser.add_argument("event_url", nargs="?", help="Event URL to purchase tickets from")
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode (no visible window)")
    parser.add_argument("--debug", action="store_true", help="On failure, pause the browser for inspection instead of closing")
    args = parser.parse_args()

    if args.debug:
        # Local run: pretty-print logs to stdout and load credentials from .env
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
            stream=sys.stdout,
        )
        load_dotenv(".env")
    else:
        # EC2: emit plain logs to stdout so Docker/CloudWatch captures them
        logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    if args.version:
        print(f"niteharts {__version__}")
        sys.exit(0)

    if not args.event_url:
        parser.print_help()
        sys.exit(1)

    buy_ticket(args.event_url, headless=args.headless, debug=args.debug)


if __name__ == "__main__":
    main()

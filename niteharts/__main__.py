import sys
from . import __version__
from .buy_ticket import buy_ticket


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "--version":
        print(f"niteharts {__version__}")
        sys.exit(0)
    if len(sys.argv) != 2:
        print(f"niteharts {__version__}")
        print("Usage: python -m niteharts <event_url>")
        sys.exit(1)
    buy_ticket(sys.argv[1])


if __name__ == "__main__":
    main()

import sys
from .buy_ticket import buy_ticket


def main():
    if len(sys.argv) != 2:
        print("Usage: python -m niteharts <event_url>")
        sys.exit(1)
    buy_ticket(sys.argv[1])


if __name__ == "__main__":
    main()

FROM python:3.14.3

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /build
RUN git clone https://github.com/kennywang01/niteharts-bot.git .

RUN pip install hatchling build
RUN python -m build --no-isolation --wheel

WORKDIR /app
RUN pip install /build/dist/niteharts-*.whl

RUN playwright install --with-deps chromium

ENV TWOCAPTCHA_API_KEY="ee243aca55a6e389ead2c3bca217da85"
ENV EVENT_URL="https://nitehartsfestival.frontgatetickets.com/"

CMD ["python", "-m", "niteharts", "--version"]

# Running main
# CMD ["sh", "-c", "python -m niteharts \"$EVENT_URL\""]

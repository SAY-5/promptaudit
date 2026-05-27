FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY batteries ./batteries
COPY evalsets ./evalsets
COPY baselines ./baselines

RUN pip install --no-cache-dir -e .

ENTRYPOINT ["promptaudit"]
CMD ["--help"]

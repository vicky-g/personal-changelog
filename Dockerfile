FROM python:3.11-slim

WORKDIR /app

# Install dependencies as a separate layer so they're cached between rebuilds
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"

COPY . .
RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]

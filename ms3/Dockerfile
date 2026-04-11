FROM python:3.11-slim

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml ./
RUN pip install --no-cache-dir uv && uv sync --no-dev

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

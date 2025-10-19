# Build stage
FROM python:3.12-slim AS builder

WORKDIR /build

# Install Poetry
RUN pip install poetry==1.8.3

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Install dependencies (no dev deps)
RUN poetry config virtualenvs.in-project true \
    && poetry install --without dev --no-interaction --no-ansi

# Final stage
FROM python:3.12-slim AS runtime

# Create non-root user
RUN groupadd -r phantom && useradd -r -g phantom -u 42100 phantom

WORKDIR /app

# Copy virtual environment
COPY --from=builder /build/.venv /app/.venv

# Copy application code
COPY phantom/ ./phantom/

# Set environment
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Create workspace directory
RUN mkdir -p /workspace && chown phantom:phantom /workspace

# Switch to non-root user
USER phantom

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s \
    CMD python -c "import httpx; httpx.get('http://localhost:3000/api/v1/health/')" || exit 1

CMD ["python", "-m", "phantom.main", "serve", "--host", "0.0.0.0", "--port", "3000"]

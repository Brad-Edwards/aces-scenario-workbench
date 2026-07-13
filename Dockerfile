FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install the workbench with the production server and PostgreSQL drivers.
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir ".[server,postgres]" \
    && aces-workbench manage collectstatic --noinput \
    && useradd --create-home --uid 10001 appuser \
    && chown -R appuser /app

USER appuser
EXPOSE 8000

# Apply migrations, then serve with gunicorn. Provide DATABASE_URL and
# ACES_WORKBENCH_SECRET_KEY via the environment.
CMD ["sh", "-c", "aces-workbench migrate --noinput && gunicorn aces_scenario_workbench.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-3}"]

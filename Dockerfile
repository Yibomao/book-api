FROM python:3.12-slim

# Don't write .pyc files, and don't buffer stdout — otherwise container logs
# arrive in chunks long after the events they describe.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies are copied and installed before the source so that editing a
# route doesn't invalidate the cached pip layer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as an unprivileged user: a process that is compromised should not also
# be root inside the container.
RUN useradd --create-home --uid 1000 appuser && chown -R appuser /app
USER appuser

ENV PORT=8000
EXPOSE 8000

# Apply the schema, then hand off to gunicorn. The Flask development server is
# single-threaded and explicitly not meant for production.
CMD ["sh", "-c", "python init_db.py && exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --access-logfile - app:app"]

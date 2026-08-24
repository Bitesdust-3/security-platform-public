FROM python:3.12-slim
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
ENV HTTP_PROXY=${HTTP_PROXY} HTTPS_PROXY=${HTTPS_PROXY} NO_PROXY=${NO_PROXY}
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/backend
ENV XDG_CACHE_HOME=/tmp/app-cache
WORKDIR /app
RUN apt-get -o Acquire::http::Timeout=30 -o Acquire::Retries=2 update && apt-get install -y --no-install-recommends nmap libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info fonts-noto-cjk && rm -rf /var/lib/apt/lists/*
RUN addgroup --system app && adduser --system --ingroup app app
RUN mkdir -p /tmp/app-cache && chown -R app:app /tmp/app-cache
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY backend /app/backend
RUN chown -R app:app /app
RUN chmod +x /app/backend/entrypoint.sh
USER app
EXPOSE 8000
CMD ["/app/backend/entrypoint.sh"]

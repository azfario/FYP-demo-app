FROM python:3.11-slim-bookworm
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 APP_ROOT=/app TORCH_THREADS=4
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN python -m pip install --no-cache-dir torch==2.7.1 torchvision==0.22.1 --index-url ${TORCH_INDEX_URL}
RUN python -m pip install --no-cache-dir -r backend/requirements.txt \
    && useradd --create-home --uid 10001 appuser
RUN apt-get update \
    && apt-get install --no-install-recommends -y libexpat1 libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY backend /app/backend
COPY models /app/models
COPY sample /app/sample
COPY ["hand test", "/app/hand test"]
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=45s --retries=5 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-server-header"]

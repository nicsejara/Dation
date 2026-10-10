FROM python:3.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080
WORKDIR /app/backend
COPY backend/requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir --require-hashes -r requirements.txt && python -m pip check
COPY --chown=65532:65532 backend/app ./app
COPY --chown=65532:65532 backend/*.py ./
COPY --chown=65532:65532 sample_data/v3 /app/sample_data/v3
USER 65532:65532
EXPOSE 8080
CMD ["sh", "-c", "exec python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]

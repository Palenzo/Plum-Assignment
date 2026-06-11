FROM python:3.12-slim

# Tesseract is needed to OCR uploaded document images/PDFs.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install the app (and its dependencies). Source is copied first so the
# package — including app/data/policy_terms.json — is built into the image.
COPY pyproject.toml ./
COPY app ./app
COPY eval.py ./
RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

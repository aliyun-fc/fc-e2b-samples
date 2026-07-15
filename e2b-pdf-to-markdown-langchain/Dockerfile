# Builder-mode source image for the E2B document-conversion template.
# Template.build injects the E2B runtime; do not add LangChain or agent code here.
FROM python:3.13-slim-bookworm

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git \
    poppler-utils \
    tesseract-ocr tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

COPY template-requirements.txt /tmp/template-requirements.txt
RUN pip install --no-cache-dir -r /tmp/template-requirements.txt \
    && python -c "import fitz, pdfplumber, pypdf, pytesseract; print('document conversion dependencies OK')"

WORKDIR /home/user

# Builder-mode source image for the E2B document-conversion template.
# Template.build injects the E2B runtime; do not add LangChain or agent code here.
FROM python:3.13-slim-bookworm

LABEL org.opencontainers.image.source="https://github.com/aliyun-fc/fc-e2b-samples"

USER root

# Use Aliyun's Debian mirrors to reduce package download time in China.
# Overseas builds: comment out the following RUN instruction to retain the base image's Debian sources.
RUN find /etc/apt -type f \( -name 'sources.list' -o -name '*.sources' \) -exec sed -i \
    -e 's|http://deb.debian.org/debian-security|https://mirrors.aliyun.com/debian-security|g' \
    -e 's|http://deb.debian.org/debian|https://mirrors.aliyun.com/debian|g' \
    {} +

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git \
    poppler-utils \
    tesseract-ocr tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

COPY template-requirements.txt /tmp/template-requirements.txt
# Use Aliyun's PyPI mirror to reduce Python package download time in China.
# Overseas builds: comment out the following ENV instruction to use pip's default index.
ENV PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

RUN pip install --no-cache-dir \
    -r /tmp/template-requirements.txt \
    && python -c "import fitz, pdfplumber, pypdf, pytesseract; print('document conversion dependencies OK')"

WORKDIR /home/user

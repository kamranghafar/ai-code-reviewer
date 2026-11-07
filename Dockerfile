FROM python:3.12-slim

LABEL maintainer="Kamran Ghaffar <kamranghafar@gmail.com>"
LABEL org.opencontainers.image.source="https://github.com/kamranghafar/ai-code-reviewer"
LABEL org.opencontainers.image.description="AI-powered code reviewer GitHub Action"

RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src/ /app/src/

ENTRYPOINT ["python", "/app/src/main.py"]

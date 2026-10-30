FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY config ./config
COPY data ./data
COPY scripts ./scripts
COPY docs ./docs
COPY mkdocs.yml ./

RUN uv pip install --system -e ".[docs]" \
 && python scripts/generate_corpus.py \
 && mkdocs build -d site

EXPOSE 8000
ENV MOCK_MY_AI_HOST=0.0.0.0
ENV MOCK_MY_AI_PORT=8000

CMD ["uvicorn", "mock_my_ai.main:app", "--host", "0.0.0.0", "--port", "8000"]
